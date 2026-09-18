"""
Módulo de Transformação - Camadas Prata (Silver) e Ouro (Gold)
Responsável pela limpeza, agregação diária e engenharia de features meteorológicas.
"""

import os
import io
import pandas as pd
import numpy as np

def transform_bronze_to_silver(bronze_dir: str = "data/bronze", output_path: str = "data/silver/fact_weather_daily.parquet"):
    """
    Camada Prata:
    - Pula cabeçalhos com metadados do INMET (linhas 1 a 8).
    - Substitui valores ausentes sentinela (-9999) por NaN.
    - Converte formatos numéricos brasileiros (vírgula para ponto).
    - Agrega dados horários em diários por estação e município.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    daily_records = []

    for fname in os.listdir(bronze_dir):
        if not fname.endswith(".csv"):
            continue
        filepath = os.path.join(bronze_dir, fname)
        with open(filepath, "r", encoding="latin1") as f:
            lines = f.read().splitlines()

        # Extrai metadados do cabeçalho
        station_meta = {}
        for l in lines[:8]:
            parts = l.split(";")
            if len(parts) >= 2:
                station_meta[parts[0].strip().replace(":", "")] = parts[1].strip()

        code = station_meta.get("CODIGO (WMO)", fname.split("_")[0])
        municipio = station_meta.get("ESTACAO", "N/A")
        lat = float(station_meta.get("LATITUDE", "-31.0").replace(",", "."))
        lon = float(station_meta.get("LONGITUDE", "-52.0").replace(",", "."))
        alt = float(station_meta.get("ALTITUDE", "50.0").replace(",", "."))

        # Carrega dados horários
        df_raw = pd.read_csv(io.StringIO("\n".join(lines[8:])), sep=";", decimal=",", na_values=["-9999", "-9999.0", ""])
        df_raw = df_raw.loc[:, ~df_raw.columns.str.contains("^Unnamed")]

        col_date = [c for c in df_raw.columns if "Data" in c][0]
        col_precip = [c for c in df_raw.columns if "PRECIPITA" in c.upper()][0]
        col_press = [c for c in df_raw.columns if "NIVEL DA ESTACAO" in c.upper() or "PRESSAO ATMOSFERICA" in c.upper()][0]
        col_rad = [c for c in df_raw.columns if "RADIACAO" in c.upper()][0]
        col_temp = [c for c in df_raw.columns if "BULBO SECO" in c.upper() or "TEMPERATURA DO AR" in c.upper()][0]
        col_temp_max = [c for c in df_raw.columns if "MÁXIMA" in c.upper() or "MAXIMA" in c.upper()][0]
        col_temp_min = [c for c in df_raw.columns if "MÍNIMA" in c.upper() or "MINIMA" in c.upper()][0]
        col_umid = [c for c in df_raw.columns if "UMIDADE RELATIVA" in c.upper()][0]
        col_wind = [c for c in df_raw.columns if "VENTO, VELOCIDADE" in c.upper()][0]

        df_raw["date"] = pd.to_datetime(df_raw[col_date].str.replace("/", "-"))

        daily = df_raw.groupby("date").agg(
            precip_mm=(col_precip, "sum"),
            temp_min=(col_temp_min, "min"),
            temp_max=(col_temp_max, "max"),
            temp_avg=(col_temp, "mean"),
            humidity_avg=(col_umid, "mean"),
            pressure_avg=(col_press, "mean"),
            wind_speed=(col_wind, "mean"),
            solar_radiation=(col_rad, lambda x: round(x.sum() / 1000.0, 2))
        ).reset_index()

        daily["station_id"] = code
        daily["municipio"] = municipio
        daily["lat"] = lat
        daily["lon"] = lon
        daily["altitude"] = alt

        daily_records.append(daily)

    df_silver = pd.concat(daily_records, ignore_index=True).sort_values(["station_id", "date"]).reset_index(drop=True)
    df_silver.to_parquet(output_path, index=False)
    # Também gera espelho CSV para interoperabilidade
    df_silver.to_csv(output_path.replace(".parquet", ".csv"), index=False, sep=";", decimal=",")
    print(f"🥈 [Silver Layer] Tabela Fato Diária criada com sucesso: {output_path} ({len(df_silver)} registros)")
    return df_silver

def transform_silver_to_gold(silver_path: str = "data/silver/fact_weather_daily.parquet", output_path: str = "data/gold/features_rain_d1.parquet"):
    """
    Camada Ouro:
    - Calcula o alvo D+1: rain_tomorrow = 1 se precip_t1 >= 1.0mm senão 0.
    - Calcula lags temporais (D-1, D-2).
    - Janelas acumuladas de precipitação (3d, 7d).
    - Variação barométrica de 24h (pressure_change_24h).
    - Sequência de dias secos contínuos (dry_days).
    - Codificação trigonométrica da sazonalidade (sen/cos do dia do ano).
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    if silver_path.endswith(".parquet"):
        df_silver = pd.read_parquet(silver_path)
    else:
        df_silver = pd.read_csv(silver_path, sep=";", decimal=",")
        df_silver["date"] = pd.to_datetime(df_silver["date"])

    dfs = []
    for station_id, group in df_silver.groupby("station_id"):
        g = group.sort_values("date").copy()

        g["precip_tomorrow"] = g["precip_mm"].shift(-1)
        g["rain_tomorrow"] = (g["precip_tomorrow"] >= 1.0).astype(int)

        g["precip_lag_1d"] = g["precip_mm"].shift(1)
        g["precip_lag_2d"] = g["precip_mm"].shift(2)

        g["precip_sum_3d"] = g["precip_mm"].rolling(3).sum()
        g["precip_sum_7d"] = g["precip_mm"].rolling(7).sum()
        g["rain_days_7d"] = (g["precip_mm"] >= 1.0).rolling(7).sum()

        g["pressure_change_24h"] = g["pressure_avg"] - g["pressure_avg"].shift(1)

        is_dry = (g["precip_mm"] < 1.0).astype(int)
        dry_cumsum = is_dry.cumsum()
        reset_mask = dry_cumsum.where(is_dry == 0).ffill().fillna(0)
        g["dry_days"] = dry_cumsum - reset_mask

        g["temp_avg_3d"] = g["temp_avg"].rolling(3).mean()
        g["humidity_avg_3d"] = g["humidity_avg"].rolling(3).mean()

        doy = g["date"].dt.dayofyear
        g["day_of_year_sin"] = np.sin(2 * np.pi * doy / 365.25)
        g["day_of_year_cos"] = np.cos(2 * np.pi * doy / 365.25)

        dfs.append(g)

    df_gold = pd.concat(dfs, ignore_index=True)
    df_gold = df_gold.dropna(subset=["rain_tomorrow", "precip_lag_2d", "precip_sum_7d", "pressure_change_24h"]).reset_index(drop=True)
    df_gold.to_parquet(output_path, index=False)
    df_gold.to_csv(output_path.replace(".parquet", ".csv"), index=False, sep=";", decimal=",")
    print(f"🥇 [Gold Layer] Tabela de Features Ouro criada com sucesso: {output_path} ({len(df_gold)} registros)")
    return df_gold

"""
Módulo de Ingestão - Camada Bronze
Responsável por coletar dados brutos do INMET ou APIs públicas de tempo
(ex: Open-Meteo) para as estações da Região Intermediária de Pelotas/Bagé (IBGE 4302).
"""

import os
import io
import zipfile
import requests
import pandas as pd
from datetime import datetime

STATIONS_4302 = {
    'A887': {'codigo_ibge': 4314407, 'municipio': 'Pelotas / Capao do Leao', 'lat': -31.7447, 'lon': -52.3783},
    'A827': {'codigo_ibge': 4301602, 'municipio': 'Bage', 'lat': -31.3283, 'lon': -54.1069},
    'A802': {'codigo_ibge': 4315602, 'municipio': 'Rio Grande', 'lat': -32.0353, 'lon': -52.0986},
    'A899': {'codigo_ibge': 4317301, 'municipio': 'Santa Vitoria do Palmar', 'lat': -33.5189, 'lon': -53.3686},
    'A838': {'codigo_ibge': 4303509, 'municipio': 'Camaqua', 'lat': -30.8517, 'lon': -51.8117},
    'A836': {'codigo_ibge': 4311007, 'municipio': 'Jaguarao', 'lat': -32.5661, 'lon': -53.3769},
    'A811': {'codigo_ibge': 4304507, 'municipio': 'Cangucu', 'lat': -31.3956, 'lon': -52.6756},
    'B823': {'codigo_ibge': 4314506, 'municipio': 'Pinheiro Machado', 'lat': -31.5794, 'lon': -53.3811},
    'B828': {'codigo_ibge': 4300034, 'municipio': 'Acegua', 'lat': -31.8667, 'lon': -54.1667},
    'B826': {'codigo_ibge': 4309605, 'municipio': 'Herval', 'lat': -32.0239, 'lon': -53.3942}
}

def ingest_from_inmet_zip(zip_path: str, output_dir: str = "data/bronze"):
    """
    Lê o pacote anual de dados brutos horários do INMET e extrai os CSVs
    das estações pertencentes ao recorte territorial para a camada Bronze.
    """
    os.makedirs(output_dir, exist_ok=True)
    zf = zipfile.ZipFile(zip_path)
    extracted = []

    for code, meta in STATIONS_4302.items():
        matched = [f for f in zf.namelist() if f'_{code}_' in f]
        if matched:
            fname = matched[0]
            target_path = os.path.join(output_dir, f"{code}_{meta['municipio'].replace(' ', '_').replace('/', '_')}_raw.csv")
            with zf.open(fname) as source, open(target_path, "wb") as target:
                target.write(source.read())
            extracted.append(target_path)
            print(f"📦 [Bronze Ingestion] Extraído: {code} ({meta['municipio']}) -> {target_path}")

    return extracted

def ingest_from_open_meteo(station_code: str, lat: float, lon: float, start_date: str, end_date: str, output_dir: str = "data/bronze"):
    """
    Fonte pública alternativa: Open-Meteo Historical Weather API.
    Útil para atualização contínua e pipelines em cloud.
    """
    os.makedirs(output_dir, exist_ok=True)
    url = f"https://archive-api.open-meteo.com/v1/archive?latitude={lat}&longitude={lon}&start_date={start_date}&end_date={end_date}&hourly=temperature_2m,relative_humidity_2m,precipitation,surface_pressure,wind_speed_10m,direct_normal_irradiance&timezone=America/Sao_Paulo"
    
    resp = requests.get(url, timeout=20)
    if resp.status_code == 200:
        data = resp.json()
        df = pd.DataFrame(data['hourly'])
        df['station_id'] = station_code
        target_path = os.path.join(output_dir, f"open_meteo_{station_code}_raw.csv")
        df.to_csv(target_path, index=False)
        print(f"🌐 [Open-Meteo API] Ingestão concluída para {station_code} -> {target_path}")
        return target_path
    else:
        print(f"❌ Erro na requisição Open-Meteo ({resp.status_code}): {resp.text}")
        return None

if __name__ == "__main__":
    zip_candidate = "2026.zip"
    if not os.path.exists(zip_candidate):
        zip_candidate = os.path.expanduser("~/Downloads/2026.zip")
    if os.path.exists(zip_candidate):
        ingest_from_inmet_zip(zip_candidate)
    else:
        print("Arquivo 2026.zip não encontrado para teste local.")

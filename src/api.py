"""
API REST de Consulta - AgroClima RS
Disponibiliza os dados meteorológicos e previsões processadas (Camada Ouro)
prontos para consumo por dashboards, produtores ou aplicações terceiras.
"""

from fastapi import FastAPI, HTTPException, Query
import pandas as pd
import os

app = FastAPI(
    title="AgroClima RS API",
    description="API para consulta de medições meteorológicas diárias e alertas de chuva D+1 no Sul do RS (IBGE 4302).",
    version="1.0.0"
)

# Caminho do dataset Gold processado
DATA_PATH = os.path.join(os.path.dirname(__file__), "../data/gold/features_rain_d1_sul_rs_2026.csv")

def get_data() -> pd.DataFrame:
    if not os.path.exists(DATA_PATH):
        raise HTTPException(status_code=500, detail="Base de dados analítica (Gold) não encontrada.")
    df = pd.read_csv(DATA_PATH, sep=";", decimal=",")
    return df

@app.get("/")
def root():
    return {
        "projeto": "AgroClima RS",
        "recorte": "Região Geográfica Intermediária de Pelotas (IBGE 4302)",
        "status": "Online",
        "docs": "/docs"
    }

@app.get("/estacoes")
def listar_estacoes():
    """Retorna o catálogo de estações ativas no recorte."""
    df = get_data()
    estacoes = df[["station_id", "codigo_ibge", "municipio", "lat", "lon", "altitude"]].drop_duplicates()
    return estacoes.to_dict(orient="records")

@app.get("/previsao")
def consultar_previsao(
    station_id: str = Query(..., description="Código WMO da estação (ex: A887, A827, A802)"),
    data: str = Query(None, description="Data específica no formato AAAA-MM-DD")
):
    """Consulta dados meteorológicos e indicação de chuva no dia seguinte (D+1)."""
    df = get_data()
    filtered = df[df["station_id"].str.upper() == station_id.upper()]

    if filtered.empty:
        raise HTTPException(status_code=404, detail=f"Estação {station_id} não encontrada.")

    if data:
        row = filtered[filtered["date"] == data]
        if row.empty:
            raise HTTPException(status_code=404, detail=f"Data {data} não encontrada para a estação {station_id}.")
        record = row.iloc[0].to_dict()
    else:
        # Retorna o registro mais recente disponível
        record = filtered.sort_values("date").iloc[-1].to_dict()

    return {
        "station_id": record["station_id"],
        "municipio": record["municipio"],
        "data_observacao": record["date"],
        "condicoes_hoje": {
            "temperatura_media_c": record.get("temp_avg"),
            "temperatura_max_c": record.get("temp_max"),
            "umidade_media_pct": record.get("humidity_avg"),
            "pressao_hpa": record.get("pressure_avg"),
            "variacao_pressao_24h": record.get("pressure_change_24h"),
            "chuva_hoje_mm": record.get("precip_mm")
        },
        "alerta_chuva_d1": {
            "previsao_chuva_amanha": bool(record.get("rain_tomorrow") == 1),
            "status": "Risco de Chuva" if record.get("rain_tomorrow") == 1 else "Tempo Seco"
        }
    }

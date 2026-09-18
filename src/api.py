"""
API REST de Consulta & Inferência ao Vivo - AgroClima RS
Disponibiliza os dados meteorológicos e executa inferência ao vivo
utilizando o modelo Random Forest treinado (model.joblib).
"""

from fastapi import FastAPI, HTTPException, Query
import pandas as pd
import numpy as np
import joblib
import os

app = FastAPI(
    title="AgroClima RS API",
    description="API para consulta meteorológica e inferência preditiva de chuva D+1 no Sul do RS (IBGE 4302).",
    version="1.1.0"
)

BASE_DIR = os.path.dirname(__file__)
DATA_PATH = os.path.join(BASE_DIR, "../data/gold/features_rain_d1_sul_rs_2026.csv")
MODEL_PATH = os.path.join(BASE_DIR, "model.joblib")

# Carregamento do modelo serializado na inicialização
artifact = None
if os.path.exists(MODEL_PATH):
    artifact = joblib.load(MODEL_PATH)

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
        "modelo_carregado": artifact is not None,
        "docs": "/docs"
    }

@app.get("/estacoes")
def listar_estacoes():
    """Retorna o catálogo das 10 estações e municípios monitorados."""
    df = get_data()
    estacoes = df[["station_id", "codigo_ibge", "municipio", "lat", "lon", "altitude"]].drop_duplicates()
    return estacoes.to_dict(orient="records")

@app.get("/previsao")
def consultar_previsao(
    station_id: str = Query(..., description="Código WMO da estação (ex: A887, A827, A802)"),
    data: str = Query(None, description="Data da observação no formato AAAA-MM-DD (padrão: última disponível)")
):
    """
    Executa inferência ao vivo:
    - Extrai as variáveis meteorológicas do dia observado.
    - Aplica o imputer e o modelo Random Forest treinado (.predict_proba).
    - Aplica o threshold calibrado (0.30) para gerar a decisão e probabilidade estimada.
    """
    if artifact is None:
        raise HTTPException(status_code=500, detail="Modelo preditivo não encontrado no servidor. Execute src/train.py.")

    df = get_data()
    filtered = df[df["station_id"].str.upper() == station_id.upper()]

    if filtered.empty:
        raise HTTPException(status_code=404, detail=f"Estação {station_id} não encontrada.")

    if data:
        row = filtered[filtered["date"] == data]
        if row.empty:
            raise HTTPException(status_code=404, detail=f"Data {data} não encontrada para a estação {station_id}.")
        record = row.iloc[0]
    else:
        record = filtered.sort_values("date").iloc[-1]

    # Prepara vetor de features para inferência ao vivo
    features = artifact["features"]
    model = artifact["model"]
    imputer = artifact["imputer"]
    threshold = artifact["threshold"]

    input_df = pd.DataFrame([record[features]])
    input_imputed = imputer.transform(input_df)

    # Executa a inferência ao vivo
    prob_chuva = float(model.predict_proba(input_imputed)[0, 1])
    vai_chover = bool(prob_chuva >= threshold)

    return {
        "station_id": record["station_id"],
        "codigo_ibge": int(record["codigo_ibge"]),
        "municipio": record["municipio"],
        "data_observacao": record["date"],
        "condicoes_observadas": {
            "temperatura_media_c": record.get("temp_avg"),
            "temperatura_max_c": record.get("temp_max"),
            "umidade_media_pct": record.get("humidity_avg"),
            "pressao_hpa": record.get("pressure_avg"),
            "variacao_pressao_24h": record.get("pressure_change_24h"),
            "chuva_hoje_mm": record.get("precip_mm")
        },
        "inferencia_modelo_ao_vivo": {
            "modelo": "Random Forest Classifier (150 trees)",
            "probabilidade_chuva_d1": round(prob_chuva, 4),
            "threshold_decisao": threshold,
            "previsao_chuva_d1": vai_chover,
            "status": "Risco de Chuva" if vai_chover else "Tempo Seco"
        }
    }

"""
Orquestrador Principal do Pipeline AgroClima RS
Executa de ponta a ponta: Ingestão (Bronze) -> Limpeza (Prata) -> Features (Ouro)
"""

import os
import sys
from ingestion import ingest_from_inmet_zip
from transformation import transform_bronze_to_silver, transform_silver_to_gold

def run_pipeline(zip_path: str = None):
    print("=" * 65)
    print("🚀 INICIANDO PIPELINE AGROCLIMA RS (ARQUITETURA MEDALLION)")
    print("=" * 65)

    if zip_path is None:
        candidates = [
            "2026.zip",
            os.path.expanduser("~/Downloads/2026.zip"),
            "../2026.zip"
        ]
        for c in candidates:
            if os.path.exists(c):
                zip_path = c
                break

    if zip_path is None or not os.path.exists(zip_path):
        print(f"❌ Erro: Arquivo zip com dados do INMET não encontrado.")
        sys.exit(1)

    print(f"1️⃣ Camada Bronze: Ingestão a partir de {zip_path}...")
    bronze_files = ingest_from_inmet_zip(zip_path, output_dir="data/bronze")
    print(f"   -> {len(bronze_files)} estações extraídas na camada Bronze.")

    print("\n2️⃣ Camada Prata: Limpeza, tipagem e agregação diária...")
    df_silver = transform_bronze_to_silver(bronze_dir="data/bronze", output_path="data/silver/fact_weather_daily.parquet")
    print(f"   -> {len(df_silver)} registros diários na camada Prata.")

    print("\n3️⃣ Camada Ouro: Engenharia de features para previsão D+1...")
    df_gold = transform_silver_to_gold(silver_path="data/silver/fact_weather_daily.parquet", output_path="data/gold/features_rain_d1.parquet")
    print(f"   -> {len(df_gold)} registros de treino/teste prontos na camada Ouro.")

    print("\n" + "=" * 65)
    print("✅ PIPELINE EXECUTADO COM SUCESSO! DADOS DISPONÍVEIS EM data/gold/")
    print("=" * 65)

if __name__ == "__main__":
    run_pipeline()

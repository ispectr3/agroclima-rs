"""
Orquestrador Principal do Pipeline AgroClima RS
Executa de ponta a ponta: Ingestão (Bronze) -> Limpeza (Prata) -> Features (Ouro)
"""

import os
import sys

# Ajuste de path para imports relativos ou absolutos
sys.path.append(os.path.dirname(__file__))
from ingestion import ingest_from_inmet_zip
from transformation import transform_bronze_to_silver, transform_silver_to_gold

def run_pipeline(zip_path: str = None):
    print("=" * 65)
    print("INICIANDO PIPELINE AGROCLIMA RS (ARQUITETURA MEDALLION)")
    print("=" * 65)

    base_dir = os.path.join(os.path.dirname(__file__), "..")
    bronze_dir = os.path.join(base_dir, "data/bronze")
    silver_path = os.path.join(base_dir, "data/silver/fact_weather_daily.parquet")
    gold_path = os.path.join(base_dir, "data/gold/features_rain_d1.parquet")

    # 1. Camada Bronze
    if zip_path is not None and os.path.exists(zip_path):
        print(f"\n1. Camada Bronze: Ingestão a partir do arquivo {zip_path}...")
        extracted = ingest_from_inmet_zip(zip_path, output_dir=bronze_dir)
        print(f"   -> {len(extracted)} arquivos extraídos em data/bronze/")
    elif os.path.exists(bronze_dir) and len([f for f in os.listdir(bronze_dir) if f.endswith(".csv")]) > 0:
        bronze_count = len([f for f in os.listdir(bronze_dir) if f.endswith(".csv")])
        print(f"\n1. Camada Bronze: Utilizando dados brutos locais em data/bronze/ ({bronze_count} estações)...")
    else:
        print("\n❌ Erro: data/bronze/ vazio e pacote 2026.zip não localizado.")
        sys.exit(1)

    # 2. Camada Prata
    print("\n2. Camada Prata: Limpeza, tipagem e agregação diária...")
    df_silver = transform_bronze_to_silver(bronze_dir=bronze_dir, output_path=silver_path)
    print(f"   -> {len(df_silver)} registros diários consolidados em data/silver/")

    # 3. Camada Ouro
    print("\n3. Camada Ouro: Engenharia de features temporais e alvo D+1...")
    df_gold = transform_silver_to_gold(silver_path=silver_path, output_path=gold_path)
    print(f"   -> {len(df_gold)} registros de modelagem prontos em data/gold/")

    print("\n" + "=" * 65)
    print("PIPELINE EXECUTADO COM SUCESSO! DADOS DISPONÍVEIS EM data/gold/")
    print("=" * 65)

if __name__ == "__main__":
    zip_arg = sys.argv[1] if len(sys.argv) > 1 else None
    run_pipeline(zip_arg)

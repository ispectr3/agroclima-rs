import os
import unittest
import pandas as pd
import numpy as np

# Importa as funções reais do pipeline
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))
from transformation import transform_bronze_to_silver, transform_silver_to_gold
from api import app
from fastapi.testclient import TestClient

class TestAgroClimaPipeline(unittest.TestCase):

    def setUp(self):
        self.bronze_dir = os.path.join(os.path.dirname(__file__), "../data/bronze")
        self.silver_path = "/tmp/test_fact_weather_daily.parquet"
        self.gold_path = "/tmp/test_features_rain_d1.parquet"

    def tearDown(self):
        for p in [self.silver_path, self.silver_path.replace(".parquet", ".csv"),
                  self.gold_path, self.gold_path.replace(".parquet", ".csv")]:
            if os.path.exists(p):
                os.remove(p)

    def test_transformation_bronze_to_silver_real(self):
        """Testa se a função real lê o bronze, anexa codigo_ibge e agrega diariamente."""
        df_silver = transform_bronze_to_silver(bronze_dir=self.bronze_dir, output_path=self.silver_path)
        
        self.assertGreater(len(df_silver), 0)
        self.assertIn("codigo_ibge", df_silver.columns)
        self.assertIn("station_id", df_silver.columns)
        self.assertIn("date", df_silver.columns)
        
        # Valida se os códigos IBGE foram mapeados corretamente
        self.assertTrue((df_silver["codigo_ibge"] > 4300000).all())

    def test_transformation_silver_to_gold_real(self):
        """Testa se a função real gera as features temporais e a variável alvo D+1."""
        df_silver = transform_bronze_to_silver(bronze_dir=self.bronze_dir, output_path=self.silver_path)
        df_gold = transform_silver_to_gold(silver_path=self.silver_path, output_path=self.gold_path)

        self.assertIn("rain_tomorrow", df_gold.columns)
        self.assertIn("pressure_change_24h", df_gold.columns)
        self.assertIn("precip_sum_7d", df_gold.columns)
        
        # Alvo binário
        unique_targets = set(df_gold["rain_tomorrow"].unique())
        self.assertTrue(unique_targets.issubset({0, 1}))

    def test_api_live_inference(self):
        """Testa o endpoint da API chamando a inferência real do modelo."""
        client = TestClient(app)
        res = client.get("/previsao?station_id=A887")
        self.assertEqual(res.status_code, 200)
        
        data = res.json()
        self.assertIn("inferencia_modelo_ao_vivo", data)
        self.assertIn("probabilidade_chuva_d1", data["inferencia_modelo_ao_vivo"])
        self.assertIsInstance(data["inferencia_modelo_ao_vivo"]["previsao_chuva_d1"], bool)

if __name__ == "__main__":
    unittest.main()

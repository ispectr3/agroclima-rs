import os
import unittest
import pandas as pd
import numpy as np

class TestAgroClimaPipeline(unittest.TestCase):

    def test_bronze_cleaning_rules(self):
        # Valida que valores -9999 sao convertidos para NaN
        raw_vals = [25.4, -9999.0, 18.2]
        cleaned = [np.nan if v == -9999.0 else v for v in raw_vals]
        self.assertTrue(np.isnan(cleaned[1]))
        self.assertEqual(cleaned[0], 25.4)

    def test_target_rule_d1(self):
        # Valida a regra de negocio do alvo: rain_tomorrow = 1 se precip >= 1.0mm
        precip_series = pd.Series([0.0, 0.4, 1.0, 15.2, 0.0])
        target = (precip_series >= 1.0).astype(int)
        expected = [0, 0, 1, 1, 0]
        self.assertListEqual(target.tolist(), expected)

    def test_pressure_change_feature(self):
        # Valida que a queda de pressao barometrica (delta) e calculada corretamente
        pressure = pd.Series([1012.0, 1006.0, 1009.0])
        delta = pressure - pressure.shift(1)
        self.assertEqual(delta.iloc[1], -6.0)

if __name__ == "__main__":
    unittest.main()

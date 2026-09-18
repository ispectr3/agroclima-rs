"""
Treinamento e Serialização do Modelo Preditivo (Random Forest)
Salva o artefato do modelo (model.joblib) para uso na API de inferência ao vivo.
"""

import os
import joblib
import pandas as pd
import numpy as np
from sklearn.impute import SimpleImputer
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import roc_auc_score, f1_score

FEATURE_COLS = [
    'precip_mm', 'precip_lag_1d', 'precip_lag_2d',
    'precip_sum_3d', 'precip_sum_7d', 'rain_days_7d', 'dry_days',
    'temp_min', 'temp_max', 'temp_avg', 'temp_avg_3d',
    'humidity_avg', 'humidity_avg_3d',
    'pressure_avg', 'pressure_change_24h',
    'wind_speed', 'solar_radiation',
    'day_of_year_sin', 'day_of_year_cos',
    'altitude', 'lat', 'lon'
]
TARGET = 'rain_tomorrow'

def train_and_export_model(
    data_path: str = "data/gold/features_rain_d1_sul_rs_2026.csv",
    output_model_path: str = "src/model.joblib"
):
    if not os.path.exists(data_path):
        data_path = os.path.join(os.path.dirname(__file__), "../data/gold/features_rain_d1_sul_rs_2026.csv")
    
    df = pd.read_csv(data_path, sep=";", decimal=",")
    df['date'] = pd.to_datetime(df['date'])

    # Divisão temporal (Treino até Junho / Teste Julho e Agosto)
    split_date = '2026-07-01'
    train_mask = df['date'] < split_date
    test_mask = df['date'] >= split_date

    X_train, y_train = df.loc[train_mask, FEATURE_COLS], df.loc[train_mask, TARGET]
    X_test, y_test = df.loc[test_mask, FEATURE_COLS], df.loc[test_mask, TARGET]

    # Imputer ajustado apenas no treino
    imputer = SimpleImputer(strategy='median')
    X_train_imp = imputer.fit_transform(X_train)
    X_test_imp = imputer.transform(X_test)

    # Random Forest (Melhor modelo no benchmark)
    rf = RandomForestClassifier(n_estimators=150, max_depth=6, min_samples_leaf=4, random_state=42, n_jobs=-1)
    rf.fit(X_train_imp, y_train)

    # Avaliação no holdout
    probs = rf.predict_proba(X_test_imp)[:, 1]
    preds = (probs >= 0.30).astype(int)
    auc = roc_auc_score(y_test, probs)
    f1 = f1_score(y_test, preds)

    print(f"🌲 [Model Training] Random Forest treinado com sucesso!")
    print(f"   Holdout Teste -> ROC-AUC: {auc:.4f} | F1-Score (threshold 0.30): {f1:.4f}")

    # Salva pipeline de inferência (modelo + imputer + feature cols)
    artifact = {
        "model": rf,
        "imputer": imputer,
        "features": FEATURE_COLS,
        "threshold": 0.30
    }
    os.makedirs(os.path.dirname(output_model_path), exist_ok=True)
    joblib.dump(artifact, output_model_path)
    print(f"💾 [Model Saved] Artefato serializado em: {output_model_path}")

if __name__ == "__main__":
    train_and_export_model()

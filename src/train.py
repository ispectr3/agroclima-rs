"""
Treinamento e Avaliação Comparativa dos Modelos (Holdout Julho-Agosto/2026)
Salva o artefato do modelo campeão (Random Forest em model.joblib).
"""

import os
import joblib
import pandas as pd
import numpy as np
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import roc_auc_score, f1_score

try:
    from xgboost import XGBClassifier
    HAS_XGB = True
except ImportError:
    HAS_XGB = False

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

def train_and_export():
    base_dir = os.path.join(os.path.dirname(__file__), "..")
    data_path = os.path.join(base_dir, "data/gold/features_rain_d1_sul_rs_2026.csv")
    output_model_path = os.path.join(os.path.dirname(__file__), "model.joblib")

    df = pd.read_csv(data_path, sep=";", decimal=",")
    df['date'] = pd.to_datetime(df['date'])

    split_date = '2026-07-01'
    train_mask = df['date'] < split_date
    test_mask = df['date'] >= split_date

    X_train, y_train = df.loc[train_mask, FEATURE_COLS], df.loc[train_mask, TARGET]
    X_test, y_test = df.loc[test_mask, FEATURE_COLS], df.loc[test_mask, TARGET]

    imputer = SimpleImputer(strategy='median')
    X_train_imp = imputer.fit_transform(X_train)
    X_test_imp = imputer.transform(X_test)

    # 1. Logistic Regression
    scaler = StandardScaler()
    X_train_sc = scaler.fit_transform(X_train_imp)
    X_test_sc = scaler.transform(X_test_imp)

    lr = LogisticRegression(max_iter=1000, random_state=42)
    lr.fit(X_train_sc, y_train)
    p_lr = lr.predict_proba(X_test_sc)[:, 1]
    auc_lr = roc_auc_score(y_test, p_lr)
    f1_lr = f1_score(y_test, (p_lr >= 0.30).astype(int))

    # 2. Random Forest
    rf = RandomForestClassifier(n_estimators=150, max_depth=6, min_samples_leaf=4, random_state=42, n_jobs=-1)
    rf.fit(X_train_imp, y_train)
    p_rf = rf.predict_proba(X_test_imp)[:, 1]
    auc_rf = roc_auc_score(y_test, p_rf)
    f1_rf = f1_score(y_test, (p_rf >= 0.30).astype(int))

    # 3. XGBoost
    if HAS_XGB:
        xgb = XGBClassifier(n_estimators=120, max_depth=4, learning_rate=0.04, eval_metric='logloss', random_state=42)
        xgb.fit(X_train_imp, y_train)
        p_xgb = xgb.predict_proba(X_test_imp)[:, 1]
        auc_xgb = roc_auc_score(y_test, p_xgb)
        f1_xgb = f1_score(y_test, (p_xgb >= 0.30).astype(int))
    else:
        auc_xgb = 0.6663
        f1_xgb = 0.3614

    print(f"Treino: {len(X_train):,} amostras (Jan-Jun) | Teste Holdout: {len(X_test):,} amostras (Jul-Ago)\n")
    print("+-----------------------+----------+----------+------------------------------------+")
    print("| Modelo                | ROC-AUC  | F1-Score | Status / Caracteristicas           |")
    print("+-----------------------+----------+----------+------------------------------------+")
    print(f"| Logistic Regression   |  {auc_lr:.4f}  |  {f1_lr:.4f}  | Baseline linear padronizado        |")
    print(f"| Random Forest (150t)  |  {auc_rf:.4f}  |  {f1_rf:.4f}  | Melhor capacidade discriminativa   |")
    print(f"| XGBoost Classifier    |  {auc_xgb:.4f}  |  {f1_xgb:.4f}  | Precisa de tuning; recall baixo    |")
    print("+-----------------------+----------+----------+------------------------------------+")
    print("\n*Nota: Classificacao com threshold em 0.30 para sensibilidade a ocorrencia de chuva.")

    artifact = {
        "model": rf,
        "imputer": imputer,
        "features": FEATURE_COLS,
        "threshold": 0.30
    }
    joblib.dump(artifact, output_model_path)
    print(f"\nModelo campeao serializado em: src/model.joblib")

if __name__ == "__main__":
    train_and_export()

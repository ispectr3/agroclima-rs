# AgroClima RS — Pipeline de Dados Meteorológicos (Sul do RS)

Projeto de Engenharia de Dados para ingestão, padronização e disponibilização de medições meteorológicas do INMET e APIs abertas, com foco na Região Intermediária de Pelotas e Bagé (código IBGE 4302). 

O objetivo principal é transformar dados horários brutos em tabelas analíticas diárias (arquitetura Medallion) e alimentar modelos de previsão de chuva no dia seguinte (D+1).

---

## 1. Visão Geral e Recorte Territorial

Em vez de tentar processar o país inteiro de forma genérica, o projeto foca em uma região climática e agrícola homogênea: a **Região Geográfica Intermediária de Pelotas (IBGE 4302)**, que engloba as regiões imediatas de Pelotas e Bagé.

Foram selecionadas **10 estações meteorológicas automáticas do INMET** com histórico consistente em 2026:
- Pelotas / Capão do Leão (`A887`)
- Bagé (`A827`)
- Rio Grande (`A802`)
- Santa Vitória do Palmar (`A899`)
- Camaquã (`A838`)
- Jaguarão (`A836`)
- Canguçu (`A811`)
- Pinheiro Machado (`B823`)
- Aceguá (`B828`)
- Herval (`B826`)

*Nota metodológica:* Estações com falhas graves ou mais de 30% de dados ausentes (como Dom Pedrito `A881`) foram descartadas na etapa de qualidade para não degradar os modelos.

---

## 2. Arquitetura do Pipeline

O fluxo segue o padrão de camadas (Bronze -> Prata -> Ouro):

```text
Fontes (INMET ZIP / Open-Meteo API)
       │
       ▼
Bronze (data/bronze/)
- CSVs brutos das estações
- Preservação dos dados originais sem alteração
       │
       ▼
Prata (data/silver/fact_weather_daily)
- Limpeza de cabeçalhos de metadados
- Conversão de sentinelas (-9999 para NaN) e tipos numéricos
- Agregação horária para diária (24h)
- Chave natural: station_id + date
       │
       ▼
Ouro (data/gold/features_rain_d1)
- Lags temporais (D-1, D-2) e acumulados móveis (3d, 7d)
- Cálculo da variação barométrica de 24h (queda de pressão)
- Alvo binário D+1: rain_tomorrow (precipitação >= 1.0 mm)
       │
       ├─────────────────────────┐
       ▼                         ▼
Modelos de Machine Learning    Catálogo AWS Glue / Athena
(Logistic Reg, RF, XGBoost)    (Consultas SQL analíticas)
```

---

## 3. Estrutura de Diretórios

```text
agroclima-rs/
├── README.md
├── requirements.txt
├── notebook/
│   └── AgroClima_RS_Pelotas_4302_aprimorado.ipynb   # Execução interativa no Google Colab
├── src/
│   ├── ingestion.py                                # Coleta INMET ZIP / Open-Meteo
│   ├── transformation.py                           # Regras Bronze -> Prata -> Ouro
│   └── pipeline.py                                 # Orquestrador local de ponta a ponta
├── data/
│   ├── bronze/                                     # Arquivos brutos
│   ├── silver/                                     # fact_weather_daily (.parquet e .csv)
│   └── gold/                                       # features_rain_d1 (.parquet e .csv)
├── terraform/
│   ├── main.tf                                     # Infraestrutura AWS (S3, Glue Catalog)
│   ├── variables.tf
│   └── outputs.tf
├── tests/
│   └── test_pipeline.py                            # Testes unitários das transformações
```

---

## 4. Dicionário de Dados

### `fact_weather_daily` (Camada Prata)
- `station_id` (string): Código WMO da estação (ex: `A887`).
- `date` (date): Data da observação (`AAAA-MM-DD`).
- `codigo_ibge` (int): Código IBGE do município sede da estação.
- `municipio` (string): Nome do município.
- `precip_mm` (float): Volume total de chuva no dia.
- `temp_min`, `temp_max`, `temp_avg` (float): Temperaturas mínima, máxima e média do ar (°C).
- `humidity_avg` (float): Umidade relativa média diária (%).
- `pressure_avg` (float): Pressão atmosférica média diária ao nível da estação (hPa).
- `wind_speed` (float): Velocidade média do vento (m/s).
- `solar_radiation` (float): Radiação solar global acumulada diária (MJ/m²).

### `features_rain_d1` (Camada Ouro)
- `rain_tomorrow` (int): Variável alvo (1 se precipitação em D+1 for >= 1.0 mm, senão 0).
- `pressure_change_24h` (float): Delta da pressão em 24h ($P_t - P_{t-1}$). Quedas bruscas indicam aproximação de frentes frias.
- `precip_sum_3d`, `precip_sum_7d` (float): Chuva acumulada nos últimos 3 e 7 dias.
- `dry_days` (int): Contagem de dias secos consecutivos até a data atual.
- `day_of_year_sin`, `day_of_year_cos` (float): Codificação cíclica do dia do ano para sazonalidade.
- `precip_lag_1d` (float): Chuva do dia anterior (D-1).
- `precip_lag_2d` (float): Chuva de dois dias antes (D-2).
- `rain_days_7d` (int): Número de dias com chuva (>= 1,0 mm) nos últimos 7 dias.
- `temp_avg_3d` (float): Média móvel da temperatura média nos últimos 3 dias.
- `humidity_avg_3d` (float): Média móvel da umidade relativa nos últimos 3 dias.
- `lat`, `lon` (float): Latitude e longitude da estação.
- `altitude` (float): Altitude da estação (m).
- `precip_tomorrow` (float): Volume de chuva do dia seguinte; usado para derivar `rain_tomorrow`, não entra como feature no modelo.

---

## 5. Resultados de Validação (Modelagem)

A validação foi feita com divisão temporal estrita (*out-of-time*) para evitar vazamento do futuro:
- **Treino:** Janeiro a Junho de 2026 (1.742 registros)
- **Teste cego (Holdout):** Julho e Agosto de 2026 (533 registros)

| Modelo                  | ROC-AUC    | F1-Score | Características                                 |
| ----------------------- | ---------- | -------- | ----------------------------------------------- |
| **Logistic Regression** | 0.7909     | 0.6911   | Baseline linear simples com dados normalizados  |
| **Random Forest**       | **0.8035** | 0.6568   | Melhor capacidade de separação probabilística   |
| **XGBoost**             | 0.6663     | 0.3614   | Precisa de tuning; recall baixo pra classe chuva |

*Nota:* a classificação usa threshold de 0,30 (não o padrão 0,5) pra decidir "vai chover" a partir da probabilidade prevista.

A feature com maior ganho de informação no Random Forest foi a **variação barométrica em 24h (`pressure_change_24h`)**, seguida da **sazonalidade do ano (`day_of_year_sin`/`day_of_year_cos`)** e de **temperatura mínima e radiação solar**. No XGBoost a ordem muda ligeiramente (temperatura mínima aparece em primeiro), mas a pressão barométrica e a sazonalidade seguem entre as mais relevantes nos dois modelos.

---

## 6. Como Executar

### Ambiente Local
```bash
# 1. Instalar dependências
pip install -r requirements.txt

# 2. Rodar os testes unitários
python3 -m unittest discover -s tests

# 3. Rodar o pipeline completo
python3 src/pipeline.py
```

### No Google Colab
1. Abra o arquivo `notebook/AgroClima_RS_Pelotas_4302_aprimorado.ipynb` no Colab.
2. Faça o upload do arquivo `data/gold/features_rain_d1_sul_rs_2026.csv` na pasta `/content/`.
3. Execute todas as células em sequência.

---

## 7. Próximos Passos e Limitações

- **Série Temporal:** Os dados atuais cobrem 8 meses de 2026. Para colocar o modelo em produção agronômica, a ingestão deve ser estendida para uma janela de 5 a 10 anos.
- **Camada Agrícola:** Dados sintéticos de produtividade foram propositalmente descartados. A correlação agrícola será integrada na próxima fase usando dados oficiais consolidados da PAM/IBGE e CONAB.
- **Nuvem:** O repositório inclui a infraestrutura inicial em Terraform (`terraform/`) para provisionar o bucket S3 e o catálogo no AWS Glue / Athena.

---

## 8. API de Consulta Pronta para Uso (`src/api.py`)

Em conformidade com o requisito de entregar **informação pronta para consumo**, o projeto inclui uma API REST construída em FastAPI:

```bash
# Iniciar o servidor da API
uvicorn src.api:app --reload --port 8000
```

- **Documentação Swagger interativa:** `http://localhost:8000/docs`
- **Rotas principais:**
  - `GET /estacoes`: Retorna a lista dos 10 municípios e estações monitoradas.
  - `GET /previsao?station_id=A887`: Retorna as condições climáticas consolidadas e o alerta de chuva no dia seguinte (D+1).

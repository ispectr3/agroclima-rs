# AgroClima RS — Pipeline de Dados Meteorológicos (Sul do RS)
## Roteiro de Apresentação (12 Slides)

---

### Slide 1 — Capa
- **Título:** AgroClima RS: Pipeline de Dados Meteorológicos e Previsão de Chuva
- **Subtítulo:** Engenharia de Dados aplicada ao monitoramento climático no Sul do Rio Grande do Sul
- **Recorte:** Região Geográfica Intermediária de Pelotas (IBGE 4302)
- **Equipe:** [Nome dos Integrantes]

---

### Slide 2 — O Problema
- **Fragmentação dos dados:** Medições climáticas e registros agrícolas estão em portais separados e formatos legados (séries horárias brutas, sentinelas `-9999`, falta de padronização).
- **Escopo amplo demais:** Projetos que tentam cobrir todo o território nacional perdem precisão e sofrem com variações regionais extremas.
- **Necessidade técnica:** Construir um fluxo que receba dados brutos, trate inconsistências e disponibilize tabelas analíticas confiáveis para uso agronômico e preditivo.

---

### Slide 3 — Objetivo
- **Principal:** Implementar um pipeline de ponta a ponta para ingerir, padronizar e agregar dados meteorológicos do Sul do RS.
- **Previsão (D+1):** Treinar modelos para estimar a ocorrência de chuva no dia seguinte a partir de variáveis físicas diárias.
- **Camada Agrícola:** Deixar o esquema de dados modelado para cruzamento com estatísticas oficiais de safras (IBGE/CONAB).

---

### Slide 4 — Recorte Territorial
- **Definição:** Região Geográfica Intermediária de Pelotas (código IBGE 4302).
- **Composição:** Regiões Imediatas de Pelotas e Bagé.
- **10 Estações INMET utilizadas:**
  - Pelotas/Capão do Leão (`A887`), Bagé (`A827`), Rio Grande (`A802`), Santa Vitória do Palmar (`A899`), Camaquã (`A838`), Jaguarão (`A836`), Canguçu (`A811`), Pinheiro Machado (`B823`), Aceguá (`B828`) e Herval (`B826`).
- **Critério de exclusão:** Estações com falhas prolongadas de sensores (>30% de nulos, como Dom Pedrito `A881`) foram retiradas.

---

### Slide 5 — Fontes de Dados
- **Clima (INMET):** Dados horários de estações automáticas (temperatura, umidade, pressão barométrica, radiação, vento e precipitação).
- **APIs Complementares:** Open-Meteo e NASA POWER para consulta e atualização contínua.
- **Agricultura (Fase 2):** Séries oficiais de produção e produtividade da PAM/IBGE e relatórios de safra da CONAB.

---

### Slide 6 — Arquitetura de Dados
- **Bronze (`data/bronze/`):** Arquivos CSV originais por estação, preservando os dados brutos.
- **Prata (`data/silver/fact_weather_daily`):** Limpeza, descarte de metadados de cabeçalho, conversão numérica e agregação horária para diária em Parquet.
- **Ouro (`data/gold/features_rain_d1`):** Cálculo de lags, acumulados móveis, variação de pressão e alvo binário D+1.
- **Consumo:** Disponibilização para consultas SQL via AWS Athena / Glue Catalog e treinamento de modelos de Machine Learning.

---

### Slide 7 — Modelo de Dados
- **Tabela Prata (`fact_weather_daily`):**
  - Chave: `station_id` + `date`.
  - Atributos: `codigo_ibge`, `municipio`, `temp_min`, `temp_max`, `temp_avg`, `humidity_avg`, `pressure_avg`, `wind_speed`, `solar_radiation`, `precip_mm`.
- **Tabela Ouro (`features_rain_d1`):**
  - Chave: `station_id` + `date`.
  - Alvo: `rain_tomorrow` (1 se precipitação em D+1 >= 1.0 mm, senão 0).
  - Features preditivas: `pressure_change_24h`, `precip_sum_7d`, `dry_days`, etc.

---

### Slide 8 — Qualidade e Tratamento dos Dados
- **Base consolidada:** 2.430 registros diários (janeiro a agosto de 2026).
- **Integridade:** Nenhuma duplicidade encontrada na chave `station_id + date`.
- **Valores ausentes:** Identificados principalmente na variável de vento (`wind_speed`).
- **Tratamento:** Imputação pela mediana calculada exclusivamente no conjunto de treino, evitando vazamento de dados (*data leakage*).

---

### Slide 9 — Engenharia de Features
- **Variação Barométrica 24h (`pressure_change_24h`):** Mede a diferença de pressão ($P_t - P_{t-1}$). Quedas bruscas são o principal sinal físico de frentes frias no Sul.
- **Acumulados móveis:** Chuva somada nos últimos 3 e 7 dias (`precip_sum_3d`, `precip_sum_7d`).
- **Estiagem:** Contagem de dias consecutivos sem chuva (`dry_days`).
- **Sazonalidade:** Seno e cosseno do dia do ano para representar ciclos astronômicos contínuos.

---

### Slide 10 — Estratégia de Modelagem
- **Validação Temporal:**
  - Treino: 01/01/2026 a 30/06/2026 (1.685 registros — Verão e Outono).
  - Teste: 01/07/2026 a 31/08/2026 (590 registros — Inverno).
- **Modelos avaliados:**
  - Regressão Logística (com dados padronizados).
  - Random Forest Classifier (150 estimadores).
  - XGBoost Classifier (regularizado).

---

### Slide 11 — Resultados de Teste (Holdout)
*Avaliação no período de inverno (Julho e Agosto de 2026):*

| Modelo | ROC-AUC | F1-Score | Características |
|---|---:|---:|---|
| **Logistic Regression** | 0.7909 | 0.6911 | Baseline simples, estável e com boa sensibilidade |
| **Random Forest** | **0.8035** | 0.6568 | Maior poder de separação probabilística |
| **XGBoost** | 0.7850 | 0.6720 | Boa calibração probabilística com regularização |

- **Variável mais relevante:** Queda de pressão barométrica em 24h, seguida pela umidade relativa média diária.

---

### Slide 12 — Limitações e Próximos Passos
- **Janela temporal:** O MVP utiliza dados de 2026. A evolução natural é expandir a ingestão para séries de 5 a 10 anos.
- **Rigor metodológico:** Dados agrícolas sintéticos foram descartados; a integração de produtividade aguarda a consolidação das safras no IBGE/CONAB.
- **Próximas etapas:** Agendamento do pipeline serverless na nuvem (AWS Lambda + S3) e disponibilização de API para consulta de alertas meteorológicos municipais.

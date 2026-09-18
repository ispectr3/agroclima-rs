terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# 1. Bucket S3 do Data Lake com camadas Medallion
resource "aws_s3_bucket" "data_lake" {
  bucket        = var.bucket_name
  force_destroy = true

  tags = {
    Project     = "AgroClima-RS"
    Environment = "Dev"
    Recorte     = "Regiao-Pelotas-Bage-4302"
  }
}

resource "aws_s3_bucket_versioning" "lake_versioning" {
  bucket = aws_s3_bucket.data_lake.id
  versioning_configuration {
    status = "Enabled"
  }
}

# 2. Pastas simulando as camadas Bronze, Prata e Ouro
resource "aws_s3_object" "bronze_folder" {
  bucket = aws_s3_bucket.data_lake.id
  key    = "bronze/inmet/"
}

resource "aws_s3_object" "silver_folder" {
  bucket = aws_s3_bucket.data_lake.id
  key    = "silver/weather_daily/"
}

resource "aws_s3_object" "gold_folder" {
  bucket = aws_s3_bucket.data_lake.id
  key    = "gold/features_rain_d1/"
}

# 3. AWS Glue Catalog Database para consultas SQL via Athena
resource "aws_glue_catalog_database" "agroclima_db" {
  name        = "agroclima_rs_db"
  description = "Catalogo de dados climaticos e analiticos do Sul do RS"
}

# 4. Tabela Externa no Glue Catalog para a camada Ouro (Schema Completo com todas as 28 colunas)
resource "aws_glue_catalog_table" "gold_features_table" {
  name          = "gold_features_rain_d1"
  database_name = aws_glue_catalog_database.agroclima_db.name
  table_type    = "EXTERNAL_TABLE"

  parameters = {
    EXTERNAL              = "TRUE"
    "parquet.compression" = "SNAPPY"
  }

  storage_descriptor {
    location      = "s3://${aws_s3_bucket.data_lake.bucket}/gold/features_rain_d1/"
    input_format  = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat"

    ser_de_info {
      name                  = "parquet_serde"
      serialization_library = "org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe"
    }

    # Identificadores e Geografia
    columns {
      name = "station_id"
      type = "string"
    }
    columns {
      name = "codigo_ibge"
      type = "bigint"
    }
    columns {
      name = "municipio"
      type = "string"
    }
    columns {
      name = "lat"
      type = "double"
    }
    columns {
      name = "lon"
      type = "double"
    }
    columns {
      name = "altitude"
      type = "double"
    }
    columns {
      name = "date"
      type = "string"
    }

    # Observacoes Meteorologicas Diarias
    columns {
      name = "precip_mm"
      type = "double"
    }
    columns {
      name = "temp_min"
      type = "double"
    }
    columns {
      name = "temp_max"
      type = "double"
    }
    columns {
      name = "temp_avg"
      type = "double"
    }
    columns {
      name = "humidity_avg"
      type = "double"
    }
    columns {
      name = "pressure_avg"
      type = "double"
    }
    columns {
      name = "wind_speed"
      type = "double"
    }
    columns {
      name = "solar_radiation"
      type = "double"
    }

    # Alvo D+1
    columns {
      name = "precip_tomorrow"
      type = "double"
    }
    columns {
      name = "rain_tomorrow"
      type = "int"
    }

    # Features Preditivas
    columns {
      name = "precip_lag_1d"
      type = "double"
    }
    columns {
      name = "precip_lag_2d"
      type = "double"
    }
    columns {
      name = "precip_sum_3d"
      type = "double"
    }
    columns {
      name = "precip_sum_7d"
      type = "double"
    }
    columns {
      name = "rain_days_7d"
      type = "double"
    }
    columns {
      name = "pressure_change_24h"
      type = "double"
    }
    columns {
      name = "dry_days"
      type = "double"
    }
    columns {
      name = "temp_avg_3d"
      type = "double"
    }
    columns {
      name = "humidity_avg_3d"
      type = "double"
    }
    columns {
      name = "day_of_year_sin"
      type = "double"
    }
    columns {
      name = "day_of_year_cos"
      type = "double"
    }
  }
}

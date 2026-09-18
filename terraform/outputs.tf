output "data_lake_bucket_id" {
  description = "Nome do bucket S3 do Data Lake"
  value       = aws_s3_bucket.data_lake.id
}

output "glue_database_name" {
  description = "Nome da base de dados do catalogo Glue"
  value       = aws_glue_catalog_database.agroclima_db.name
}

output "gold_features_table_name" {
  description = "Tabela externa para consumo analitico via Athena"
  value       = aws_glue_catalog_table.gold_features_table.name
}

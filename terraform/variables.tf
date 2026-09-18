variable "aws_region" {
  description = "Regiao da AWS para implantacao"
  type        = string
  default     = "us-east-1"
}

variable "bucket_name" {
  description = "Nome unico do bucket do Data Lake"
  type        = string
  default     = "agroclima-rs-lake-4302"
}

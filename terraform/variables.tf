variable "region" {
  description = "AWS region for EC2 and VPC"
  default     = "eu-north-1"
}

variable "instance_type" {
  description = "EC2 instance type"
  default     = "t3.small"
}

variable "app_name" {
  description = "Tag prefix for all resources"
  default     = "puf-pay"
}

variable "github_repo" {
  description = "Public GitHub repo to clone on the instance"
  default     = "https://github.com/jayjain2365/ChipVault.git"
}

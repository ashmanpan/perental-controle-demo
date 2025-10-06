terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket         = "parental-control-terraform-state-mumbai"
    key            = "terraform.tfstate"
    region         = "ap-south-1"  # Mumbai
    encrypt        = true
    dynamodb_table = "terraform-state-lock"
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "ParentalControl"
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  }
}

# Local variables
locals {
  name_prefix = "pc-${var.environment}"
  common_tags = {
    Project     = "ParentalControl"
    Environment = var.environment
  }
}

# Data sources
data "aws_caller_identity" "current" {}
data "aws_availability_zones" "available" {
  state = "available"
}

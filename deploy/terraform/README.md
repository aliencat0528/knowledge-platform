# Terraform 部署規劃

> 此目錄為未來擴展預留，目前為規劃文件。

## 概述

當專案需要更進階的基礎設施管理時，可使用 Terraform 進行：
- 多環境管理（dev/staging/prod）
- 自動化基礎設施佈建
- 版本控制的基礎設施變更

## 支援的雲端平台

### 1. DigitalOcean（推薦入門）

```hcl
# main.tf 範例
terraform {
  required_providers {
    digitalocean = {
      source  = "digitalocean/digitalocean"
      version = "~> 2.0"
    }
  }
}

resource "digitalocean_droplet" "knowledge" {
  image  = "docker-20-04"
  name   = "knowledge-platform"
  region = "sgp1"  # Singapore
  size   = "s-1vcpu-1gb"

  user_data = file("cloud-init.yml")
}

resource "digitalocean_volume" "data" {
  name   = "knowledge-data"
  region = "sgp1"
  size   = 10  # GB
}
```

預估成本：~$6/月

### 2. AWS EC2 + EBS

```hcl
# main.tf 範例
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

resource "aws_instance" "knowledge" {
  ami           = "ami-xxxxx"  # Ubuntu 22.04
  instance_type = "t3.micro"

  root_block_device {
    volume_size = 20
  }

  tags = {
    Name = "knowledge-platform"
  }
}

resource "aws_ebs_volume" "data" {
  availability_zone = aws_instance.knowledge.availability_zone
  size              = 10
  type              = "gp3"
}
```

預估成本：~$10-15/月

### 3. GCP Compute Engine

```hcl
# main.tf 範例
terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

resource "google_compute_instance" "knowledge" {
  name         = "knowledge-platform"
  machine_type = "e2-micro"
  zone         = "asia-east1-a"  # Taiwan

  boot_disk {
    initialize_params {
      image = "ubuntu-os-cloud/ubuntu-2204-lts"
      size  = 20
    }
  }

  network_interface {
    network = "default"
    access_config {}
  }
}
```

預估成本：~$8-12/月

## 目錄結構（規劃）

```
terraform/
├── environments/
│   ├── dev/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── terraform.tfvars
│   └── prod/
│       ├── main.tf
│       ├── variables.tf
│       └── terraform.tfvars
├── modules/
│   ├── compute/
│   ├── network/
│   └── storage/
└── README.md
```

## 實作時機

建議在以下情況考慮 Terraform：

| 條件 | 說明 |
|------|------|
| 多環境需求 | 需要 dev/staging/prod 環境 |
| 團隊協作 | 多人管理基礎設施 |
| 災難恢復 | 需要快速重建環境能力 |
| 成本優化 | 需要精確控制雲端資源 |

## 學習資源

- [Terraform 官方教學](https://developer.hashicorp.com/terraform/tutorials)
- [DigitalOcean Terraform Provider](https://registry.terraform.io/providers/digitalocean/digitalocean/latest/docs)
- [AWS Terraform Provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)

## 下一步

Phase 7 可選擇實作以下其一：
1. **7A**: Docker Compose + VPS 手動部署
2. **7B**: Terraform + DigitalOcean 自動化部署
3. **7C**: Terraform + AWS 企業級部署

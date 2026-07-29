# Rafeeq Kernel v2.3.0 — Terraform Infrastructure
# Basic DigitalOcean deployment example

terraform {
  required_providers {
    digitalocean = {
      source  = "digitalocean/digitalocean"
      version = "~> 2.0"
    }
  }
}

variable "do_token" {
  description = "DigitalOcean API Token"
  type        = string
  sensitive   = true
}

provider "digitalocean" {
  token = var.do_token
}

# Droplet
resource "digitalocean_droplet" "rafeeq" {
  image    = "ubuntu-22-04-x64"
  name     = "rafeeq-production"
  region   = "nyc1"
  size     = "s-2vcpu-4gb"
  ssh_keys = [digitalocean_ssh_key.rafeeq.id]

  user_data = <<-EOF
              #!/bin/bash
              apt-get update
              apt-get install -y docker.io docker-compose
              systemctl enable docker
              EOF

  tags = ["rafeeq", "production"]
}

# SSH Key
resource "digitalocean_ssh_key" "rafeeq" {
  name       = "rafeeq-deploy-key"
  public_key = file("~/.ssh/id_rsa.pub")
}

# Firewall
resource "digitalocean_firewall" "rafeeq" {
  name = "rafeeq-firewall"

  droplet_ids = [digitalocean_droplet.rafeeq.id]

  inbound_rule {
    protocol         = "tcp"
    port_range       = "22"
    source_addresses = ["0.0.0.0/0", "::/0"]
  }

  inbound_rule {
    protocol         = "tcp"
    port_range       = "80"
    source_addresses = ["0.0.0.0/0", "::/0"]
  }

  inbound_rule {
    protocol         = "tcp"
    port_range       = "443"
    source_addresses = ["0.0.0.0/0", "::/0"]
  }

  outbound_rule {
    protocol              = "tcp"
    port_range            = "1-65535"
    destination_addresses = ["0.0.0.0/0", "::/0"]
  }
}

# Domain
resource "digitalocean_domain" "rafeeq" {
  name = "rafeeq.ai"
}

resource "digitalocean_record" "www" {
  domain = digitalocean_domain.rafeeq.name
  type   = "A"
  name   = "www"
  value  = digitalocean_droplet.rafeeq.ipv4_address
}

output "server_ip" {
  value = digitalocean_droplet.rafeeq.ipv4_address
}

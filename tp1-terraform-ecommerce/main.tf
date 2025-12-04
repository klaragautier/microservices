terraform {
  required_providers {
    docker = {
      source  = "kreuzwerker/docker"
      version = "~> 3.0"
    }
  }
}

provider "docker" {}

variable "service_name1" {
  type        = string
  description = "Nom du microservice"
  default     = "catalogue"
}

variable "service_name2" {
  type        = string
  description = "Nom du microservice"
  default     = "cart"
}

variable "external_port1" {
  type        = number
  description = "Port exposé sur la machine hôte"
  default     = 8081
}

variable "external_port2" {
  type        = number
  description = "Port exposé sur la machine hôte"
  default     = 8082
}

resource "docker_network" "ecommerce" {
  name = "ecommerce-net"
}

resource "docker_image" "service" {
  name         = "nginxdemos/hello:latest"
  keep_locally = true
}

resource "docker_container" "service" {
  name  = "${var.service_name1}-service"
  image = docker_image.service.image_id

  networks_advanced {
    name = docker_network.ecommerce.name
  }


  ports {
    internal = 80
    external = var.external_port1
  }

  env = [
    "SERVICE_NAME=${var.service_name1}",
    "ENVIRONMENT=dev"
  ]
}


resource "docker_container" "cart" {
  name  = "${var.service_name2}-service"
  image = docker_image.service.image_id

  networks_advanced {
    name = docker_network.ecommerce.name
  }

  ports {
    internal = 80
    external = var.external_port2
  }

  env = [
    "SERVICE_NAME=${var.service_name2}",
    "ENVIRONMENT=dev"
  ]
}

output "service_url1" {
  value = "http://localhost:${var.external_port1}"
}

output "service_url2" {
  value = "http://localhost:${var.external_port2}"
}

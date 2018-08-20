job "dp-conceptual-search" {
  datacenters = ["eu-west-1"]
  region      = "eu"
  type        = "service"

  update {
    stagger          = "60s"
    min_healthy_time = "30s"
    healthy_deadline = "2m"
    max_parallel     = 1
    auto_revert      = true
  }

  group "web" {
    count = "{{WEB_TASK_COUNT}}"

    constraint {
      attribute = "${node.class}"
      operator  = "regexp"
      value     = "web.*"
    }

    restart {
      attempts = 3
      delay    = "15s"
      interval = "1m"
      mode     = "delay"
    }

    task "dp-conceptual-search" {
      driver = "docker"

      artifact {
        source = "s3::https://s3-eu-west-1.amazonaws.com/{{DEPLOYMENT_BUCKET}}/dp-conceptual-search/{{REVISION}}.tar.gz"
      }

      config {
        command = "${NOMAD_TASK_DIR}/start-task"

        args = [
          "python",
          "manager.py",
        ]

        image = "{{ECR_URL}}:concourse-{{REVISION}}"

        port_map {
          http = 5000
        }
      }

      service {
        name = "dp-conceptual-search"
        port = "http"
        tags = ["web"]

        check {
          type     = "http"
          path     = "/healthcheck"
          interval = "10s"
          timeout  = "2s"
        }
      }

      resources {
        cpu    = "{{WEB_RESOURCE_CPU}}"
        memory = "{{WEB_RESOURCE_MEM}}"

        network {
          port "http" {}
        }
      }

      template {
        source      = "${NOMAD_TASK_DIR}/vars-template"
        destination = "${NOMAD_TASK_DIR}/vars"
      }

      vault {
        policies = ["dp-conceptual-search"]
      }
    }
  }

  group "publishing" {
    count = "{{PUBLISHING_TASK_COUNT}}"

    constraint {
      attribute = "${node.class}"
      operator  = "regexp"
      value     = "publishing.*"
    }

    restart {
      attempts = 3
      delay    = "15s"
      interval = "1m"
      mode     = "delay"
    }

    task "dp-conceptual-search" {
      driver = "docker"

      artifact {
        source = "s3::https://s3-eu-west-1.amazonaws.com/{{DEPLOYMENT_BUCKET}}/dp-conceptual-search/{{REVISION}}.tar.gz"
      }

      config {
        command = "${NOMAD_TASK_DIR}/start-task"

        args = [
          "python",
          "manager.py",
        ]

        image = "{{ECR_URL}}:concourse-{{REVISION}}"

        port_map {
          http = 5000
        }
      }

      service {
        name = "dp-conceptual-search"
        port = "http"
        tags = ["publishing"]

        check {
          type     = "http"
          path     = "/healthcheck"
          interval = "10s"
          timeout  = "2s"
        }
      }

      resources {
        cpu    = "{{PUBLISHING_RESOURCE_CPU}}"
        memory = "{{PUBLISHING_RESOURCE_MEM}}"

        network {
          port "http" {}
        }
      }

      template {
        source      = "${NOMAD_TASK_DIR}/vars-template"
        destination = "${NOMAD_TASK_DIR}/vars"
      }

      vault {
        policies = ["dp-conceptual-search"]
      }
    }
  }
}
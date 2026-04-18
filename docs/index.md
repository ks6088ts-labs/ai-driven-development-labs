# ai-driven-development-labs

An experimental repository for practicing and validating **AI-Driven Development** workflows.
It combines an embedded-oriented subject (an IMU sensor HAL implementation) with a local observability stack
that supports its operation, so the full cycle — design, implementation, testing, documentation, and operations —
can be iterated on together with AI assistants such as GitHub Copilot.

Source code is hosted on GitHub:
**<https://github.com/ks6088ts-labs/ai-driven-development-labs>**

## What's included

- **IMU HAL (Hardware Abstraction Layer)** — `ai_driven_development_labs/imu/`
    - Abstraction over sensors and buses (I2C / SPI) via the `ISensorHAL` / `IBusDriver` interfaces
    - Real-device implementations for STMicroelectronics (e.g. LSM6DSO) and TDK InvenSense (e.g. ICM-42688-P)
    - Mock implementations for testing, a CLI to initialise and read sensors, and OpenTelemetry-based telemetry
    - Design details: [IMU HAL documentation](imu-hal.md)
- **Local observability stack** — `compose.observability.yml` / `docker/observability/`
    - One-command (`make obs-up`) OTel Collector → Prometheus / Jaeger → Grafana pipeline
    - Pre-provisioned Grafana data sources and an IMU dashboard
    - Setup and operations guide: [Observability documentation](observability.md)
- **Development & CI/CD foundation**
    - Package management with `uv`, linting with `ruff` / `ty` / `pyrefly`, and tests with `pytest`
    - Dockerfile and GitHub Actions workflows that publish images to Docker Hub and GHCR
    - MkDocs (Material + i18n) documentation site with automated deployment

## Prerequisites

- [Python 3.10+](https://www.python.org/downloads/)
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- [GNU Make](https://www.gnu.org/software/make/)

## Development instructions

### Local development

Use Makefile to run the project locally.

```shell
# help
make

# install dependencies for development
make install-deps-dev

# run tests
make test

# run CI tests
make ci-test
```

### Docker development

```shell
# build docker image
make docker-build

# run docker container
make docker-run

# run CI tests in docker container
make ci-test-docker
```

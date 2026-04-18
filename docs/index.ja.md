# ai-driven-development-labs

AI 駆動開発 (AI-Driven Development) の実践・検証を目的とした実験用リポジトリです。
組み込み寄りの題材 (IMU センサーの HAL 実装) と、その運用を支えるローカル可観測性スタックを組み合わせ、
設計・実装・テスト・ドキュメント・運用までを AI アシスタント (GitHub Copilot など) と共に進めるワークフローを検証しています。

ソースコードは GitHub で公開しています:
**<https://github.com/ks6088ts-labs/ai-driven-development-labs>**

## 同梱されているもの

- **IMU HAL (Hardware Abstraction Layer)** — `ai_driven_development_labs/imu/`
    - `ISensorHAL` / `IBusDriver` インターフェースによる、センサーとバス (I2C / SPI) の抽象化
    - 実機向け実装: STMicroelectronics (LSM6DSO 等) / TDK InvenSense (ICM-42688-P 等)
    - テスト用 Mock 実装、センサーを初期化・読み出しするための CLI、OpenTelemetry によるテレメトリ送出
    - 設計詳細: [IMU HAL ドキュメント](imu-hal.ja.md)
- **ローカル可観測性スタック** — `compose.observability.yml` / `docker/observability/`
    - `make obs-up` 一発で起動する OTel Collector → Prometheus / Jaeger → Grafana パイプライン
    - プロビジョニング済みの Grafana データソースと IMU 用ダッシュボード
    - セットアップ / 運用手順: [Observability ドキュメント](observability.ja.md)
- **開発・CI/CD 基盤**
    - `uv` ベースのパッケージ管理、`ruff` / `ty` / `pyrefly` による lint、`pytest` によるテスト
    - Dockerfile と GitHub Actions による Docker Hub / GHCR へのイメージ公開
    - MkDocs (Material + i18n) によるドキュメントサイトの自動デプロイ

## 前提条件

- [Python 3.10+](https://www.python.org/downloads/)
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- [GNU Make](https://www.gnu.org/software/make/)

## 開発手順

### ローカル開発

Makefile を利用してプロジェクトをローカルで実行します。

```shell
# ヘルプを表示
make

# 開発用の依存関係をインストール
make install-deps-dev

# テストを実行
make test

# CI テストを実行
make ci-test
```

### Docker による開発

```shell
# Docker イメージをビルド
make docker-build

# Docker コンテナを実行
make docker-run

# Docker コンテナ内で CI テストを実行
make ci-test-docker
```

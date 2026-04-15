# IMU HAL 開発者向けドキュメント

## 1. アーキテクチャ概要

### レイヤ構造図

```
┌────────────────────────────────────────────────────────┐
│                   アプリケーション層                       │
│              (CLI / テスト / ユーザーコード)               │
└───────────────────────┬────────────────────────────────┘
                        │ ISensorHAL
┌───────────────────────▼────────────────────────────────┐
│                    センサー HAL 層                        │
│  ┌──────────────┐  ┌─────────────────┐  ┌───────────┐  │
│  │ MockSensorHAL│  │STMicroSensorHAL │  │TDKSensor  │  │
│  │              │  │ (LSM6DSO 等)    │  │HAL        │  │
│  └──────────────┘  └─────────────────┘  └───────────┘  │
└───────────────────────┬────────────────────────────────┘
                        │ IBusDriver
┌───────────────────────▼────────────────────────────────┐
│                    バスドライバ層                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │MockBusDriver │  │ I2CBusDriver │  │ SPIBusDriver │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
└────────────────────────────────────────────────────────┘
```

### モジュール依存関係

```
ai_driven_development_labs/
├── bus/
│   ├── interfaces.py      # IBusDriver (抽象基底クラス)
│   ├── mock.py            # MockBusDriver (テスト用仮想バス)
│   ├── i2c.py             # I2CBusDriver (I2C ペリフェラル)
│   └── spi.py             # SPIBusDriver (SPI ペリフェラル)
└── imu/
    ├── interfaces.py      # ISensorHAL (抽象基底クラス)
    ├── models.py          # SensorInfo, SensorEvent, SensorType 等
    ├── factory.py         # create_bus_driver(), create_sensor_hal()
    ├── cli.py             # CLI エントリーポイント
    └── hal/
        ├── mock.py        # MockSensorHAL (テスト用モック)
        ├── stmicro.py     # STMicroSensorHAL (LSM6DSO / ISM330DHCX)
        └── tdk.py         # TDKSensorHAL (ICM-42688-P 等)
```

### 設計原則

本 IMU HAL は [Android Sensors AIDL HAL](https://source.android.com/docs/core/interaction/sensors/sensors-aidl-hal) の設計を参考にしており、以下の原則に従っています:

- **依存性逆転の原則 (DIP)**: アプリケーション層は `ISensorHAL` と `IBusDriver` の抽象インターフェースのみに依存する
- **依存性注入 (DI)**: バスドライバは `initialize(bus)` を通じてセンサー HAL に注入される
- **テスト容易性**: `MockBusDriver` と `MockSensorHAL` によりハードウェアなしでテスト可能

---

## 2. クイックスタート

### 前提条件

```bash
# 依存パッケージのインストール
uv sync
```

### MockSensorHAL + CLI による動作確認

```bash
# センサー一覧の表示 (mock HAL / mock バス)
uv run imu-hal list-sensors --hal mock --bus mock

# センサーデータのポーリング (3 回、1 秒間隔)
uv run imu-hal poll --hal mock --bus mock --count 3 --interval 1.0

# JSON 形式で出力
uv run imu-hal poll --hal mock --bus mock --format json --count 2
```

### Python コードからの利用

```python
from ai_driven_development_labs.bus.mock import MockBusDriver
from ai_driven_development_labs.imu.hal.mock import MockSensorHAL

# バスドライバとセンサー HAL を生成
bus = MockBusDriver()
hal = MockSensorHAL()

# HAL を初期化 (バスドライバを DI で注入)
hal.initialize(bus)

# センサー一覧の取得
sensors = hal.get_sensor_list()
for sensor in sensors:
    print(f"  {sensor.name} (handle={sensor.sensor_handle})")

# センサーを有効化してデータ取得
for sensor in sensors:
    hal.activate(sensor.sensor_handle, True)

events = hal.get_events()
for event in events:
    print(f"  {event.sensor_type.name}: {event.values}")

# リソース解放
hal.finalize()
```

### STMicro HAL + MockBusDriver による動作確認

```python
from ai_driven_development_labs.bus.mock import MockBusDriver
from ai_driven_development_labs.imu.hal.stmicro import STMicroSensorHAL

# LSM6DSO のレジスタマップを模倣
register_map = {
    0x0F: 0x6C,  # WHO_AM_I = LSM6DSO
    0x1E: 0x03,  # STATUS_REG: accel + gyro data ready
}
bus = MockBusDriver(register_map=register_map)
hal = STMicroSensorHAL()
hal.initialize(bus)

sensors = hal.get_sensor_list()
hal.finalize()
```

---

## 3. 新規ベンダー追加ガイド

`ISensorHAL` を実装して新しい IMU ベンダーを追加する手順を説明します。

### ステップ 1: HAL クラスの作成

`ai_driven_development_labs/imu/hal/` に新しいファイルを作成します。例: `bosch.py`

```python
"""Bosch IMU HAL (BMI270 等) の実装。"""

import struct
import time

from ai_driven_development_labs.bus.interfaces import IBusDriver
from ai_driven_development_labs.imu.interfaces import ISensorHAL
from ai_driven_development_labs.imu.models import ReportingMode, SensorEvent, SensorInfo, SensorType

_ACCEL_HANDLE = 1
_GYRO_HANDLE = 2

# レジスタアドレス (BMI270 の例)
_REG_CHIP_ID = 0x00   # CHIP_ID
_REG_STATUS = 0x03    # STATUS

# スケール変換係数 (±2g, ±2000 dps の例)
_ACCEL_SENSITIVITY_G_PER_LSB = 1.0 / 16384.0
_GYRO_SENSITIVITY_DPS_PER_LSB = 1.0 / 16.4


class BoschSensorHAL(ISensorHAL):
    """Bosch 製 IMU (BMI270 等) 用 HAL。"""

    SUPPORTED_DEVICES: dict[int, str] = {
        0x24: "BMI270",
    }

    def __init__(self) -> None:
        self._bus: IBusDriver | None = None
        self._device_name: str = ""
        self._active: dict[int, bool] = {}

    def initialize(self, bus: IBusDriver) -> None:
        bus.open()
        self._bus = bus

        chip_id = bus.read_register(_REG_CHIP_ID, 1)[0]
        if chip_id not in self.SUPPORTED_DEVICES:
            bus.close()
            self._bus = None
            raise RuntimeError(f"Unsupported device: CHIP_ID=0x{chip_id:02X}")
        self._device_name = self.SUPPORTED_DEVICES[chip_id]
        self._active = {_ACCEL_HANDLE: False, _GYRO_HANDLE: False}

    def get_sensor_list(self) -> list[SensorInfo]:
        return [
            SensorInfo(
                sensor_handle=_ACCEL_HANDLE,
                name=f"{self._device_name} Accelerometer",
                vendor="Bosch",
                sensor_type=SensorType.ACCELEROMETER,
                reporting_mode=ReportingMode.CONTINUOUS,
            ),
            SensorInfo(
                sensor_handle=_GYRO_HANDLE,
                name=f"{self._device_name} Gyroscope",
                vendor="Bosch",
                sensor_type=SensorType.GYROSCOPE,
                reporting_mode=ReportingMode.CONTINUOUS,
            ),
        ]

    def activate(self, sensor_handle: int, enabled: bool) -> None:
        self._active[sensor_handle] = enabled

    def configure(self, sensor_handle: int, sampling_period_us: int, max_report_latency_us: int) -> None:
        pass  # ODR 設定を実装する

    def flush(self, sensor_handle: int) -> None:
        pass

    def get_events(self) -> list[SensorEvent]:
        if self._bus is None:
            return []
        # STATUS レジスタでデータ準備完了を確認し、出力レジスタを読み出す
        # ... 実装省略 ...
        return []

    def finalize(self) -> None:
        if self._bus is not None:
            self._bus.close()
            self._bus = None
        self._active = {}
```

### ステップ 2: factory.py への登録

`ai_driven_development_labs/imu/factory.py` の `create_sensor_hal()` に新しい HAL を追加します:

```python
from ai_driven_development_labs.imu.hal.bosch import BoschSensorHAL

def create_sensor_hal(hal_type: str) -> ISensorHAL:
    match hal_type:
        case "mock":
            return MockSensorHAL()
        case "stmicro":
            return STMicroSensorHAL()
        case "tdk":
            return TDKSensorHAL()
        case "bosch":           # 追加
            return BoschSensorHAL()
        case _:
            raise ValueError(f"Unknown HAL type: {hal_type}")
```

### ステップ 3: テストの追加

`tests/test_imu/test_hal/` に新しいテストファイルを追加します:

```python
# tests/test_imu/test_hal/test_bosch.py
from ai_driven_development_labs.bus.mock import MockBusDriver
from ai_driven_development_labs.imu.hal.bosch import BoschSensorHAL
from ai_driven_development_labs.imu.models import SensorType


class TestBoschSensorHAL:
    def test_initialize_with_supported_device(self):
        bus = MockBusDriver(register_map={0x00: 0x24})  # BMI270
        hal = BoschSensorHAL()
        hal.initialize(bus)
        sensors = hal.get_sensor_list()
        assert any(s.sensor_type == SensorType.ACCELEROMETER for s in sensors)
        hal.finalize()
```

---

## 4. 新規バスドライバ追加ガイド

`IBusDriver` を実装して新しいペリフェラルバスを追加する手順を説明します。

### ステップ 1: バスドライバクラスの作成

`ai_driven_development_labs/bus/` に新しいファイルを作成します。例: `uart.py`

```python
"""UART バスドライバの実装。"""

from ai_driven_development_labs.bus.interfaces import IBusDriver


class UARTBusDriver(IBusDriver):
    """UART を通じてセンサーと通信するバスドライバ。"""

    def __init__(self, port: str = "/dev/ttyUSB0", baudrate: int = 115200):
        self._port = port
        self._baudrate = baudrate
        self._serial = None  # pyserial などを利用

    def open(self) -> None:
        """UART ポートを開く。"""
        # import serial
        # self._serial = serial.Serial(self._port, self._baudrate)
        ...

    def close(self) -> None:
        """UART ポートを閉じる。"""
        if self._serial is not None:
            # self._serial.close()
            self._serial = None

    def read_register(self, register: int, length: int) -> bytes:
        """レジスタから指定バイト数を読み出す。"""
        # プロトコルに応じた実装
        ...
        return bytes(length)

    def write_register(self, register: int, data: bytes) -> None:
        """レジスタにデータを書き込む。"""
        ...

    def transfer(self, data: bytes) -> bytes:
        """全二重転送を行う。"""
        ...
        return bytes(len(data))
```

### ステップ 2: factory.py への登録

`ai_driven_development_labs/imu/factory.py` の `create_bus_driver()` に追加します:

```python
from ai_driven_development_labs.bus.uart import UARTBusDriver

def create_bus_driver(bus_type: str, bus_id: int = 0, device: int = 0) -> IBusDriver:
    match bus_type:
        case "mock":
            return MockBusDriver()
        case "i2c":
            return I2CBusDriver(bus_id=bus_id, address=device)
        case "spi":
            return SPIBusDriver(bus=bus_id, device=device)
        case "uart":            # 追加
            return UARTBusDriver(port=f"/dev/ttyUSB{bus_id}")
        case _:
            raise ValueError(f"Unknown bus type: {bus_type}")
```

### ステップ 3: テストの追加

`IBusDriver` の各メソッドが仕様通りに動作することを確認するテストを追加します:

```python
# tests/test_bus/test_uart_bus.py
from ai_driven_development_labs.bus.uart import UARTBusDriver
from ai_driven_development_labs.bus.interfaces import IBusDriver


class TestUARTBusDriver:
    def test_is_instance_of_ibus_driver(self):
        bus = UARTBusDriver()
        assert isinstance(bus, IBusDriver)
```

---

## 5. API リファレンス

### `IBusDriver` (抽象基底クラス)

**モジュール**: `ai_driven_development_labs.bus.interfaces`

ペリフェラルバスと通信するための抽象インターフェース。

| メソッド | シグネチャ | 説明 |
|---------|-----------|------|
| `open` | `() -> None` | バスを初期化して通信を開始する。 |
| `close` | `() -> None` | バスを閉じてリソースを解放する。 |
| `read_register` | `(register: int, length: int) -> bytes` | 指定レジスタから `length` バイトを読み出す。 |
| `write_register` | `(register: int, data: bytes) -> None` | 指定レジスタにデータを書き込む。 |
| `transfer` | `(data: bytes) -> bytes` | 全二重転送を行い受信データを返す (SPI 用)。 |

### `ISensorHAL` (抽象基底クラス)

**モジュール**: `ai_driven_development_labs.imu.interfaces`

Android `ISensors.aidl` に準拠したセンサー HAL の抽象インターフェース。

| メソッド | シグネチャ | 説明 |
|---------|-----------|------|
| `initialize` | `(bus: IBusDriver) -> None` | HAL を初期化する。バスドライバを DI で受け取る。 |
| `get_sensor_list` | `() -> list[SensorInfo]` | 利用可能なセンサー一覧を返す。 |
| `activate` | `(sensor_handle: int, enabled: bool) -> None` | センサーを有効化/無効化する。 |
| `configure` | `(sensor_handle: int, sampling_period_us: int, max_report_latency_us: int) -> None` | サンプリング周期と最大レポート遅延を設定する。 |
| `flush` | `(sensor_handle: int) -> None` | FIFO バッファをフラッシュする。 |
| `get_events` | `() -> list[SensorEvent]` | 最新のセンサーイベントを取得する。 |
| `finalize` | `() -> None` | HAL を終了しリソースを解放する。 |

### `SensorInfo` (データクラス)

**モジュール**: `ai_driven_development_labs.imu.models`

Android `SensorInfo.aidl` に準拠したセンサー情報。`frozen=True` の不変データクラス。

| フィールド | 型 | 説明 |
|-----------|---|------|
| `sensor_handle` | `int` | センサーを一意に識別するハンドル。 |
| `name` | `str` | センサーの名前。 |
| `vendor` | `str` | センサーのベンダー名。 |
| `sensor_type` | `SensorType` | センサーの種別。 |
| `version` | `int` | HAL バージョン (デフォルト: 1)。 |
| `max_range` | `float` | センサーの最大計測範囲。 |
| `resolution` | `float` | センサーの分解能。 |
| `power` | `float` | 消費電流 (mA)。 |
| `min_delay` | `int` | 最小サンプリング周期 (μs)。0 はオンデマンドを意味する。 |
| `max_delay` | `int` | 最大サンプリング周期 (μs)。 |
| `fifo_reserved_event_count` | `int` | FIFO に予約されたイベント数。 |
| `fifo_max_event_count` | `int` | FIFO の最大イベント数。 |
| `reporting_mode` | `ReportingMode` | レポートモード。 |

### `SensorEvent` (データクラス)

**モジュール**: `ai_driven_development_labs.imu.models`

Android `Event.aidl` に準拠したセンサーイベント。

| フィールド | 型 | 説明 |
|-----------|---|------|
| `sensor_handle` | `int` | イベントを生成したセンサーのハンドル。 |
| `sensor_type` | `SensorType` | センサーの種別。 |
| `timestamp_ns` | `int` | イベントのタイムスタンプ (ナノ秒)。 |
| `values` | `list[float]` | センサー計測値のリスト (例: [x, y, z])。 |

### `SensorType` (IntEnum)

**モジュール**: `ai_driven_development_labs.imu.models`

| 値 | 定数 | 説明 |
|---|-----|------|
| 1 | `ACCELEROMETER` | 加速度計 |
| 4 | `GYROSCOPE` | ジャイロスコープ |
| 35 | `ACCELEROMETER_UNCALIBRATED` | 未補正加速度計 |
| 16 | `GYROSCOPE_UNCALIBRATED` | 未補正ジャイロスコープ |

### `ReportingMode` (IntEnum)

**モジュール**: `ai_driven_development_labs.imu.models`

| 値 | 定数 | 説明 |
|---|-----|------|
| 0 | `CONTINUOUS` | 一定周期でデータを報告する。 |
| 1 | `ON_CHANGE` | 値が変化したときにデータを報告する。 |
| 2 | `ONE_SHOT` | 一度だけデータを報告する。 |
| 3 | `SPECIAL_TRIGGER` | 特定のトリガー条件でデータを報告する。 |

### `MockBusDriver`

**モジュール**: `ai_driven_development_labs.bus.mock`

メモリ上で仮想レジスタマップを管理するモックバスドライバ。テストやエミュレーション用途。

```python
MockBusDriver(register_map: dict[int, int] | None = None)
```

- `register_map`: 初期レジスタ値の辞書 `{register_addr: value}`。未登録レジスタは `0x00` を返す。

### `MockSensorHAL`

**モジュール**: `ai_driven_development_labs.imu.hal.mock`

ハードウェアなしで動作するモック HAL。ランダムまたは固定パターンのセンサーデータを生成する。

```python
MockSensorHAL(
    accel_range: float = 16.0,
    gyro_range: float = 2000.0,
    noise_stddev: float = 0.01,
)
```

- `accel_range`: 加速度計のフルスケール範囲 (g)。
- `gyro_range`: ジャイロスコープのフルスケール範囲 (dps)。
- `noise_stddev`: センサーノイズの標準偏差。

### `STMicroSensorHAL`

**モジュール**: `ai_driven_development_labs.imu.hal.stmicro`

STMicroelectronics 製 IMU (LSM6DSO / ISM330DHCX 等) 用 HAL。WHO_AM_I レジスタ (0x0F) でデバイスを識別する。

対応デバイス:

| WHO_AM_I | デバイス名 |
|---------|----------|
| 0x6C | LSM6DSO |
| 0x6B | ISM330DHCX |

### `TDKSensorHAL`

**モジュール**: `ai_driven_development_labs.imu.hal.tdk`

TDK InvenSense 製 IMU (ICM-42688-P 等) 用 HAL。WHO_AM_I レジスタ (0x75) でデバイスを識別する。

---

## 参考資料

- [Android Sensors AIDL HAL - 検証](https://source.android.com/docs/core/interaction/sensors/sensors-aidl-hal?hl=ja#validation)
- [Android ISensors.aidl](https://source.android.com/docs/core/interaction/sensors?hl=ja)

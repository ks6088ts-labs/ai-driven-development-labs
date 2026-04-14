"""Data models for IMU HAL, based on Android SensorInfo.aidl / Event.aidl."""

from dataclasses import dataclass, field
from enum import IntEnum


class SensorType(IntEnum):
    """Android SensorType.aidl 準拠のセンサー種別。"""

    ACCELEROMETER = 1
    GYROSCOPE = 4
    ACCELEROMETER_UNCALIBRATED = 35
    GYROSCOPE_UNCALIBRATED = 16


class ReportingMode(IntEnum):
    """センサーのレポートモード。"""

    CONTINUOUS = 0
    ON_CHANGE = 1
    ONE_SHOT = 2
    SPECIAL_TRIGGER = 3


@dataclass(frozen=True)
class SensorInfo:
    """Android SensorInfo.aidl に準拠したセンサー情報。

    Attributes:
        sensor_handle: センサーを一意に識別するハンドル。
        name: センサーの名前。
        vendor: センサーのベンダー名。
        sensor_type: センサーの種別。
        version: HAL バージョン。
        max_range: センサーの最大計測範囲。
        resolution: センサーの分解能。
        power: 消費電流 (mA)。
        min_delay: 最小サンプリング周期 (μs)。0 はオンデマンドを意味する。
        max_delay: 最大サンプリング周期 (μs)。
        fifo_reserved_event_count: FIFO に予約されたイベント数。
        fifo_max_event_count: FIFO の最大イベント数。
        reporting_mode: レポートモード。
    """

    sensor_handle: int
    name: str
    vendor: str
    sensor_type: SensorType
    version: int = 1
    max_range: float = 0.0
    resolution: float = 0.0
    power: float = 0.0
    min_delay: int = 0
    max_delay: int = 0
    fifo_reserved_event_count: int = 0
    fifo_max_event_count: int = 0
    reporting_mode: ReportingMode = ReportingMode.CONTINUOUS


@dataclass
class SensorEvent:
    """Android Event.aidl に準拠したセンサーイベント。

    Attributes:
        sensor_handle: イベントを生成したセンサーのハンドル。
        sensor_type: センサーの種別。
        timestamp_ns: イベントのタイムスタンプ (ナノ秒)。
        values: センサー計測値のリスト。
    """

    sensor_handle: int
    sensor_type: SensorType
    timestamp_ns: int
    values: list[float] = field(default_factory=list)

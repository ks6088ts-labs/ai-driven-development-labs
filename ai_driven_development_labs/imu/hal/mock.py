"""Mock sensor HAL for hardware-free testing and emulation."""

import random
import time

from ai_driven_development_labs.bus.interfaces import IBusDriver
from ai_driven_development_labs.imu.interfaces import ISensorHAL
from ai_driven_development_labs.imu.models import ReportingMode, SensorEvent, SensorInfo, SensorType

_ACCEL_HANDLE = 1
_GYRO_HANDLE = 2

_GRAVITY = 9.81


class MockSensorHAL(ISensorHAL):
    """ハードウェアなしで動作するモック HAL。

    ランダムまたは固定パターンのセンサーデータを生成する。
    テストおよびソフトウェアエミュレーション用途。
    """

    def __init__(
        self,
        accel_range: float = 16.0,
        gyro_range: float = 2000.0,
        noise_stddev: float = 0.01,
    ):
        """
        Args:
            accel_range: 加速度計のフルスケール範囲 (g)。デフォルト ±16g。
            gyro_range: ジャイロスコープのフルスケール範囲 (dps)。デフォルト ±2000 dps。
            noise_stddev: センサーノイズの標準偏差。
        """
        self._accel_range = accel_range
        self._gyro_range = gyro_range
        self._noise_stddev = noise_stddev
        self._bus: IBusDriver | None = None
        self._active: dict[int, bool] = {}
        self._sampling_period_us: dict[int, int] = {}

    def initialize(self, bus: IBusDriver) -> None:
        """HAL を初期化する。バスドライバを DI で受け取る。

        Args:
            bus: 使用するバスドライバ。
        """
        self._bus = bus
        self._active = {_ACCEL_HANDLE: False, _GYRO_HANDLE: False}

    def get_sensor_list(self) -> list[SensorInfo]:
        """利用可能なセンサー一覧を返す。

        Returns:
            加速度計とジャイロスコープの情報リスト。
        """
        return [
            SensorInfo(
                sensor_handle=_ACCEL_HANDLE,
                name="Mock Accelerometer",
                vendor="MockVendor",
                sensor_type=SensorType.ACCELEROMETER,
                max_range=self._accel_range,
                reporting_mode=ReportingMode.CONTINUOUS,
            ),
            SensorInfo(
                sensor_handle=_GYRO_HANDLE,
                name="Mock Gyroscope",
                vendor="MockVendor",
                sensor_type=SensorType.GYROSCOPE,
                max_range=self._gyro_range,
                reporting_mode=ReportingMode.CONTINUOUS,
            ),
        ]

    def activate(self, sensor_handle: int, enabled: bool) -> None:
        """センサーを有効化/無効化する。

        Args:
            sensor_handle: 対象センサーのハンドル。
            enabled: True で有効化、False で無効化。
        """
        self._active[sensor_handle] = enabled

    def configure(self, sensor_handle: int, sampling_period_us: int, max_report_latency_us: int) -> None:
        """サンプリング周期と最大レポート遅延を設定する。

        Args:
            sensor_handle: 対象センサーのハンドル。
            sampling_period_us: サンプリング周期 (μs)。
            max_report_latency_us: 最大レポート遅延 (μs)。
        """
        self._sampling_period_us[sensor_handle] = sampling_period_us

    def flush(self, sensor_handle: int) -> None:
        """FIFO バッファをフラッシュする。

        Args:
            sensor_handle: 対象センサーのハンドル。
        """

    def get_events(self) -> list[SensorEvent]:
        """最新のセンサーイベントを取得する。

        アクティブなセンサーのみイベントを生成する。
        加速度計は重力加速度 z=9.81 のオフセット付きランダムノイズを返す。

        Returns:
            センサーイベントのリスト。
        """
        events: list[SensorEvent] = []
        ts = time.time_ns()

        def _noise() -> float:
            return random.gauss(0.0, self._noise_stddev)

        if self._active.get(_ACCEL_HANDLE, False):
            events.append(
                SensorEvent(
                    sensor_handle=_ACCEL_HANDLE,
                    sensor_type=SensorType.ACCELEROMETER,
                    timestamp_ns=ts,
                    values=[_noise(), _noise(), _GRAVITY + _noise()],
                )
            )

        if self._active.get(_GYRO_HANDLE, False):
            events.append(
                SensorEvent(
                    sensor_handle=_GYRO_HANDLE,
                    sensor_type=SensorType.GYROSCOPE,
                    timestamp_ns=ts,
                    values=[_noise(), _noise(), _noise()],
                )
            )

        return events

    def finalize(self) -> None:
        """HAL を終了しリソースを解放する。"""
        self._bus = None
        self._active = {}

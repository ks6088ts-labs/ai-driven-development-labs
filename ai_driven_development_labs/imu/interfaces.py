"""Abstract interfaces for IMU HAL, inspired by Android ISensors.aidl."""

from abc import ABC, abstractmethod

from ai_driven_development_labs.bus.interfaces import IBusDriver
from ai_driven_development_labs.imu.models import SensorEvent, SensorInfo

__all__ = ["IBusDriver", "ISensorHAL"]


class ISensorHAL(ABC):
    """Android ISensors.aidl に準拠したセンサー HAL の抽象インターフェース。

    バスドライバは initialize() 時に DI で注入される。
    アプリケーション層はこの ABC のみに依存し、具象クラスは外部から注入する。
    """

    @abstractmethod
    def initialize(self, bus: IBusDriver) -> None:
        """HAL を初期化する。バスドライバを DI で受け取る。

        Args:
            bus: 使用するバスドライバ。
        """
        ...

    @abstractmethod
    def get_sensor_list(self) -> list[SensorInfo]:
        """利用可能なセンサー一覧を返す。

        Returns:
            センサー情報のリスト。ハンドルは安定していること。
        """
        ...

    @abstractmethod
    def activate(self, sensor_handle: int, enabled: bool) -> None:
        """センサーを有効化/無効化する。

        Args:
            sensor_handle: 対象センサーのハンドル。
            enabled: True で有効化、False で無効化。
        """
        ...

    @abstractmethod
    def configure(self, sensor_handle: int, sampling_period_us: int, max_report_latency_us: int) -> None:
        """サンプリング周期と最大レポート遅延を設定する。

        Args:
            sensor_handle: 対象センサーのハンドル。
            sampling_period_us: サンプリング周期 (μs)。
            max_report_latency_us: 最大レポート遅延 (μs)。
        """
        ...

    @abstractmethod
    def flush(self, sensor_handle: int) -> None:
        """FIFO バッファをフラッシュする。

        Args:
            sensor_handle: 対象センサーのハンドル。
        """
        ...

    @abstractmethod
    def get_events(self) -> list[SensorEvent]:
        """最新のセンサーイベントを取得する。

        Returns:
            センサーイベントのリスト。
        """
        ...

    @abstractmethod
    def finalize(self) -> None:
        """HAL を終了しリソースを解放する。"""
        ...

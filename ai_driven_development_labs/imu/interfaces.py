"""Abstract interfaces for IMU HAL, inspired by Android ISensors.aidl."""

from abc import ABC, abstractmethod

from ai_driven_development_labs.imu.models import SensorEvent, SensorInfo


class IBusDriver(ABC):
    """ペリフェラルバスドライバの抽象インターフェース。

    SPI / I2C / UART などのバスドライバを統一的に扱うための ABC。
    具象クラスを ISensorHAL.initialize() に DI することで、
    ベンダー種別やバス種別の差異を吸収する。
    """

    @abstractmethod
    def open(self) -> None:
        """バスを初期化して通信を開始する。"""
        ...

    @abstractmethod
    def close(self) -> None:
        """バスを閉じてリソースを解放する。"""
        ...

    @abstractmethod
    def read_register(self, register: int, length: int) -> bytes:
        """指定レジスタから length バイト読み出す。

        Args:
            register: 読み出し対象のレジスタアドレス。
            length: 読み出すバイト数。

        Returns:
            読み出したデータ (bytes)。
        """
        ...

    @abstractmethod
    def write_register(self, register: int, data: bytes) -> None:
        """指定レジスタに data を書き込む。

        Args:
            register: 書き込み対象のレジスタアドレス。
            data: 書き込むデータ (bytes)。
        """
        ...

    @abstractmethod
    def transfer(self, data: bytes) -> bytes:
        """全二重転送を行い、受信データを返す。

        Args:
            data: 送信データ (bytes)。

        Returns:
            受信データ (bytes)。
        """
        ...


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

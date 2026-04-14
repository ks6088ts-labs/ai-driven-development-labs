"""Abstract interfaces for peripheral bus drivers."""

from abc import ABC, abstractmethod


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

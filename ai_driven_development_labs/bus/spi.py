"""SPI bus driver using Linux spidev."""

from typing import Any

from ai_driven_development_labs.bus.interfaces import IBusDriver

SPI_READ_MASK = 0x80


class SPIBusDriver(IBusDriver):
    """Linux spidev を使用した SPI バスドライバ。

    spidev がインストールされていない環境では ImportError を発生させる。
    """

    def __init__(self, bus: int = 0, device: int = 0, max_speed_hz: int = 1_000_000, mode: int = 0):
        """
        Args:
            bus: SPIバス番号。
            device: SPIデバイス番号。
            max_speed_hz: 最大クロック周波数 (Hz)。
            mode: SPI モード (0-3)。
        """
        self._bus = bus
        self._device = device
        self._max_speed_hz = max_speed_hz
        self._mode = mode
        self._spi: Any = None

    def open(self) -> None:
        """spidev を使用して SPI バスを初期化する。"""
        try:
            import spidev  # type: ignore[import-untyped]  # ty: ignore[unresolved-import]
        except ImportError as e:
            raise ImportError(
                "spidev パッケージが見つかりません。"
                " Raspberry Pi などの Linux 環境で `pip install spidev` を実行してください。"
            ) from e

        self._spi = spidev.SpiDev()
        self._spi.open(self._bus, self._device)
        self._spi.max_speed_hz = self._max_speed_hz
        self._spi.mode = self._mode

    def close(self) -> None:
        """SPI バスを閉じてリソースを解放する。"""
        if self._spi is not None:
            self._spi.close()
            self._spi = None

    def _check_open(self) -> None:
        if self._spi is None:
            raise RuntimeError("Bus is not open. Call open() first.")

    def read_register(self, register: int, length: int) -> bytes:
        """指定レジスタから length バイト読み出す。

        Args:
            register: 読み出し対象のレジスタアドレス。
            length: 読み出すバイト数。

        Returns:
            読み出したデータ (bytes)。
        """
        self._check_open()
        cmd = [register | SPI_READ_MASK] + [0x00] * length
        response = self._spi.xfer2(cmd)
        return bytes(response[1:])

    def write_register(self, register: int, data: bytes) -> None:
        """指定レジスタに data を書き込む。

        Args:
            register: 書き込み対象のレジスタアドレス。
            data: 書き込むデータ (bytes)。
        """
        self._check_open()
        cmd = [register & ~SPI_READ_MASK] + list(data)
        self._spi.xfer2(cmd)

    def transfer(self, data: bytes) -> bytes:
        """全二重転送を行い、受信データを返す。

        Args:
            data: 送信データ (bytes)。

        Returns:
            受信データ (bytes)。
        """
        self._check_open()
        response = self._spi.xfer2(list(data))
        return bytes(response)

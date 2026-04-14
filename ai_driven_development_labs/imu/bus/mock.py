"""Mock bus driver for hardware-free testing and emulation."""

from ai_driven_development_labs.imu.interfaces import IBusDriver

_SPI_READ_MASK = 0x80


class MockBusDriver(IBusDriver):
    """メモリ上で仮想レジスタマップを管理する Mock バスドライバ。

    テストやエミュレーション用途。
    """

    def __init__(self, register_map: dict[int, int] | None = None):
        """
        Args:
            register_map: 初期レジスタ値の辞書 {register_addr: value}
        """
        self._registers: dict[int, int] = register_map or {}
        self._is_open: bool = False

    def open(self) -> None:
        """バスを初期化して通信を開始する。"""
        self._is_open = True

    def close(self) -> None:
        """バスを閉じてリソースを解放する。"""
        self._is_open = False

    def _check_open(self) -> None:
        if not self._is_open:
            raise RuntimeError("Bus is not open. Call open() first.")

    def read_register(self, register: int, length: int) -> bytes:
        """レジスタマップから値を返す。未登録レジスタは 0x00 を返す。

        Args:
            register: 読み出し対象のレジスタアドレス。
            length: 読み出すバイト数。

        Returns:
            読み出したデータ (bytes)。
        """
        self._check_open()
        return bytes(self._registers.get(register + i, 0x00) for i in range(length))

    def write_register(self, register: int, data: bytes) -> None:
        """レジスタマップに値を書き込む。

        Args:
            register: 書き込み対象のレジスタアドレス。
            data: 書き込むデータ (bytes)。
        """
        self._check_open()
        for i, byte in enumerate(data):
            self._registers[register + i] = byte

    def transfer(self, data: bytes) -> bytes:
        """全二重転送を行い、受信データを返す。

        最初のバイトをコマンドとして解釈し、適切なレスポンスを返す。
        MSB が 1 の場合は読み出し、0 の場合は書き込みとして扱う。

        Args:
            data: 送信データ (bytes)。最初のバイトがコマンド/レジスタアドレス。

        Returns:
            受信データ (bytes)。
        """
        self._check_open()
        if not data:
            return b""

        command = data[0]
        is_read = bool(command & _SPI_READ_MASK)
        register = command & ~_SPI_READ_MASK

        if is_read:
            length = len(data) - 1
            read_data = bytes(self._registers.get(register + i, 0x00) for i in range(length))
            return bytes(1) + read_data
        else:
            for i, byte in enumerate(data[1:]):
                self._registers[register + i] = byte
            return bytes(len(data))

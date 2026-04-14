"""I2C bus driver using Linux smbus2."""

from ai_driven_development_labs.imu.interfaces import IBusDriver


class I2CBusDriver(IBusDriver):
    """Linux smbus2 を使用した I2C バスドライバ。

    smbus2 がインストールされていない環境では ImportError を発生させる。
    """

    def __init__(self, bus: int = 1, address: int = 0x6A):
        """
        Args:
            bus: I2C バス番号。
            address: デバイスの I2C アドレス。
        """
        self._bus_number = bus
        self._address = address
        self._smbus = None

    def open(self) -> None:
        """smbus2 を使用して I2C バスを初期化する。"""
        try:
            import smbus2
        except ImportError as e:
            raise ImportError(
                "smbus2 パッケージが見つかりません。"
                " Raspberry Pi などの Linux 環境で `pip install smbus2` を実行してください。"
            ) from e

        self._smbus = smbus2.SMBus(self._bus_number)

    def close(self) -> None:
        """I2C バスを閉じてリソースを解放する。"""
        if self._smbus is not None:
            self._smbus.close()
            self._smbus = None

    def _check_open(self) -> None:
        if self._smbus is None:
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
        data = self._smbus.read_i2c_block_data(self._address, register, length)
        return bytes(data)

    def write_register(self, register: int, data: bytes) -> None:
        """指定レジスタに data を書き込む。

        Args:
            register: 書き込み対象のレジスタアドレス。
            data: 書き込むデータ (bytes)。
        """
        self._check_open()
        self._smbus.write_i2c_block_data(self._address, register, list(data))

    def transfer(self, data: bytes) -> bytes:
        """全二重転送を行い、受信データを返す。

        I2C は半二重通信のため、最初のバイトをレジスタアドレスとして解釈し、
        残りのバイト数分だけ読み出しを行う。

        Args:
            data: 送信データ (bytes)。最初のバイトがレジスタアドレス。

        Returns:
            受信データ (bytes)。
        """
        self._check_open()
        if not data:
            return b""
        register = data[0]
        length = len(data) - 1
        if length == 0:
            return b""
        result = self._smbus.read_i2c_block_data(self._address, register, length)
        return bytes(result)

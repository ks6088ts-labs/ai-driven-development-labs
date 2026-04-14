"""Unit tests for MockBusDriver."""

import pytest

from ai_driven_development_labs.imu.bus.mock import MockBusDriver
from ai_driven_development_labs.imu.interfaces import IBusDriver


class TestMockBusDriverInit:
    """MockBusDriver 初期化のテスト。"""

    def test_is_instance_of_ibus_driver(self):
        """MockBusDriver が IBusDriver のインスタンスであることを確認する。"""
        driver = MockBusDriver()
        assert isinstance(driver, IBusDriver)

    def test_default_register_map_is_empty(self):
        """デフォルトでレジスタマップが空であることを確認する。"""
        driver = MockBusDriver()
        assert driver._registers == {}

    def test_initial_register_map_is_applied(self):
        """初期レジスタマップが正しく反映されることを確認する。"""
        reg_map = {0x10: 0xAB, 0x20: 0xCD}
        driver = MockBusDriver(register_map=reg_map)
        assert driver._registers == reg_map

    def test_initial_state_is_closed(self):
        """初期状態でバスが閉じていることを確認する。"""
        driver = MockBusDriver()
        assert driver._is_open is False


class TestMockBusDriverOpenClose:
    """MockBusDriver の open / close のテスト。"""

    def test_open_sets_is_open_true(self):
        """open() 後に _is_open が True になることを確認する。"""
        driver = MockBusDriver()
        driver.open()
        assert driver._is_open is True

    def test_close_sets_is_open_false(self):
        """close() 後に _is_open が False になることを確認する。"""
        driver = MockBusDriver()
        driver.open()
        driver.close()
        assert driver._is_open is False

    def test_open_close_cycle(self):
        """open() / close() のサイクルが正しく機能することを確認する。"""
        driver = MockBusDriver()
        driver.open()
        assert driver._is_open is True
        driver.close()
        assert driver._is_open is False
        driver.open()
        assert driver._is_open is True


class TestMockBusDriverReadRegister:
    """MockBusDriver の read_register のテスト。"""

    def test_unregistered_register_returns_zero(self):
        """未登録レジスタが 0x00 を返すことを確認する。"""
        driver = MockBusDriver()
        driver.open()
        result = driver.read_register(0x00, 1)
        assert result == b"\x00"

    def test_read_registered_value(self):
        """登録済みレジスタから正しい値が読めることを確認する。"""
        driver = MockBusDriver(register_map={0x10: 0xAB})
        driver.open()
        result = driver.read_register(0x10, 1)
        assert result == bytes([0xAB])

    def test_read_multiple_bytes(self):
        """複数バイトの読み出しが正しく機能することを確認する。"""
        driver = MockBusDriver(register_map={0x10: 0x01, 0x11: 0x02, 0x12: 0x03})
        driver.open()
        result = driver.read_register(0x10, 3)
        assert result == bytes([0x01, 0x02, 0x03])

    def test_read_partial_unregistered_returns_zero(self):
        """一部が未登録の場合、未登録バイトは 0x00 を返すことを確認する。"""
        driver = MockBusDriver(register_map={0x10: 0xAA})
        driver.open()
        result = driver.read_register(0x10, 2)
        assert result == bytes([0xAA, 0x00])

    def test_read_when_closed_raises_runtime_error(self):
        """close() 後に read_register() を呼ぶと RuntimeError が発生することを確認する。"""
        driver = MockBusDriver()
        with pytest.raises(RuntimeError):
            driver.read_register(0x00, 1)


class TestMockBusDriverWriteRegister:
    """MockBusDriver の write_register のテスト。"""

    def test_write_and_read_back(self):
        """write_register() で書き込んだ値が read_register() で読めることを確認する。"""
        driver = MockBusDriver()
        driver.open()
        driver.write_register(0x10, bytes([0xAB]))
        result = driver.read_register(0x10, 1)
        assert result == bytes([0xAB])

    def test_write_multiple_bytes(self):
        """複数バイトの書き込みが正しく機能することを確認する。"""
        driver = MockBusDriver()
        driver.open()
        driver.write_register(0x10, bytes([0x01, 0x02, 0x03]))
        result = driver.read_register(0x10, 3)
        assert result == bytes([0x01, 0x02, 0x03])

    def test_write_overwrites_existing_value(self):
        """既存の値が上書きされることを確認する。"""
        driver = MockBusDriver(register_map={0x10: 0xFF})
        driver.open()
        driver.write_register(0x10, bytes([0x00]))
        result = driver.read_register(0x10, 1)
        assert result == bytes([0x00])

    def test_write_when_closed_raises_runtime_error(self):
        """close() 後に write_register() を呼ぶと RuntimeError が発生することを確認する。"""
        driver = MockBusDriver()
        with pytest.raises(RuntimeError):
            driver.write_register(0x00, bytes([0x00]))


class TestMockBusDriverTransfer:
    """MockBusDriver の transfer のテスト。"""

    def test_transfer_read_command(self):
        """MSB が 1 (読み出しコマンド) の転送が正しく機能することを確認する。"""
        driver = MockBusDriver(register_map={0x10: 0xAB})
        driver.open()
        # 0x90 = 0x10 | 0x80 (read bit)
        result = driver.transfer(bytes([0x90, 0x00]))
        assert len(result) == 2
        assert result[1] == 0xAB

    def test_transfer_write_command(self):
        """MSB が 0 (書き込みコマンド) の転送が正しく機能することを確認する。"""
        driver = MockBusDriver()
        driver.open()
        driver.transfer(bytes([0x10, 0xCD]))
        result = driver.read_register(0x10, 1)
        assert result == bytes([0xCD])

    def test_transfer_empty_data(self):
        """空データの転送が空バイトを返すことを確認する。"""
        driver = MockBusDriver()
        driver.open()
        result = driver.transfer(b"")
        assert result == b""

    def test_transfer_when_closed_raises_runtime_error(self):
        """close() 後に transfer() を呼ぶと RuntimeError が発生することを確認する。"""
        driver = MockBusDriver()
        with pytest.raises(RuntimeError):
            driver.transfer(bytes([0x00]))

    def test_transfer_read_multiple_bytes(self):
        """読み出しコマンドで複数バイトが取得できることを確認する。"""
        driver = MockBusDriver(register_map={0x10: 0x01, 0x11: 0x02})
        driver.open()
        # 0x90 = 0x10 | 0x80
        result = driver.transfer(bytes([0x90, 0x00, 0x00]))
        assert len(result) == 3
        assert result[1] == 0x01
        assert result[2] == 0x02

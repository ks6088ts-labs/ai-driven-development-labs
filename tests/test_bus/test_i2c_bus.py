"""Unit tests for I2CBusDriver."""

import sys
from unittest.mock import MagicMock, patch

import pytest

from ai_driven_development_labs.bus.i2c import I2CBusDriver
from ai_driven_development_labs.bus.interfaces import IBusDriver


class TestI2CBusDriverInit:
    """I2CBusDriver 初期化のテスト。"""

    def test_is_instance_of_ibus_driver(self):
        """I2CBusDriver が IBusDriver のインスタンスであることを確認する。"""
        driver = I2CBusDriver()
        assert isinstance(driver, IBusDriver)

    def test_default_params(self):
        """デフォルトパラメータが正しく設定されることを確認する。"""
        driver = I2CBusDriver()
        assert driver._bus_number == 1
        assert driver._address == 0x6A

    def test_custom_params(self):
        """カスタムパラメータが正しく設定されることを確認する。"""
        driver = I2CBusDriver(bus=2, address=0x68)
        assert driver._bus_number == 2
        assert driver._address == 0x68

    def test_initial_smbus_is_none(self):
        """初期状態で _smbus が None であることを確認する。"""
        driver = I2CBusDriver()
        assert driver._smbus is None


class TestI2CBusDriverImportError:
    """smbus2 未インストール環境のテスト。"""

    def test_open_raises_import_error_when_smbus2_missing(self):
        """smbus2 がない場合に open() が ImportError を発生させることを確認する。"""
        driver = I2CBusDriver()
        with patch.dict(sys.modules, {"smbus2": None}):
            with pytest.raises(ImportError) as exc_info:
                driver.open()
        assert "smbus2" in str(exc_info.value)


class TestI2CBusDriverWithMock:
    """モックを使用した I2CBusDriver のテスト。"""

    def _make_driver_with_mock_smbus(self):
        mock_smbus2_module = MagicMock()
        mock_smbus_instance = MagicMock()
        mock_smbus2_module.SMBus.return_value = mock_smbus_instance

        driver = I2CBusDriver(bus=1, address=0x6A)
        with patch.dict(sys.modules, {"smbus2": mock_smbus2_module}):
            driver.open()
        driver._smbus = mock_smbus_instance
        return driver, mock_smbus_instance

    def test_open_initializes_smbus(self):
        """open() が smbus2 を正しく初期化することを確認する。"""
        mock_smbus2_module = MagicMock()
        mock_smbus_instance = MagicMock()
        mock_smbus2_module.SMBus.return_value = mock_smbus_instance

        driver = I2CBusDriver(bus=1, address=0x6A)
        with patch.dict(sys.modules, {"smbus2": mock_smbus2_module}):
            driver.open()

        mock_smbus2_module.SMBus.assert_called_once_with(1)

    def test_close_calls_smbus_close(self):
        """close() が smbus.close() を呼び出すことを確認する。"""
        driver, mock_smbus = self._make_driver_with_mock_smbus()
        driver.close()
        mock_smbus.close.assert_called_once()
        assert driver._smbus is None

    def test_close_when_not_open_is_noop(self):
        """open() 前に close() を呼んでもエラーにならないことを確認する。"""
        driver = I2CBusDriver()
        driver.close()  # should not raise

    def test_read_register_calls_read_i2c_block_data(self):
        """read_register() が read_i2c_block_data を呼び出すことを確認する。"""
        driver, mock_smbus = self._make_driver_with_mock_smbus()
        mock_smbus.read_i2c_block_data.return_value = [0xAB]

        result = driver.read_register(0x10, 1)

        mock_smbus.read_i2c_block_data.assert_called_once_with(0x6A, 0x10, 1)
        assert result == bytes([0xAB])

    def test_write_register_calls_write_i2c_block_data(self):
        """write_register() が write_i2c_block_data を呼び出すことを確認する。"""
        driver, mock_smbus = self._make_driver_with_mock_smbus()

        driver.write_register(0x10, bytes([0xCD]))

        mock_smbus.write_i2c_block_data.assert_called_once_with(0x6A, 0x10, [0xCD])

    def test_transfer_calls_read_i2c_block_data(self):
        """transfer() が read_i2c_block_data を呼び出すことを確認する。"""
        driver, mock_smbus = self._make_driver_with_mock_smbus()
        mock_smbus.read_i2c_block_data.return_value = [0x01, 0x02]

        result = driver.transfer(bytes([0x10, 0x00, 0x00]))

        mock_smbus.read_i2c_block_data.assert_called_once_with(0x6A, 0x10, 2)
        assert result == bytes([0x01, 0x02])

    def test_transfer_empty_data_returns_empty(self):
        """空データの転送が空バイトを返すことを確認する。"""
        driver, _ = self._make_driver_with_mock_smbus()
        result = driver.transfer(b"")
        assert result == b""

    def test_transfer_single_byte_returns_empty(self):
        """1 バイトのデータ (レジスタのみ) の転送が空バイトを返すことを確認する。"""
        driver, _ = self._make_driver_with_mock_smbus()
        result = driver.transfer(bytes([0x10]))
        assert result == b""

    def test_read_register_when_closed_raises_runtime_error(self):
        """close() 後に read_register() を呼ぶと RuntimeError が発生することを確認する。"""
        driver = I2CBusDriver()
        with pytest.raises(RuntimeError):
            driver.read_register(0x00, 1)

    def test_write_register_when_closed_raises_runtime_error(self):
        """close() 後に write_register() を呼ぶと RuntimeError が発生することを確認する。"""
        driver = I2CBusDriver()
        with pytest.raises(RuntimeError):
            driver.write_register(0x00, bytes([0x00]))

    def test_transfer_when_closed_raises_runtime_error(self):
        """close() 後に transfer() を呼ぶと RuntimeError が発生することを確認する。"""
        driver = I2CBusDriver()
        with pytest.raises(RuntimeError):
            driver.transfer(bytes([0x00]))

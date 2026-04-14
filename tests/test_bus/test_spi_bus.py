"""Unit tests for SPIBusDriver."""

import sys
from unittest.mock import MagicMock, patch

import pytest

from ai_driven_development_labs.bus.interfaces import IBusDriver
from ai_driven_development_labs.bus.spi import SPI_READ_MASK, SPIBusDriver


class TestSPIBusDriverInit:
    """SPIBusDriver 初期化のテスト。"""

    def test_is_instance_of_ibus_driver(self):
        """SPIBusDriver が IBusDriver のインスタンスであることを確認する。"""
        driver = SPIBusDriver()
        assert isinstance(driver, IBusDriver)

    def test_default_params(self):
        """デフォルトパラメータが正しく設定されることを確認する。"""
        driver = SPIBusDriver()
        assert driver._bus == 0
        assert driver._device == 0
        assert driver._max_speed_hz == 1_000_000
        assert driver._mode == 0

    def test_custom_params(self):
        """カスタムパラメータが正しく設定されることを確認する。"""
        driver = SPIBusDriver(bus=1, device=2, max_speed_hz=500_000, mode=3)
        assert driver._bus == 1
        assert driver._device == 2
        assert driver._max_speed_hz == 500_000
        assert driver._mode == 3

    def test_initial_spi_is_none(self):
        """初期状態で _spi が None であることを確認する。"""
        driver = SPIBusDriver()
        assert driver._spi is None


class TestSPIBusDriverImportError:
    """spidev 未インストール環境のテスト。"""

    def test_open_raises_import_error_when_spidev_missing(self):
        """spidev がない場合に open() が ImportError を発生させることを確認する。"""
        driver = SPIBusDriver()
        with patch.dict(sys.modules, {"spidev": None}):
            with pytest.raises(ImportError) as exc_info:
                driver.open()
        assert "spidev" in str(exc_info.value)


class TestSPIBusDriverWithMock:
    """モックを使用した SPIBusDriver のテスト。"""

    def _make_driver_with_mock_spi(self):
        mock_spidev_module = MagicMock()
        mock_spi_instance = MagicMock()
        mock_spidev_module.SpiDev.return_value = mock_spi_instance

        driver = SPIBusDriver(bus=0, device=0, max_speed_hz=1_000_000, mode=0)
        with patch.dict(sys.modules, {"spidev": mock_spidev_module}):
            driver.open()
        driver._spi = mock_spi_instance
        return driver, mock_spi_instance

    def test_open_initializes_spi(self):
        """open() が spidev を正しく初期化することを確認する。"""
        mock_spidev_module = MagicMock()
        mock_spi_instance = MagicMock()
        mock_spidev_module.SpiDev.return_value = mock_spi_instance

        driver = SPIBusDriver(bus=0, device=0, max_speed_hz=1_000_000, mode=0)
        with patch.dict(sys.modules, {"spidev": mock_spidev_module}):
            driver.open()

        mock_spi_instance.open.assert_called_once_with(0, 0)
        assert mock_spi_instance.max_speed_hz == 1_000_000
        assert mock_spi_instance.mode == 0

    def test_close_calls_spi_close(self):
        """close() が spi.close() を呼び出すことを確認する。"""
        driver, mock_spi = self._make_driver_with_mock_spi()
        driver.close()
        mock_spi.close.assert_called_once()
        assert driver._spi is None

    def test_close_when_not_open_is_noop(self):
        """open() 前に close() を呼んでもエラーにならないことを確認する。"""
        driver = SPIBusDriver()
        driver.close()  # should not raise

    def test_read_register_sends_read_command(self):
        """read_register() が SPI_READ_MASK を付けたコマンドを送ることを確認する。"""
        driver, mock_spi = self._make_driver_with_mock_spi()
        mock_spi.xfer2.return_value = [0x00, 0xAB]

        result = driver.read_register(0x10, 1)

        mock_spi.xfer2.assert_called_once_with([0x10 | SPI_READ_MASK, 0x00])
        assert result == bytes([0xAB])

    def test_write_register_sends_write_command(self):
        """write_register() が書き込みコマンドを送ることを確認する。"""
        driver, mock_spi = self._make_driver_with_mock_spi()
        mock_spi.xfer2.return_value = [0x00, 0x00]

        driver.write_register(0x10, bytes([0xCD]))

        mock_spi.xfer2.assert_called_once_with([0x10 & ~SPI_READ_MASK, 0xCD])

    def test_transfer_calls_xfer2(self):
        """transfer() が xfer2 を呼び出すことを確認する。"""
        driver, mock_spi = self._make_driver_with_mock_spi()
        mock_spi.xfer2.return_value = [0x01, 0x02]

        result = driver.transfer(bytes([0x01, 0x02]))

        mock_spi.xfer2.assert_called_once_with([0x01, 0x02])
        assert result == bytes([0x01, 0x02])

    def test_read_register_when_closed_raises_runtime_error(self):
        """close() 後に read_register() を呼ぶと RuntimeError が発生することを確認する。"""
        driver = SPIBusDriver()
        with pytest.raises(RuntimeError):
            driver.read_register(0x00, 1)

    def test_write_register_when_closed_raises_runtime_error(self):
        """close() 後に write_register() を呼ぶと RuntimeError が発生することを確認する。"""
        driver = SPIBusDriver()
        with pytest.raises(RuntimeError):
            driver.write_register(0x00, bytes([0x00]))

    def test_transfer_when_closed_raises_runtime_error(self):
        """close() 後に transfer() を呼ぶと RuntimeError が発生することを確認する。"""
        driver = SPIBusDriver()
        with pytest.raises(RuntimeError):
            driver.transfer(bytes([0x00]))

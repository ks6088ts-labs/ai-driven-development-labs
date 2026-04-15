"""Unit tests for IMU factory functions."""

import pytest

from ai_driven_development_labs.bus.i2c import I2CBusDriver
from ai_driven_development_labs.bus.mock import MockBusDriver
from ai_driven_development_labs.bus.spi import SPIBusDriver
from ai_driven_development_labs.imu.factory import create_bus_driver, create_sensor_hal
from ai_driven_development_labs.imu.hal.mock import MockSensorHAL
from ai_driven_development_labs.imu.hal.stmicro import STMicroSensorHAL
from ai_driven_development_labs.imu.hal.tdk import TDKSensorHAL


class TestCreateBusDriver:
    """create_bus_driver() のテスト。"""

    def test_mock_returns_mock_bus_driver(self):
        """'mock' 指定で MockBusDriver が返ることを確認する。"""
        bus = create_bus_driver("mock")
        assert isinstance(bus, MockBusDriver)

    def test_spi_returns_spi_bus_driver(self):
        """'spi' 指定で SPIBusDriver が返ることを確認する。"""
        bus = create_bus_driver("spi", bus_id=0, device=0)
        assert isinstance(bus, SPIBusDriver)

    def test_i2c_returns_i2c_bus_driver(self):
        """'i2c' 指定で I2CBusDriver が返ることを確認する。"""
        bus = create_bus_driver("i2c", bus_id=1, device=0x6A)
        assert isinstance(bus, I2CBusDriver)

    def test_invalid_bus_type_raises_value_error(self):
        """未知のバス種別で ValueError が発生することを確認する。"""
        with pytest.raises(ValueError, match="Unknown bus type"):
            create_bus_driver("invalid")

    def test_default_bus_id_and_device(self):
        """デフォルト引数 (bus_id=0, device=0) で生成できることを確認する。"""
        bus = create_bus_driver("mock")
        assert isinstance(bus, MockBusDriver)

    def test_spi_with_custom_params(self):
        """SPI バスドライバがカスタムパラメータで生成されることを確認する。"""
        bus = create_bus_driver("spi", bus_id=1, device=2)
        assert isinstance(bus, SPIBusDriver)

    def test_i2c_with_custom_address(self):
        """I2C バスドライバがカスタムアドレスで生成されることを確認する。"""
        bus = create_bus_driver("i2c", bus_id=1, device=0x68)
        assert isinstance(bus, I2CBusDriver)


class TestCreateSensorHAL:
    """create_sensor_hal() のテスト。"""

    def test_mock_returns_mock_sensor_hal(self):
        """'mock' 指定で MockSensorHAL が返ることを確認する。"""
        hal = create_sensor_hal("mock")
        assert isinstance(hal, MockSensorHAL)

    def test_stmicro_returns_stmicro_sensor_hal(self):
        """'stmicro' 指定で STMicroSensorHAL が返ることを確認する。"""
        hal = create_sensor_hal("stmicro")
        assert isinstance(hal, STMicroSensorHAL)

    def test_tdk_returns_tdk_sensor_hal(self):
        """'tdk' 指定で TDKSensorHAL が返ることを確認する。"""
        hal = create_sensor_hal("tdk")
        assert isinstance(hal, TDKSensorHAL)

    def test_invalid_hal_type_raises_value_error(self):
        """未知の HAL 種別で ValueError が発生することを確認する。"""
        with pytest.raises(ValueError, match="Unknown HAL type"):
            create_sensor_hal("invalid")

"""Factory functions for creating bus drivers and sensor HALs from CLI options."""

from ai_driven_development_labs.bus.i2c import I2CBusDriver
from ai_driven_development_labs.bus.interfaces import IBusDriver
from ai_driven_development_labs.bus.mock import MockBusDriver
from ai_driven_development_labs.bus.spi import SPIBusDriver
from ai_driven_development_labs.imu.hal.mock import MockSensorHAL
from ai_driven_development_labs.imu.hal.stmicro import STMicroSensorHAL
from ai_driven_development_labs.imu.hal.tdk import TDKSensorHAL
from ai_driven_development_labs.imu.interfaces import ISensorHAL


def create_bus_driver(bus_type: str, bus_id: int = 0, device: int = 0) -> IBusDriver:
    """CLI オプションからバスドライバを生成する。

    Args:
        bus_type: バスドライバの種別 ('mock', 'spi', 'i2c')。
        bus_id: バス番号。
        device: デバイス番号（SPI CS） / I2C アドレス。

    Returns:
        指定された種別のバスドライバインスタンス。

    Raises:
        ValueError: 未知のバス種別が指定された場合。
    """
    match bus_type:
        case "mock":
            return MockBusDriver()
        case "spi":
            return SPIBusDriver(bus=bus_id, device=device)
        case "i2c":
            return I2CBusDriver(bus=bus_id, address=device)
        case _:
            raise ValueError(f"Unknown bus type: {bus_type}")


def create_sensor_hal(hal_type: str) -> ISensorHAL:
    """CLI オプションからセンサー HAL を生成する。

    Args:
        hal_type: センサー HAL の種別 ('mock', 'stmicro', 'tdk')。

    Returns:
        指定された種別のセンサー HAL インスタンス。

    Raises:
        ValueError: 未知の HAL 種別が指定された場合。
    """
    match hal_type:
        case "mock":
            return MockSensorHAL()
        case "stmicro":
            return STMicroSensorHAL()
        case "tdk":
            return TDKSensorHAL()
        case _:
            raise ValueError(f"Unknown HAL type: {hal_type}")

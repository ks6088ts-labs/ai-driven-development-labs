"""Unit tests for IMU HAL abstract interfaces."""

import pytest

from ai_driven_development_labs.bus.interfaces import IBusDriver
from ai_driven_development_labs.imu.interfaces import ISensorHAL
from ai_driven_development_labs.imu.models import SensorEvent, SensorInfo, SensorType


class TestISensorHALABC:
    """ISensorHAL ABC のテスト。"""

    def test_cannot_instantiate_directly(self):
        """ISensorHAL を直接インスタンス化すると TypeError が発生することを確認する。"""
        with pytest.raises(TypeError):
            ISensorHAL()  # type: ignore[abstract]

    def test_concrete_without_all_methods_raises(self):
        """抽象メソッドを一部しか実装しない具象クラスは TypeError になることを確認する。"""

        class PartialSensorHAL(ISensorHAL):
            def initialize(self, bus: IBusDriver) -> None:
                pass

            # 残りの抽象メソッドは未実装

        with pytest.raises(TypeError):
            PartialSensorHAL()  # type: ignore[abstract]

    def test_concrete_full_implementation(self):
        """すべての抽象メソッドを実装した具象クラスはインスタンス化できることを確認する。"""

        class MockSensorHAL(ISensorHAL):
            def initialize(self, bus: IBusDriver) -> None:
                self._bus = bus

            def get_sensor_list(self) -> list[SensorInfo]:
                return []

            def activate(self, sensor_handle: int, enabled: bool) -> None:
                pass

            def configure(self, sensor_handle: int, sampling_period_us: int, max_report_latency_us: int) -> None:
                pass

            def flush(self, sensor_handle: int) -> None:
                pass

            def get_events(self) -> list[SensorEvent]:
                return []

            def finalize(self) -> None:
                pass

        hal = MockSensorHAL()
        assert isinstance(hal, ISensorHAL)

    def test_abstract_methods_list(self):
        """ISensorHAL が期待する抽象メソッドをすべて持つことを確認する。"""
        expected = {"initialize", "get_sensor_list", "activate", "configure", "flush", "get_events", "finalize"}
        assert ISensorHAL.__abstractmethods__ == expected

    def test_mock_hal_integration_with_mock_bus(self):
        """MockSensorHAL と MockBusDriver を組み合わせて DI が機能することを確認する。"""

        class MockBusDriver(IBusDriver):
            def open(self) -> None:
                pass

            def close(self) -> None:
                pass

            def read_register(self, register: int, length: int) -> bytes:
                return bytes(length)

            def write_register(self, register: int, data: bytes) -> None:
                pass

            def transfer(self, data: bytes) -> bytes:
                return data

        class MockSensorHAL(ISensorHAL):
            def __init__(self):
                self._bus: IBusDriver | None = None
                self._active: dict[int, bool] = {}

            def initialize(self, bus: IBusDriver) -> None:
                self._bus = bus

            def get_sensor_list(self) -> list[SensorInfo]:
                return [
                    SensorInfo(
                        sensor_handle=1,
                        name="Mock Accelerometer",
                        vendor="MockVendor",
                        sensor_type=SensorType.ACCELEROMETER,
                    )
                ]

            def activate(self, sensor_handle: int, enabled: bool) -> None:
                self._active[sensor_handle] = enabled

            def configure(self, sensor_handle: int, sampling_period_us: int, max_report_latency_us: int) -> None:
                pass

            def flush(self, sensor_handle: int) -> None:
                pass

            def get_events(self) -> list[SensorEvent]:
                return [
                    SensorEvent(
                        sensor_handle=1,
                        sensor_type=SensorType.ACCELEROMETER,
                        timestamp_ns=1_000_000,
                        values=[0.0, 0.0, -9.8],
                    )
                ]

            def finalize(self) -> None:
                self._bus = None

        bus = MockBusDriver()
        hal = MockSensorHAL()
        hal.initialize(bus)

        sensors = hal.get_sensor_list()
        assert len(sensors) == 1
        assert sensors[0].name == "Mock Accelerometer"

        hal.activate(1, True)
        events = hal.get_events()
        assert len(events) == 1
        assert events[0].values == [0.0, 0.0, -9.8]

        hal.finalize()

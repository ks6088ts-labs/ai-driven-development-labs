"""IMU HAL の統合テスト。MockBusDriver + 各ベンダー HAL + CLI を組み合わせたエンドツーエンドテスト。"""

import pytest

from ai_driven_development_labs.bus.mock import MockBusDriver
from ai_driven_development_labs.imu.hal.mock import MockSensorHAL
from ai_driven_development_labs.imu.hal.stmicro import STMicroSensorHAL
from ai_driven_development_labs.imu.models import SensorType


class TestEndToEnd:
    """エンドツーエンド統合テスト。"""

    def test_end_to_end_mock(self):
        """Mock HAL のエンドツーエンドテスト。"""
        bus = MockBusDriver()
        hal = MockSensorHAL()
        hal.initialize(bus)

        sensors = hal.get_sensor_list()
        assert len(sensors) >= 2

        for sensor in sensors:
            hal.activate(sensor.sensor_handle, True)
            hal.configure(sensor.sensor_handle, sampling_period_us=10_000, max_report_latency_us=0)

        events = hal.get_events()
        assert len(events) > 0

        for sensor in sensors:
            hal.activate(sensor.sensor_handle, False)

        hal.finalize()

    def test_end_to_end_stmicro_with_mock_bus(self):
        """STMicro HAL + MockBusDriver のエンドツーエンドテスト。"""
        register_map = {
            0x0F: 0x6C,  # WHO_AM_I = LSM6DSO
            0x1E: 0x05,  # STATUS_REG: accel + gyro data ready
            # 出力レジスタ (0x22-0x2D) に固定値を設定
            0x22: 0x00, 0x23: 0x00,  # GYRO_X
            0x24: 0x00, 0x25: 0x00,  # GYRO_Y
            0x26: 0x00, 0x27: 0x00,  # GYRO_Z
            0x28: 0x00, 0x29: 0x00,  # ACCEL_X
            0x2A: 0x00, 0x2B: 0x40,  # ACCEL_Y
            0x2C: 0x00, 0x2D: 0x00,  # ACCEL_Z
        }
        bus = MockBusDriver(register_map=register_map)
        hal = STMicroSensorHAL()
        hal.initialize(bus)

        sensors = hal.get_sensor_list()
        assert any(s.sensor_type == SensorType.ACCELEROMETER for s in sensors)
        assert any(s.sensor_type == SensorType.GYROSCOPE for s in sensors)

        hal.finalize()


class TestDIPattern:
    """DI パターンの検証テスト。"""

    @pytest.mark.parametrize(
        "bus_factory",
        [
            lambda: MockBusDriver(register_map={0x0F: 0x6C, 0x1E: 0x05}),
        ],
    )
    def test_stmicro_hal_with_different_buses(self, bus_factory):
        """STMicro HAL が異なるバスドライバで動作すること。"""
        bus = bus_factory()
        hal = STMicroSensorHAL()
        hal.initialize(bus)
        sensors = hal.get_sensor_list()
        assert len(sensors) > 0
        hal.finalize()

    def test_mock_hal_bus_injection(self):
        """MockSensorHAL が任意の MockBusDriver を受け取れること。"""
        bus = MockBusDriver()
        hal = MockSensorHAL()
        hal.initialize(bus)
        sensors = hal.get_sensor_list()
        assert len(sensors) > 0
        hal.finalize()

    def test_stmicro_hal_sensors_have_correct_types(self):
        """STMicro HAL のセンサーリストに加速度計とジャイロスコープが含まれること。"""
        register_map = {0x0F: 0x6C, 0x1E: 0x00}
        bus = MockBusDriver(register_map=register_map)
        hal = STMicroSensorHAL()
        hal.initialize(bus)

        sensors = hal.get_sensor_list()
        sensor_types = {s.sensor_type for s in sensors}
        assert SensorType.ACCELEROMETER in sensor_types
        assert SensorType.GYROSCOPE in sensor_types

        hal.finalize()

    def test_stmicro_hal_unsupported_device_raises(self):
        """未サポートの WHO_AM_I 値で初期化すると RuntimeError が発生すること。"""
        bus = MockBusDriver(register_map={0x0F: 0xFF})
        hal = STMicroSensorHAL()
        with pytest.raises(RuntimeError, match="Unsupported device"):
            hal.initialize(bus)

    def test_mock_hal_events_after_activate(self):
        """センサーを有効化した後に get_events() がイベントを返すこと。"""
        bus = MockBusDriver()
        hal = MockSensorHAL()
        hal.initialize(bus)

        sensors = hal.get_sensor_list()
        for sensor in sensors:
            hal.activate(sensor.sensor_handle, True)

        events = hal.get_events()
        assert len(events) == len(sensors)

        hal.finalize()

    def test_mock_hal_no_events_before_activate(self):
        """センサーを有効化していない状態では get_events() が空リストを返すこと。"""
        bus = MockBusDriver()
        hal = MockSensorHAL()
        hal.initialize(bus)

        events = hal.get_events()
        assert events == []

        hal.finalize()

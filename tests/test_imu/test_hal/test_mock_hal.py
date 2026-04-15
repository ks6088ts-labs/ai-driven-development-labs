"""Unit tests for MockSensorHAL."""

import pytest

from ai_driven_development_labs.bus.mock import MockBusDriver
from ai_driven_development_labs.imu.hal.mock import MockSensorHAL
from ai_driven_development_labs.imu.interfaces import ISensorHAL
from ai_driven_development_labs.imu.models import SensorType


class TestMockSensorHALInit:
    """MockSensorHAL 初期化のテスト。"""

    def test_is_instance_of_isensor_hal(self):
        """MockSensorHAL が ISensorHAL のインスタンスであることを確認する。"""
        hal = MockSensorHAL()
        assert isinstance(hal, ISensorHAL)

    def test_custom_ranges(self):
        """カスタムレンジで初期化できることを確認する。"""
        hal = MockSensorHAL(accel_range=4.0, gyro_range=500.0, noise_stddev=0.001)
        assert hal._accel_range == 4.0
        assert hal._gyro_range == 500.0
        assert hal._noise_stddev == 0.001


class TestMockSensorHALSensorList:
    """MockSensorHAL.get_sensor_list() のテスト。"""

    def setup_method(self):
        self.bus = MockBusDriver()
        self.hal = MockSensorHAL()
        self.hal.initialize(self.bus)

    def test_sensor_list_has_two_sensors(self):
        """初期化後に加速度計とジャイロの 2 センサーが返ることを確認する。"""
        sensors = self.hal.get_sensor_list()
        assert len(sensors) == 2

    def test_accelerometer_sensor_handle(self):
        """加速度計のハンドルが 1 であることを確認する。"""
        sensors = self.hal.get_sensor_list()
        accel = next(s for s in sensors if s.sensor_type == SensorType.ACCELEROMETER)
        assert accel.sensor_handle == 1

    def test_gyroscope_sensor_handle(self):
        """ジャイロスコープのハンドルが 2 であることを確認する。"""
        sensors = self.hal.get_sensor_list()
        gyro = next(s for s in sensors if s.sensor_type == SensorType.GYROSCOPE)
        assert gyro.sensor_handle == 2

    def test_sensor_vendor(self):
        """センサーベンダーが 'MockVendor' であることを確認する。"""
        sensors = self.hal.get_sensor_list()
        for s in sensors:
            assert s.vendor == "MockVendor"

    def test_accel_max_range(self):
        """加速度計の max_range がコンストラクタ引数と一致することを確認する。"""
        hal = MockSensorHAL(accel_range=4.0)
        hal.initialize(MockBusDriver())
        sensors = hal.get_sensor_list()
        accel = next(s for s in sensors if s.sensor_type == SensorType.ACCELEROMETER)
        assert accel.max_range == 4.0


class TestMockSensorHALActivateAndEvents:
    """MockSensorHAL の activate() / get_events() のテスト。"""

    def setup_method(self):
        self.bus = MockBusDriver()
        self.hal = MockSensorHAL(noise_stddev=0.0)
        self.hal.initialize(self.bus)

    def test_get_events_before_activate_returns_empty(self):
        """activate() 前の get_events() は空リストを返すことを確認する。"""
        events = self.hal.get_events()
        assert events == []

    def test_activate_accel_returns_accel_event(self):
        """加速度計を activate() すると get_events() でイベントが取得できることを確認する。"""
        self.hal.activate(1, True)
        events = self.hal.get_events()
        assert len(events) == 1
        assert events[0].sensor_type == SensorType.ACCELEROMETER
        assert events[0].sensor_handle == 1

    def test_activate_gyro_returns_gyro_event(self):
        """ジャイロを activate() すると get_events() でイベントが取得できることを確認する。"""
        self.hal.activate(2, True)
        events = self.hal.get_events()
        assert len(events) == 1
        assert events[0].sensor_type == SensorType.GYROSCOPE
        assert events[0].sensor_handle == 2

    def test_activate_both_returns_two_events(self):
        """両センサーを activate() すると get_events() で 2 イベントが取得できることを確認する。"""
        self.hal.activate(1, True)
        self.hal.activate(2, True)
        events = self.hal.get_events()
        assert len(events) == 2

    def test_deactivate_sensor_stops_events(self):
        """deactivate() 後は get_events() で対象センサーのイベントが返らないことを確認する。"""
        self.hal.activate(1, True)
        self.hal.activate(1, False)
        events = self.hal.get_events()
        assert events == []

    def test_accel_event_gravity_offset(self):
        """加速度計イベントの z 軸に重力加速度 9.81 のオフセットがあることを確認する。"""
        self.hal.activate(1, True)
        events = self.hal.get_events()
        assert len(events) == 1
        assert pytest.approx(events[0].values[2], abs=1e-9) == 9.81

    def test_event_timestamp_is_positive(self):
        """イベントのタイムスタンプが正の値であることを確認する。"""
        self.hal.activate(1, True)
        events = self.hal.get_events()
        assert events[0].timestamp_ns > 0


class TestMockSensorHALConfigure:
    """MockSensorHAL.configure() のテスト。"""

    def setup_method(self):
        self.bus = MockBusDriver()
        self.hal = MockSensorHAL()
        self.hal.initialize(self.bus)

    def test_configure_stores_sampling_period(self):
        """configure() でサンプリング周期がメモリに保持されることを確認する。"""
        self.hal.configure(1, 10_000, 0)
        assert self.hal._sampling_period_us[1] == 10_000

    def test_configure_multiple_sensors(self):
        """複数センサーのサンプリング周期を個別に設定できることを確認する。"""
        self.hal.configure(1, 10_000, 0)
        self.hal.configure(2, 20_000, 0)
        assert self.hal._sampling_period_us[1] == 10_000
        assert self.hal._sampling_period_us[2] == 20_000


class TestMockSensorHALFlush:
    """MockSensorHAL.flush() のテスト。"""

    def setup_method(self):
        self.bus = MockBusDriver()
        self.hal = MockSensorHAL()
        self.hal.initialize(self.bus)

    def test_flush_completes_without_error(self):
        """flush() がエラーなく正常に完了することを確認する。"""
        self.hal.flush(1)
        self.hal.flush(2)


class TestMockSensorHALFinalize:
    """MockSensorHAL.finalize() のテスト。"""

    def setup_method(self):
        self.bus = MockBusDriver()
        self.hal = MockSensorHAL()
        self.hal.initialize(self.bus)

    def test_finalize_releases_bus(self):
        """finalize() 後にバスが解放されることを確認する。"""
        self.hal.finalize()
        assert self.hal._bus is None

    def test_finalize_closes_bus(self):
        """finalize() 後にバスが閉じられることを確認する。"""
        self.hal.finalize()
        assert not self.bus._is_open

    def test_finalize_clears_active_sensors(self):
        """finalize() 後にアクティブセンサー辞書がクリアされることを確認する。"""
        self.hal.activate(1, True)
        self.hal.finalize()
        assert self.hal._active == {}

    def test_finalize_clears_sampling_period(self):
        """finalize() 後にサンプリング周期辞書がクリアされることを確認する。"""
        self.hal.configure(1, 10_000, 0)
        self.hal.finalize()
        assert self.hal._sampling_period_us == {}

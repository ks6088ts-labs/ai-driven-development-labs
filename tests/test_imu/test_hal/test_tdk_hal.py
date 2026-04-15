"""Unit tests for TDKSensorHAL."""

import struct

import pytest

from ai_driven_development_labs.bus.mock import MockBusDriver
from ai_driven_development_labs.imu.hal.tdk import (
    _ACCEL_CONFIG0_DEFAULT,
    _ACCEL_SENSITIVITY_G_PER_LSB,
    _GYRO_CONFIG0_DEFAULT,
    _GYRO_SENSITIVITY_DPS_PER_LSB,
    _PWR_MGMT0_DEFAULT,
    _REG_ACCEL_CONFIG0,
    _REG_ACCEL_DATA_X1,
    _REG_BANK_SEL,
    _REG_GYRO_CONFIG0,
    _REG_GYRO_DATA_X1,
    _REG_INT_STATUS,
    _REG_PWR_MGMT0,
    _REG_WHO_AM_I,
    TDKSensorHAL,
)
from ai_driven_development_labs.imu.interfaces import ISensorHAL
from ai_driven_development_labs.imu.models import SensorType


def _make_icm42688p_bus(extra_regs: dict[int, int] | None = None) -> MockBusDriver:
    """ICM-42688-P の WHO_AM_I を持つ MockBusDriver を生成する。"""
    reg_map = {_REG_WHO_AM_I: 0x47}
    if extra_regs:
        reg_map.update(extra_regs)
    return MockBusDriver(register_map=reg_map)


def _encode_accel_regs(ax: int = 0, ay: int = 0, az: int = 0) -> dict[int, int]:
    """加速度計出力レジスタ (big-endian) のレジスタマップを返す。"""
    raw = struct.pack(">hhh", ax, ay, az)
    return {_REG_ACCEL_DATA_X1 + i: b for i, b in enumerate(raw)}


def _encode_gyro_regs(gx: int = 0, gy: int = 0, gz: int = 0) -> dict[int, int]:
    """ジャイロスコープ出力レジスタ (big-endian) のレジスタマップを返す。"""
    raw = struct.pack(">hhh", gx, gy, gz)
    return {_REG_GYRO_DATA_X1 + i: b for i, b in enumerate(raw)}


class TestTDKSensorHALInit:
    """TDKSensorHAL 初期化のテスト。"""

    def test_is_instance_of_isensor_hal(self):
        """TDKSensorHAL が ISensorHAL のインスタンスであることを確認する。"""
        hal = TDKSensorHAL()
        assert isinstance(hal, ISensorHAL)

    def test_initialize_icm42688p(self):
        """ICM-42688-P の WHO_AM_I (0x47) で初期化できることを確認する。"""
        bus = _make_icm42688p_bus()
        hal = TDKSensorHAL()
        hal.initialize(bus)
        assert hal._device_name == "ICM-42688-P"

    def test_unsupported_who_am_i_raises(self):
        """未サポートの WHO_AM_I の場合に RuntimeError が発生することを確認する。"""
        bus = MockBusDriver(register_map={_REG_WHO_AM_I: 0xFF})
        hal = TDKSensorHAL()
        with pytest.raises(RuntimeError, match="Unsupported device"):
            hal.initialize(bus)

    def test_control_registers_written_on_init(self):
        """初期化時にコントロールレジスタが正しい値で書き込まれることを確認する。"""
        bus = _make_icm42688p_bus()
        hal = TDKSensorHAL()
        hal.initialize(bus)
        assert bus._registers[_REG_BANK_SEL] == 0x00
        assert bus._registers[_REG_PWR_MGMT0] == _PWR_MGMT0_DEFAULT
        assert bus._registers[_REG_GYRO_CONFIG0] == _GYRO_CONFIG0_DEFAULT
        assert bus._registers[_REG_ACCEL_CONFIG0] == _ACCEL_CONFIG0_DEFAULT


class TestTDKSensorHALSensorList:
    """TDKSensorHAL.get_sensor_list() のテスト。"""

    def setup_method(self):
        bus = _make_icm42688p_bus()
        self.hal = TDKSensorHAL()
        self.hal.initialize(bus)

    def test_sensor_list_has_two_sensors(self):
        """初期化後に 2 センサーが返ることを確認する。"""
        sensors = self.hal.get_sensor_list()
        assert len(sensors) == 2

    def test_vendor_is_tdk_invensense(self):
        """ベンダーが 'TDK InvenSense' であることを確認する。"""
        sensors = self.hal.get_sensor_list()
        for s in sensors:
            assert s.vendor == "TDK InvenSense"

    def test_accel_handle(self):
        """加速度計のハンドルが 1 であることを確認する。"""
        sensors = self.hal.get_sensor_list()
        accel = next(s for s in sensors if s.sensor_type == SensorType.ACCELEROMETER)
        assert accel.sensor_handle == 1

    def test_gyro_handle(self):
        """ジャイロスコープのハンドルが 2 であることを確認する。"""
        sensors = self.hal.get_sensor_list()
        gyro = next(s for s in sensors if s.sensor_type == SensorType.GYROSCOPE)
        assert gyro.sensor_handle == 2

    def test_sensor_name_contains_device_name(self):
        """センサー名にデバイス名 (ICM-42688-P) が含まれることを確認する。"""
        sensors = self.hal.get_sensor_list()
        for s in sensors:
            assert "ICM-42688-P" in s.name


class TestTDKSensorHALGetEvents:
    """TDKSensorHAL.get_events() のテスト。"""

    def test_no_events_when_int_status_zero(self):
        """INT_STATUS = 0 (データ未準備) の場合に空リストを返すことを確認する。"""
        bus = _make_icm42688p_bus(extra_regs={_REG_INT_STATUS: 0x00})
        hal = TDKSensorHAL()
        hal.initialize(bus)
        hal.activate(1, True)
        hal.activate(2, True)
        assert hal.get_events() == []

    def test_accel_event_returned_when_data_ready(self):
        """DATA_RDY_INT ビット (bit 3) が立っているとき加速度計イベントが返ることを確認する。"""
        accel_regs = _encode_accel_regs(az=2048)
        bus = _make_icm42688p_bus(extra_regs={_REG_INT_STATUS: 0x08, **accel_regs})
        hal = TDKSensorHAL()
        hal.initialize(bus)
        hal.activate(1, True)
        events = hal.get_events()
        accel_events = [e for e in events if e.sensor_type == SensorType.ACCELEROMETER]
        assert len(accel_events) == 1

    def test_gyro_event_returned_when_data_ready(self):
        """DATA_RDY_INT ビット (bit 3) が立っているときジャイロイベントが返ることを確認する。"""
        gyro_regs = _encode_gyro_regs(gx=164)
        bus = _make_icm42688p_bus(extra_regs={_REG_INT_STATUS: 0x08, **gyro_regs})
        hal = TDKSensorHAL()
        hal.initialize(bus)
        hal.activate(2, True)
        events = hal.get_events()
        gyro_events = [e for e in events if e.sensor_type == SensorType.GYROSCOPE]
        assert len(gyro_events) == 1

    def test_no_event_for_inactive_sensor(self):
        """非アクティブセンサーのイベントは返らないことを確認する。"""
        accel_regs = _encode_accel_regs(ax=1000)
        gyro_regs = _encode_gyro_regs(gx=1000)
        bus = _make_icm42688p_bus(extra_regs={_REG_INT_STATUS: 0x08, **accel_regs, **gyro_regs})
        hal = TDKSensorHAL()
        hal.initialize(bus)
        # どちらも activate しない
        events = hal.get_events()
        assert events == []

    def test_accel_raw_to_physical_conversion(self):
        """生データ → g への変換が正しいことを確認する。"""
        raw_az = 2048  # 2048 LSB → 1.0 g
        expected_az = raw_az * _ACCEL_SENSITIVITY_G_PER_LSB
        accel_regs = _encode_accel_regs(az=raw_az)
        bus = _make_icm42688p_bus(extra_regs={_REG_INT_STATUS: 0x08, **accel_regs})
        hal = TDKSensorHAL()
        hal.initialize(bus)
        hal.activate(1, True)
        events = hal.get_events()
        accel_events = [e for e in events if e.sensor_type == SensorType.ACCELEROMETER]
        assert len(accel_events) == 1
        assert pytest.approx(accel_events[0].values[2], rel=1e-6) == expected_az

    def test_gyro_raw_to_physical_conversion(self):
        """生データ → dps への変換が正しいことを確認する。"""
        raw_gx = 164  # 164 LSB → 10.0 dps
        expected_gx = raw_gx * _GYRO_SENSITIVITY_DPS_PER_LSB
        gyro_regs = _encode_gyro_regs(gx=raw_gx)
        bus = _make_icm42688p_bus(extra_regs={_REG_INT_STATUS: 0x08, **gyro_regs})
        hal = TDKSensorHAL()
        hal.initialize(bus)
        hal.activate(2, True)
        events = hal.get_events()
        gyro_events = [e for e in events if e.sensor_type == SensorType.GYROSCOPE]
        assert len(gyro_events) == 1
        assert pytest.approx(gyro_events[0].values[0], rel=1e-6) == expected_gx

    def test_negative_raw_value_conversion(self):
        """負の生データが正しく変換されることを確認する (2 の補数)。"""
        raw_gx = -164
        expected_gx = raw_gx * _GYRO_SENSITIVITY_DPS_PER_LSB
        gyro_regs = _encode_gyro_regs(gx=raw_gx)
        bus = _make_icm42688p_bus(extra_regs={_REG_INT_STATUS: 0x08, **gyro_regs})
        hal = TDKSensorHAL()
        hal.initialize(bus)
        hal.activate(2, True)
        events = hal.get_events()
        gyro_events = [e for e in events if e.sensor_type == SensorType.GYROSCOPE]
        assert len(gyro_events) == 1
        assert pytest.approx(gyro_events[0].values[0], rel=1e-6) == expected_gx

    def test_event_timestamp_is_positive(self):
        """イベントのタイムスタンプが正の値であることを確認する。"""
        accel_regs = _encode_accel_regs(ax=1000)
        bus = _make_icm42688p_bus(extra_regs={_REG_INT_STATUS: 0x08, **accel_regs})
        hal = TDKSensorHAL()
        hal.initialize(bus)
        hal.activate(1, True)
        events = hal.get_events()
        assert events[0].timestamp_ns > 0


class TestTDKSensorHALFinalize:
    """TDKSensorHAL.finalize() のテスト。"""

    def test_finalize_releases_bus(self):
        """finalize() 後にバスが解放されることを確認する。"""
        bus = _make_icm42688p_bus()
        hal = TDKSensorHAL()
        hal.initialize(bus)
        hal.finalize()
        assert hal._bus is None

    def test_finalize_clears_active_sensors(self):
        """finalize() 後にアクティブセンサー辞書がクリアされることを確認する。"""
        bus = _make_icm42688p_bus()
        hal = TDKSensorHAL()
        hal.initialize(bus)
        hal.activate(1, True)
        hal.finalize()
        assert hal._active == {}

    def test_finalize_clears_sampling_period(self):
        """finalize() 後にサンプリング周期辞書がクリアされることを確認する。"""
        bus = _make_icm42688p_bus()
        hal = TDKSensorHAL()
        hal.initialize(bus)
        hal.configure(1, 10_000, 0)
        hal.finalize()
        assert hal._sampling_period_us == {}

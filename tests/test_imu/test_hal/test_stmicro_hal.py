"""Unit tests for STMicroSensorHAL."""

import struct

import pytest

from ai_driven_development_labs.bus.mock import MockBusDriver
from ai_driven_development_labs.imu.hal.stmicro import (
    _ACCEL_SENSITIVITY_G_PER_LSB,
    _CTRL1_XL_DEFAULT,
    _CTRL2_G_DEFAULT,
    _CTRL3_C_DEFAULT,
    _GYRO_SENSITIVITY_DPS_PER_LSB,
    _REG_CTRL1_XL,
    _REG_CTRL2_G,
    _REG_CTRL3_C,
    _REG_CTRL4_C,
    _REG_CTRL5_C,
    _REG_CTRL6_C,
    _REG_CTRL7_G,
    _REG_CTRL8_XL,
    _REG_CTRL9_XL,
    _REG_CTRL10_C,
    _REG_OUT_START,
    _REG_STATUS,
    _REG_WHO_AM_I,
    STMicroSensorHAL,
)
from ai_driven_development_labs.imu.interfaces import ISensorHAL
from ai_driven_development_labs.imu.models import SensorType


def _make_lsm6dso_bus(extra_regs: dict[int, int] | None = None) -> MockBusDriver:
    """LSM6DSO の WHO_AM_I を持つ MockBusDriver を生成する。"""
    reg_map = {_REG_WHO_AM_I: 0x6C}
    if extra_regs:
        reg_map.update(extra_regs)
    return MockBusDriver(register_map=reg_map)


def _make_ism330dhcx_bus(extra_regs: dict[int, int] | None = None) -> MockBusDriver:
    """ISM330DHCX の WHO_AM_I を持つ MockBusDriver を生成する。"""
    reg_map = {_REG_WHO_AM_I: 0x6B}
    if extra_regs:
        reg_map.update(extra_regs)
    return MockBusDriver(register_map=reg_map)


def _encode_out_registers(
    gx: int = 0,
    gy: int = 0,
    gz: int = 0,
    ax: int = 0,
    ay: int = 0,
    az: int = 0,
) -> dict[int, int]:
    """出力レジスタ (0x22〜0x2D) に書き込む 12 バイトのレジスタマップを返す。"""
    raw = struct.pack("<hhhhhh", gx, gy, gz, ax, ay, az)
    return {_REG_OUT_START + i: b for i, b in enumerate(raw)}


class TestSTMicroSensorHALInit:
    """STMicroSensorHAL 初期化のテスト。"""

    def test_is_instance_of_isensor_hal(self):
        """STMicroSensorHAL が ISensorHAL のインスタンスであることを確認する。"""
        hal = STMicroSensorHAL()
        assert isinstance(hal, ISensorHAL)

    def test_initialize_lsm6dso(self):
        """LSM6DSO の WHO_AM_I (0x6C) で初期化できることを確認する。"""
        bus = _make_lsm6dso_bus()
        hal = STMicroSensorHAL()
        hal.initialize(bus)
        assert hal._device_name == "LSM6DSO"

    def test_initialize_ism330dhcx(self):
        """ISM330DHCX の WHO_AM_I (0x6B) で初期化できることを確認する。"""
        bus = _make_ism330dhcx_bus()
        hal = STMicroSensorHAL()
        hal.initialize(bus)
        assert hal._device_name == "ISM330DHCX"

    def test_unsupported_who_am_i_raises(self):
        """未サポートの WHO_AM_I の場合に RuntimeError が発生することを確認する。"""
        bus = MockBusDriver(register_map={_REG_WHO_AM_I: 0xFF})
        hal = STMicroSensorHAL()
        with pytest.raises(RuntimeError, match="Unsupported device"):
            hal.initialize(bus)

    def test_control_registers_written_on_init(self):
        """初期化時にコントロールレジスタが正しい値で書き込まれることを確認する。"""
        bus = _make_lsm6dso_bus()
        hal = STMicroSensorHAL()
        hal.initialize(bus)
        assert bus._registers[_REG_CTRL1_XL] == _CTRL1_XL_DEFAULT
        assert bus._registers[_REG_CTRL2_G] == _CTRL2_G_DEFAULT
        assert bus._registers[_REG_CTRL3_C] == _CTRL3_C_DEFAULT
        assert bus._registers[_REG_CTRL4_C] == 0x00
        assert bus._registers[_REG_CTRL5_C] == 0x00
        assert bus._registers[_REG_CTRL6_C] == 0x00
        assert bus._registers[_REG_CTRL7_G] == 0x00
        assert bus._registers[_REG_CTRL8_XL] == 0x00
        assert bus._registers[_REG_CTRL9_XL] == 0x00
        assert bus._registers[_REG_CTRL10_C] == 0x00


class TestSTMicroSensorHALSensorList:
    """STMicroSensorHAL.get_sensor_list() のテスト。"""

    def setup_method(self):
        bus = _make_lsm6dso_bus()
        self.hal = STMicroSensorHAL()
        self.hal.initialize(bus)

    def test_sensor_list_has_two_sensors(self):
        """初期化後に 2 センサーが返ることを確認する。"""
        sensors = self.hal.get_sensor_list()
        assert len(sensors) == 2

    def test_vendor_is_stmicroelectronics(self):
        """ベンダーが 'STMicroelectronics' であることを確認する。"""
        sensors = self.hal.get_sensor_list()
        for s in sensors:
            assert s.vendor == "STMicroelectronics"

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
        """センサー名にデバイス名 (LSM6DSO) が含まれることを確認する。"""
        sensors = self.hal.get_sensor_list()
        for s in sensors:
            assert "LSM6DSO" in s.name


class TestSTMicroSensorHALGetEvents:
    """STMicroSensorHAL.get_events() のテスト。"""

    def test_no_events_when_status_reg_zero(self):
        """STATUS_REG = 0 (データ未準備) の場合に空リストを返すことを確認する。"""
        bus = _make_lsm6dso_bus(extra_regs={_REG_STATUS: 0x00})
        hal = STMicroSensorHAL()
        hal.initialize(bus)
        hal.activate(1, True)
        hal.activate(2, True)
        assert hal.get_events() == []

    def test_accel_event_returned_when_xlda_set(self):
        """XLDA ビット (bit 0) が立っているとき加速度計イベントが返ることを確認する。"""
        out_regs = _encode_out_registers(ax=16384)
        bus = _make_lsm6dso_bus(extra_regs={_REG_STATUS: 0x01, **out_regs})
        hal = STMicroSensorHAL()
        hal.initialize(bus)
        hal.activate(1, True)
        events = hal.get_events()
        accel_events = [e for e in events if e.sensor_type == SensorType.ACCELEROMETER]
        assert len(accel_events) == 1

    def test_gyro_event_returned_when_gda_set(self):
        """GDA ビット (bit 1) が立っているときジャイロイベントが返ることを確認する。"""
        out_regs = _encode_out_registers(gx=1000)
        bus = _make_lsm6dso_bus(extra_regs={_REG_STATUS: 0x02, **out_regs})
        hal = STMicroSensorHAL()
        hal.initialize(bus)
        hal.activate(2, True)
        events = hal.get_events()
        gyro_events = [e for e in events if e.sensor_type == SensorType.GYROSCOPE]
        assert len(gyro_events) == 1

    def test_no_event_for_inactive_sensor(self):
        """非アクティブセンサーのイベントは返らないことを確認する。"""
        out_regs = _encode_out_registers(ax=1000, gx=1000)
        bus = _make_lsm6dso_bus(extra_regs={_REG_STATUS: 0x03, **out_regs})
        hal = STMicroSensorHAL()
        hal.initialize(bus)
        # どちらも activate しない
        events = hal.get_events()
        assert events == []

    def test_accel_raw_to_physical_conversion(self):
        """生データ → g への変換が正しいことを確認する。"""
        raw_az = 16384  # 16384 LSB
        expected_az = raw_az * _ACCEL_SENSITIVITY_G_PER_LSB
        out_regs = _encode_out_registers(az=raw_az)
        bus = _make_lsm6dso_bus(extra_regs={_REG_STATUS: 0x01, **out_regs})
        hal = STMicroSensorHAL()
        hal.initialize(bus)
        hal.activate(1, True)
        events = hal.get_events()
        accel_events = [e for e in events if e.sensor_type == SensorType.ACCELEROMETER]
        assert len(accel_events) == 1
        assert pytest.approx(accel_events[0].values[2], rel=1e-6) == expected_az

    def test_gyro_raw_to_physical_conversion(self):
        """生データ → dps への変換が正しいことを確認する。"""
        raw_gx = 1000  # 1000 LSB
        expected_gx = raw_gx * _GYRO_SENSITIVITY_DPS_PER_LSB
        out_regs = _encode_out_registers(gx=raw_gx)
        bus = _make_lsm6dso_bus(extra_regs={_REG_STATUS: 0x02, **out_regs})
        hal = STMicroSensorHAL()
        hal.initialize(bus)
        hal.activate(2, True)
        events = hal.get_events()
        gyro_events = [e for e in events if e.sensor_type == SensorType.GYROSCOPE]
        assert len(gyro_events) == 1
        assert pytest.approx(gyro_events[0].values[0], rel=1e-6) == expected_gx

    def test_negative_raw_value_conversion(self):
        """負の生データが正しく変換されることを確認する (2 の補数)。"""
        raw_gx = -1000
        expected_gx = raw_gx * _GYRO_SENSITIVITY_DPS_PER_LSB
        out_regs = _encode_out_registers(gx=raw_gx)
        bus = _make_lsm6dso_bus(extra_regs={_REG_STATUS: 0x02, **out_regs})
        hal = STMicroSensorHAL()
        hal.initialize(bus)
        hal.activate(2, True)
        events = hal.get_events()
        gyro_events = [e for e in events if e.sensor_type == SensorType.GYROSCOPE]
        assert len(gyro_events) == 1
        assert pytest.approx(gyro_events[0].values[0], rel=1e-6) == expected_gx

    def test_event_timestamp_is_positive(self):
        """イベントのタイムスタンプが正の値であることを確認する。"""
        out_regs = _encode_out_registers(ax=1000)
        bus = _make_lsm6dso_bus(extra_regs={_REG_STATUS: 0x01, **out_regs})
        hal = STMicroSensorHAL()
        hal.initialize(bus)
        hal.activate(1, True)
        events = hal.get_events()
        assert events[0].timestamp_ns > 0


class TestSTMicroSensorHALFinalize:
    """STMicroSensorHAL.finalize() のテスト。"""

    def test_finalize_releases_bus(self):
        """finalize() 後にバスが解放されることを確認する。"""
        bus = _make_lsm6dso_bus()
        hal = STMicroSensorHAL()
        hal.initialize(bus)
        hal.finalize()
        assert hal._bus is None

    def test_finalize_clears_active_sensors(self):
        """finalize() 後にアクティブセンサー辞書がクリアされることを確認する。"""
        bus = _make_lsm6dso_bus()
        hal = STMicroSensorHAL()
        hal.initialize(bus)
        hal.activate(1, True)
        hal.finalize()
        assert hal._active == {}

    def test_finalize_clears_sampling_period(self):
        """finalize() 後にサンプリング周期辞書がクリアされることを確認する。"""
        bus = _make_lsm6dso_bus()
        hal = STMicroSensorHAL()
        hal.initialize(bus)
        hal.configure(1, 10_000, 0)
        hal.finalize()
        assert hal._sampling_period_us == {}

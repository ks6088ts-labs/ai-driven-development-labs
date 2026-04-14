"""Unit tests for IMU HAL data models."""

import pytest

from ai_driven_development_labs.imu.models import ReportingMode, SensorEvent, SensorInfo, SensorType


class TestSensorType:
    """SensorType enum のテスト。"""

    def test_accelerometer_value(self):
        """ACCELEROMETER の値が Android SensorType.aidl 準拠であることを確認する。"""
        assert SensorType.ACCELEROMETER == 1

    def test_gyroscope_value(self):
        """GYROSCOPE の値が Android SensorType.aidl 準拠であることを確認する。"""
        assert SensorType.GYROSCOPE == 4

    def test_accelerometer_uncalibrated_value(self):
        """ACCELEROMETER_UNCALIBRATED の値を確認する。"""
        assert SensorType.ACCELEROMETER_UNCALIBRATED == 35

    def test_gyroscope_uncalibrated_value(self):
        """GYROSCOPE_UNCALIBRATED の値を確認する。"""
        assert SensorType.GYROSCOPE_UNCALIBRATED == 16

    def test_is_int_enum(self):
        """SensorType が int として比較できることを確認する。"""
        assert SensorType.ACCELEROMETER == 1
        assert isinstance(SensorType.GYROSCOPE, int)


class TestReportingMode:
    """ReportingMode enum のテスト。"""

    def test_continuous_value(self):
        """CONTINUOUS の値を確認する。"""
        assert ReportingMode.CONTINUOUS == 0

    def test_on_change_value(self):
        """ON_CHANGE の値を確認する。"""
        assert ReportingMode.ON_CHANGE == 1

    def test_one_shot_value(self):
        """ONE_SHOT の値を確認する。"""
        assert ReportingMode.ONE_SHOT == 2

    def test_special_trigger_value(self):
        """SPECIAL_TRIGGER の値を確認する。"""
        assert ReportingMode.SPECIAL_TRIGGER == 3


class TestSensorInfo:
    """SensorInfo データクラスのテスト。"""

    def test_create_minimal(self):
        """必須フィールドのみでインスタンスを生成できることを確認する。"""
        info = SensorInfo(
            sensor_handle=1,
            name="Accelerometer",
            vendor="TestVendor",
            sensor_type=SensorType.ACCELEROMETER,
        )
        assert info.sensor_handle == 1
        assert info.name == "Accelerometer"
        assert info.vendor == "TestVendor"
        assert info.sensor_type == SensorType.ACCELEROMETER

    def test_default_values(self):
        """デフォルト値が正しく設定されることを確認する。"""
        info = SensorInfo(
            sensor_handle=2,
            name="Gyroscope",
            vendor="TestVendor",
            sensor_type=SensorType.GYROSCOPE,
        )
        assert info.version == 1
        assert info.max_range == 0.0
        assert info.resolution == 0.0
        assert info.power == 0.0
        assert info.min_delay == 0
        assert info.max_delay == 0
        assert info.fifo_reserved_event_count == 0
        assert info.fifo_max_event_count == 0
        assert info.reporting_mode == ReportingMode.CONTINUOUS

    def test_create_full(self):
        """すべてのフィールドを指定してインスタンスを生成できることを確認する。"""
        info = SensorInfo(
            sensor_handle=10,
            name="LSM6DSO Accelerometer",
            vendor="STMicroelectronics",
            sensor_type=SensorType.ACCELEROMETER,
            version=2,
            max_range=16.0,
            resolution=0.001,
            power=0.9,
            min_delay=1000,
            max_delay=500000,
            fifo_reserved_event_count=128,
            fifo_max_event_count=4096,
            reporting_mode=ReportingMode.CONTINUOUS,
        )
        assert info.sensor_handle == 10
        assert info.name == "LSM6DSO Accelerometer"
        assert info.vendor == "STMicroelectronics"
        assert info.version == 2
        assert info.max_range == 16.0
        assert info.resolution == 0.001
        assert info.power == 0.9
        assert info.min_delay == 1000
        assert info.max_delay == 500000
        assert info.fifo_reserved_event_count == 128
        assert info.fifo_max_event_count == 4096
        assert info.reporting_mode == ReportingMode.CONTINUOUS

    def test_frozen(self):
        """SensorInfo が frozen dataclass であることを確認する（変更不可）。"""
        info = SensorInfo(
            sensor_handle=1,
            name="Accelerometer",
            vendor="TestVendor",
            sensor_type=SensorType.ACCELEROMETER,
        )
        with pytest.raises(Exception):
            setattr(info, "name", "Modified")


class TestSensorEvent:
    """SensorEvent データクラスのテスト。"""

    def test_create_minimal(self):
        """必須フィールドのみでインスタンスを生成できることを確認する。"""
        event = SensorEvent(
            sensor_handle=1,
            sensor_type=SensorType.ACCELEROMETER,
            timestamp_ns=1_000_000_000,
        )
        assert event.sensor_handle == 1
        assert event.sensor_type == SensorType.ACCELEROMETER
        assert event.timestamp_ns == 1_000_000_000
        assert event.values == []

    def test_create_with_values(self):
        """values フィールドを指定してインスタンスを生成できることを確認する。"""
        event = SensorEvent(
            sensor_handle=1,
            sensor_type=SensorType.ACCELEROMETER,
            timestamp_ns=2_000_000_000,
            values=[0.1, -9.8, 0.05],
        )
        assert event.values == [0.1, -9.8, 0.05]

    def test_values_default_is_independent(self):
        """values のデフォルト値がインスタンス間で共有されないことを確認する。"""
        event1 = SensorEvent(sensor_handle=1, sensor_type=SensorType.ACCELEROMETER, timestamp_ns=0)
        event2 = SensorEvent(sensor_handle=2, sensor_type=SensorType.GYROSCOPE, timestamp_ns=0)
        event1.values.append(1.0)
        assert event2.values == []

    def test_mutable(self):
        """SensorEvent が mutable であることを確認する。"""
        event = SensorEvent(
            sensor_handle=1,
            sensor_type=SensorType.ACCELEROMETER,
            timestamp_ns=0,
            values=[0.0, 0.0, 0.0],
        )
        event.timestamp_ns = 999
        assert event.timestamp_ns == 999

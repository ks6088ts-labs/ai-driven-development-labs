"""Unit tests for IMU HAL CLI using typer.testing.CliRunner."""

import json

from typer.testing import CliRunner

from ai_driven_development_labs.imu.cli import app

runner = CliRunner()


class TestListSensors:
    """list-sensors コマンドのテスト。"""

    def test_list_sensors_mock_exit_code(self):
        """list-sensors --hal mock が正常終了することを確認する。"""
        result = runner.invoke(app, ["list-sensors", "--hal", "mock"])
        assert result.exit_code == 0

    def test_list_sensors_mock_shows_accelerometer(self):
        """list-sensors --hal mock に ACCELEROMETER が表示されることを確認する。"""
        result = runner.invoke(app, ["list-sensors", "--hal", "mock"])
        assert "ACCELEROMETER" in result.output

    def test_list_sensors_mock_shows_gyroscope(self):
        """list-sensors --hal mock に GYROSCOPE が表示されることを確認する。"""
        result = runner.invoke(app, ["list-sensors", "--hal", "mock"])
        assert "GYROSCOPE" in result.output

    def test_list_sensors_mock_shows_header(self):
        """list-sensors --hal mock にヘッダー行が表示されることを確認する。"""
        result = runner.invoke(app, ["list-sensors", "--hal", "mock"])
        assert "Handle" in result.output
        assert "Type" in result.output
        assert "Name" in result.output
        assert "Vendor" in result.output

    def test_list_sensors_invalid_hal_exits_nonzero(self):
        """不正な --hal 指定でゼロ以外の終了コードが返ることを確認する。"""
        result = runner.invoke(app, ["list-sensors", "--hal", "invalid"])
        assert result.exit_code != 0

    def test_list_sensors_invalid_bus_exits_nonzero(self):
        """不正な --bus 指定でゼロ以外の終了コードが返ることを確認する。"""
        result = runner.invoke(app, ["list-sensors", "--hal", "mock", "--bus", "invalid"])
        assert result.exit_code != 0


class TestReadOnce:
    """read-once コマンドのテスト。"""

    def test_read_once_csv_exit_code(self):
        """read-once --hal mock (デフォルト CSV) が正常終了することを確認する。"""
        result = runner.invoke(app, ["read-once", "--hal", "mock"])
        assert result.exit_code == 0

    def test_read_once_csv_has_header(self):
        """read-once CSV 出力にヘッダー行が含まれることを確認する。"""
        result = runner.invoke(app, ["read-once", "--hal", "mock", "--format", "csv"])
        assert "timestamp_ns,sensor_handle,sensor_type,x,y,z" in result.output

    def test_read_once_csv_has_accelerometer(self):
        """read-once CSV 出力に ACCELEROMETER データが含まれることを確認する。"""
        result = runner.invoke(app, ["read-once", "--hal", "mock", "--format", "csv"])
        assert "ACCELEROMETER" in result.output

    def test_read_once_csv_has_gyroscope(self):
        """read-once CSV 出力に GYROSCOPE データが含まれることを確認する。"""
        result = runner.invoke(app, ["read-once", "--hal", "mock", "--format", "csv"])
        assert "GYROSCOPE" in result.output

    def test_read_once_json_exit_code(self):
        """read-once --hal mock --format json が正常終了することを確認する。"""
        result = runner.invoke(app, ["read-once", "--hal", "mock", "--format", "json"])
        assert result.exit_code == 0

    def test_read_once_json_is_valid_json(self):
        """read-once JSON 出力が有効な JSON であることを確認する。"""
        result = runner.invoke(app, ["read-once", "--hal", "mock", "--format", "json"])
        data = json.loads(result.output)
        assert isinstance(data, list)

    def test_read_once_json_has_required_fields(self):
        """read-once JSON 出力に必須フィールドが含まれることを確認する。"""
        result = runner.invoke(app, ["read-once", "--hal", "mock", "--format", "json"])
        data = json.loads(result.output)
        assert len(data) > 0
        for item in data:
            assert "sensor_handle" in item
            assert "sensor_type" in item
            assert "timestamp_ns" in item
            assert "values" in item

    def test_read_once_json_sensor_types(self):
        """read-once JSON 出力のセンサー種別を確認する。"""
        result = runner.invoke(app, ["read-once", "--hal", "mock", "--format", "json"])
        data = json.loads(result.output)
        sensor_types = {item["sensor_type"] for item in data}
        assert "ACCELEROMETER" in sensor_types
        assert "GYROSCOPE" in sensor_types

    def test_read_once_table_exit_code(self):
        """read-once --hal mock --format table が正常終了することを確認する。"""
        result = runner.invoke(app, ["read-once", "--hal", "mock", "--format", "table"])
        assert result.exit_code == 0

    def test_read_once_table_has_header(self):
        """read-once テーブル出力にヘッダーが含まれることを確認する。"""
        result = runner.invoke(app, ["read-once", "--hal", "mock", "--format", "table"])
        assert "Timestamp" in result.output

    def test_read_once_invalid_hal_exits_nonzero(self):
        """不正な --hal 指定でゼロ以外の終了コードが返ることを確認する。"""
        result = runner.invoke(app, ["read-once", "--hal", "invalid"])
        assert result.exit_code != 0

    def test_read_once_invalid_bus_exits_nonzero(self):
        """不正な --bus 指定でゼロ以外の終了コードが返ることを確認する。"""
        result = runner.invoke(app, ["read-once", "--hal", "mock", "--bus", "invalid"])
        assert result.exit_code != 0


class TestRead:
    """read コマンドのテスト。"""

    def test_read_mock_count_1_exit_code(self):
        """read --hal mock --count 1 が正常終了することを確認する。"""
        result = runner.invoke(app, ["read", "--hal", "mock", "--count", "1", "--interval", "0"])
        assert result.exit_code == 0

    def test_read_mock_count_3_exit_code(self):
        """read --hal mock --count 3 が正常終了することを確認する。"""
        result = runner.invoke(app, ["read", "--hal", "mock", "--count", "3", "--interval", "0"])
        assert result.exit_code == 0

    def test_read_mock_csv_has_header(self):
        """read CSV 出力にヘッダー行が含まれることを確認する。"""
        result = runner.invoke(app, ["read", "--hal", "mock", "--count", "1", "--interval", "0"])
        assert "timestamp_ns,sensor_handle,sensor_type,x,y,z" in result.output

    def test_read_mock_csv_has_data(self):
        """read CSV 出力にセンサーデータが含まれることを確認する。"""
        result = runner.invoke(app, ["read", "--hal", "mock", "--count", "1", "--interval", "0"])
        assert "ACCELEROMETER" in result.output
        assert "GYROSCOPE" in result.output

    def test_read_mock_json_exit_code(self):
        """read --format json が正常終了することを確認する。"""
        result = runner.invoke(app, ["read", "--hal", "mock", "--count", "1", "--interval", "0", "--format", "json"])
        assert result.exit_code == 0

    def test_read_mock_table_exit_code(self):
        """read --format table が正常終了することを確認する。"""
        result = runner.invoke(app, ["read", "--hal", "mock", "--count", "1", "--interval", "0", "--format", "table"])
        assert result.exit_code == 0

    def test_read_invalid_hal_exits_nonzero(self):
        """不正な --hal 指定でゼロ以外の終了コードが返ることを確認する。"""
        result = runner.invoke(app, ["read", "--hal", "invalid", "--count", "1"])
        assert result.exit_code != 0

    def test_read_invalid_bus_exits_nonzero(self):
        """不正な --bus 指定でゼロ以外の終了コードが返ることを確認する。"""
        result = runner.invoke(app, ["read", "--hal", "mock", "--bus", "invalid", "--count", "1"])
        assert result.exit_code != 0


class TestInfo:
    """info コマンドのテスト。"""

    def test_info_mock_exit_code(self):
        """info --hal mock が正常終了することを確認する。"""
        result = runner.invoke(app, ["info", "--hal", "mock"])
        assert result.exit_code == 0

    def test_info_shows_hal_type(self):
        """info 出力に HAL 種別が含まれることを確認する。"""
        result = runner.invoke(app, ["info", "--hal", "mock"])
        assert "mock" in result.output

    def test_info_shows_bus_driver_class(self):
        """info 出力にバスドライバクラス名が含まれることを確認する。"""
        result = runner.invoke(app, ["info", "--hal", "mock"])
        assert "MockBusDriver" in result.output

    def test_info_shows_sensor_hal_class(self):
        """info 出力にセンサー HAL クラス名が含まれることを確認する。"""
        result = runner.invoke(app, ["info", "--hal", "mock"])
        assert "MockSensorHAL" in result.output

    def test_info_invalid_hal_exits_nonzero(self):
        """不正な --hal 指定でゼロ以外の終了コードが返ることを確認する。"""
        result = runner.invoke(app, ["info", "--hal", "invalid"])
        assert result.exit_code != 0


class TestRegisterDump:
    """register-dump コマンドのテスト。"""

    def test_register_dump_mock_exit_code(self):
        """register-dump --hal mock が正常終了することを確認する。"""
        result = runner.invoke(app, ["register-dump", "--hal", "mock"])
        assert result.exit_code == 0

    def test_register_dump_mock_shows_header(self):
        """register-dump 出力に 'Register Dump' が含まれることを確認する。"""
        result = runner.invoke(app, ["register-dump", "--hal", "mock"])
        assert "Register Dump" in result.output

    def test_register_dump_invalid_hal_exits_nonzero(self):
        """不正な --hal 指定でゼロ以外の終了コードが返ることを確認する。"""
        result = runner.invoke(app, ["register-dump", "--hal", "invalid"])
        assert result.exit_code != 0

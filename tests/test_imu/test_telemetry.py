"""Unit tests for ImuTelemetry using in-memory OTel exporters."""

import pytest
from opentelemetry.sdk.metrics.export import InMemoryMetricReader
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from ai_driven_development_labs.imu.models import SensorEvent, SensorInfo, SensorType
from ai_driven_development_labs.imu.telemetry import ImuTelemetry


def _make_telemetry() -> tuple[ImuTelemetry, InMemoryMetricReader, InMemorySpanExporter]:
    """テスト用の ImuTelemetry と in-memory エクスポーターを生成する。"""
    reader = InMemoryMetricReader()
    span_exporter = InMemorySpanExporter()
    tel = ImuTelemetry(metric_reader=reader, span_exporter=span_exporter)
    return tel, reader, span_exporter


class TestImuTelemetryMetrics:
    """ImuTelemetry のメトリクス計装テスト。"""

    def test_accel_gauges_recorded(self):
        """加速度計のゲージ値が記録されることを確認する。"""
        tel, reader, _ = _make_telemetry()
        events = [
            SensorEvent(
                sensor_handle=1,
                sensor_type=SensorType.ACCELEROMETER,
                timestamp_ns=0,
                values=[1.0, 2.0, 9.81],
            )
        ]
        tel.record_events(events)

        data = reader.get_metrics_data()
        metric_names = {m.name for rm in data.resource_metrics for sm in rm.scope_metrics for m in sm.metrics}
        assert "imu.accel.x" in metric_names
        assert "imu.accel.y" in metric_names
        assert "imu.accel.z" in metric_names
        tel.shutdown()

    def test_gyro_gauges_recorded(self):
        """ジャイロスコープのゲージ値が記録されることを確認する。"""
        tel, reader, _ = _make_telemetry()
        events = [
            SensorEvent(
                sensor_handle=2,
                sensor_type=SensorType.GYROSCOPE,
                timestamp_ns=0,
                values=[0.1, 0.2, 0.3],
            )
        ]
        tel.record_events(events)

        data = reader.get_metrics_data()
        metric_names = {m.name for rm in data.resource_metrics for sm in rm.scope_metrics for m in sm.metrics}
        assert "imu.gyro.x" in metric_names
        assert "imu.gyro.y" in metric_names
        assert "imu.gyro.z" in metric_names
        tel.shutdown()

    def test_accel_gauge_values(self):
        """加速度計のゲージ値が正しいことを確認する。"""
        tel, reader, _ = _make_telemetry()
        events = [
            SensorEvent(
                sensor_handle=1,
                sensor_type=SensorType.ACCELEROMETER,
                timestamp_ns=0,
                values=[1.5, -2.5, 9.81],
            )
        ]
        tel.record_events(events)

        data = reader.get_metrics_data()
        accel_x = next(
            m
            for rm in data.resource_metrics
            for sm in rm.scope_metrics
            for m in sm.metrics
            if m.name == "imu.accel.x"
        )
        dp = accel_x.data.data_points[0]
        assert dp.value == pytest.approx(1.5)
        tel.shutdown()

    def test_gyro_gauge_values(self):
        """ジャイロスコープのゲージ値が正しいことを確認する。"""
        tel, reader, _ = _make_telemetry()
        events = [
            SensorEvent(
                sensor_handle=2,
                sensor_type=SensorType.GYROSCOPE,
                timestamp_ns=0,
                values=[0.1, 0.2, 0.3],
            )
        ]
        tel.record_events(events)

        data = reader.get_metrics_data()
        gyro_z = next(
            m
            for rm in data.resource_metrics
            for sm in rm.scope_metrics
            for m in sm.metrics
            if m.name == "imu.gyro.z"
        )
        dp = gyro_z.data.data_points[0]
        assert dp.value == pytest.approx(0.3)
        tel.shutdown()

    def test_read_latency_histogram_recorded(self):
        """imu.read.latency ヒストグラムが記録されることを確認する。"""
        tel, reader, _ = _make_telemetry()
        tel.record_read_latency(12.5)

        data = reader.get_metrics_data()
        metric_names = {m.name for rm in data.resource_metrics for sm in rm.scope_metrics for m in sm.metrics}
        assert "imu.read.latency" in metric_names
        tel.shutdown()

    def test_read_latency_histogram_sum(self):
        """imu.read.latency の sum が記録した値と一致することを確認する。"""
        tel, reader, _ = _make_telemetry()
        tel.record_read_latency(10.0)
        tel.record_read_latency(20.0)

        data = reader.get_metrics_data()
        hist = next(
            m
            for rm in data.resource_metrics
            for sm in rm.scope_metrics
            for m in sm.metrics
            if m.name == "imu.read.latency"
        )
        dp = hist.data.data_points[0]
        assert dp.sum == pytest.approx(30.0)
        assert dp.count == 2
        tel.shutdown()

    def test_sensor_type_attributes_on_accel(self):
        """加速度計のメトリクスに sensor_type 属性が付与されることを確認する。"""
        tel, reader, _ = _make_telemetry()
        events = [
            SensorEvent(
                sensor_handle=1,
                sensor_type=SensorType.ACCELEROMETER,
                timestamp_ns=0,
                values=[0.0, 0.0, 9.81],
            )
        ]
        tel.record_events(events)

        data = reader.get_metrics_data()
        accel_x = next(
            m
            for rm in data.resource_metrics
            for sm in rm.scope_metrics
            for m in sm.metrics
            if m.name == "imu.accel.x"
        )
        attrs = accel_x.data.data_points[0].attributes
        assert attrs["sensor_type"] == "ACCELEROMETER"
        assert attrs["sensor_handle"] == "1"
        tel.shutdown()

    def test_vendor_attribute_from_sensor_info(self):
        """SensorInfo を渡すと vendor 属性が付与されることを確認する。"""
        tel, reader, _ = _make_telemetry()
        info = SensorInfo(sensor_handle=1, name="Accel", vendor="AcmeVendor", sensor_type=SensorType.ACCELEROMETER)
        events = [
            SensorEvent(
                sensor_handle=1,
                sensor_type=SensorType.ACCELEROMETER,
                timestamp_ns=0,
                values=[0.0, 0.0, 9.81],
            )
        ]
        tel.record_events(events, sensor_info_by_handle={1: info})

        data = reader.get_metrics_data()
        accel_x = next(
            m
            for rm in data.resource_metrics
            for sm in rm.scope_metrics
            for m in sm.metrics
            if m.name == "imu.accel.x"
        )
        attrs = accel_x.data.data_points[0].attributes
        assert attrs["vendor"] == "AcmeVendor"
        tel.shutdown()

    def test_unknown_sensor_type_not_recorded(self):
        """未知のセンサータイプはメトリクスを記録しないことを確認する。"""
        tel, reader, _ = _make_telemetry()
        events = [
            SensorEvent(
                sensor_handle=3,
                sensor_type=SensorType.GYROSCOPE_UNCALIBRATED,
                timestamp_ns=0,
                values=[0.0, 0.0, 0.0],
            )
        ]
        tel.record_events(events)

        data = reader.get_metrics_data()
        # No matching metrics were recorded, so data is None or contains no accel/gyro metrics
        if data is not None:
            metric_names = {m.name for rm in data.resource_metrics for sm in rm.scope_metrics for m in sm.metrics}
            assert "imu.accel.x" not in metric_names
            assert "imu.gyro.x" not in metric_names
        tel.shutdown()


class TestImuTelemetrySpans:
    """ImuTelemetry のトレース計装テスト。"""

    def test_imu_read_span_created(self):
        """span_imu_read() が 'imu.read' スパンを生成することを確認する。"""
        tel, _, span_exporter = _make_telemetry()
        with tel.span_imu_read():
            pass
        spans = span_exporter.get_finished_spans()
        assert any(s.name == "imu.read" for s in spans)
        tel.shutdown()

    def test_hal_initialize_span_created(self):
        """span_hal_initialize() が 'hal.initialize' スパンを生成することを確認する。"""
        tel, _, span_exporter = _make_telemetry()
        with tel.span_hal_initialize():
            pass
        spans = span_exporter.get_finished_spans()
        assert any(s.name == "hal.initialize" for s in spans)
        tel.shutdown()

    def test_hal_activate_span_created(self):
        """span_hal_activate() が 'hal.activate' スパンを生成することを確認する。"""
        tel, _, span_exporter = _make_telemetry()
        with tel.span_hal_activate(sensor_handle=1):
            pass
        spans = span_exporter.get_finished_spans()
        assert any(s.name == "hal.activate" for s in spans)
        tel.shutdown()

    def test_hal_activate_span_has_sensor_handle_attribute(self):
        """hal.activate スパンに sensor_handle 属性が付与されることを確認する。"""
        tel, _, span_exporter = _make_telemetry()
        with tel.span_hal_activate(sensor_handle=42):
            pass
        spans = span_exporter.get_finished_spans()
        activate_span = next(s for s in spans if s.name == "hal.activate")
        assert activate_span.attributes["sensor_handle"] == 42
        tel.shutdown()

    def test_child_spans_nested_within_imu_read(self):
        """hal.initialize と hal.activate が imu.read の子スパンになることを確認する。"""
        tel, _, span_exporter = _make_telemetry()
        with tel.span_imu_read():
            with tel.span_hal_initialize():
                pass
            with tel.span_hal_activate(sensor_handle=1):
                pass

        spans = span_exporter.get_finished_spans()
        parent_span = next(s for s in spans if s.name == "imu.read")
        init_span = next(s for s in spans if s.name == "hal.initialize")
        activate_span = next(s for s in spans if s.name == "hal.activate")

        assert init_span.parent is not None
        assert init_span.parent.span_id == parent_span.context.span_id
        assert activate_span.parent is not None
        assert activate_span.parent.span_id == parent_span.context.span_id
        tel.shutdown()

    def test_multiple_imu_read_spans(self):
        """複数回の span_imu_read() 呼び出しで個別スパンが生成されることを確認する。"""
        tel, _, span_exporter = _make_telemetry()
        with tel.span_imu_read():
            pass
        with tel.span_imu_read():
            pass
        spans = [s for s in span_exporter.get_finished_spans() if s.name == "imu.read"]
        assert len(spans) == 2
        tel.shutdown()


class TestImuTelemetryConfiguration:
    """ImuTelemetry の設定テスト。"""

    def test_service_name_in_resource(self):
        """リソースにサービス名が設定されることを確認する。"""
        tel, reader, _ = _make_telemetry()
        tel.record_read_latency(1.0)
        data = reader.get_metrics_data()
        assert data is not None
        assert data.resource_metrics[0].resource.attributes.get("service.name") == "imu-cli"
        tel.shutdown()

    def test_custom_service_name(self):
        """カスタムサービス名が設定できることを確認する。"""
        reader = InMemoryMetricReader()
        span_exporter = InMemorySpanExporter()
        tel = ImuTelemetry(service_name="custom-service", metric_reader=reader, span_exporter=span_exporter)
        tel.record_read_latency(1.0)
        data = reader.get_metrics_data()
        assert data.resource_metrics[0].resource.attributes.get("service.name") == "custom-service"
        tel.shutdown()


class TestImuTelemetryCliIntegration:
    """CLI の --otel フラグを使ったテスト。"""

    def _make_patched_telemetry(self) -> tuple[ImuTelemetry, InMemoryMetricReader, InMemorySpanExporter]:
        """インメモリエクスポーターを使った ImuTelemetry を生成する。"""
        reader = InMemoryMetricReader()
        span_exporter = InMemorySpanExporter()
        tel = ImuTelemetry(metric_reader=reader, span_exporter=span_exporter)
        return tel, reader, span_exporter

    def test_read_once_with_otel_flag(self):
        """read-once --otel が正常終了することを確認する。"""
        from unittest.mock import patch

        from typer.testing import CliRunner

        from ai_driven_development_labs.imu.cli import app

        tel, reader, span_exporter = self._make_patched_telemetry()
        cli_runner = CliRunner()
        with patch("ai_driven_development_labs.imu.telemetry.ImuTelemetry", return_value=tel):
            result = cli_runner.invoke(app, ["read-once", "--hal", "mock", "--otel"])
        assert result.exit_code == 0

    def test_read_with_otel_flag(self):
        """read --otel --count 1 が正常終了することを確認する。"""
        from unittest.mock import patch

        from typer.testing import CliRunner

        from ai_driven_development_labs.imu.cli import app

        tel, reader, span_exporter = self._make_patched_telemetry()
        cli_runner = CliRunner()
        with patch("ai_driven_development_labs.imu.telemetry.ImuTelemetry", return_value=tel):
            result = cli_runner.invoke(
                app, ["read", "--hal", "mock", "--count", "1", "--interval", "0", "--otel"]
            )
        assert result.exit_code == 0

    def test_read_once_with_otel_records_spans(self):
        """read-once --otel 実行後に imu.read スパンが記録されることを確認する。"""
        from unittest.mock import patch

        from typer.testing import CliRunner

        from ai_driven_development_labs.imu.cli import app

        tel, _, span_exporter = self._make_patched_telemetry()
        cli_runner = CliRunner()
        with patch("ai_driven_development_labs.imu.telemetry.ImuTelemetry", return_value=tel):
            result = cli_runner.invoke(app, ["read-once", "--hal", "mock", "--otel"])
        assert result.exit_code == 0
        span_names = [s.name for s in span_exporter.get_finished_spans()]
        assert "imu.read" in span_names
        assert "hal.initialize" in span_names
        assert "hal.activate" in span_names

    def test_read_with_otel_records_metrics(self):
        """read --otel 実行後に加速度計メトリクスが記録されることを確認する。"""
        from unittest.mock import patch

        from typer.testing import CliRunner

        from ai_driven_development_labs.imu.cli import app

        tel, reader, _ = self._make_patched_telemetry()
        cli_runner = CliRunner()
        with patch("ai_driven_development_labs.imu.telemetry.ImuTelemetry", return_value=tel):
            result = cli_runner.invoke(
                app, ["read", "--hal", "mock", "--count", "1", "--interval", "0", "--otel"]
            )
        assert result.exit_code == 0
        data = reader.get_metrics_data()
        assert data is not None
        metric_names = {m.name for rm in data.resource_metrics for sm in rm.scope_metrics for m in sm.metrics}
        assert "imu.read.latency" in metric_names

    def test_read_with_no_otel_flag_default(self):
        """read --no-otel (デフォルト) が OTel なしで正常終了することを確認する。"""
        from typer.testing import CliRunner

        from ai_driven_development_labs.imu.cli import app

        cli_runner = CliRunner()
        result = cli_runner.invoke(app, ["read", "--hal", "mock", "--count", "1", "--interval", "0", "--no-otel"])
        assert result.exit_code == 0

    def test_read_once_no_otel_is_default(self):
        """--otel なし (デフォルト) で read-once が正常終了することを確認する。"""
        from typer.testing import CliRunner

        from ai_driven_development_labs.imu.cli import app

        cli_runner = CliRunner()
        result = cli_runner.invoke(app, ["read-once", "--hal", "mock"])
        assert result.exit_code == 0

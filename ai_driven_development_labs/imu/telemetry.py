"""OpenTelemetry instrumentation for the IMU CLI.

Provides metrics (Gauge / Histogram) and distributed traces via OTLP.
Inject custom exporters / readers for unit testing.
"""

import os
from collections.abc import Generator
from contextlib import contextmanager

from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import MetricReader, PeriodicExportingMetricReader
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SimpleSpanProcessor, SpanExporter

from ai_driven_development_labs.imu.models import SensorEvent, SensorInfo, SensorType

_DEFAULT_ENDPOINT = "http://localhost:4317"
_DEFAULT_SERVICE_NAME = "imu-cli"


class ImuTelemetry:
    """OpenTelemetry Metrics / Traces instrumentation for the IMU CLI.

    By default exports via OTLP gRPC to the endpoint given by the
    ``OTEL_EXPORTER_OTLP_ENDPOINT`` environment variable (default
    ``http://localhost:4317``).  Pass *metric_reader* and/or *span_exporter*
    to inject in-memory stubs for unit testing.
    """

    def __init__(
        self,
        endpoint: str | None = None,
        service_name: str | None = None,
        metric_reader: MetricReader | None = None,
        span_exporter: SpanExporter | None = None,
    ) -> None:
        self._endpoint = endpoint or os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", _DEFAULT_ENDPOINT)
        self._service_name = service_name or os.environ.get("OTEL_SERVICE_NAME", _DEFAULT_SERVICE_NAME)

        resource = Resource.create({SERVICE_NAME: self._service_name})

        # --- Metrics provider ---
        if metric_reader is None:
            from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter

            reader: MetricReader = PeriodicExportingMetricReader(OTLPMetricExporter(endpoint=self._endpoint))
        else:
            reader = metric_reader

        self._meter_provider = MeterProvider(resource=resource, metric_readers=[reader])
        self._meter = self._meter_provider.get_meter("imu-cli")

        # Synchronous Gauge instruments (one per axis)
        self._accel_x = self._meter.create_gauge("imu.accel.x", unit="m/s2", description="Accelerometer X axis (m/s²)")
        self._accel_y = self._meter.create_gauge("imu.accel.y", unit="m/s2", description="Accelerometer Y axis (m/s²)")
        self._accel_z = self._meter.create_gauge("imu.accel.z", unit="m/s2", description="Accelerometer Z axis (m/s²)")
        self._gyro_x = self._meter.create_gauge("imu.gyro.x", unit="rad/s", description="Gyroscope X axis (rad/s)")
        self._gyro_y = self._meter.create_gauge("imu.gyro.y", unit="rad/s", description="Gyroscope Y axis (rad/s)")
        self._gyro_z = self._meter.create_gauge("imu.gyro.z", unit="rad/s", description="Gyroscope Z axis (rad/s)")
        self._read_latency = self._meter.create_histogram(
            "imu.read.latency", unit="ms", description="IMU read latency (ms)"
        )

        # --- Traces provider ---
        if span_exporter is None:
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

            processor = BatchSpanProcessor(OTLPSpanExporter(endpoint=self._endpoint))
        else:
            processor = SimpleSpanProcessor(span_exporter)

        self._tracer_provider = TracerProvider(resource=resource)
        self._tracer_provider.add_span_processor(processor)
        self._tracer = self._tracer_provider.get_tracer("imu-cli")

    # ------------------------------------------------------------------
    # Metric helpers
    # ------------------------------------------------------------------

    def record_events(
        self,
        events: list[SensorEvent],
        sensor_info_by_handle: dict[int, SensorInfo] | None = None,
    ) -> None:
        """Record sensor events as OTel gauge metrics.

        Args:
            events: Sensor events returned by ``ISensorHAL.get_events()``.
            sensor_info_by_handle: Optional mapping from ``sensor_handle`` to
                ``SensorInfo`` used to populate the ``vendor`` attribute.
        """
        for event in events:
            info = sensor_info_by_handle.get(event.sensor_handle) if sensor_info_by_handle else None
            attrs: dict[str, str] = {
                "sensor_handle": str(event.sensor_handle),
                "sensor_type": event.sensor_type.name,
                "vendor": info.vendor if info else "",
            }
            vals = (event.values + [0.0, 0.0, 0.0])[:3]
            if event.sensor_type == SensorType.ACCELEROMETER:
                self._accel_x.set(vals[0], attrs)
                self._accel_y.set(vals[1], attrs)
                self._accel_z.set(vals[2], attrs)
            elif event.sensor_type == SensorType.GYROSCOPE:
                self._gyro_x.set(vals[0], attrs)
                self._gyro_y.set(vals[1], attrs)
                self._gyro_z.set(vals[2], attrs)

    def record_read_latency(self, latency_ms: float) -> None:
        """Record a read-latency observation in the histogram.

        Args:
            latency_ms: Elapsed time for one ``get_events()`` call (milliseconds).
        """
        self._read_latency.record(latency_ms)

    # ------------------------------------------------------------------
    # Span helpers
    # ------------------------------------------------------------------

    @contextmanager
    def span_imu_read(self) -> Generator[None, None, None]:
        """Context manager that wraps a read operation in an ``imu.read`` span."""
        with self._tracer.start_as_current_span("imu.read"):
            yield

    @contextmanager
    def span_hal_initialize(self) -> Generator[None, None, None]:
        """Context manager that wraps HAL initialisation in a child span."""
        with self._tracer.start_as_current_span("hal.initialize"):
            yield

    @contextmanager
    def span_hal_activate(self, sensor_handle: int) -> Generator[None, None, None]:
        """Context manager that wraps a single sensor activation in a child span.

        Args:
            sensor_handle: The handle of the sensor being activated.
        """
        with self._tracer.start_as_current_span(
            "hal.activate",
            attributes={"sensor_handle": sensor_handle},
        ):
            yield

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def shutdown(self) -> None:
        """Flush pending data and shut down both providers."""
        self._meter_provider.shutdown()
        self._tracer_provider.shutdown()

"""IMU HAL CLI Tool."""

import json
import time
from typing import Annotated

import typer

from ai_driven_development_labs.bus.mock import MockBusDriver
from ai_driven_development_labs.imu.factory import create_bus_driver, create_sensor_hal

app = typer.Typer(help="IMU HAL CLI Tool")

_HAL_HELP = "使用する HAL (mock, stmicro, tdk)"
_BUS_HELP = "使用するバスドライバ (mock, spi, i2c)"
_BUS_ID_HELP = "バス番号"
_BUS_DEVICE_HELP = "デバイス番号（SPI CS） / I2C アドレス"
_FORMAT_HELP = "出力形式 (csv, json, table)"


def _format_events_csv(events, *, header: bool = False) -> list[str]:
    """センサーイベントを CSV 形式の文字列リストに変換する。"""
    lines = []
    if header:
        lines.append("timestamp_ns,sensor_handle,sensor_type,x,y,z")
    for event in events:
        vals = (event.values + [0.0, 0.0, 0.0])[:3]
        lines.append(
            f"{event.timestamp_ns},{event.sensor_handle},{event.sensor_type.name},"
            f"{vals[0]:.3f},{vals[1]:.3f},{vals[2]:.3f}"
        )
    return lines


@app.command("list-sensors")
def list_sensors(
    hal: Annotated[str, typer.Option(help=_HAL_HELP)] = "mock",
    bus: Annotated[str, typer.Option(help=_BUS_HELP)] = "mock",
    bus_id: Annotated[int, typer.Option(help=_BUS_ID_HELP)] = 0,
    bus_device: Annotated[int, typer.Option(help=_BUS_DEVICE_HELP)] = 0,
) -> None:
    """利用可能なセンサー一覧を表示"""
    try:
        bus_driver = create_bus_driver(bus, bus_id, bus_device)
        sensor_hal = create_sensor_hal(hal)
    except ValueError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(1)

    sensor_hal.initialize(bus_driver)
    sensors = sensor_hal.get_sensor_list()

    typer.echo(f"{'Handle':<8}{'Type':<17}{'Name':<24}{'Vendor'}")
    typer.echo(f"{'------':<8}{'----':<17}{'----':<24}{'------'}")
    for s in sensors:
        typer.echo(f"{s.sensor_handle:<8}{s.sensor_type.name:<17}{s.name:<24}{s.vendor}")

    sensor_hal.finalize()


@app.command("read-once")
def read_once(
    hal: Annotated[str, typer.Option(help=_HAL_HELP)] = "mock",
    bus: Annotated[str, typer.Option(help=_BUS_HELP)] = "mock",
    bus_id: Annotated[int, typer.Option(help=_BUS_ID_HELP)] = 0,
    bus_device: Annotated[int, typer.Option(help=_BUS_DEVICE_HELP)] = 0,
    output_format: Annotated[str, typer.Option("--format", help=_FORMAT_HELP)] = "csv",
) -> None:
    """センサーデータを1回だけ読み出し"""
    try:
        bus_driver = create_bus_driver(bus, bus_id, bus_device)
        sensor_hal = create_sensor_hal(hal)
    except ValueError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(1)

    sensor_hal.initialize(bus_driver)
    sensors = sensor_hal.get_sensor_list()
    for s in sensors:
        sensor_hal.activate(s.sensor_handle, True)

    events = sensor_hal.get_events()

    if output_format == "json":
        output = [
            {
                "sensor_handle": e.sensor_handle,
                "sensor_type": e.sensor_type.name,
                "timestamp_ns": e.timestamp_ns,
                "values": e.values,
            }
            for e in events
        ]
        typer.echo(json.dumps(output, indent=2))
    elif output_format == "table":
        typer.echo(f"{'Timestamp (ns)':<22}{'Handle':<8}{'Type':<17}{'X':>10}{'Y':>10}{'Z':>10}")
        typer.echo("-" * 77)
        for e in events:
            vals = (e.values + [0.0, 0.0, 0.0])[:3]
            typer.echo(
                f"{e.timestamp_ns:<22}{e.sensor_handle:<8}{e.sensor_type.name:<17}"
                f"{vals[0]:>10.3f}{vals[1]:>10.3f}{vals[2]:>10.3f}"
            )
    else:
        for line in _format_events_csv(events, header=True):
            typer.echo(line)

    sensor_hal.finalize()


@app.command("read")
def read(
    hal: Annotated[str, typer.Option(help=_HAL_HELP)] = "mock",
    bus: Annotated[str, typer.Option(help=_BUS_HELP)] = "mock",
    bus_id: Annotated[int, typer.Option(help=_BUS_ID_HELP)] = 0,
    bus_device: Annotated[int, typer.Option(help=_BUS_DEVICE_HELP)] = 0,
    interval: Annotated[float, typer.Option(help="サンプリング間隔 (秒)")] = 1.0,
    count: Annotated[int, typer.Option(help="読み出し回数 (0=無限)")] = 0,
    output_format: Annotated[str, typer.Option("--format", help=_FORMAT_HELP)] = "csv",
) -> None:
    """センサーデータを継続的に読み出し"""
    try:
        bus_driver = create_bus_driver(bus, bus_id, bus_device)
        sensor_hal = create_sensor_hal(hal)
    except ValueError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(1)

    sensor_hal.initialize(bus_driver)
    sensors = sensor_hal.get_sensor_list()
    for s in sensors:
        sensor_hal.activate(s.sensor_handle, True)

    if output_format == "csv":
        typer.echo("timestamp_ns,sensor_handle,sensor_type,x,y,z")

    iteration = 0
    try:
        while count == 0 or iteration < count:
            events = sensor_hal.get_events()
            if output_format == "csv":
                for line in _format_events_csv(events):
                    typer.echo(line)
            elif output_format == "json":
                for e in events:
                    typer.echo(
                        json.dumps(
                            {
                                "sensor_handle": e.sensor_handle,
                                "sensor_type": e.sensor_type.name,
                                "timestamp_ns": e.timestamp_ns,
                                "values": e.values,
                            }
                        )
                    )
            else:
                for e in events:
                    vals = (e.values + [0.0, 0.0, 0.0])[:3]
                    typer.echo(
                        f"{e.timestamp_ns:<22}{e.sensor_handle:<8}{e.sensor_type.name:<17}"
                        f"{vals[0]:>10.3f}{vals[1]:>10.3f}{vals[2]:>10.3f}"
                    )
            iteration += 1
            if count == 0 or iteration < count:
                time.sleep(interval)
    except KeyboardInterrupt:
        pass
    finally:
        sensor_hal.finalize()


@app.command("info")
def info(
    hal: Annotated[str, typer.Option(help=_HAL_HELP)] = "mock",
    bus: Annotated[str, typer.Option(help=_BUS_HELP)] = "mock",
    bus_id: Annotated[int, typer.Option(help=_BUS_ID_HELP)] = 0,
    bus_device: Annotated[int, typer.Option(help=_BUS_DEVICE_HELP)] = 0,
) -> None:
    """HAL とバスドライバの情報を表示"""
    typer.echo(f"HAL type    : {hal}")
    typer.echo(f"Bus type    : {bus}")
    typer.echo(f"Bus ID      : {bus_id}")
    typer.echo(f"Bus device  : {bus_device}")

    try:
        bus_driver = create_bus_driver(bus, bus_id, bus_device)
        sensor_hal = create_sensor_hal(hal)
    except ValueError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(1)

    typer.echo(f"Bus driver  : {type(bus_driver).__name__}")
    typer.echo(f"Sensor HAL  : {type(sensor_hal).__name__}")

    sensor_hal.initialize(bus_driver)
    sensors = sensor_hal.get_sensor_list()
    typer.echo(f"Sensor count: {len(sensors)}")
    sensor_hal.finalize()


@app.command("register-dump")
def register_dump(
    hal: Annotated[str, typer.Option(help=_HAL_HELP)] = "mock",
    bus: Annotated[str, typer.Option(help=_BUS_HELP)] = "mock",
    bus_id: Annotated[int, typer.Option(help=_BUS_ID_HELP)] = 0,
    bus_device: Annotated[int, typer.Option(help=_BUS_DEVICE_HELP)] = 0,
) -> None:
    """レジスタダンプ (デバッグ用)"""
    try:
        bus_driver = create_bus_driver(bus, bus_id, bus_device)
        sensor_hal = create_sensor_hal(hal)
    except ValueError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(1)

    sensor_hal.initialize(bus_driver)

    if isinstance(bus_driver, MockBusDriver):
        typer.echo("Register Dump (MockBusDriver):")
        if bus_driver._registers:
            typer.echo(f"{'Address':<12}{'Value'}")
            typer.echo(f"{'-------':<12}{'-----'}")
            for addr, val in sorted(bus_driver._registers.items()):
                typer.echo(f"0x{addr:02X}         0x{val:02X}")
        else:
            typer.echo("(no registers set)")
    else:
        sensor_hal.finalize()
        typer.echo("Register dump is only supported with MockBusDriver", err=True)
        raise typer.Exit(1)

    sensor_hal.finalize()


if __name__ == "__main__":
    app()

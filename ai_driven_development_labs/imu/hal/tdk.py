"""TDK InvenSense IMU HAL (ICM-42688-P 等) の実装。"""

import struct
import time

from ai_driven_development_labs.bus.interfaces import IBusDriver
from ai_driven_development_labs.imu.interfaces import ISensorHAL
from ai_driven_development_labs.imu.models import ReportingMode, SensorEvent, SensorInfo, SensorType

_ACCEL_HANDLE = 1
_GYRO_HANDLE = 2

# --- レジスタアドレス (Bank 0) ---
_REG_WHO_AM_I = 0x75
_REG_INT_STATUS = 0x2D  # bit 3: DATA_RDY_INT

_REG_ACCEL_DATA_X1 = 0x1F  # 加速度計 X 高バイト (big-endian: X1=high, X0=low)
_REG_GYRO_DATA_X1 = 0x25  # ジャイロスコープ X 高バイト

_REG_PWR_MGMT0 = 0x4E  # 電源管理: 加速度計・ジャイロの動作モード
_REG_GYRO_CONFIG0 = 0x4F  # ジャイロ ODR / FS
_REG_ACCEL_CONFIG0 = 0x50  # 加速度計 ODR / FS
_REG_BANK_SEL = 0x76  # レジスタバンク選択

# INT_STATUS ビット
_STATUS_DATA_RDY = 0x08  # bit 3: DATA_RDY_INT

# デフォルト制御レジスタ値
# PWR_MGMT0: accel=LN mode (0b11), gyro=LN mode (0b11)
_PWR_MGMT0_DEFAULT = 0x0F
# GYRO_CONFIG0: FS_SEL=000 (±2000 dps), ODR=0110 (1 kHz)
_GYRO_CONFIG0_DEFAULT = 0x06
# ACCEL_CONFIG0: FS_SEL=000 (±16g), ODR=0110 (1 kHz)
_ACCEL_CONFIG0_DEFAULT = 0x06

# --- スケール変換係数 ---
# ±16g の感度: 2048 LSB/g → g/LSB
_ACCEL_SENSITIVITY_G_PER_LSB = 1.0 / 2048.0
# ±2000 dps の感度: 16.4 LSB/dps → dps/LSB
_GYRO_SENSITIVITY_DPS_PER_LSB = 1.0 / 16.4


class TDKSensorHAL(ISensorHAL):
    """TDK InvenSense 製 IMU (ICM-42688-P 等) 用 HAL。

    WHO_AM_I レジスタ (0x75) でデバイスを識別する。
    Bank 選択レジスタ (0x76) によるバンク管理に対応。
    """

    SUPPORTED_DEVICES: dict[int, str] = {
        0x47: "ICM-42688-P",
    }

    def __init__(self) -> None:
        self._bus: IBusDriver | None = None
        self._device_name: str = ""
        self._active: dict[int, bool] = {}
        self._sampling_period_us: dict[int, int] = {}

    def _select_bank(self, bank: int) -> None:
        """レジスタバンクを選択する。

        Args:
            bank: バンク番号 (0〜4)。
        """
        if self._bus is not None:
            self._bus.write_register(_REG_BANK_SEL, bytes([bank & 0x07]))

    def initialize(self, bus: IBusDriver) -> None:
        """HAL を初期化する。WHO_AM_I でデバイスを識別しコントロールレジスタを設定する。

        Args:
            bus: 使用するバスドライバ。

        Raises:
            RuntimeError: WHO_AM_I が未サポートのデバイスを示す場合。
        """
        bus.open()
        self._bus = bus

        # Bank 0 を選択
        self._select_bank(0)

        who_am_i = bus.read_register(_REG_WHO_AM_I, 1)[0]
        if who_am_i not in self.SUPPORTED_DEVICES:
            bus.close()
            self._bus = None
            raise RuntimeError(
                f"Unsupported device: WHO_AM_I=0x{who_am_i:02X}. "
                f"Supported: {list(f'0x{k:02X}' for k in self.SUPPORTED_DEVICES)}"
            )
        self._device_name = self.SUPPORTED_DEVICES[who_am_i]

        # コントロールレジスタ初期設定
        bus.write_register(_REG_PWR_MGMT0, bytes([_PWR_MGMT0_DEFAULT]))
        bus.write_register(_REG_GYRO_CONFIG0, bytes([_GYRO_CONFIG0_DEFAULT]))
        bus.write_register(_REG_ACCEL_CONFIG0, bytes([_ACCEL_CONFIG0_DEFAULT]))

        self._active = {_ACCEL_HANDLE: False, _GYRO_HANDLE: False}

    def get_sensor_list(self) -> list[SensorInfo]:
        """利用可能なセンサー一覧を返す。

        Returns:
            加速度計とジャイロスコープの情報リスト。
        """
        return [
            SensorInfo(
                sensor_handle=_ACCEL_HANDLE,
                name=f"{self._device_name} Accelerometer",
                vendor="TDK InvenSense",
                sensor_type=SensorType.ACCELEROMETER,
                max_range=16.0,
                resolution=_ACCEL_SENSITIVITY_G_PER_LSB,
                reporting_mode=ReportingMode.CONTINUOUS,
            ),
            SensorInfo(
                sensor_handle=_GYRO_HANDLE,
                name=f"{self._device_name} Gyroscope",
                vendor="TDK InvenSense",
                sensor_type=SensorType.GYROSCOPE,
                max_range=2000.0,
                resolution=_GYRO_SENSITIVITY_DPS_PER_LSB,
                reporting_mode=ReportingMode.CONTINUOUS,
            ),
        ]

    def activate(self, sensor_handle: int, enabled: bool) -> None:
        """センサーを有効化/無効化する。

        Args:
            sensor_handle: 対象センサーのハンドル。
            enabled: True で有効化、False で無効化。
        """
        self._active[sensor_handle] = enabled

    def configure(self, sensor_handle: int, sampling_period_us: int, max_report_latency_us: int) -> None:
        """サンプリング周期を設定する。

        Args:
            sensor_handle: 対象センサーのハンドル。
            sampling_period_us: サンプリング周期 (μs)。
            max_report_latency_us: 最大レポート遅延 (μs)。現在の実装では未使用。
        """
        self._sampling_period_us[sensor_handle] = sampling_period_us

    def flush(self, sensor_handle: int) -> None:
        """FIFO バッファをフラッシュする。

        Args:
            sensor_handle: 対象センサーのハンドル。
        """

    def get_events(self) -> list[SensorEvent]:
        """最新のセンサーイベントを取得する。

        INT_STATUS (0x2D) の DATA_RDY_INT ビット (bit 3) を確認し、
        加速度計・ジャイロの出力レジスタから各 6 バイトを読み出して物理量に変換する。

        Returns:
            センサーイベントのリスト。データが準備できていない場合は空リスト。
        """
        if self._bus is None:
            return []

        status = self._bus.read_register(_REG_INT_STATUS, 1)[0]
        if not (status & _STATUS_DATA_RDY):
            return []

        # 加速度計データ読み出し: 0x1F〜0x24 (6 バイト, big-endian)
        accel_raw = self._bus.read_register(_REG_ACCEL_DATA_X1, 6)
        # ジャイロスコープデータ読み出し: 0x25〜0x2A (6 バイト, big-endian)
        gyro_raw = self._bus.read_register(_REG_GYRO_DATA_X1, 6)

        ts = time.time_ns()

        ax_raw, ay_raw, az_raw = struct.unpack_from(">hhh", accel_raw, 0)
        gx_raw, gy_raw, gz_raw = struct.unpack_from(">hhh", gyro_raw, 0)

        ax = ax_raw * _ACCEL_SENSITIVITY_G_PER_LSB
        ay = ay_raw * _ACCEL_SENSITIVITY_G_PER_LSB
        az = az_raw * _ACCEL_SENSITIVITY_G_PER_LSB

        gx = gx_raw * _GYRO_SENSITIVITY_DPS_PER_LSB
        gy = gy_raw * _GYRO_SENSITIVITY_DPS_PER_LSB
        gz = gz_raw * _GYRO_SENSITIVITY_DPS_PER_LSB

        events: list[SensorEvent] = []

        if self._active.get(_ACCEL_HANDLE, False):
            events.append(
                SensorEvent(
                    sensor_handle=_ACCEL_HANDLE,
                    sensor_type=SensorType.ACCELEROMETER,
                    timestamp_ns=ts,
                    values=[ax, ay, az],
                )
            )

        if self._active.get(_GYRO_HANDLE, False):
            events.append(
                SensorEvent(
                    sensor_handle=_GYRO_HANDLE,
                    sensor_type=SensorType.GYROSCOPE,
                    timestamp_ns=ts,
                    values=[gx, gy, gz],
                )
            )

        return events

    def finalize(self) -> None:
        """HAL を終了しリソースを解放する。"""
        if self._bus is not None:
            self._bus.close()
            self._bus = None
        self._active = {}
        self._sampling_period_us = {}

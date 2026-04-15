"""STMicroelectronics IMU HAL (LSM6DSO / ISM330DHCX 等) の実装。"""

import struct
import time

from ai_driven_development_labs.bus.interfaces import IBusDriver
from ai_driven_development_labs.imu.interfaces import ISensorHAL
from ai_driven_development_labs.imu.models import ReportingMode, SensorEvent, SensorInfo, SensorType

_ACCEL_HANDLE = 1
_GYRO_HANDLE = 2

# --- レジスタアドレス ---
_REG_WHO_AM_I = 0x0F

_REG_CTRL1_XL = 0x10  # 加速度計制御 (ODR, FS_XL)
_REG_CTRL2_G = 0x11  # ジャイロスコープ制御 (ODR, FS_G)
_REG_CTRL3_C = 0x12  # 共通制御 (BDU, IF_INC 等)
_REG_CTRL4_C = 0x13
_REG_CTRL5_C = 0x14
_REG_CTRL6_C = 0x15
_REG_CTRL7_G = 0x16
_REG_CTRL8_XL = 0x17
_REG_CTRL9_XL = 0x18
_REG_CTRL10_C = 0x19

_REG_STATUS = 0x1E  # STATUS_REG
_REG_OUT_START = 0x22  # OUTX_L_G 〜 OUTZ_H_A (12 バイト)

# STATUS_REG ビット
_STATUS_XLDA = 0x01  # 加速度計データ準備完了
_STATUS_GDA = 0x02  # ジャイロスコープデータ準備完了

# デフォルト制御レジスタ値
# CTRL1_XL: ODR_XL=0110 (417 Hz), FS_XL=00 (±2g)
_CTRL1_XL_DEFAULT = 0x60
# CTRL2_G: ODR_G=0110 (417 Hz), FS_G=000 (±250 dps)
_CTRL2_G_DEFAULT = 0x60
# CTRL3_C: BDU=1 (block data update), IF_INC=1
_CTRL3_C_DEFAULT = 0x44

# --- スケール変換係数 ---
# ±2g の感度: 0.061 mg/LSB → g/LSB
_ACCEL_SENSITIVITY_G_PER_LSB = 0.000061
# ±250 dps の感度: 8.75 mdps/LSB → dps/LSB
_GYRO_SENSITIVITY_DPS_PER_LSB = 0.00875


class STMicroSensorHAL(ISensorHAL):
    """STMicroelectronics 製 IMU (LSM6DSO / ISM330DHCX 等) 用 HAL。

    iNEMO ファミリのレジスタマップに対応。
    WHO_AM_I レジスタ (0x0F) でデバイスを識別する。
    """

    SUPPORTED_DEVICES: dict[int, str] = {
        0x6C: "LSM6DSO",
        0x6B: "ISM330DHCX",
    }

    def __init__(self) -> None:
        self._bus: IBusDriver | None = None
        self._device_name: str = ""
        self._active: dict[int, bool] = {}
        self._sampling_period_us: dict[int, int] = {}

    def initialize(self, bus: IBusDriver) -> None:
        """HAL を初期化する。WHO_AM_I でデバイスを識別しコントロールレジスタを設定する。

        Args:
            bus: 使用するバスドライバ。

        Raises:
            RuntimeError: WHO_AM_I が未サポートのデバイスを示す場合。
        """
        bus.open()
        self._bus = bus

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
        bus.write_register(_REG_CTRL1_XL, bytes([_CTRL1_XL_DEFAULT]))
        bus.write_register(_REG_CTRL2_G, bytes([_CTRL2_G_DEFAULT]))
        bus.write_register(_REG_CTRL3_C, bytes([_CTRL3_C_DEFAULT]))
        bus.write_register(_REG_CTRL4_C, bytes([0x00]))
        bus.write_register(_REG_CTRL5_C, bytes([0x00]))
        bus.write_register(_REG_CTRL6_C, bytes([0x00]))
        bus.write_register(_REG_CTRL7_G, bytes([0x00]))
        bus.write_register(_REG_CTRL8_XL, bytes([0x00]))
        bus.write_register(_REG_CTRL9_XL, bytes([0x00]))
        bus.write_register(_REG_CTRL10_C, bytes([0x00]))

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
                vendor="STMicroelectronics",
                sensor_type=SensorType.ACCELEROMETER,
                max_range=2.0,
                resolution=_ACCEL_SENSITIVITY_G_PER_LSB,
                reporting_mode=ReportingMode.CONTINUOUS,
            ),
            SensorInfo(
                sensor_handle=_GYRO_HANDLE,
                name=f"{self._device_name} Gyroscope",
                vendor="STMicroelectronics",
                sensor_type=SensorType.GYROSCOPE,
                max_range=250.0,
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

        STATUS_REG (0x1E) のデータレディビットを確認し、出力レジスタ
        (0x22〜0x2D) から 12 バイトを burst read して物理量に変換する。

        Returns:
            センサーイベントのリスト。データが準備できていない場合は空リスト。
        """
        if self._bus is None:
            return []

        status = self._bus.read_register(_REG_STATUS, 1)[0]
        if not (status & (_STATUS_XLDA | _STATUS_GDA)):
            return []

        raw = self._bus.read_register(_REG_OUT_START, 12)
        ts = time.time_ns()

        # レイアウト: [gyro_xl, gyro_xh, gyro_yl, gyro_yh, gyro_zl, gyro_zh,
        #              accel_xl, accel_xh, accel_yl, accel_yh, accel_zl, accel_zh]
        gx_raw, gy_raw, gz_raw = struct.unpack_from("<hhh", raw, 0)
        ax_raw, ay_raw, az_raw = struct.unpack_from("<hhh", raw, 6)

        gx = gx_raw * _GYRO_SENSITIVITY_DPS_PER_LSB
        gy = gy_raw * _GYRO_SENSITIVITY_DPS_PER_LSB
        gz = gz_raw * _GYRO_SENSITIVITY_DPS_PER_LSB

        ax = ax_raw * _ACCEL_SENSITIVITY_G_PER_LSB
        ay = ay_raw * _ACCEL_SENSITIVITY_G_PER_LSB
        az = az_raw * _ACCEL_SENSITIVITY_G_PER_LSB

        events: list[SensorEvent] = []

        if self._active.get(_ACCEL_HANDLE, False) and (status & _STATUS_XLDA):
            events.append(
                SensorEvent(
                    sensor_handle=_ACCEL_HANDLE,
                    sensor_type=SensorType.ACCELEROMETER,
                    timestamp_ns=ts,
                    values=[ax, ay, az],
                )
            )

        if self._active.get(_GYRO_HANDLE, False) and (status & _STATUS_GDA):
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

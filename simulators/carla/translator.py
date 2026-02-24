from __future__ import annotations
from typing import Any
from nexus.core.translator import AdapterTranslator
from nexus.core.types import VehicleControl, SensorData
import numpy as np


class CarlaTranslator(AdapterTranslator):
    """
    Translates between Nexus canonical types and CARLA's native API types.

    control_to_simulator : VehicleControl → carla.VehicleControl
    sensor_from_simulator: raw CARLA sensor data → SensorData

    This class is the ONLY place in the entire codebase that imports from carla.
    All sensor normalization logic (previously _parse_image) lives here.
    """

    def control_to_simulator(self, cmd: VehicleControl) -> Any:
        import carla

        return carla.VehicleControl(
            throttle=float(cmd.throttle),
            brake=float(cmd.brake),
            steer=float(cmd.steer),
            reverse=cmd.reverse,
            hand_brake=cmd.hand_brake,
        )

    def sensor_from_simulator(self, raw: Any, sensor_type: str) -> SensorData:
        if sensor_type == "camera_rgb":
            return self._parse_camera(raw)
        if sensor_type == "gnss":
            return self._parse_gnss(raw)
        if sensor_type == "imu":
            return self._parse_imu(raw)
        raise ValueError(f"CarlaTranslator: unknown sensor type '{sensor_type}'")

    def _parse_camera(self, raw: Any) -> SensorData:
        """Migrated from _parse_image() in custom_path_test.py."""
        array = np.frombuffer(raw.raw_data, dtype=np.uint8)
        array = np.reshape(array, (raw.height, raw.width, 4))
        array = array[:, :, :3]  # drop alpha channel
        array = array[:, :, ::-1]  # BGR → RGB
        return SensorData(
            sensor_type="camera_rgb",
            timestamp=float(raw.timestamp),
            data={
                "array": array,
                "width": raw.width,
                "height": raw.height,
            },
        )

    def _parse_gnss(self, raw: Any) -> SensorData:
        return SensorData(
            sensor_type="gnss",
            timestamp=float(raw.timestamp),
            data={
                "lat": raw.latitude,
                "lon": raw.longitude,
                "alt": raw.altitude,
            },
        )

    def _parse_imu(self, raw: Any) -> SensorData:
        return SensorData(
            sensor_type="imu",
            timestamp=float(raw.timestamp),
            data={
                "accel": {
                    "x": raw.accelerometer.x,
                    "y": raw.accelerometer.y,
                    "z": raw.accelerometer.z,
                },
                "gyro": {
                    "x": raw.gyroscope.x,
                    "y": raw.gyroscope.y,
                    "z": raw.gyroscope.z,
                },
            },
        )

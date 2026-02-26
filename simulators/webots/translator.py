# simulators/webots/__init__.py  (empty)

# simulators/webots/translator.py
from __future__ import annotations
from typing import Any
from nexus.core.translator import AdapterTranslator
from nexus.core.types import VehicleControl, SensorData


class WebotsTranslator(AdapterTranslator):
    """
    Translates between Nexus canonical types and Webots motor/sensor API.

    Webots uses differential wheel velocity to steer (no carla.VehicleControl).
    control_to_simulator converts VehicleControl → dict of motor name → speed (rad/s).
    """

    def control_to_simulator(self, cmd: VehicleControl) -> dict[str, float]:
        max_speed: float = float(self.config.get("max_speed_ms", 14.0))
        motor_names: list[str] = self.config.get(
            "motors",
            [
                "left front wheel",
                "right front wheel",
                "left rear wheel",
                "right rear wheel",
            ],
        )
        base = cmd.throttle * max_speed - cmd.brake * max_speed
        steer_diff = cmd.steer * max_speed * 0.5
        left = base - steer_diff
        right = base + steer_diff
        result = {}
        for name in motor_names:
            result[name] = left if "left" in name else right
        return result

    def sensor_from_simulator(self, raw: Any, sensor_type: str) -> SensorData:
        if sensor_type == "camera":
            return self._parse_camera(raw)
        if sensor_type == "gps":
            return self._parse_gps(raw)
        raise ValueError(f"WebotsTranslator: unknown sensor type '{sensor_type}'")

    def _parse_camera(self, raw: Any) -> SensorData:
        import numpy as np

        array = np.frombuffer(raw["data"], dtype=np.uint8)
        array = array.reshape((raw["height"], raw["width"], 4))
        array = array[:, :, :3][:, :, ::-1]  # BGRA → RGB
        return SensorData(
            sensor_type="camera_rgb",
            timestamp=float(raw.get("timestamp", 0.0)),
            data={"array": array, "width": raw["width"], "height": raw["height"]},
        )

    def _parse_gps(self, raw: Any) -> SensorData:
        return SensorData(
            sensor_type="gnss",
            timestamp=float(raw.get("timestamp", 0.0)),
            data={"lat": raw["x"], "lon": raw["y"], "alt": raw["z"]},
        )

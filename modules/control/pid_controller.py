from __future__ import annotations
from typing import Any
import numpy as np
from nexus.core.base_module import BaseModule, Topic
from nexus.core.types import VehicleControl


class PIDController:
    def __init__(
        self,
        Kp: float,
        Ki: float,
        Kd: float,
        limits: tuple[float, float] = (-1.0, 1.0),
    ) -> None:
        self.Kp = Kp
        self.Ki = Ki
        self.Kd = Kd
        self.limits = limits
        self.integral = 0.0
        self.last_error = 0.0

    def compute(self, setpoint: float, current: float, dt: float) -> tuple[float, float]:
        dt = max(dt, 0.001)
        error = setpoint - current
        self.integral += error * dt
        derivative = (error - self.last_error) / dt
        output = self.Kp * error + self.Ki * self.integral + self.Kd * derivative
        self.last_error = error
        return float(np.clip(output, self.limits[0], self.limits[1])), error


class PIDControllerModule(BaseModule):
    name = "control_pid"

    def setup(self) -> None:
        lon = self.config.get("longitudinal", {})
        lat = self.config.get("lateral", {})
        self.lon_pid = PIDController(
            Kp=float(lon.get("Kp", 0.8)),
            Ki=float(lon.get("Ki", 0.05)),
            Kd=float(lon.get("Kd", 0.2)),
            limits=(0.0, 1.0),
        )
        self.lat_pid = PIDController(
            Kp=float(lat.get("Kp", 0.5)),
            Ki=float(lat.get("Ki", 0.05)),
            Kd=float(lat.get("Kd", 0.2)),
            limits=(-1.0, 1.0),
        )
        self.setpoint_kmh: float = float(lon.get("setpoint_kmh", 25.0))
        self._dt: float = 1.0 / 60.0

    def process(self, msg: Any) -> None:
        speed_kmh: float = msg["velocity"].speed_kmh
        current_y: float = msg["pose"].y
        closest_y: float = msg["closest_waypoint_y"]

        accel, e_lon = self.lon_pid.compute(self.setpoint_kmh, speed_kmh, self._dt)
        steer, e_lat = self.lat_pid.compute(closest_y, current_y, self._dt)

        cmd = VehicleControl(
            throttle=float(max(0.0, accel)),
            brake=float(abs(min(0.0, accel))),
            steer=float(steer),
        )
        self.publish("/nexus/control/cmd", cmd)
        self.publish(
            "/nexus/hud/telemetry",
            {
                "e_lon": e_lon,
                "e_lat": e_lat,
                "speed": speed_kmh,
                "steer": steer,
                "setpoint": self.setpoint_kmh,
                "mode": "auto",
            },
        )

    def teardown(self) -> None:
        pass

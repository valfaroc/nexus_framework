from __future__ import annotations
from typing import Any
import numpy as np
from nexus.core.base_module import BaseModule
from nexus.core.types import VehicleControl


class PIDController:
    def __init__(self, Kp: float, Ki: float, Kd: float,
                 limits: tuple[float, float] = (-1.0, 1.0)) -> None:
        self.Kp = Kp; self.Ki = Ki; self.Kd = Kd
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


class LateralPIDController(BaseModule):
    """
    Lateral-only PID controller for Webots differential drive.

    Throttle is fixed (constant forward speed).
    Only the steer output drives the left/right wheel speed difference.

    This is simpler than the dual-axis CARLA controller because
    Webots differential drive handles speed naturally via motor velocity.
    """
    name = "control_lateral_pid"

    def setup(self) -> None:
        lat = self.config.get("lateral", {})
        self.lat_pid = PIDController(
            Kp=float(lat.get("Kp", 1.2)),
            Ki=float(lat.get("Ki", 0.0)),
            Kd=float(lat.get("Kd", 0.3)),
            limits=(-1.0, 1.0),
        )
        self._dt: float = 1.0 / 20.0
        # Fixed throttle — let the motor velocity handle speed
        self._throttle: float = float(self.config.get("throttle", 0.4))

    def process(self, msg: Any) -> None:
        steer, e_lat = self.lat_pid.compute(
            msg["closest_waypoint_y"],
            msg["pose"].y,
            self._dt,
        )
        self.publish("/nexus/control/cmd", VehicleControl(
            throttle=self._throttle,
            brake=0.0,
            steer=float(steer),
        ))
        self.publish("/nexus/hud/telemetry", {
            "e_lat":  e_lat,
            "steer":  steer,
            "speed":  msg["velocity"].speed_kmh,
            "mode":   "lateral_only",
        })

    def teardown(self) -> None:
        pass
```

---

## Step 7 — Update the Webots world file

Add a LiDAR device to `simulators/webots/worlds/simple_road.wbt` inside the `Robot` node, alongside the existing GPS:
```
    Lidar {
      name "lidar"
      horizontalResolution 512
      fieldOfView 6.28318    # 360 degrees
      numberOfLayers 1
      maxRange 12.0
      noise 0.01
    }

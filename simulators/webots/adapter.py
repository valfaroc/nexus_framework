# simulators/webots/adapter.py
from __future__ import annotations
from typing import Any
import structlog
from nexus.core.base_simulator import SimulatorInterface
from nexus.core.types import (
    VehicleConfig,
    VehicleControl,
    SensorData,
    WorldState,
    VehiclePose,
    VehicleVelocity,
)
from simulators.webots.translator import WebotsTranslator

logger = structlog.get_logger()


class WebotsAdapter(SimulatorInterface):
    """
    Simulator adapter for Webots R2023b.

    Uses the Webots Python API (controller module) available inside the container.
    import controller is local to each method body — never at module level.
    """

    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config
        self.translator = WebotsTranslator(config)
        self._robot: Any = None
        self._motors: dict[str, Any] = {}
        self._sensors: dict[str, Any] = {}
        self._sensor_data: dict[str, SensorData | None] = {}
        self._timestep: int = 32  # ms

    def connect(self, host: str = "localhost", port: int = 0) -> None:
        from controller import Robot  # local import

        self._robot = Robot()
        self._timestep = int(self._robot.getBasicTimeStep())
        motor_names: list[str] = self.config.get(
            "motors",
            [
                "left front wheel",
                "right front wheel",
                "left rear wheel",
                "right rear wheel",
            ],
        )
        for name in motor_names:
            m = self._robot.getDevice(name)
            m.setPosition(float("inf"))  # velocity mode
            m.setVelocity(0.0)
            self._motors[name] = m
        logger.info("Webots connected", timestep=self._timestep)

    def disconnect(self) -> None:
        for motor in self._motors.values():
            try:
                motor.setVelocity(0.0)
            except Exception:
                pass
        self._motors.clear()
        self._sensors.clear()
        self._sensor_data.clear()
        logger.info("Webots adapter disconnected")

    def spawn_ego(self, config: VehicleConfig) -> str:
        # In Webots the robot IS the ego — it's defined in the world file.
        # Return a fixed ID.
        return "webots_ego"

    def swap_ego(self, config: VehicleConfig) -> str:
        return "webots_ego"

    def destroy_actor(self, actor_id: str) -> None:
        pass  # Webots world management is out of scope for MVP

    def apply_control(self, actor_id: str, control: VehicleControl) -> None:
        velocities = self.translator.control_to_simulator(control)
        for name, vel in velocities.items():
            if name in self._motors:
                self._motors[name].setVelocity(float(vel))

    def tick(self) -> WorldState:
        if self._robot is None:
            raise RuntimeError("WebotsAdapter: not connected")
        self._robot.step(self._timestep)
        # Read GPS/IMU from Webots translation
        t = self._robot.getTime()
        # Webots supervisor or GPS device gives position
        gps_device = self._sensors.get("gps")
        if gps_device:
            pos = gps_device.getValues()  # [x, y, z]
        else:
            pos = [0.0, 0.0, 0.0]
        return WorldState(
            tick=int(t / (self._timestep / 1000.0)),
            timestamp=float(t),
            ego_pose=VehiclePose(
                x=float(pos[0]),
                y=float(pos[1]),
                z=float(pos[2]),
                roll=0.0,
                pitch=0.0,
                yaw=0.0,
                timestamp=float(t),
            ),
            ego_velocity=VehicleVelocity(
                vx=0.0,
                vy=0.0,
                vz=0.0,
                speed_kmh=0.0,
                timestamp=float(t),
            ),
        )

    def get_spawn_points(self) -> list[dict[str, Any]]:
        return [{"x": 0.0, "y": 0.0, "z": 0.0}]

    def setup_sensor(self, sensor_type: str, config: dict[str, Any], parent_id: str) -> str:
        device_name = config.get("device_name", sensor_type)
        device = self._robot.getDevice(device_name)
        device.enable(self._timestep)
        sensor_id = f"{sensor_type}_{device_name}"
        self._sensors[sensor_type] = device
        self._sensor_data[sensor_id] = None
        logger.info("Webots sensor enabled", sensor_type=sensor_type, device=device_name)
        return sensor_id

    def get_sensor_data(self, sensor_id: str) -> SensorData | None:
        return self._sensor_data.get(sensor_id)

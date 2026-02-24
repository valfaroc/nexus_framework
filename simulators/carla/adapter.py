from __future__ import annotations
from typing import Any
from nexus.core.base_simulator import SimulatorInterface
from nexus.core.types import (
    VehicleConfig,
    VehicleControl,
    SensorData,
    WorldState,
    VehiclePose,
    VehicleVelocity,
)
from simulators.carla.translator import CarlaTranslator
import numpy as np
import structlog

logger = structlog.get_logger()


class CarlaAdapter(SimulatorInterface):
    """
    Simulator adapter for CARLA 0.9.16.

    Implements SimulatorInterface — no code outside this file and
    simulators/carla/translator.py ever imports from the carla package.

    Pairs with CarlaTranslator for all type conversions.
    """

    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config
        self.translator = CarlaTranslator(config)
        self._client: Any = None
        self._world: Any = None
        self._actors: dict[str, Any] = {}
        self._sensor_data: dict[str, SensorData | None] = {}

    def connect(self, host: str = "localhost", port: int = 2000) -> None:
        import carla

        self._client = carla.Client(host, port)
        self._client.set_timeout(10.0)
        self._world = self._client.get_world()
        logger.info("CARLA connected", host=host, port=port)

    def disconnect(self) -> None:
        for actor_id, actor in list(self._actors.items()):
            try:
                actor.destroy()
                logger.info("Actor destroyed", actor_id=actor_id)
            except Exception as e:
                logger.warning("Failed to destroy actor", actor_id=actor_id, error=str(e))
        self._actors.clear()
        self._sensor_data.clear()
        logger.info("CARLA adapter disconnected")

    def spawn_ego(self, config: VehicleConfig) -> str:
        bp_lib = self._world.get_blueprint_library()
        bp = bp_lib.find(config.blueprint)
        spawn_points = self._world.get_map().get_spawn_points()
        spawn_point = spawn_points[config.spawn_index]
        vehicle = self._world.spawn_actor(bp, spawn_point)
        actor_id = str(vehicle.id)
        self._actors[actor_id] = vehicle
        logger.info("Ego spawned", blueprint=config.blueprint, actor_id=actor_id)
        return actor_id

    def swap_ego(self, config: VehicleConfig) -> str:
        """Migrated from vehicle_random_choice() in custom_path_test.py."""
        for actor_id in list(self._actors.keys()):
            try:
                self._actors[actor_id].destroy()
            except Exception:
                pass
        self._actors.clear()
        return self.spawn_ego(config)

    def destroy_actor(self, actor_id: str) -> None:
        if actor_id in self._actors:
            self._actors[actor_id].destroy()
            del self._actors[actor_id]
            self._sensor_data.pop(actor_id, None)

    def apply_control(self, actor_id: str, control: VehicleControl) -> None:
        carla_control = self.translator.control_to_simulator(control)
        self._actors[actor_id].apply_control(carla_control)

    def tick(self) -> WorldState:
        snapshot = self._world.get_snapshot()
        vehicle = next(iter(self._actors.values()))
        transform = vehicle.get_transform()
        velocity = vehicle.get_velocity()
        speed_kmh = 3.6 * float(np.sqrt(velocity.x**2 + velocity.y**2 + velocity.z**2))
        timestamp = float(snapshot.timestamp.elapsed_seconds)
        return WorldState(
            tick=snapshot.frame,
            timestamp=timestamp,
            ego_pose=VehiclePose(
                x=transform.location.x,
                y=transform.location.y,
                z=transform.location.z,
                roll=transform.rotation.roll,
                pitch=transform.rotation.pitch,
                yaw=transform.rotation.yaw,
                timestamp=timestamp,
            ),
            ego_velocity=VehicleVelocity(
                vx=velocity.x,
                vy=velocity.y,
                vz=velocity.z,
                speed_kmh=speed_kmh,
                timestamp=timestamp,
            ),
        )

    def get_spawn_points(self) -> list[dict[str, Any]]:
        points = self._world.get_map().get_spawn_points()
        return [{"x": p.location.x, "y": p.location.y, "z": p.location.z} for p in points]

    def setup_sensor(self, sensor_type: str, config: dict[str, Any], parent_id: str) -> str:
        import carla

        bp_map = {
            "camera_rgb": "sensor.camera.rgb",
            "gnss": "sensor.other.gnss",
            "imu": "sensor.other.imu",
        }
        if sensor_type not in bp_map:
            raise ValueError(f"CarlaAdapter: unsupported sensor type '{sensor_type}'")

        bp = self._world.get_blueprint_library().find(bp_map[sensor_type])

        if sensor_type == "camera_rgb":
            bp.set_attribute("image_size_x", str(config.get("width", 1200)))
            bp.set_attribute("image_size_y", str(config.get("height", 800)))

        pos = config.get("position", {})
        rot = config.get("rotation", {})
        transform = carla.Transform(
            carla.Location(
                x=float(pos.get("x", 0.0)),
                y=float(pos.get("y", 0.0)),
                z=float(pos.get("z", 0.0)),
            ),
            carla.Rotation(
                pitch=float(rot.get("pitch", 0.0)),
                yaw=float(rot.get("yaw", 0.0)),
                roll=float(rot.get("roll", 0.0)),
            ),
        )
        parent = self._actors[parent_id]
        sensor = self._world.spawn_actor(bp, transform, attach_to=parent)
        sensor_id = str(sensor.id)
        self._actors[sensor_id] = sensor
        self._sensor_data[sensor_id] = None
        sensor.listen(
            lambda data, sid=sensor_id, st=sensor_type: self._on_sensor_data(sid, st, data)
        )
        logger.info("Sensor attached", sensor_type=sensor_type, sensor_id=sensor_id)
        return sensor_id

    def _on_sensor_data(self, sensor_id: str, sensor_type: str, raw: Any) -> None:
        self._sensor_data[sensor_id] = self.translator.sensor_from_simulator(raw, sensor_type)

    def get_sensor_data(self, sensor_id: str) -> SensorData | None:
        return self._sensor_data.get(sensor_id)

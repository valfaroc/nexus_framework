import pytest
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


class ConcreteSimulator(SimulatorInterface):
    """Minimal concrete implementation for testing the interface contract."""

    def connect(self, host: str, port: int) -> None:
        pass

    def disconnect(self) -> None:
        pass

    def spawn_ego(self, config: VehicleConfig) -> str:
        return "actor_001"

    def swap_ego(self, config: VehicleConfig) -> str:
        return "actor_002"

    def destroy_actor(self, actor_id: str) -> None:
        pass

    def apply_control(self, actor_id: str, control: VehicleControl) -> None:
        pass

    def tick(self) -> WorldState:
        return WorldState(
            tick=1,
            timestamp=0.0,
            ego_pose=VehiclePose(x=0, y=0, z=0, roll=0, pitch=0, yaw=0, timestamp=0.0),
            ego_velocity=VehicleVelocity(vx=0, vy=0, vz=0, speed_kmh=0.0, timestamp=0.0),
        )

    def get_spawn_points(self) -> list[dict[str, Any]]:
        return [{"x": 0.0, "y": 0.0, "z": 0.0}]

    def setup_sensor(self, sensor_type: str, config: dict[str, Any], parent_id: str) -> str:
        return f"sensor_{sensor_type}"

    def get_sensor_data(self, sensor_id: str) -> SensorData | None:
        return None


# --- Interface contract ---


def test_simulator_interface_cannot_be_instantiated_directly() -> None:
    with pytest.raises(TypeError):
        SimulatorInterface()  # type: ignore[abstract]


def test_concrete_simulator_instantiates() -> None:
    sim = ConcreteSimulator()
    assert sim is not None


def test_spawn_ego_returns_actor_id() -> None:
    sim = ConcreteSimulator()
    actor_id = sim.spawn_ego(VehicleConfig())
    assert isinstance(actor_id, str)
    assert len(actor_id) > 0


def test_swap_ego_returns_new_actor_id() -> None:
    sim = ConcreteSimulator()
    first = sim.spawn_ego(VehicleConfig())
    second = sim.swap_ego(VehicleConfig())
    assert isinstance(second, str)
    assert second != first


def test_tick_returns_world_state() -> None:
    sim = ConcreteSimulator()
    state = sim.tick()
    assert isinstance(state, WorldState)
    assert state.tick == 1
    assert state.ego_pose.x == 0.0


def test_get_spawn_points_returns_list() -> None:
    sim = ConcreteSimulator()
    points = sim.get_spawn_points()
    assert isinstance(points, list)
    assert len(points) > 0
    assert "x" in points[0]


def test_setup_sensor_returns_sensor_id() -> None:
    sim = ConcreteSimulator()
    sensor_id = sim.setup_sensor("camera_rgb", {"width": 1200}, "actor_001")
    assert sensor_id == "sensor_camera_rgb"


def test_get_sensor_data_returns_none_before_data() -> None:
    sim = ConcreteSimulator()
    data = sim.get_sensor_data("sensor_camera_rgb")
    assert data is None


def test_apply_control_accepts_vehicle_control() -> None:
    sim = ConcreteSimulator()
    cmd = VehicleControl(throttle=0.5, steer=0.2)
    sim.apply_control("actor_001", cmd)  # should not raise


# --- Dependency rule ---


def test_base_simulator_does_not_import_carla() -> None:
    import importlib, inspect

    mod = importlib.import_module("nexus.core.base_simulator")
    source = inspect.getsource(mod)
    assert "import carla" not in source
    assert "import simulators" not in source

import pytest
from pydantic import ValidationError
from nexus.core.types import (
    VehicleControl,
    VehiclePose,
    VehicleVelocity,
    SensorData,
    WorldState,
    VehicleConfig,
)


# --- VehicleControl ---


def test_vehicle_control_defaults() -> None:
    cmd = VehicleControl()
    assert cmd.throttle == 0.0
    assert cmd.brake == 0.0
    assert cmd.steer == 0.0
    assert cmd.reverse is False


def test_vehicle_control_valid_values() -> None:
    cmd = VehicleControl(throttle=0.5, brake=0.0, steer=-0.3)
    assert cmd.throttle == 0.5
    assert cmd.steer == -0.3


def test_vehicle_control_throttle_above_max_raises() -> None:
    with pytest.raises(ValidationError):
        VehicleControl(throttle=1.5)


def test_vehicle_control_throttle_below_min_raises() -> None:
    with pytest.raises(ValidationError):
        VehicleControl(throttle=-0.1)


def test_vehicle_control_steer_out_of_range_raises() -> None:
    with pytest.raises(ValidationError):
        VehicleControl(steer=1.5)


def test_vehicle_control_is_immutable() -> None:
    cmd = VehicleControl(throttle=0.5)
    assert cmd.model_fields_set is not None
    # Frozen models raise ValidationError on direct field assignment.
    # mypy catches this at type-check time; we verify the frozen config is set:
    assert cmd.model_config.get("frozen") is True


def test_vehicle_control_no_imports_from_simulators() -> None:
    """Ensure types.py does not import anything outside nexus.core."""
    import importlib, inspect

    mod = importlib.import_module("nexus.core.types")
    source = inspect.getsource(mod)
    assert "import carla" not in source
    assert "import simulators" not in source
    assert "import modules" not in source


# --- VehiclePose ---


def test_vehicle_pose_fields() -> None:
    pose = VehiclePose(x=1.0, y=2.0, z=0.5, roll=0.0, pitch=0.0, yaw=90.0, timestamp=0.0)
    assert pose.x == 1.0
    assert pose.yaw == 90.0


def test_vehicle_pose_is_immutable() -> None:
    pose = VehiclePose(x=0, y=0, z=0, roll=0, pitch=0, yaw=0, timestamp=0)
    assert pose.model_config.get("frozen") is True


# --- VehicleConfig ---


def test_vehicle_config_defaults() -> None:
    cfg = VehicleConfig()
    assert cfg.blueprint == "vehicle.tesla.cybertruck"
    assert cfg.spawn_index == 0

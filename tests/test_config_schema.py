import pytest
from pydantic import ValidationError
from nexus.config.schema import (
    NexusConfig,
    SimulatorConfig,
    ControlConfig,
    ModulesConfig,
)


def test_nexus_config_minimal_valid() -> None:
    cfg = NexusConfig(project={"name": "test_project"})
    assert cfg.project.name == "test_project"


def test_nexus_config_defaults() -> None:
    cfg = NexusConfig(project={"name": "test"})
    assert cfg.simulator.type == "carla"
    assert cfg.modules.control.type == "pid"
    assert cfg.modules.control.translator is None


def test_project_name_required() -> None:
    with pytest.raises(ValidationError):
        NexusConfig()  # type: ignore[call-arg]


def test_simulator_type_valid_options() -> None:
    for sim_type in ["carla", "webots", "gazebo", "mock"]:
        cfg = NexusConfig(project={"name": "test"}, simulator={"type": sim_type})
        assert cfg.simulator.type == sim_type


def test_simulator_type_invalid_raises() -> None:
    with pytest.raises(ValidationError):
        NexusConfig(project={"name": "test"}, simulator={"type": "unknown_sim"})


def test_control_config_open_accepts_pid_params() -> None:
    cfg = NexusConfig(
        project={"name": "test"},
        modules={
            "control": {
                "type": "pid",
                "config": {"Kp": 0.8, "Ki": 0.05, "Kd": 0.2, "setpoint_kmh": 25},
            }
        },
    )
    assert cfg.modules.control.config["Kp"] == 0.8


def test_control_config_open_accepts_mpc_params() -> None:
    cfg = NexusConfig(
        project={"name": "test"},
        modules={
            "control": {
                "type": "mpc",
                "translator": "mpc_to_vehicle_control",
                "config": {"horizon": 20, "max_accel": 3.0},
            }
        },
    )
    assert cfg.modules.control.type == "mpc"
    assert cfg.modules.control.translator == "mpc_to_vehicle_control"
    assert cfg.modules.control.config["horizon"] == 20


def test_control_config_open_accepts_fuzzy_params() -> None:
    cfg = NexusConfig(
        project={"name": "test"},
        modules={
            "control": {"type": "fuzzy", "config": {"rules": "mamdani", "defuzz": "centroid"}}
        },
    )
    assert cfg.modules.control.type == "fuzzy"


def test_webots_simulator_accepts_extra_config() -> None:
    cfg = NexusConfig(
        project={"name": "test"},
        simulator={
            "type": "webots",
            "config": {"max_speed_ms": 14.0, "motors": ["left front wheel", "right front wheel"]},
        },
    )
    assert cfg.simulator.config["max_speed_ms"] == 14.0

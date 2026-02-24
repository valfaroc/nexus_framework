# tests/test_carla_translator.py
from __future__ import annotations
from typing import Any
from unittest.mock import MagicMock, patch
import numpy as np
import pytest
from nexus.core.types import VehicleControl, SensorData
from simulators.carla.translator import CarlaTranslator


@pytest.fixture
def translator() -> CarlaTranslator:
    return CarlaTranslator({})


# --- control_to_simulator ---


def test_control_to_simulator_throttle_and_steer(translator: CarlaTranslator) -> None:
    mock_carla_control = MagicMock()

    with patch.dict("sys.modules", {"carla": MagicMock()}):
        import carla

        carla.VehicleControl.return_value = mock_carla_control

        cmd = VehicleControl(throttle=0.7, brake=0.0, steer=0.3)
        result = translator.control_to_simulator(cmd)
        assert result is mock_carla_control


def test_control_to_simulator_full_brake(translator: CarlaTranslator) -> None:
    with patch.dict("sys.modules", {"carla": MagicMock()}):
        import carla

        cmd = VehicleControl(throttle=0.0, brake=1.0, steer=0.0)
        translator.control_to_simulator(cmd)
        carla.VehicleControl.assert_called_with(
            throttle=0.0, brake=1.0, steer=0.0, reverse=False, hand_brake=False
        )


def test_control_to_simulator_reverse(translator: CarlaTranslator) -> None:
    with patch.dict("sys.modules", {"carla": MagicMock()}):
        import carla

        cmd = VehicleControl(throttle=0.5, reverse=True)
        translator.control_to_simulator(cmd)
        carla.VehicleControl.assert_called_with(
            throttle=0.5, brake=0.0, steer=0.0, reverse=True, hand_brake=False
        )


# --- sensor_from_simulator: camera ---


def _make_mock_camera(width: int = 4, height: int = 2) -> Any:
    """Create a fake CARLA camera image with known pixel values."""
    raw = MagicMock()
    raw.width = width
    raw.height = height
    raw.timestamp = 1.5
    # BGRA flat array — 4 channels
    array = np.zeros((height, width, 4), dtype=np.uint8)
    array[:, :, 0] = 100  # B
    array[:, :, 1] = 150  # G
    array[:, :, 2] = 200  # R
    array[:, :, 3] = 255  # A
    raw.raw_data = array.tobytes()
    return raw


def test_camera_returns_sensor_data(translator: CarlaTranslator) -> None:
    raw = _make_mock_camera()
    result = translator.sensor_from_simulator(raw, "camera_rgb")
    assert isinstance(result, SensorData)
    assert result.sensor_type == "camera_rgb"
    assert result.timestamp == 1.5


def test_camera_drops_alpha_channel(translator: CarlaTranslator) -> None:
    raw = _make_mock_camera(width=4, height=2)
    result = translator.sensor_from_simulator(raw, "camera_rgb")
    array = result.data["array"]
    assert array.shape == (2, 4, 3)  # height, width, RGB — no alpha


def test_camera_converts_bgr_to_rgb(translator: CarlaTranslator) -> None:
    raw = _make_mock_camera(width=4, height=2)
    result = translator.sensor_from_simulator(raw, "camera_rgb")
    array = result.data["array"]
    # Original B=100, G=150, R=200 → after BGR→RGB: R=200, G=150, B=100
    assert array[0, 0, 0] == 200  # R
    assert array[0, 0, 1] == 150  # G
    assert array[0, 0, 2] == 100  # B


# --- sensor_from_simulator: gnss ---


def test_gnss_returns_sensor_data(translator: CarlaTranslator) -> None:
    raw = MagicMock()
    raw.timestamp = 2.0
    raw.latitude = 40.4168
    raw.longitude = -3.7038
    raw.altitude = 650.0
    result = translator.sensor_from_simulator(raw, "gnss")
    assert result.sensor_type == "gnss"
    assert result.data["lat"] == pytest.approx(40.4168)
    assert result.data["lon"] == pytest.approx(-3.7038)


# --- sensor_from_simulator: imu ---


def test_imu_returns_sensor_data(translator: CarlaTranslator) -> None:
    raw = MagicMock()
    raw.timestamp = 3.0
    raw.accelerometer = MagicMock(x=0.1, y=0.0, z=9.81)
    raw.gyroscope = MagicMock(x=0.0, y=0.0, z=0.05)
    result = translator.sensor_from_simulator(raw, "imu")
    assert result.sensor_type == "imu"
    assert result.data["accel"]["z"] == pytest.approx(9.81)
    assert result.data["gyro"]["z"] == pytest.approx(0.05)


# --- unknown sensor type ---


def test_unknown_sensor_type_raises(translator: CarlaTranslator) -> None:
    with pytest.raises(ValueError, match="unknown sensor type"):
        translator.sensor_from_simulator(MagicMock(), "lidar_unknown")


# --- dependency rule ---


def test_carla_translator_not_imported_at_module_level() -> None:
    """carla import must be local (inside methods), not at module level."""
    import importlib, inspect

    mod = importlib.import_module("simulators.carla.translator")
    source_lines = inspect.getsource(mod).split("\n")
    top_level_imports = [
        l for l in source_lines if l.startswith("import carla") or l.startswith("from carla")
    ]
    assert len(top_level_imports) == 0

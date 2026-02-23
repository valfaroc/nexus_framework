import pytest
from nexus.core.translator import (
    AdapterTranslator,
    ModuleTranslator,
    TranslatorValidationError,
)
from nexus.core.types import VehicleControl, SensorData
from typing import Any


# --- AdapterTranslator ---


class ConcreteAdapterTranslator(AdapterTranslator):
    def control_to_simulator(self, cmd: VehicleControl) -> Any:
        return {"throttle": cmd.throttle, "steer": cmd.steer}

    def sensor_from_simulator(self, raw: Any, sensor_type: str) -> SensorData:
        return SensorData(sensor_type=sensor_type, timestamp=0.0, data={})


def test_adapter_translator_cannot_be_instantiated_directly() -> None:
    with pytest.raises(TypeError):
        AdapterTranslator({})  # type: ignore[abstract]


def test_adapter_translator_concrete_works() -> None:
    t = ConcreteAdapterTranslator({})
    result = t.control_to_simulator(VehicleControl(throttle=0.5, steer=0.3))
    assert result["throttle"] == 0.5
    assert result["steer"] == 0.3


def test_adapter_translator_sensor_returns_sensor_data() -> None:
    t = ConcreteAdapterTranslator({})
    data = t.sensor_from_simulator({}, "camera_rgb")
    assert data.sensor_type == "camera_rgb"


# --- ModuleTranslator ---


class ConcreteModuleTranslator(ModuleTranslator):
    input_type = dict
    output_type = VehicleControl

    def translate(self, msg: Any) -> VehicleControl:
        return VehicleControl(throttle=msg["throttle"], steer=msg["steer"])


def test_module_translator_cannot_be_instantiated_directly() -> None:
    with pytest.raises(TypeError):
        ModuleTranslator({})  # type: ignore[abstract]


def test_module_translator_translate_works() -> None:
    t = ConcreteModuleTranslator({})
    result = t.safe_translate({"throttle": 0.8, "steer": -0.2})
    assert isinstance(result, VehicleControl)
    assert result.throttle == 0.8


def test_module_translator_validation_error_propagates() -> None:
    class StrictTranslator(ModuleTranslator):
        input_type = dict
        output_type = VehicleControl

        def validate(self, msg: Any) -> None:
            if msg.get("throttle", 0) > 1.0:
                raise TranslatorValidationError("throttle exceeds maximum")

        def translate(self, msg: Any) -> VehicleControl:
            return VehicleControl(throttle=msg["throttle"])

    t = StrictTranslator({})
    with pytest.raises(TranslatorValidationError):
        t.safe_translate({"throttle": 1.5})


def test_translator_validation_error_is_exception() -> None:
    err = TranslatorValidationError("test message")
    assert isinstance(err, Exception)
    assert str(err) == "test message"

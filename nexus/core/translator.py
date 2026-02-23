# nexus/core/translator.py
from abc import ABC, abstractmethod
from typing import Any
from nexus.core.types import VehicleControl, SensorData


class TranslatorValidationError(Exception):
    """Raised by ModuleTranslator.validate() when output is implausible."""

    pass


class AdapterTranslator(ABC):
    """
    Translates between the framework's canonical types and a
    simulator's native format. One per simulator adapter.
    Lives in simulators/[name]/translator.py.
    """

    def __init__(self, config: dict[str, Any]):
        self.config = config

    @abstractmethod
    def control_to_simulator(self, cmd: VehicleControl) -> Any:
        """VehicleControl -> simulator-specific control command."""
        ...

    @abstractmethod
    def sensor_from_simulator(self, raw: Any, sensor_type: str) -> SensorData:
        """Simulator-specific sensor output -> canonical SensorData."""
        ...


class ModuleTranslator(ABC):
    """
    Translates a module's domain-native output into the canonical
    type expected by the ROS2 bus. Declared in nexus.yaml per module.
    Lives in modules/[domain]/translators/ or projects/[name]/translators/.
    """

    input_type: type
    output_type: type

    def __init__(self, config: dict[str, Any]):
        self.config = config

    def validate(self, msg: Any) -> None:
        """
        Optional safety check. Raise TranslatorValidationError if msg
        is physically implausible. Framework applies safe zero-output on error.
        """
        pass

    @abstractmethod
    def translate(self, msg: Any) -> Any: ...

    def safe_translate(self, msg: Any) -> Any:
        """Called by the registry. Validates then translates."""
        self.validate(msg)
        return self.translate(msg)

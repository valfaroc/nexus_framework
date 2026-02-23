from abc import ABC, abstractmethod
from typing import Any
from nexus.core.types import VehicleConfig, VehicleControl, SensorData, WorldState


class SimulatorInterface(ABC):
    """
    Abstract base class for all simulator adapters.

    Implementing this interface is all that is required to add
    a new simulator to Nexus. Pair with an AdapterTranslator.

    No code outside simulators/ should import from a concrete simulator package.
    """

    @abstractmethod
    def connect(self, host: str, port: int) -> None: ...

    @abstractmethod
    def disconnect(self) -> None: ...

    @abstractmethod
    def spawn_ego(self, config: VehicleConfig) -> str:
        """Returns actor ID string."""
        ...

    @abstractmethod
    def swap_ego(self, config: VehicleConfig) -> str:
        """Destroy current ego and spawn a new one."""
        ...

    @abstractmethod
    def destroy_actor(self, actor_id: str) -> None: ...

    @abstractmethod
    def apply_control(self, actor_id: str, control: VehicleControl) -> None: ...

    @abstractmethod
    def tick(self) -> WorldState: ...

    @abstractmethod
    def get_spawn_points(self) -> list[dict[str, Any]]: ...

    @abstractmethod
    def setup_sensor(self, sensor_type: str, config: dict[str, Any], parent_id: str) -> str:
        """Attach a sensor to an actor. Returns sensor ID."""
        ...

    @abstractmethod
    def get_sensor_data(self, sensor_id: str) -> SensorData | None: ...

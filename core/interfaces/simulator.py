from abc import ABC, abstractmethod
from core.data_models import VehicleState, PerceptionState

class BaseSimulatorBridge(ABC):
    @abstractmethod
    def get_observation(self) -> dict:
        """Collects raw data from all active sensors."""
        pass

    @abstractmethod
    def get_state(self) -> VehicleState:
        """Returns the ego-vehicle's current pose and velocity."""
        pass

    @abstractmethod
    def apply_control(self, control_cmd):
        """Sends throttle, steer, and brake to the simulator."""
        pass

    @abstractmethod
    def cleanup(self):
        """Safely destroys actors and closes connections."""
        pass
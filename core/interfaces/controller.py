from abc import ABC, abstractmethod

class BaseController(ABC):
    def __init__(self, config):
        self.config = config

    @abstractmethod
    def get_control_signal(self, current_state, target_path, dt):
        """
        Calculates the actuator signals.
        Returns: carla.VehicleControl(throttle, steer, brake)
        """
        pass
    
    @abstractmethod
    def reset(self):
        """Clears integrals or internal states of the controller."""
        pass
from abc import ABC, abstractmethod

class BasePerception(ABC):
    @abstractmethod
    def update(self, sensor_data):
        """Processes raw data from CARLA/ROS2 sensors."""
        pass

    @abstractmethod
    def get_detected_objects(self):
        """Returns a list of tracked actors (vehicles, pedestrians)."""
        pass

    @abstractmethod
    def get_lane_status(self):
        """Returns information about lane markings and boundaries."""
        pass
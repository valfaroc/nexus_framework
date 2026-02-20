from abc import ABC, abstractmethod

class BasePlanner(ABC):
    @abstractmethod
    def generate_path(self, current_pose, target_goal, occupancy_map):
        """
        Calculates a list of waypoints.
        Input: Mission goal and map of obstacles from Perception.
        Output: A Path (trajectory).
        """
        pass
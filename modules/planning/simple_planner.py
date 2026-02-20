from core.interfaces.planner import BasePlanner
from core.data_models import Trajectory, Pose, Vector3D
import numpy as np

class SimpleSinePlanner(BasePlanner):
    def __init__(self):
        self.points_distance = 2.0  # meters between points
        self.amplitude = 5.0       # sine wave height
        self.wavelength = 50.0     # distance of one full wave

    def generate_path(self, current_pose, world_model) -> Trajectory:
        """Generates a sine wave trajectory starting from the current position."""
        waypoints = []
        velocities = []
        
        # Start from the current ego position
        curr_x = current_pose.position.x
        curr_y = current_pose.position.y
        
        # Generate 20 points ahead
        for i in range(1, 21):
            dist = i * self.points_distance
            x = curr_x + dist
            # Sine wave math from your original script
            y = curr_y + self.amplitude * np.sin(2 * np.pi * dist / self.wavelength)
            
            waypoints.append(Pose(
                position=Vector3D(x, y, current_pose.position.z),
                orientation=Vector3D(0, 0, 0) # Simplified
            ))
            velocities.append(5.5) # Constant target speed (~20 km/h)

        return Trajectory(waypoints=waypoints, target_velocities=velocities)
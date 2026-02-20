import carla
import pygame
import numpy as np
from core.interfaces.simulator import BaseSimulatorBridge
from core.data_models import VehicleState, Vector3D, Pose

class CarlaBridge(BaseSimulatorBridge):
    def __init__(self, town="Town03", host="127.0.0.1", port=2000):
        print(f"Connecting to CARLA at {host}:{port}...")
        self.client = carla.Client(host, port)
        self.client.set_timeout(5.0) # time to connect with the server
        
        self.world = self.client.get_world()
        self.settings = self.world.get_settings()
        self.settings.fixed_delta_seconds = 0.05 # 20Hz matching your engine
        self.settings.synchronous_mode = True
        self.world.apply_settings(self.settings)

        self.vehicle = None

    def _setup_vehicle(self):
        bp = self.world.get_blueprint_library().find('vehicle.toyota.prius')
        bp.set_attribute('color', '255,255,0') # Yellow Taxi
        spawn_point = self.world.get_map().get_spawn_points()[0]
        return self.world.spawn_actor(bp, spawn_point)

    def get_state(self) -> VehicleState:
        """Translates CARLA's transform into our universal Data Model."""
        t = self.vehicle.get_transform()
        v = self.vehicle.get_velocity()
        
        return VehicleState(
            pose=Pose(
                position=Vector3D(t.location.x, t.location.y, t.location.z),
                orientation=Vector3D(t.rotation.roll, t.rotation.pitch, t.rotation.yaw)
            ),
            velocity_mag=np.sqrt(v.x**2 + v.y**2 + v.z**2)
        )
    
    def get_pose(self):
        pass

    def apply_control(self, control_cmd):
        """Directly applies the command to the CARLA actor."""
        self.vehicle.apply_control(control_cmd)

    def get_observation(self) -> dict:
        """
        Implementation of the abstract method.
        Collects the current state of the world to pass to Perception.
        """
        snapshot = self.world.get_snapshot()
        return {
            'world': self.world,
            'timestamp': snapshot.timestamp.elapsed_seconds,
            'frame': snapshot.frame
        }

    def cleanup(self):
        if self.vehicle:
            self.vehicle.destroy()
        pygame.quit()
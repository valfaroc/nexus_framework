from core.interfaces.perception import BasePerception
from core.data_models import PerceptionState, ObjectDetection

class GroundTruthModule(BasePerception):
    def update(self, sensor_data):
        world = sensor_data['world']
        vehicles = world.get_actors().filter('vehicle.*')
        
        state = PerceptionState(timestamp=sensor_data['timestamp'])
        for v in vehicles:
            # Convert CARLA actor to our ObjectDetection data model
            state.objects.append(ObjectDetection(
                id=v.id,
                label='vehicle',
                pose=v.get_transform(), # Simplified
                velocity=v.get_velocity(),
                confidence=1.0
            ))
        return state
    
    def get_detected_objects(self):
        """Returns a list of tracked actors (vehicles, pedestrians)."""
        pass

    def get_lane_status(self):
        """Returns information about lane markings and boundaries."""
        pass
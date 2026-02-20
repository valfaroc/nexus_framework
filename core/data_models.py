from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class Vector3D:
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

@dataclass
class Pose:
    position: Vector3D
    orientation: Vector3D  # Roll, Pitch, Yaw

@dataclass
class ObjectDetection:
    id: int
    label: str  # 'vehicle', 'pedestrian', 'traffic_light'
    pose: Pose
    velocity: Vector3D
    confidence: float
    bounding_box: List[float]  # [length, width, height]

@dataclass
class PerceptionState:
    timestamp: float
    objects: List[ObjectDetection] = field(default_factory=list)
    lane_lines: List[List[Vector3D]] = field(default_factory=list)
    traffic_light_state: str = "Unknown"

@dataclass
class Trajectory:
    waypoints: List[Pose]
    target_velocities: List[float]
    is_emergency_stop: bool = False

@dataclass
class VehicleState:
    pass
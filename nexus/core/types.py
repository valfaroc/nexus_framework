from pydantic import BaseModel, Field
from typing import Optional


class VehicleControl(BaseModel):
    """Canonical control command. All control modules output this type."""

    model_config = {"frozen": True}

    throttle: float = Field(0.0, ge=0.0, le=1.0)
    brake: float = Field(0.0, ge=0.0, le=1.0)
    steer: float = Field(0.0, ge=-1.0, le=1.0)
    reverse: bool = False
    hand_brake: bool = False


class VehiclePose(BaseModel):
    model_config = {"frozen": True}
    x: float
    y: float
    z: float
    roll: float
    pitch: float
    yaw: float
    timestamp: float


class VehicleVelocity(BaseModel):
    model_config = {"frozen": True}
    vx: float
    vy: float
    vz: float
    speed_kmh: float
    timestamp: float


class SensorData(BaseModel):
    model_config = {"frozen": True}
    sensor_type: str
    timestamp: float
    data: dict[str, object]  # type-specific payload


class WorldState(BaseModel):
    model_config = {"frozen": True}
    tick: int
    timestamp: float
    ego_pose: VehiclePose
    ego_velocity: VehicleVelocity


class VehicleConfig(BaseModel):
    blueprint: str = "vehicle.tesla.cybertruck"
    spawn_index: int = 0
    color: Optional[str] = None

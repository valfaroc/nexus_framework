# nexus/config/schema.py
from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Any, Literal


class SensorConfig(BaseModel):
    type: Literal["camera_rgb", "lidar", "gnss", "imu"]
    width: int = 1200
    height: int = 800
    position: dict[str, float] = Field(default_factory=lambda: {"x": -5.5, "z": 2.8})
    rotation: dict[str, float] = Field(default_factory=lambda: {"pitch": -15.0})


class ControlConfig(BaseModel):
    type: str = "pid"  # pid, mpc, fuzzy, stanley — anything
    translator: str | None = None  # name of ModuleTranslator, or null
    config: dict[str, Any] = Field(default_factory=dict)  # fully open — module validates internally


class PlanningConfig(BaseModel):
    type: str = "waypoint_follower"  # open — same pattern as control
    config: dict[str, Any] = Field(default_factory=dict)


class WheelConfig(BaseModel):
    enabled: bool = False
    config: str = "hardware/wheel_config.ini"


class HardwareInputConfig(BaseModel):
    keyboard: bool = True
    wheel: WheelConfig = Field(default_factory=WheelConfig)


class ModulesConfig(BaseModel):
    sensing: bool = True
    localization: bool = True
    planning: PlanningConfig = Field(default_factory=PlanningConfig)
    control: ControlConfig = Field(default_factory=ControlConfig)
    hud: bool = True
    hardware_input: HardwareInputConfig = Field(default_factory=HardwareInputConfig)
    custom_modules: dict[str, str] = Field(default_factory=dict)


class SimulatorConfig(BaseModel):
    type: Literal["carla", "webots", "gazebo", "mock"] = "carla"
    version: str | None = None
    map: str = "Town04"
    host: str = "localhost"
    port: int = 2000
    config: dict[str, Any] = Field(  # open for simulator-specific params
        default_factory=dict  # e.g. webots motor names, max_speed, etc.
    )


class VehicleConfig(BaseModel):
    blueprint: str = "vehicle.tesla.model3"
    spawn_index: int = 0


class ProjectConfig(BaseModel):
    name: str
    version: str = "0.1"


class NexusConfig(BaseModel):
    """Root config model. Validated from nexus.yaml on every nexus up."""

    project: ProjectConfig
    simulator: SimulatorConfig = Field(default_factory=SimulatorConfig)
    vehicle: VehicleConfig = Field(default_factory=VehicleConfig)
    sensors: list[SensorConfig] = Field(default_factory=list)
    modules: ModulesConfig = Field(default_factory=ModulesConfig)
    visualizer: dict[str, Any] = Field(default_factory=lambda: {"rviz2": True})

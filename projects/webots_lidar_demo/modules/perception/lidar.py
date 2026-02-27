from __future__ import annotations
from typing import Any
from nexus.core.base_module import BaseModule


class LidarModule(BaseModule):
    """
    Reads point cloud data from a Webots LiDAR device each tick
    and publishes it to /nexus/sensors/lidar as a flat list of
    {x, y, z, distance} dicts — ROS2-serialisable, no numpy dependency.

    The device name must match the name in the .wbt world file.
    Default: "lidar"
    """
    name = "perception_lidar"

    def setup(self) -> None:
        self._device_name: str = self.config.get("device_name", "lidar")
        self._ready = False

    def process(self, msg: Any) -> None:
        """
        msg is a Webots LiDAR device object passed directly from the loop.
        In the simulation loop, perception modules receive the raw device
        rather than going through adapter.get_sensor_data(), because LiDAR
        point clouds are large and benefit from direct access.
        """
        if msg is None:
            return
        try:
            point_cloud = msg.getPointCloud()
            points = [
                {
                    "x":        float(p.x),
                    "y":        float(p.y),
                    "z":        float(p.z),
                    "distance": float(p.x**2 + p.y**2 + p.z**2) ** 0.5,
                }
                for p in point_cloud
                if not (p.x == 0.0 and p.y == 0.0 and p.z == 0.0)
            ]
            self.publish("/nexus/sensors/lidar", {
                "points":    points,
                "count":     len(points),
                "device":    self._device_name,
            })
        except Exception as e:
            self.log("warning", "LiDAR read failed", error=str(e))

    def teardown(self) -> None:
        self._ready = False

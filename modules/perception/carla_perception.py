from __future__ import annotations
from typing import Any
from nexus.core.base_module import BaseModule


class CarlaPerceptionModule(BaseModule):
    name = "perception_carla"

    def setup(self) -> None:
        pass

    def process(self, msg: Any) -> None:
        sensor_type: str = msg.sensor_type
        topic_map = {
            "camera_rgb": "/nexus/sensors/camera",
            "gnss": "/nexus/sensors/gnss",
            "imu": "/nexus/sensors/imu",
        }
        if sensor_type in topic_map:
            self.publish(topic_map[sensor_type], msg)

    def teardown(self) -> None:
        pass

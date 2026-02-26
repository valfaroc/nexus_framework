from __future__ import annotations
from typing import Any
from nexus.core.base_module import BaseModule


class CarlaCameraModule(BaseModule):
    """
    Routes CARLA sensor data to the appropriate /nexus/sensors/* topic.
    Migrated from the sensor callback logic in custom_path_test.py.
    """
    name = "perception_carla"

    def setup(self) -> None:
        pass

    def process(self, msg: Any) -> None:
        topic_map = {
            "camera_rgb": "/nexus/sensors/camera",
            "gnss":       "/nexus/sensors/gnss",
            "imu":        "/nexus/sensors/imu",
        }
        if msg.sensor_type in topic_map:
            self.publish(topic_map[msg.sensor_type], msg)

    def teardown(self) -> None:
        pass

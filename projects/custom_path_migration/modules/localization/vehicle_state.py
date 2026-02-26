from __future__ import annotations
from typing import Any
from nexus.core.base_module import BaseModule


class VehicleStateModule(BaseModule):
    """
    Extracts pose and velocity from WorldState each tick.
    Migrated from the transform/velocity reading in custom_path_test.py.
    """
    name = "localization_vehicle_state"

    def setup(self) -> None:
        pass

    def process(self, msg: Any) -> None:
        self.publish("/nexus/localization/pose",     msg.ego_pose)
        self.publish("/nexus/localization/velocity", msg.ego_velocity)

    def teardown(self) -> None:
        pass

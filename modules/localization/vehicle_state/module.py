from __future__ import annotations
from typing import Any
from nexus.core.base_module import BaseModule


class VehicleStateModule(BaseModule):
    name = "localization_vehicle_state"

    def setup(self) -> None:
        pass

    def process(self, msg: Any) -> None:
        # msg is WorldState from adapter.tick()
        self.publish("/nexus/localization/pose", msg.ego_pose)
        self.publish("/nexus/localization/velocity", msg.ego_velocity)

    def teardown(self) -> None:
        pass

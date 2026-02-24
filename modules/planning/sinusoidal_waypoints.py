from __future__ import annotations
from typing import Any
import numpy as np
from nexus.core.base_module import BaseModule


class SinusoidalWaypointPlanner(BaseModule):
    name = "planning_sinusoidal"

    def setup(self) -> None:
        self._path: list[dict[str, float]] = []
        self._path_generated = False

    def process(self, msg: Any) -> None:
        if not self._path_generated:
            self._generate_path(msg["pose"])

        pose = msg["pose"]
        closest = min(
            self._path,
            key=lambda p: float(np.hypot(p["x"] - pose.x, p["y"] - pose.y)),
        )
        self.publish(
            "/nexus/planning/path",
            {"waypoints": self._path, "closest": closest},
        )

    def _generate_path(self, pose: Any) -> None:
        """Migrated from generate_path() in custom_path_test.py."""
        n_points: int = int(self.config.get("n_points", 120))
        step: float = float(self.config.get("step_m", 2.0))
        amplitude: float = float(self.config.get("amplitude", 1.0))
        frequency: float = float(self.config.get("frequency", 3.0))
        self._path = [
            {
                "x": pose.x + i * step,
                "y": pose.y + amplitude * float(np.sin(i / frequency)),
                "z": pose.z + 0.2,
            }
            for i in range(n_points)
        ]
        self._path_generated = True

    def teardown(self) -> None:
        self._path = []
        self._path_generated = False

from __future__ import annotations
from typing import Any
import time
import structlog
from nexus.bridge.node import NexusNode
from nexus.core.registry import ModuleRegistry
from nexus.core.base_simulator import SimulatorInterface
from nexus.config.schema import NexusConfig

logger = structlog.get_logger()


class SimulationLoop:
    """
    Main simulation loop. Wires the adapter, modules, and ROS2 node together.

    Pipeline each tick:
        adapter.tick()
            → WorldState
            → VehicleStateModule.process()     publishes pose + velocity
            → SinusoidalWaypointPlanner.process()  publishes path
            → PIDControllerModule.process()     publishes VehicleControl
            → adapter.apply_control()

    Hz is configurable via nexus.yaml simulator.config.hz (default 20).
    """

    def __init__(
        self,
        config: NexusConfig,
        adapter: SimulatorInterface,
        registry: ModuleRegistry,
        node: NexusNode,
    ) -> None:
        self.config   = config
        self.adapter  = adapter
        self.registry = registry
        self.node     = node
        self.hz: float = float(config.simulator.config.get("hz", 20.0))
        self._running  = False
        self._pending:  dict[str, Any] = {}   # topic → latest message

    def setup(self) -> None:
        """
        Register all modules with the ROS2 node and call setup() on each.
        Must be called after node.start() and adapter.connect().
        """
        for module in self.registry.modules.values():
            self.node.register_module(module)
        self.registry.setup_all()
        self.node._loop_callback = self.on_publish
        logger.info("SimulationLoop ready", hz=self.hz,
                    modules=list(self.registry.modules.keys()))

    def run(self) -> None:
        """
        Blocking loop. Runs until stop() is called or KeyboardInterrupt.
        """
        self._running = True
        dt = 1.0 / self.hz
        logger.info("Simulation loop started", hz=self.hz)
        try:
            while self._running:
                t0 = time.monotonic()
                self._tick()
                self.node.spin_once(timeout_sec=0.0)
                elapsed = time.monotonic() - t0
                sleep_time = dt - elapsed
                if sleep_time > 0:
                    time.sleep(sleep_time)
        except KeyboardInterrupt:
            logger.info("Simulation loop interrupted")
        finally:
            self.teardown()

    def stop(self) -> None:
        self._running = False

    def teardown(self) -> None:
        self.registry.teardown_all()
        self.adapter.disconnect()
        self.node.stop()
        logger.info("Simulation loop torn down")

    def _tick(self) -> None:
        """One simulation step through the full CCAM pipeline."""
        # 1 — get world state from simulator
        world_state = self.adapter.tick()

        # 2 — Localization: WorldState → pose + velocity topics
        loc = self.registry.modules.get("localization_vehicle_state")
        if loc:
            loc.process(world_state)
            pose     = world_state.ego_pose
            velocity = world_state.ego_velocity
        else:
            return

        # 3 — Planning: pose → path topic
        planner = self.registry.modules.get("planning_sinusoidal")
        if planner:
            planner.process({"pose": pose})
            # grab the last published path from pending messages
            path = self._pending.get("/nexus/planning/path", {})
        else:
            path = {}

        # 4 — Control: pose + velocity + path → VehicleControl
        controller = self.registry.modules.get("control_pid")
        if controller and path:
            closest = path.get("closest", {})
            controller.process({
                "pose":               pose,
                "velocity":           velocity,
                "closest_waypoint_y": closest.get("y", pose.y),
            })
            cmd = self._pending.get("/nexus/control/cmd")
            if cmd:
                actor_id = next(iter(self.adapter._actors), None)  # type: ignore[attr-defined]
                if actor_id:
                    self.adapter.apply_control(actor_id, cmd)

        # 5 — HUD telemetry (non-blocking)
        hud = self.registry.modules.get("tools_hud")
        telemetry = self._pending.get("/nexus/hud/telemetry", {})
        if hud and telemetry:
            hud.process(telemetry)

    def on_publish(self, topic: str, msg: Any) -> None:
        """
        Called by NexusNode.publish() to cache the latest message per topic.
        Allows _tick() to read what modules published without going through ROS2.
        """
        self._pending[topic] = msg

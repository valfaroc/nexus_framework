from __future__ import annotations
import subprocess
from pathlib import Path
import typer
import structlog

logger = structlog.get_logger()
app = typer.Typer(name="nexus", help="Modular, simulator-agnostic CCAM simulation framework")

# FIX: sensing, hud and hardware input are not modules anymore
# FIX: looks like this template should be loaded from nexus.yaml and not being hardcoded
NEXUS_YAML_TEMPLATE = """\
project:
  name: {name}
  version: "0.1"

simulator:
  type: carla        # carla | webots | mock
  map: Town04
  host: localhost
  port: 2000

vehicle:
  blueprint: vehicle.tesla.cybertruck
  spawn_index: 0

sensors:
  - type: camera_rgb
    width: 1200
    height: 800
    position: {{x: -5.5, z: 2.8}}
    rotation: {{pitch: -15}}
  - type: gnss
  - type: imu

modules:
  sensing: true
  localization: true
  planning:
    type: sinusoidal
    config:
      n_points: 120
      step_m: 2.0
      amplitude: 1.0
      frequency: 3.0
  control:
    type: pid
    translator: null
    config:
      longitudinal: {{Kp: 0.8, Ki: 0.05, Kd: 0.2, setpoint_kmh: 25}}
      lateral:      {{Kp: 0.5, Ki: 0.05, Kd: 0.2}}
  hud: true
  hardware_input:
    keyboard: true
    wheel:
      enabled: false
      config: hardware/wheel_config.ini
"""


@app.command()
def new(project_name: str) -> None:
    """Scaffold a new Nexus project."""
    project_dir = Path("projects") / project_name
    if project_dir.exists():
        typer.echo(f"❌ Project '{project_name}' already exists at {project_dir}")
        raise typer.Exit(1)

    # FIX: should the modules and extra folders come from nexus.yaml file or they should keep harcoded?
    (project_dir / "modules" / "perception").mkdir(parents=True)
    (project_dir / "modules" / "localization").mkdir(parents=True)
    (project_dir / "modules" / "planning").mkdir(parents=True)
    (project_dir / "modules" / "control").mkdir(parents=True)
    (project_dir / "scenarios").mkdir(parents=True)
    (project_dir / "translators").mkdir(parents=True)

    nexus_yaml = project_dir / "nexus.yaml"
    nexus_yaml.write_text(NEXUS_YAML_TEMPLATE.format(name=project_name))

    typer.echo(f"✅  Project '{project_name}' created at {project_dir}")
    typer.echo(f"    Edit {nexus_yaml} then run:")
    typer.echo(f"    cd {project_dir} && nexus up")

@app.command()
def run(
    config: str = typer.Option("nexus.yaml", help="Path to nexus.yaml"),
) -> None:
    """Start the simulation loop (runs inside the ROS2 container)."""
    from nexus.config.loader import load_config
    from nexus.core.registry import ModuleRegistry
    from nexus.bridge.node import NexusNode
    from nexus.bridge.loop import SimulationLoop

    cfg = load_config(config)
    registry = ModuleRegistry(cfg)
    registry.discover()

    # Load the correct adapter based on simulator type
    adapter = _load_adapter(cfg)

    node = NexusNode()
    loop = SimulationLoop(cfg, adapter, registry, node)

    typer.echo(f"🚀  Starting simulation loop — {cfg.simulator.type} @ {loop.hz}Hz")
    node.start()
    adapter.connect(host=cfg.simulator.host, port=cfg.simulator.port)
    ego_id = adapter.spawn_ego(
        __import__("nexus.core.types", fromlist=["VehicleConfig"]).VehicleConfig(
            **cfg.vehicle.model_dump()
        )
    )
    typer.echo(f"🚗  Ego spawned: {ego_id}")
    loop.setup()
    loop.run()


def _load_adapter(cfg: Any) -> Any:
    sim_type = cfg.simulator.type

    # MockAdapter for webots in ROS2 container — Webots connection is handled
    # by the extern controller running inside the Webots container itself.
    # The ROS2 container orchestrates modules; the Webots container drives the robot.
    if sim_type in ("mock", "webots"):
        return _MockAdapter()

    sim_map: dict[str, str] = {
        "carla": "simulators.carla.adapter:CarlaAdapter",
    }
    if sim_type not in sim_map:
        raise ValueError(f"No adapter registered for simulator type '{sim_type}'")

    import importlib
    module_path, class_name = sim_map[sim_type].rsplit(":", 1)
    cls = getattr(importlib.import_module(module_path), class_name)
    return cls(dict(cfg.simulator.config))

@app.command()
def up(config: str = typer.Option("nexus.yaml")) -> None:
    from nexus.config.loader import load_config
    from nexus.orchestrator.composer import Orchestrator
    cfg = load_config(config)
    typer.echo(f"🔗  Nexus — starting '{cfg.project.name}' with simulator: {cfg.simulator.type}")
    compose_path = Orchestrator(cfg).generate_compose(config_path=config)
    typer.echo(f"📄  Generated {compose_path}")
    subprocess.run(
        ["docker", "compose", "-f", compose_path, "up", "--build"],
        check=True,
    )


@app.command()
def down(
    config: str = typer.Option("nexus.yaml", help="Path to nexus.yaml"),
) -> None:
    """Stop all running Nexus services."""
    from nexus.config.loader import load_config
    from nexus.orchestrator.composer import Orchestrator

    cfg = load_config(config)
    orch = Orchestrator(cfg)
    compose_path = orch.generate_compose()
    subprocess.run(
        ["docker", "compose", "-f", compose_path, "down"],
        check=True,
    )


@app.command()
def validate(
    config: str = typer.Option("nexus.yaml", help="Path to nexus.yaml"),
) -> None:
    """Validate nexus.yaml without launching anything."""
    from nexus.config.loader import load_config
    from nexus.core.registry import ModuleRegistry

    cfg = load_config(config)
    registry = ModuleRegistry(cfg)
    registry.discover()
    typer.echo(f"✅  nexus.yaml is valid")
    typer.echo(f"    Config:     {config}")
    typer.echo(f"    Project:    {cfg.project.name}")
    typer.echo(f"    Simulator:  {cfg.simulator.type}")
    typer.echo(f"    Modules:    {', '.join(registry.modules.keys())}")


class _MockAdapter:
    """Minimal adapter for local testing without a real simulator."""
    from nexus.core.types import (
        WorldState, VehiclePose, VehicleVelocity, VehicleConfig, VehicleControl, SensorData
    )

    _actors: dict[str, str] = {}
    _tick_count: int = 0

    def connect(self, host: str = "localhost", port: int = 0) -> None:
        import structlog
        structlog.get_logger().info("MockAdapter connected")

    def disconnect(self) -> None:
        pass

    def spawn_ego(self, config: VehicleConfig) -> str:  # type: ignore[override]
        self._actors["mock_ego"] = "mock_ego"
        return "mock_ego"

    def spawn_ego(self, config: Any) -> str:  # type: ignore[override]
        self._actors["mock_ego"] = "mock_ego"
        return "mock_ego"

    def destroy_actor(self, actor_id: str) -> None:
        pass

    def apply_control(self, actor_id: str, control: VehicleControl) -> None:  # type: ignore[override]
        pass

    def tick(self) -> WorldState:  # type: ignore[override]
        from nexus.core.types import WorldState, VehiclePose, VehicleVelocity
        self._tick_count += 1
        t = float(self._tick_count) / 20.0
        return WorldState(
            tick=self._tick_count,
            timestamp=t,
            ego_pose=VehiclePose(
                x=float(self._tick_count) * 0.5,
                y=0.0, z=0.0,
                roll=0.0, pitch=0.0, yaw=0.0,
                timestamp=t,
            ),
            ego_velocity=VehicleVelocity(
                vx=10.0, vy=0.0, vz=0.0,
                speed_kmh=36.0,
                timestamp=t,
            ),
        )

    def get_spawn_points(self) -> list[dict[str, object]]:
        return [{"x": 0.0, "y": 0.0, "z": 0.0}]

    def setup_sensor(self, sensor_type: str, config: dict[str, object], parent_id: str) -> str:
        return f"mock_{sensor_type}"

    def get_sensor_data(self, sensor_id: str) -> None:
        return None

if __name__ == "__main__":
    app()

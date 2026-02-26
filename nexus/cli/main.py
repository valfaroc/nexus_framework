# nexus/cli/main.py
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
def up(
    config: str = typer.Option("nexus.yaml", help="Path to nexus.yaml"),
) -> None:
    """Launch all simulation services defined in nexus.yaml."""
    from nexus.config.loader import load_config
    from nexus.orchestrator.composer import Orchestrator

    cfg = load_config(config)
    typer.echo(
        f"🔗  Nexus — starting '{cfg.project.name}' " f"with simulator: {cfg.simulator.type}"
    )
    orch = Orchestrator(cfg)
    compose_path = orch.generate_compose()
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
    typer.echo(f"    Project:    {cfg.project.name}")
    typer.echo(f"    Simulator:  {cfg.simulator.type}")
    typer.echo(f"    Modules:    {', '.join(registry.modules.keys())}")


if __name__ == "__main__":
    app()

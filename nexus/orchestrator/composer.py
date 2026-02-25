from __future__ import annotations
from pathlib import Path
import structlog
from jinja2 import Environment, FileSystemLoader, select_autoescape
from nexus.config.schema import NexusConfig

logger = structlog.get_logger()

TEMPLATES_DIR = Path(__file__).parent / "templates"


class Orchestrator:

    def __init__(self, config: NexusConfig) -> None:
        self.config = config
        self.env = Environment(
            loader=FileSystemLoader(str(TEMPLATES_DIR)),
            autoescape=select_autoescape([]),
        )

    def generate_compose(self, output_path: str = "docker-compose.generated.yml") -> str:
        sim_type = self.config.simulator.type
        template_name = f"{sim_type}.yml.j2"

        # Check template exists, fall back to carla if not found
        template_path = TEMPLATES_DIR / template_name
        if not template_path.exists():
            logger.warning(
                "No template found for simulator, falling back to carla",
                simulator=sim_type,
            )
            template_name = "carla.yml.j2"

        sim_content = self.env.get_template(template_name).render(config=self.config)
        ros2_content = self.env.get_template("ros2.yml.j2").render(config=self.config)

        compose = self._assemble([sim_content, ros2_content])

        with open(output_path, "w") as f:
            f.write(compose)

        logger.info(
            "docker-compose generated",
            path=output_path,
            simulator=sim_type,
        )
        return output_path

    def _assemble(self, service_blocks: list[str]) -> str:
        lines = ["services:"]
        for block in service_blocks:
            for line in block.strip().split("\n"):
                lines.append(f"  {line}")
        lines.append("")
        lines.append("volumes:")
        lines.append("  rviz_shared_configs:")
        lines.append("")
        lines.append("networks:")
        lines.append("  nexus_net:")
        lines.append("    driver: bridge")
        lines.append("")
        return "\n".join(lines)

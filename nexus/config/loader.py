from __future__ import annotations
from pathlib import Path
import yaml
import structlog
from nexus.config.schema import NexusConfig

logger = structlog.get_logger()


def load_config(path: str = "nexus.yaml") -> NexusConfig:
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(
            f"nexus.yaml not found at {config_path.resolve()}.\n"
            f"Run `nexus new [project-name]` to scaffold a new project."
        )
    with open(config_path) as f:
        raw = yaml.safe_load(f)
    if raw is None:
        raise ValueError("nexus.yaml is empty.")
    try:
        config = NexusConfig(**raw)
        logger.info("Config loaded", project=config.project.name)
        return config
    except Exception as e:
        raise ValueError(f"Invalid nexus.yaml:\n{e}") from e

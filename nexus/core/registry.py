from __future__ import annotations
import importlib
from typing import Any
import structlog
from nexus.core.base_module import BaseModule
from nexus.core.translator import ModuleTranslator
from nexus.config.schema import NexusConfig

logger = structlog.get_logger()

# Maps nexus.yaml module type strings to importable class paths
BUILTIN_MODULES: dict[str, str] = {
    "perception_carla": "modules.perception.carla_perception:CarlaPerceptionModule",
    "localization_vehicle_state": "modules.localization.vehicle_state:VehicleStateModule",
    "planning_sinusoidal": "modules.planning.sinusoidal_waypoints:SinusoidalWaypointPlanner",
    "control_pid": "modules.control.pid_controller:PIDControllerModule",
    "tools_hud": "modules.tools.hud.pygame_hud:PygameHUD",
    "tools_hardware_input": "modules.tools.hardware_input.hardware_input:HardwareInput",
}

BUILTIN_TRANSLATORS: dict[str, str] = {
    # "mpc_to_vehicle_control": "modules.control.translators.mpc:MPCToVehicleControl",
}


def _import_class(dotted_path: str) -> type[Any]:
    module_path, class_name = dotted_path.rsplit(":", 1)
    mod = importlib.import_module(module_path)
    return getattr(mod, class_name)  # type: ignore[no-any-return]


class ModuleRegistry:

    def __init__(self, config: NexusConfig) -> None:
        self.config = config
        self.modules: dict[str, BaseModule] = {}
        self.translators: dict[str, ModuleTranslator] = {}

    def discover(self) -> None:
        """Instantiate all modules declared active in nexus.yaml."""
        mc = self.config.modules

        if mc.sensing:
            self._register("perception_carla", {})

        if mc.localization:
            self._register("localization_vehicle_state", {})

        planning_type = mc.planning.type
        planning_key = f"planning_{planning_type}"
        self._register(
            planning_key if planning_key in BUILTIN_MODULES else "planning_sinusoidal",
            dict(mc.planning.config),
        )

        ctrl = mc.control
        ctrl_key = f"control_{ctrl.type}"
        self._register(
            ctrl_key if ctrl_key in BUILTIN_MODULES else "control_pid",
            dict(ctrl.config),
        )
        if ctrl.translator:
            self._register_translator(f"control_{ctrl.type}", ctrl.translator, dict(ctrl.config))

        if mc.hud:
            self._register("tools_hud", {})

        hw = mc.hardware_input
        if hw.keyboard or hw.wheel.enabled:
            self._register("tools_hardware_input", hw.model_dump())

        # Load custom modules declared in nexus.yaml
        custom = getattr(self.config, "custom_modules", {}) or {}
        for key, dotted_path in custom.items():
            self._register_custom(key, dotted_path, {})

        logger.info("Discovery complete", modules=list(self.modules.keys()))

    def _register(self, key: str, config: dict[str, Any]) -> None:
        if key not in BUILTIN_MODULES:
            raise ValueError(
                f"Unknown module type '{key}'. " f"Check nexus.yaml or register a custom module."
            )
        cls = _import_class(BUILTIN_MODULES[key])
        self.modules[key] = cls(config)
        logger.info("Module registered", module=key)

    def _register_translator(
        self, module_key: str, translator_name: str, config: dict[str, Any]
    ) -> None:
        if translator_name not in BUILTIN_TRANSLATORS:
            raise ValueError(f"Unknown translator '{translator_name}'.")
        cls = _import_class(BUILTIN_TRANSLATORS[translator_name])
        self.translators[module_key] = cls(config)
        logger.info("Translator registered", module=module_key, translator=translator_name)

    def _register_custom(self, key: str, dotted_path: str, config: dict[str, Any]) -> None:
        cls = _import_class(dotted_path)
        self.modules[key] = cls(config)
        logger.info("Custom module registered", module=key)

    def setup_all(self) -> None:
        for name, module in self.modules.items():
            module.setup()
            logger.info("Module setup complete", module=name)

    def teardown_all(self) -> None:
        for name, module in self.modules.items():
            try:
                module.teardown()
            except Exception as e:
                logger.error("Teardown failed", module=name, error=str(e))

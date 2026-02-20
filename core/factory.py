from modules.control.pid_controller import PIDModule
from modules.control.dummy_controller import DummyController
from modules.perception.ground_truth import GroundTruthModule
from modules.planning.simple_planner import SimpleSinePlanner

class ControllerFactory:
    """Gestiona la creación de controladores"""
    _controllers = {
        "pid": PIDModule,
        "dummy": DummyController
    }

    @classmethod
    def get(cls, name, config=None):
        name = name.lower()
        if name not in cls._controllers:
            raise ValueError(f"Controlador '{name}' no encontrado en el framework.")
        return cls._controllers[name](config)

class PerceptionFactory:
    """Gestiona la creación de módulos de percepción"""
    _modules = {
        "ground_truth": GroundTruthModule
    }

    @classmethod
    def get(cls, name):
        name = name.lower()
        if name not in cls._modules:
            raise ValueError(f"Módulo de percepción '{name}' no encontrado.")
        return cls._modules[name]()

class PlannerFactory:
    _planners = {
        "sine": SimpleSinePlanner
    }

    @classmethod
    def get(cls, name):
        name = name.lower()
        if name not in cls._planners:
            raise ValueError(f"Planner '{name}' not found.")
        return cls._planners[name]()
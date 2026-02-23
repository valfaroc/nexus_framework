import pytest
from typing import Any
from nexus.core.base_module import BaseModule, Topic
from nexus.core.types import VehicleControl


# --- Topic dataclass ---


def test_topic_creation() -> None:
    t = Topic(name="/nexus/control/cmd", msg_type=VehicleControl)
    assert t.name == "/nexus/control/cmd"
    assert t.msg_type is VehicleControl


def test_topic_is_immutable() -> None:
    t = Topic(name="/nexus/control/cmd", msg_type=VehicleControl)
    with pytest.raises(Exception):
        t.name = "/other/topic"  # type: ignore[misc]


def test_topic_equality() -> None:
    t1 = Topic(name="/nexus/control/cmd", msg_type=VehicleControl)
    t2 = Topic(name="/nexus/control/cmd", msg_type=VehicleControl)
    assert t1 == t2


# --- BaseModule ABC ---


def test_base_module_cannot_be_instantiated_directly() -> None:
    with pytest.raises(TypeError):
        BaseModule({})  # type: ignore[abstract]


# --- Concrete subclass ---


class MinimalModule(BaseModule):
    name = "minimal_test_module"
    subscribes = [Topic("/nexus/localization/pose", object)]
    publishes = [Topic("/nexus/control/cmd", VehicleControl)]

    def setup(self) -> None:
        self.setup_called = True

    def process(self, msg: Any) -> None:
        self.last_msg = msg

    def teardown(self) -> None:
        self.teardown_called = True


def test_concrete_module_instantiates() -> None:
    m = MinimalModule({"Kp": 0.5})
    assert m is not None


def test_module_config_accessible() -> None:
    m = MinimalModule({"Kp": 0.5, "Ki": 0.1})
    assert m.config["Kp"] == 0.5
    assert m.config["Ki"] == 0.1


def test_module_name_set() -> None:
    m = MinimalModule({})
    assert m.name == "minimal_test_module"


def test_module_topics_declared() -> None:
    m = MinimalModule({})
    assert len(m.subscribes) == 1
    assert len(m.publishes) == 1
    assert m.subscribes[0].name == "/nexus/localization/pose"
    assert m.publishes[0].name == "/nexus/control/cmd"


def test_module_setup_called() -> None:
    m = MinimalModule({})
    m.setup()
    assert m.setup_called is True


def test_module_process_called() -> None:
    m = MinimalModule({})
    m.process({"x": 1.0, "y": 2.0})
    assert m.last_msg == {"x": 1.0, "y": 2.0}


def test_module_teardown_called() -> None:
    m = MinimalModule({})
    m.teardown()
    assert m.teardown_called is True


def test_module_publish_raises_without_node() -> None:
    m = MinimalModule({})
    with pytest.raises(RuntimeError, match="not yet registered"):
        m.publish("/nexus/control/cmd", VehicleControl())


def test_module_node_is_none_before_registration() -> None:
    m = MinimalModule({})
    assert m._node is None


# --- Dependency rule ---


def test_base_module_does_not_import_simulators() -> None:
    import importlib, inspect

    mod = importlib.import_module("nexus.core.base_module")
    source = inspect.getsource(mod)
    assert "import carla" not in source
    assert "import simulators" not in source
    assert "import modules" not in source

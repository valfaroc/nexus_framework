from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Type
import structlog

logger = structlog.get_logger()


@dataclass(frozen=True)
class Topic:
    name: str
    msg_type: type[Any]


class BaseModule(ABC):
    """
    Abstract base class for all Nexus CCAM modules.

    Subclass this, declare `subscribes` and `publishes`,
    and implement `setup`, `process`, and `teardown`.
    The framework handles all ROS2 wiring automatically.

    Example:
        class MyControl(BaseModule):
            name = "my_control"
            subscribes = [Topic("/nexus/planning/path", Path)]
            publishes  = [Topic("/nexus/control/cmd", VehicleControl)]

            def setup(self): ...
            def process(self, msg): ...
            def teardown(self): ...
    """

    name: str = ""
    subscribes: list[Topic] = []
    publishes: list[Topic] = []

    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config
        self._logger = structlog.get_logger(module=self.name)
        self._node = None  # set by registry after ROS2 wiring

    @abstractmethod
    def setup(self) -> None:
        """Called once at startup before the first message."""
        ...

    @abstractmethod
    def process(self, msg: Any) -> None:
        """Called on every incoming message. Return value is ignored."""
        ...

    @abstractmethod
    def teardown(self) -> None:
        """Called on shutdown. Release resources here."""
        ...

    def publish(self, topic_name: str, msg: Any) -> None:
        """Publish a message on a declared topic. Called from process()."""
        if self._node is None:
            raise RuntimeError("Module not yet registered with ROS2 node")
        self._node.publish(topic_name, msg)

    def log(self, level: str, message: str, **kwargs: Any) -> None:
        getattr(self._logger, level)(message, **kwargs)

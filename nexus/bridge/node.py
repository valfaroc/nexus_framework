from __future__ import annotations
from typing import Any
import structlog

logger = structlog.get_logger()


class NexusNode:
    """
    Wraps rclpy to give each BaseModule a real publish/subscribe node.

    All ROS2 imports are local to methods — this file is importable
    on any machine regardless of whether ROS2 is installed.
    When running outside the container (no rclpy), publish() still
    routes through _loop_callback so the simulation loop works locally
    with the MockAdapter for testing.
    """

    def __init__(self, node_name: str = "nexus_bridge") -> None:
        self.node_name = node_name
        self._node: Any = None
        self._publishers:  dict[str, Any] = {}
        self._subscribers: dict[str, Any] = {}
        self._modules:     dict[str, Any] = {}
        self._loop_callback: Any = None     # set by SimulationLoop.setup()
        self._ros2_available = False        # set to True in start() if rclpy loads

    def start(self) -> None:
        try:
            import rclpy
            from rclpy.node import Node
            rclpy.init()
            self._node = Node(self.node_name)
            self._ros2_available = True
            logger.info("ROS2 node started", node=self.node_name)
        except ModuleNotFoundError:
            logger.warning("rclpy not available — running without ROS2 pub/sub")

    def stop(self) -> None:
        if self._ros2_available:
            import rclpy
            if self._node:
                self._node.destroy_node()
            rclpy.shutdown()
        logger.info("ROS2 node stopped")

    def register_module(self, module: Any) -> None:
        """
        Attach a module to this node.
        Sets module._node = self so BaseModule.publish() routes here.
        Creates ROS2 publishers only when rclpy is available.
        """
        module._node = self
        self._modules[module.name] = module

        if not self._ros2_available:
            logger.debug("ROS2 unavailable — skipping publisher creation",
                         module=module.name)
            return

        from std_msgs.msg import String
        for topic in module.publishes:
            if topic.name not in self._publishers:
                self._publishers[topic.name] = self._node.create_publisher(
                    String, topic.name, 10
                )
                logger.info("Publisher created", topic=topic.name, module=module.name)

    def publish(self, topic: str, msg: Any) -> None:
        # Always notify the loop cache
        if self._loop_callback:
            self._loop_callback(topic, msg)

        if not self._ros2_available:
            return

        from std_msgs.msg import String
        import json

        # Create publisher on first use if it doesn't exist yet
        if topic not in self._publishers:
            self._publishers[topic] = self._node.create_publisher(String, topic, 10)
            logger.info("Publisher created (lazy)", topic=topic)

        ros_msg = String()
        ros_msg.data = json.dumps(self._serialise(msg))
        self._publishers[topic].publish(ros_msg)

    def subscribe(self, topic: str, module: Any) -> None:
        if not self._ros2_available:
            return

        import json
        from std_msgs.msg import String

        def callback(ros_msg: Any) -> None:
            try:
                module.process(json.loads(ros_msg.data))
            except Exception as e:
                logger.error("Message processing failed", topic=topic,
                             module=module.name, error=str(e))

        self._subscribers[topic] = self._node.create_subscription(
            String, topic, callback, 10
        )
        logger.info("Subscriber created", topic=topic, module=module.name)

    def spin_once(self, timeout_sec: float = 0.0) -> None:
        if self._ros2_available:
            import rclpy
            rclpy.spin_once(self._node, timeout_sec=timeout_sec)

    def _serialise(self, msg: Any) -> Any:
        if hasattr(msg, "model_dump"):
            return msg.model_dump()
        if isinstance(msg, dict):
            return {k: self._serialise(v) for k, v in msg.items()}
        if hasattr(msg, "tolist"):
            return msg.tolist()
        return msg

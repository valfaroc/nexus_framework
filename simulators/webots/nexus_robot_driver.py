"""
Nexus Webots Driver — runs inside the Webots container via webots_ros2_driver.

This plugin is loaded by webots_ros2_driver automatically. It:
  - Reads motor commands from /nexus/control/cmd (published by nexus run)
  - Publishes GPS pose to /nexus/sensors/raw
  - webots_ros2_driver auto-publishes LiDAR to /nexus/sensors/lidar

No rclpy setup needed here — webots_ros2_driver handles the ROS2 node lifecycle.
"""
import json
import rclpy
from std_msgs.msg import String


MOTOR_NAMES = [
    "left front wheel", "right front wheel",
    "left rear wheel",  "right rear wheel",
]
MAX_SPEED = 5.0


class NexusRobotDriver:
    def init(self, webots_node, properties):
        self.__robot = webots_node.robot
        timestep = int(self.__robot.getBasicTimeStep())

        # Motors
        self.__motors = {}
        for name in MOTOR_NAMES:
            m = self.__robot.getDevice(name)
            if m:
                m.setPosition(float("inf"))
                m.setVelocity(0.0)
                self.__motors[name] = m

        # GPS
        self.__gps = self.__robot.getDevice("gps")
        if self.__gps:
            self.__gps.enable(timestep)

        # Control state
        self.__throttle = 0.0
        self.__brake    = 0.0
        self.__steer    = 0.0

        # ROS2 — node already created by webots_ros2_driver, just get it
        self.__node = rclpy.create_node("nexus_robot_driver")
        self.__node.create_subscription(
            String, "/nexus/control/cmd", self.__on_cmd, 1
        )
        self.__gps_pub = self.__node.create_publisher(
            String, "/nexus/sensors/raw", 1
        )

    def __on_cmd(self, msg):
        try:
            cmd = json.loads(msg.data)
            self.__throttle = float(cmd.get("throttle", 0.0))
            self.__brake    = float(cmd.get("brake",    0.0))
            self.__steer    = float(cmd.get("steer",    0.0))
        except Exception:
            pass

    def step(self):
        rclpy.spin_once(self.__node, timeout_sec=0)

        # Apply control to motors
        speed = (self.__throttle - self.__brake) * MAX_SPEED
        diff  = self.__steer * MAX_SPEED * 0.5
        for name, motor in self.__motors.items():
            v = speed - diff if "left" in name else speed + diff
            motor.setVelocity(v)

        # Publish GPS
        if self.__gps:
            pos = self.__gps.getValues()
            self.__gps_pub.publish(
                String(data=json.dumps({"x": pos[0], "y": pos[1], "z": pos[2]}))
            )

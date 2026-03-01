"""
Nexus Webots Driver plugin for webots_ros2_driver.
webots_ros2_driver manages the ROS2 node lifecycle — do NOT call rclpy.init()
or rclpy.create_node() here. Use webots_node.ros2_parameters instead.
"""

import json

from std_msgs.msg import String

MOTOR_NAMES = [
    "left front wheel",
    "right front wheel",
    "left rear wheel",
    "right rear wheel",
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
                print(f"[NexusDriver] Motor ready: {name}")
            else:
                print(f"[NexusDriver] WARNING: motor not found: {name}")

        # GPS
        self.__gps = self.__robot.getDevice("gps")
        if self.__gps:
            self.__gps.enable(timestep)
            print("[NexusDriver] GPS enabled")
        else:
            print("[NexusDriver] WARNING: GPS not found")

        # Control state
        self.__throttle = 0.0
        self.__brake = 0.0
        self.__steer = 0.0

        # Use the ROS2 node provided by webots_ros2_driver — do NOT create one
        self.__node = webots_node.ros2_node
        self.__node.create_subscription(String, "/nexus/control/cmd", self.__on_cmd, 1)
        self.__gps_pub = self.__node.create_publisher(String, "/nexus/sensors/raw", 1)
        print("[NexusDriver] Ready — subscribed to /nexus/control/cmd")

    def __on_cmd(self, msg):
        try:
            cmd = json.loads(msg.data)
            self.__throttle = float(cmd.get("throttle", 0.0))
            self.__brake = float(cmd.get("brake", 0.0))
            self.__steer = float(cmd.get("steer", 0.0))
        except Exception as e:
            print(f"[NexusDriver] cmd parse error: {e}")

    def step(self):
        speed = (self.__throttle - self.__brake) * MAX_SPEED
        diff = self.__steer * MAX_SPEED * 0.5
        for name, motor in self.__motors.items():
            v = speed - diff if "left" in name else speed + diff
            motor.setVelocity(v)

        if self.__gps:
            pos = self.__gps.getValues()
            self.__gps_pub.publish(
                String(data=json.dumps({"x": pos[0], "y": pos[1], "z": pos[2]}))
            )

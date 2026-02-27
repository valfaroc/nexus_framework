#!/usr/bin/env python3
"""
Webots extern controller — runs INSIDE the Webots container.

Webots launches this script as the robot controller (controller "<extern>").
It connects to the robot via the Webots controller API, reads sensor data,
and publishes it to ROS2 topics. It also subscribes to /nexus/control/cmd
and applies VehicleControl to the robot motors.

This is the bridge between Webots physics and the ROS2 simulation loop.
"""
from __future__ import annotations
import json
import time
from controller import Robot  # only available inside Webots container


def main() -> None:
    robot = Robot()
    timestep = int(robot.getBasicTimeStep())

    # Initialize motors
    motor_names = [
        "left front wheel", "right front wheel",
        "left rear wheel",  "right rear wheel",
    ]
    motors = {}
    for name in motor_names:
        m = robot.getDevice(name)
        m.setPosition(float("inf"))
        m.setVelocity(0.0)
        motors[name] = m

    # Initialize GPS
    gps = robot.getDevice("gps")
    gps.enable(timestep)

    ## Initialize LiDAR if present
    lidar = robot.getDevice("lidar")
    if lidar:
        lidar.enable(timestep)
        lidar.enablePointCloud()
        print("✅ LiDAR enabled")
    else:
        print("⚠️  LiDAR device not found — check device name in .wbt file")

    # ROS2 setup
    import rclpy
    from rclpy.node import Node
    from std_msgs.msg import String

    rclpy.init()
    node = Node("webots_extern_controller")

    # Publisher — sensor data out
    sensor_pub = node.create_publisher(String, "/nexus/sensors/raw", 10)
    lidar_pub  = node.create_publisher(String, "/nexus/sensors/lidar", 10)

    # Latest control command
    latest_cmd: dict = {"throttle": 0.0, "brake": 0.0, "steer": 0.0}

    def on_control_cmd(msg: String) -> None:
        nonlocal latest_cmd
        try:
            latest_cmd = json.loads(msg.data)
        except Exception:
            pass

    node.create_subscription(String, "/nexus/control/cmd", on_control_cmd, 10)

    max_speed: float = 5.0

    print("✅ Webots extern controller ready")

    while robot.step(timestep) != -1:
        rclpy.spin_once(node, timeout_sec=0.0)

        # Apply control
        throttle = float(latest_cmd.get("throttle", 0.0))
        brake    = float(latest_cmd.get("brake", 0.0))
        steer    = float(latest_cmd.get("steer", 0.0))

        base  = throttle * max_speed - brake * max_speed
        diff  = steer * max_speed * 0.5
        left  = base - diff
        right = base + diff

        for name, motor in motors.items():
            motor.setVelocity(left if "left" in name else right)

        # Publish GPS
        pos = gps.getValues()
        sensor_msg = String()
        sensor_msg.data = json.dumps({
            "type": "gps",
            "timestamp": robot.getTime(),
            "x": pos[0], "y": pos[1], "z": pos[2],
        })
        sensor_pub.publish(sensor_msg)

        # Publish LiDAR
        if lidar:
            points = lidar.getPointCloud()
            lidar_msg = String()
            lidar_msg.data = json.dumps({
                "points": [
                    {"x": float(p.x), "y": float(p.y), "z": float(p.z)}
                    for p in points
                    if not (p.x == 0.0 and p.y == 0.0 and p.z == 0.0)
                ],
                "count": len(points),
                "timestamp": robot.getTime(),
            })
            lidar_pub.publish(lidar_msg)

    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()

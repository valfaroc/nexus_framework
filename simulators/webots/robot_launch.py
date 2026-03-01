import os
import pathlib

import launch
from launch import LaunchDescription
from launch_ros.actions import Node
from webots_ros2_driver.utils import controller_url_prefix
from webots_ros2_driver.webots_launcher import WebotsLauncher

WORLD = "/nexus/worlds/simple_road.wbt"
URDF = "/nexus/driver/nexus_robot.urdf"
ROBOT = "nexus_vehicle"


def generate_launch_description():
    webots = WebotsLauncher(
        world=WORLD,
        gui=True,
        mode="realtime",
        ros2_supervisor=True,
    )

    driver = Node(
        package="webots_ros2_driver",
        executable="driver",
        output="screen",
        additional_env={
            "WEBOTS_CONTROLLER_URL": controller_url_prefix() + ROBOT,
            "PYTHONPATH": "/nexus/driver:/nexus:" + os.environ.get("PYTHONPATH", ""),
        },
        # Pass file path instead of string content — fixes deprecation warning
        parameters=[
            {
                "robot_description": URDF,
                "use_sim_time": True,
            }
        ],
    )

    return LaunchDescription(
        [
            webots,
            # Wait for Webots to be ready before starting driver
            launch.actions.TimerAction(period=8.0, actions=[driver]),
            launch.actions.RegisterEventHandler(
                event_handler=launch.event_handlers.OnProcessExit(
                    target_action=webots,
                    on_exit=[launch.actions.EmitEvent(event=launch.events.Shutdown())],
                )
            ),
        ]
    )

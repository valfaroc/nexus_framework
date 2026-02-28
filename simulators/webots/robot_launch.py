"""
Launch file for webots_ros2_driver inside the nexus_webots container.
Starts Webots and connects the NexusRobotDriver plugin automatically.
"""
import os
import pathlib
import launch
from launch_ros.actions import Node
from launch import LaunchDescription
from webots_ros2_driver.webots_launcher import WebotsLauncher
from webots_ros2_driver.utils import controller_url_prefix


WORLD   = "/nexus/worlds/simple_road.wbt"
URDF    = "/nexus/driver/nexus_robot.urdf"
ROBOT   = "nexus_vehicle"


def generate_launch_description():
    robot_description = pathlib.Path(URDF).read_text()

    webots = WebotsLauncher(world=WORLD, ros2_supervisor=True)

    driver = Node(
        package="webots_ros2_driver",
        executable="driver",
        output="screen",
        additional_env={
            "WEBOTS_CONTROLLER_URL": controller_url_prefix() + ROBOT,
            "PYTHONPATH": "/nexus/driver:/nexus:" + os.environ.get("PYTHONPATH", ""),
        },
        parameters=[{"robot_description": robot_description}],
    )

    return LaunchDescription([
        webots,
        driver,
        launch.actions.RegisterEventHandler(
            event_handler=launch.event_handlers.OnProcessExit(
                target_action=webots,
                on_exit=[launch.actions.EmitEvent(event=launch.events.Shutdown())],
            )
        ),
    ])

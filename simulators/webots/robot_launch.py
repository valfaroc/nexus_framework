import os

import launch
from launch import LaunchDescription
from launch_ros.actions import Node
from webots_ros2_driver.utils import controller_url_prefix
from webots_ros2_driver.webots_launcher import WebotsLauncher

WORLD = "/nexus/worlds/simple_road.wbt"
URDF = "/nexus/driver/nexus_robot.urdf"
ROBOT = "nexus_vehicle"

ROS_PYTHON_PATH = (
    "/opt/ros/humble/local/lib/python3.10/dist-packages:"
    "/opt/ros/humble/lib/python3.10/site-packages"
)


def generate_launch_description():
    webots = WebotsLauncher(
        world=WORLD,
        gui=True,
        mode="realtime",
        ros2_supervisor=False,
    )

    driver = Node(
        package="webots_ros2_driver",
        executable="driver",
        output="screen",
        additional_env={
            "WEBOTS_CONTROLLER_URL": controller_url_prefix() + ROBOT,
            "PYTHONPATH": f"/nexus/driver:/nexus:{ROS_PYTHON_PATH}:{os.environ.get('PYTHONPATH', '')}",
        },
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
            launch.actions.TimerAction(period=10.0, actions=[driver]),
            launch.actions.RegisterEventHandler(
                event_handler=launch.event_handlers.OnProcessExit(
                    target_action=webots,
                    on_exit=[launch.actions.EmitEvent(event=launch.events.Shutdown())],
                )
            ),
        ]
    )

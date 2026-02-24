from __future__ import annotations
from configparser import ConfigParser
from typing import Any
import os
import pygame
from nexus.core.base_module import BaseModule
from nexus.core.types import VehicleControl


class HardwareInputModule(BaseModule):
    name = "hardware_input"

    def setup(self) -> None:
        pygame.joystick.init()
        self.joystick: pygame.joystick.JoystickType | None = None
        self.reverse = False
        self._load_wheel_config()
        self._detect_wheel()

    def _load_wheel_config(self) -> None:
        ini_path: str = self.config.get("wheel", {}).get("config", "hardware/wheel_config.ini")
        parser = ConfigParser()
        if os.path.exists(ini_path):
            parser.read(ini_path)
            section = "Fanatec DD Pro"
            self._steer_idx = int(parser.get(section, "steering_wheel"))
            self._throttle_idx = int(parser.get(section, "throttle"))
            self._brake_idx = int(parser.get(section, "brake"))
            self._reverse_btn = int(parser.get(section, "reverse"))
        else:
            self._steer_idx = 0
            self._throttle_idx = 2
            self._brake_idx = 5
            self._reverse_btn = 102

    def _detect_wheel(self) -> None:
        for i in range(pygame.joystick.get_count()):
            j = pygame.joystick.Joystick(i)
            j.init()
            if "FANATEC" in j.get_name().upper():
                self.joystick = j
                self.log("info", "Fanatec wheel detected", name=j.get_name())
                break

    def process(self, msg: Any) -> None:
        for event in msg.get("events", []):
            if event.type == pygame.JOYBUTTONDOWN:
                if event.button == self._reverse_btn:
                    self.reverse = not self.reverse

        keys = pygame.key.get_pressed()
        wheel_enabled: bool = self.config.get("wheel", {}).get("enabled", False)

        if self.joystick and wheel_enabled:
            cmd = self._wheel_control()
        else:
            cmd = self._keyboard_control(keys)

        self.publish("/nexus/control/cmd", cmd)

    def _wheel_control(self) -> VehicleControl:
        assert self.joystick is not None
        steer = float(self.joystick.get_axis(self._steer_idx))
        steer = steer if abs(steer) > 0.01 else 0.0

        throttle_raw = float(self.joystick.get_axis(self._throttle_idx))
        throttle = max(0.0, (1.0 - throttle_raw) / 2.0)
        if throttle < 0.05:
            throttle = 0.0

        brake_raw = float(self.joystick.get_axis(self._brake_idx))
        brake = max(0.0, (1.0 - brake_raw) / 2.0)
        if brake < 0.05:
            brake = 0.0

        return VehicleControl(
            throttle=throttle,
            brake=brake,
            steer=steer,
            reverse=self.reverse,
        )

    def _keyboard_control(self, keys: Any) -> VehicleControl:
        return VehicleControl(
            throttle=1.0 if keys[pygame.K_w] else 0.0,
            brake=1.0 if keys[pygame.K_s] else 0.0,
            steer=-0.6 if keys[pygame.K_a] else (0.6 if keys[pygame.K_d] else 0.0),
            reverse=self.reverse,
        )

    def teardown(self) -> None:
        pass

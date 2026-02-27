from __future__ import annotations
from collections import deque
from typing import Any
import numpy as np
from nexus.core.base_module import BaseModule


class PygameHUD(BaseModule):
    name = "tools_hud"

    def setup(self) -> None:
        self._available = False
        try:
            import pygame  # lazy — only imported when HUD actually sets up
            self._pygame = pygame
            pygame.init()
            w: int = int(self.config.get("width", 1200))
            h: int = int(self.config.get("height", 800))
            self.display = pygame.display.set_mode((w, h))
            pygame.display.set_caption("Nexus HUD")
            self.font = pygame.font.SysFont("mono", 15)
            self.surface: Any = None
            hist = int(self.config.get("history_len", 200))
            self.lon_history: deque[float] = deque([0.0] * hist, maxlen=hist)
            self.lat_history: deque[float] = deque([0.0] * hist, maxlen=hist)
            self._width = w
            self._available = True
        except Exception as e:
            import structlog
            structlog.get_logger().warning(
                "HUD unavailable — pygame failed to initialise", error=str(e)
            )

    def process(self, msg: Any) -> None:
        if not self._available:
            return
        pygame = self._pygame
        if hasattr(msg, "sensor_type") and msg.sensor_type == "camera_rgb":
            arr: Any = msg.data["array"]
            self.surface = pygame.surfarray.make_surface(arr.swapaxes(0, 1))
            return
        self.lon_history.append(float(msg.get("e_lon", 0.0)))
        self.lat_history.append(float(msg.get("e_lat", 0.0)))
        self._render(msg)

    def _render(self, telemetry: dict[str, Any]) -> None:
        pygame = self._pygame
        if self.surface:
            self.display.blit(self.surface, (0, 0))
        self._render_hud(telemetry)
        self._draw_graph(self.lon_history, (self._width - 280, 50),
                         "Error Longitudinal", (255, 50, 50))
        self._draw_graph(self.lat_history, (self._width - 280, 180),
                         "Error Lateral", (50, 150, 255))
        pygame.display.flip()

    def _render_hud(self, t: dict[str, Any]) -> None:
        pygame = self._pygame
        overlay = pygame.Surface((210, 140))
        overlay.set_alpha(180)
        overlay.fill((0, 0, 0))
        self.display.blit(overlay, (10, 10))
        lines = [
            f"Vel:     {t.get('speed', 0.0):.1f} km/h",
            f"Steer:   {t.get('steer', 0.0):.2f}",
            f"E_Lon:   {t.get('e_lon', 0.0):.2f}",
            f"E_Lat:   {t.get('e_lat', 0.0):.2f}",
            f"Mode:    {str(t.get('mode', 'MANUAL')).upper()}",
        ]
        for i, text in enumerate(lines):
            self.display.blit(self.font.render(text, True, (255, 255, 255)),
                              (15, 15 + i * 18))

    def _draw_graph(self, data: deque[float], pos: tuple[int, int],
                    title: str, color: tuple[int, int, int],
                    scale: int = 10) -> None:
        pygame = self._pygame
        import numpy as np
        w, h = 250, 100
        pygame.draw.rect(self.display, (200, 200, 200), (*pos, w, h))
        cx, cy = pos[0], pos[1] + h // 2
        pygame.draw.line(self.display, (70, 70, 70), (cx, cy), (cx + w, cy))
        if len(data) > 1:
            pts = [(pos[0] + i * (w / len(data)),
                    float(np.clip(cy - val * scale, pos[1], pos[1] + h)))
                   for i, val in enumerate(data)]
            pygame.draw.lines(self.display, color, False, pts, 2)
        self.display.blit(self.font.render(title, True, (255, 255, 255)),
                          (pos[0], pos[1] - 20))

    def teardown(self) -> None:
        if self._available:
            self._pygame.quit()

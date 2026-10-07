"""Per-frame update logic for the success (balloons) and failure (explosion) screens.

No SVG/cairo calls here -- these only move/scale already-rasterized Surfaces,
which are cached and supplied by renderer.py / svg_assets.py.
"""

import math
import random


class Balloon:
    BALLOON_W = 200
    BALLOON_H = 320

    def __init__(self, screen_w: int, screen_h: int, color: str):
        self.color = color
        self.screen_w = screen_w
        self.screen_h = screen_h
        self.scale = random.uniform(0.75, 1.3)
        self.base_x = random.uniform(0, screen_w - self.BALLOON_W * self.scale)
        self.y = random.uniform(0, screen_h)
        self.phase = random.uniform(0, math.tau)
        self.speed = random.uniform(40, 80)
        self.sway_amplitude = random.uniform(15, 40)
        self.sway_freq = random.uniform(0.5, 1.2)
        self._t = 0.0

    @property
    def x(self) -> float:
        return self.base_x + self.sway_amplitude * math.sin(self._t * self.sway_freq + self.phase)

    @property
    def width(self) -> int:
        return int(self.BALLOON_W * self.scale)

    @property
    def height(self) -> int:
        return int(self.BALLOON_H * self.scale)

    def update(self, dt: float) -> None:
        self._t += dt
        self.y -= self.speed * dt
        if self.y + self.height < -40:
            self.y = self.screen_h + random.uniform(0, 200)
            self.base_x = random.uniform(0, self.screen_w - self.width)
            self.phase = random.uniform(0, math.tau)


class Explosion:
    def __init__(self, base_size: int = 500):
        self.base_size = base_size
        self._t = 0.0

    def update(self, dt: float) -> None:
        self._t += dt

    def current_size(self) -> tuple[int, int]:
        scale = 1 + 0.08 * math.sin(self._t * 2)
        size = int(self.base_size * scale)
        return size, size


class FuseBurn:
    """Tracks the 2-second fuse burn-down leading up to the blast."""

    DURATION = 2.0

    def __init__(self):
        self._t = 0.0

    def update(self, dt: float) -> None:
        self._t += dt

    @property
    def progress(self) -> float:
        """0.0 (just lit) -> 1.0 (burned down to the bomb)."""
        return min(1.0, self._t / self.DURATION)

    @property
    def done(self) -> bool:
        return self._t >= self.DURATION


class ExplosionGrow:
    """Animates the blast growing from a small flash to filling the screen."""

    DURATION = 2.3

    def __init__(self, target_size: int):
        self.target_size = target_size
        self.start_size = max(1, int(target_size * 0.06))
        self._t = 0.0

    def update(self, dt: float) -> None:
        self._t += dt

    @property
    def done(self) -> bool:
        return self._t >= self.DURATION

    def current_size(self) -> tuple[int, int]:
        p = min(1.0, self._t / self.DURATION)
        eased = 1 - (1 - p) ** 3  # ease-out cubic: fast growth, settling near the end
        size = int(self.start_size + (self.target_size - self.start_size) * eased)
        return size, size

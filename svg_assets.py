"""Hand-authored SVG string builders for the countdown, balloons, and explosion.

No external files or network access — every visual is generated here as SVG
markup and rasterized elsewhere (see renderer.py).
"""

import math
from xml.sax.saxutils import escape

PALETTE = ["#ff4d6d", "#ffd166", "#4dd9ff", "#8affc1", "#c38cff", "#ff9f4d"]


def digit_svg(mmss: str, fill: str = "#ff2d2d", w: int = 900, h: int = 320) -> str:
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 900 320">
  <defs>
    <filter id="glow" x="-60%" y="-60%" width="220%" height="220%">
      <feGaussianBlur stdDeviation="10" result="blur"/>
      <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
  </defs>
  <text x="450" y="230" font-family="DejaVu Sans Mono, monospace" font-size="220"
        font-weight="bold" fill="{fill}" text-anchor="middle" filter="url(#glow)">{mmss}</text>
</svg>'''


def tagline_svg(text: str, fill: str = "#ff6b6b", font_size: int = 36, h: int = 90) -> str:
    safe_text = escape(text)
    # Width scales with text length (plus generous side padding) so the viewBox
    # always fits the rendered text -- a fixed viewBox clipped long phrases.
    char_width = font_size * 0.62 + 2  # avg glyph width + letter-spacing, bold DejaVu Sans
    w = int(len(text) * char_width + 200)
    cx, cy = w / 2, h / 2 + font_size * 0.32
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">
  <text x="{cx}" y="{cy}" font-family="DejaVu Sans, sans-serif" font-size="{font_size}"
        font-weight="bold" letter-spacing="2" fill="{fill}" text-anchor="middle">{safe_text}</text>
</svg>'''


def _polyline_prefix(points: list[tuple[float, float]], fraction: float) -> list[tuple[float, float]]:
    """Sub-path of `points` starting at points[0], covering `fraction` of the
    total path length (0..1), with the cut point linearly interpolated."""
    if fraction <= 0:
        return [points[0]]
    total = sum(math.hypot(x2 - x1, y2 - y1) for (x1, y1), (x2, y2) in zip(points, points[1:]))
    target = total * fraction
    acc = 0.0
    result = [points[0]]
    for (x1, y1), (x2, y2) in zip(points, points[1:]):
        seg = math.hypot(x2 - x1, y2 - y1)
        if acc + seg >= target:
            t = (target - acc) / seg if seg > 0 else 0
            result.append((x1 + (x2 - x1) * t, y1 + (y2 - y1) * t))
            return result
        result.append((x2, y2))
        acc += seg
    return result


def bomb_fuse_svg(progress: float, size: int = 560) -> str:
    """A bomb with a burning fuse. progress: 0.0 (just lit, full fuse) ->
    1.0 (burned down to the bomb)."""
    progress = max(0.0, min(1.0, progress))
    bomb_cx = size * 0.5
    bomb_cy = size * 0.72
    bomb_r = size * 0.19

    attach = (bomb_cx + bomb_r * 0.15, bomb_cy - bomb_r * 0.95)
    fuse_points = [
        attach,
        (attach[0] + size * 0.05, attach[1] - size * 0.11),
        (attach[0] - size * 0.07, attach[1] - size * 0.20),
        (attach[0] + size * 0.08, attach[1] - size * 0.30),
        (attach[0] - size * 0.04, attach[1] - size * 0.40),
    ]
    remaining = _polyline_prefix(fuse_points, 1 - progress)
    path_d = "M " + " L ".join(f"{x:.1f},{y:.1f}" for x, y in remaining)
    spark_x, spark_y = remaining[-1]
    spark_r = 9 + 5 * abs(math.sin(progress * math.pi * 8))

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 {size} {size}">
  <defs>
    <filter id="spark-glow" x="-120%" y="-120%" width="340%" height="340%">
      <feGaussianBlur stdDeviation="6" result="blur"/>
      <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>
    <radialGradient id="spark-grad" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="#fff6c0"/>
      <stop offset="50%" stop-color="#ffb347"/>
      <stop offset="100%" stop-color="#ff5e1a"/>
    </radialGradient>
  </defs>
  <ellipse cx="{bomb_cx}" cy="{bomb_cy + bomb_r * 1.05}" rx="{bomb_r * 1.1}" ry="{bomb_r * 0.25}" fill="#000000" fill-opacity="0.35"/>
  <circle cx="{bomb_cx}" cy="{bomb_cy}" r="{bomb_r}" fill="#1a1a1a" stroke="#000000" stroke-width="4"/>
  <ellipse cx="{bomb_cx - bomb_r * 0.35}" cy="{bomb_cy - bomb_r * 0.35}" rx="{bomb_r * 0.28}" ry="{bomb_r * 0.18}" fill="#ffffff" fill-opacity="0.12"/>
  <path d="{path_d}" stroke="#8a6a4a" stroke-width="7" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
  <circle cx="{spark_x:.1f}" cy="{spark_y:.1f}" r="{spark_r:.1f}" fill="url(#spark-grad)" filter="url(#spark-glow)"/>
</svg>'''


def balloon_svg(color: str, w: int = 400, h: int = 640) -> str:
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 200 320">
  <ellipse cx="100" cy="110" rx="80" ry="100" fill="{color}" stroke="#000000" stroke-opacity="0.15" stroke-width="3"/>
  <ellipse cx="70" cy="70" rx="22" ry="34" fill="#ffffff" fill-opacity="0.35"/>
  <polygon points="90,205 110,205 100,225" fill="{color}"/>
  <path d="M100,225 Q90,260 100,295 Q110,320 100,320" stroke="#444444" stroke-width="3" fill="none"/>
</svg>'''


def explosion_svg(size: int = 700) -> str:
    cx = cy = size / 2
    outer, inner = size * 0.46, size * 0.27
    pts = []
    for i in range(24):
        r = outer if i % 2 == 0 else inner
        a = math.radians(i * 15)
        pts.append(f"{cx + r * math.cos(a):.1f},{cy + r * math.sin(a):.1f}")
    points = " ".join(pts)
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 {size} {size}">
  <defs>
    <radialGradient id="blast" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="#fff6c0"/>
      <stop offset="35%" stop-color="#ffd23f"/>
      <stop offset="65%" stop-color="#ff6b35"/>
      <stop offset="100%" stop-color="#c81d25"/>
    </radialGradient>
  </defs>
  <polygon points="{points}" fill="url(#blast)"/>
</svg>'''

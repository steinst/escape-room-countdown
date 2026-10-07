"""Rasterize SVG strings to pygame Surfaces, with caching by key."""

import io

import cairosvg
import pygame

_cache: dict[str, pygame.Surface] = {}


def svg_to_surface(
    svg_string: str,
    cache_key: str | None = None,
    size: tuple[int, int] | None = None,
) -> pygame.Surface:
    if cache_key is not None and cache_key in _cache:
        return _cache[cache_key]

    kwargs: dict = {"bytestring": svg_string.encode()}
    if size:
        kwargs["output_width"], kwargs["output_height"] = size
    png_bytes = cairosvg.svg2png(**kwargs)
    surf = pygame.image.load(io.BytesIO(png_bytes), "x.png").convert_alpha()

    if cache_key is not None:
        _cache[cache_key] = surf
    return surf

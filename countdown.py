#!/usr/bin/env python3
"""Fullscreen escape-room countdown clock.

Launches straight to a blank screen -- the countdown doesn't start, or even
appear, until the game master presses Space. Typing the configured stop word
(see config.toml) defuses the countdown: the timer freezes (shown in green in
the background) and balloons rise in front of it while a looping happy tune
plays. Reaching zero plays out a bomb sequence: a 2-second burning fuse, then
an explosion that booms, roars like thunder, and grows to fill the screen,
settling into a held screen with a red 0:00, a failure message, and a
looping ghostly bass tune. Either held screen stays until the game master
presses R, which goes back to the blank waiting screen for the next run. The
window only closes on Ctrl+Q -- Escape does nothing, so players can't
accidentally stop the program.
"""

import argparse
import re
import sys

import pygame

from animations import Balloon, Explosion, ExplosionGrow, FuseBurn
from audio import (
    load_sound,
    synth_failure_boom,
    synth_fuse_hiss,
    synth_ghost_bass,
    synth_mountain_king,
    synth_thunder,
)
from config_loader import load_config
from keybuffer import StopWordMatcher
from renderer import svg_to_surface
from svg_assets import PALETTE, balloon_svg, bomb_fuse_svg, digit_svg, explosion_svg, tagline_svg

STATE_READY = "ready"
STATE_COUNTING = "counting"
STATE_SUCCESS = "success"
STATE_FUSE = "fuse"
STATE_BLAST = "blast"
STATE_FAILURE_HELD = "failure_held"

RESETTABLE_STATES = (STATE_SUCCESS, STATE_FAILURE_HELD)

BG_READY = (0, 0, 0)
BG_COUNTING = (5, 6, 15)
BG_SUCCESS = (10, 20, 40)
BG_FAILURE = (10, 2, 2)

COLOR_NORMAL = "#ff2d2d"
COLOR_URGENT = "#ffffff"
COLOR_FROZEN = "#33ff66"
COLOR_TAGLINE_NORMAL = "#ff6b6b"
COLOR_TAGLINE_FROZEN = "#66ffa3"

URGENT_THRESHOLD_SECONDS = 10
NUM_BALLOONS = 35


def parse_duration(s: str) -> int:
    if re.fullmatch(r"\d+", s):
        return int(s)
    if m := re.fullmatch(r"(\d+)s", s):
        return int(m[1])
    if m := re.fullmatch(r"(\d+)m", s):
        return int(m[1]) * 60
    if m := re.fullmatch(r"(\d+):(\d+)", s):
        return int(m[1]) * 60 + int(m[2])
    raise argparse.ArgumentTypeError(
        f"bad duration '{s}' (use plain seconds like 90, Ns/Nm like 90s or 5m, or MM:SS like 05:00)"
    )


def fmt_mmss(seconds: float) -> str:
    seconds = max(0, int(seconds))
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


def main() -> None:
    ap = argparse.ArgumentParser(description="Fullscreen escape-room countdown clock.")
    ap.add_argument("duration", type=parse_duration, help="90, 90s, 5m, or 05:00")
    ap.add_argument("--config", default=None, help="Path to config.toml")
    args = ap.parse_args()

    cfg = load_config(args.config)

    pygame.init()
    pygame.mixer.init()
    screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    pygame.mouse.set_visible(False)
    w, h = screen.get_size()
    clock = pygame.time.Clock()
    blast_target_size = int(max(w, h) * 1.6)

    success_sound = load_sound(cfg.success_sound_path, synth_mountain_king)
    boom_sound = load_sound(cfg.failure_sound_path, synth_failure_boom)
    thunder_sound = pygame.mixer.Sound(synth_thunder())
    ghost_sound = pygame.mixer.Sound(synth_ghost_bass())
    fuse_hiss_sound = pygame.mixer.Sound(synth_fuse_hiss())

    tagline_surf_normal = svg_to_surface(
        tagline_svg(cfg.tagline, fill=COLOR_TAGLINE_NORMAL), cache_key="tagline:normal"
    )
    tagline_surf_frozen = svg_to_surface(
        tagline_svg(cfg.tagline_success, fill=COLOR_TAGLINE_FROZEN), cache_key="tagline:frozen"
    )
    tagline_surf_failure = svg_to_surface(
        tagline_svg(cfg.tagline_failure, fill=COLOR_TAGLINE_NORMAL), cache_key="tagline:failure"
    )
    failure_digit_surf = svg_to_surface(
        digit_svg("00:00", fill=COLOR_NORMAL), cache_key="digit:failure", size=(w, h // 3)
    )

    def fresh_state() -> dict:
        return {
            "state": STATE_READY,
            "start_ms": None,
            "matcher": StopWordMatcher(cfg.stop_word),
            "balloons": [],
            "frozen_digit_surf": None,
            "fuse": None,
            "blast": None,
            "settled_explosion": None,
        }

    g = fresh_state()
    last_digit_key = None
    digit_surf = None
    running = True

    while running:
        dt = clock.tick(60) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_q and event.mod & pygame.KMOD_CTRL:
                    running = False
                elif g["state"] in RESETTABLE_STATES and event.key == pygame.K_r:
                    pygame.mixer.stop()
                    g = fresh_state()
                    last_digit_key = None
                elif g["state"] == STATE_READY and event.key == pygame.K_SPACE:
                    g["state"] = STATE_COUNTING
                    g["start_ms"] = pygame.time.get_ticks()
                elif g["state"] == STATE_COUNTING and g["matcher"].feed(event.unicode):
                    elapsed = (pygame.time.get_ticks() - g["start_ms"]) / 1000.0
                    frozen_text = fmt_mmss(args.duration - elapsed)
                    g["frozen_digit_surf"] = svg_to_surface(
                        digit_svg(frozen_text, fill=COLOR_FROZEN),
                        cache_key=f"digit:frozen:{frozen_text}",
                        size=(w, h // 3),
                    )
                    g["state"] = STATE_SUCCESS
                    success_sound.play(loops=-1)
                    g["balloons"] = [Balloon(w, h, PALETTE[i % len(PALETTE)]) for i in range(NUM_BALLOONS)]

        if g["state"] == STATE_READY:
            screen.fill(BG_READY)

        elif g["state"] == STATE_COUNTING:
            elapsed = (pygame.time.get_ticks() - g["start_ms"]) / 1000.0
            remaining = args.duration - elapsed
            if remaining <= 0:
                g["state"] = STATE_FUSE
                g["fuse"] = FuseBurn()
                fuse_hiss_sound.play()
                screen.fill(BG_FAILURE)
            else:
                screen.fill(BG_COUNTING)
                text = fmt_mmss(remaining)
                urgent = remaining <= URGENT_THRESHOLD_SECONDS and int(elapsed * 2) % 2 == 0
                digit_key = (text, urgent)
                if digit_key != last_digit_key:
                    fill = COLOR_URGENT if urgent else COLOR_NORMAL
                    digit_surf = svg_to_surface(
                        digit_svg(text, fill=fill),
                        cache_key=f"digit:{text}:{urgent}",
                        size=(w, h // 3),
                    )
                    last_digit_key = digit_key
                digit_rect = digit_surf.get_rect(center=(w // 2, h // 2))
                screen.blit(digit_surf, digit_rect)
                tagline_rect = tagline_surf_normal.get_rect(centerx=w // 2, top=digit_rect.bottom + 40)
                screen.blit(tagline_surf_normal, tagline_rect)

        elif g["state"] == STATE_SUCCESS:
            screen.fill(BG_SUCCESS)
            digit_rect = g["frozen_digit_surf"].get_rect(center=(w // 2, h // 2))
            screen.blit(g["frozen_digit_surf"], digit_rect)
            tagline_rect = tagline_surf_frozen.get_rect(centerx=w // 2, top=digit_rect.bottom + 40)
            screen.blit(tagline_surf_frozen, tagline_rect)
            for b in g["balloons"]:
                b.update(dt)
                surf = svg_to_surface(balloon_svg(b.color), cache_key=f"balloon:{b.color}")
                scaled = pygame.transform.smoothscale(surf, (b.width, b.height))
                screen.blit(scaled, (b.x, b.y))

        elif g["state"] == STATE_FUSE:
            screen.fill(BG_FAILURE)
            fuse = g["fuse"]
            fuse.update(dt)
            svg = bomb_fuse_svg(fuse.progress)
            surf = svg_to_surface(svg, cache_key=f"fuse:{round(fuse.progress, 2)}")
            screen.blit(surf, surf.get_rect(center=(w // 2, h // 2)))
            if fuse.done:
                fuse_hiss_sound.stop()
                g["state"] = STATE_BLAST
                g["blast"] = ExplosionGrow(blast_target_size)
                boom_sound.play()
                thunder_sound.play()

        elif g["state"] == STATE_BLAST:
            screen.fill(BG_FAILURE)
            blast = g["blast"]
            blast.update(dt)
            surf = svg_to_surface(explosion_svg(), cache_key="explosion")
            scaled = pygame.transform.smoothscale(surf, blast.current_size())
            screen.blit(scaled, scaled.get_rect(center=(w // 2, h // 2)))
            if blast.done:
                g["state"] = STATE_FAILURE_HELD
                g["settled_explosion"] = Explosion(base_size=220)
                ghost_sound.play(loops=-1)

        elif g["state"] == STATE_FAILURE_HELD:
            screen.fill(BG_FAILURE)
            settled = g["settled_explosion"]
            settled.update(dt)
            surf = svg_to_surface(explosion_svg(), cache_key="explosion")
            scaled = pygame.transform.smoothscale(surf, settled.current_size())
            screen.blit(scaled, scaled.get_rect(center=(w // 2, h // 2)))
            digit_rect = failure_digit_surf.get_rect(center=(w // 2, h // 2))
            screen.blit(failure_digit_surf, digit_rect)
            tagline_rect = tagline_surf_failure.get_rect(centerx=w // 2, top=digit_rect.bottom + 40)
            screen.blit(tagline_surf_failure, tagline_rect)

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)

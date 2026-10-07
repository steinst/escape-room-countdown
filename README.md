# Escape Room Countdown

A fullscreen countdown clock for escape rooms. All graphics are rendered
from SVG at runtime. Type a secret word on the keyboard to defuse the
countdown; let it reach zero and a bomb sequence plays out instead.

## Features

- Fullscreen countdown clock, duration set from the command line
- Type a configured stop word at any time to defuse the countdown — the
  timer freezes, balloons rise, and a happy tune plays on loop
- Let it reach zero and a 2-second burning fuse leads into an explosion
  (boom + rolling thunder) that grows to fill the screen, settling into a
  held failure screen with a looping ghostly tune
- Configurable Icelandic flavor text under the clock for each state
- The two tunes are driven by real public-domain sheet music — see
  [Music](#music) below
- The window only closes on **Ctrl+Q** — Escape does nothing, so players
  can't accidentally stop the program

## Requirements

- Linux with a graphical session (X11 or Wayland/XWayland)
- Python 3.11+ (uses the standard library's `tomllib`)

## Setup

```bash
git clone https://github.com/steinst/escape-room-countdown.git
cd escape-room-countdown
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Running

```bash
source venv/bin/activate
python countdown.py 5m          # 5 minutes
python countdown.py 300         # 300 seconds
python countdown.py 05:00       # MM:SS
python countdown.py 5m --config path/to/config.toml
```

If the fullscreen window misbehaves under a native Wayland session, try
forcing SDL's X11 backend (via XWayland):

```bash
SDL_VIDEODRIVER=x11 python countdown.py 5m
```

### Controls

| Key | Effect |
|---|---|
| *(type the stop word)* | Defuses the countdown, while it's still running |
| `R` | Reset to a fresh countdown — only once a run has ended (success or failure) |
| `Ctrl+Q` | Quit the program (Escape is intentionally ignored) |

## Configuration

Edit `config.toml` (or pass `--config` to point elsewhere):

```toml
stop_word = "hestur"   # case-insensitive, typed on the keyboard to defuse

tagline = "AFTENGIÐ SPRENGJUNA ÁÐUR EN TÍMINN RENNUR ÚT"   # shown while counting (red)
tagline_success = "SPRENGJAN ER AFTENGD!"                    # shown once defused (green)
tagline_failure = "YKKUR MISTÓKST — ALLT ER SPRUNGIÐ!"        # shown after the bomb goes off (red)

[sounds]
# Optional: point at your own .wav/.ogg files instead of the built-in tunes.
# Leave empty ("") to use the synthesized versions.
success = ""
failure = ""
```

## Music

Both loops are built from real public-domain sheet music, not invented
approximations: note pitch, rhythm, and rests were extracted from MIDI
transcriptions published by the [Mutopia Project](https://www.mutopiaproject.org)
(which publishes only public-domain scores for free reuse):

- **Success tune**: the melody of Grieg's *In the Hall of the Mountain King*
  (*Peer Gynt* Suite No. 1, Op. 46 No. 4, 1875 — public domain, Grieg died 1907)
- **Failure tune**: the opening of Bach's *Toccata and Fugue in D minor*,
  BWV 565 (source edition: Bach-Gesellschaft Ausgabe, 1867 — public domain,
  Bach died 1750), the piece used in the intro of the 1986 Mac game Dark Castle

The extracted notes are synthesized into audio by original code in
`audio.py` (timbre, harmonics, envelopes, tremolo, transposition, and
dynamics are all written here, not sampled from any recording). Real .mid
files for both pieces are included in `assets/`; regenerate them with:

```bash
python audio.py
```

## Project structure

```
countdown.py       entry point: CLI, main loop, state machine
config_loader.py    loads and validates config.toml
keybuffer.py         sliding-window stop-word matcher
svg_assets.py         SVG string builders (digits, balloons, bomb, explosion)
renderer.py            SVG -> pygame.Surface, with caching
animations.py            balloon / fuse / explosion per-frame animation
audio.py                   sound synthesis + the MIDI note data and writer
config.toml                stop word, taglines, sound overrides
assets/                     generated .mid files
```

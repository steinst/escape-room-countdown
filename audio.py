"""Procedural sound synthesis, with support for custom overrides.

The success and failure loops are driven by real note data (pitch, duration,
velocity, rest-after) extracted from public-domain MIDI transcriptions
published by the Mutopia Project (mutopiaproject.org, which explicitly
publishes only public-domain sheet music for free reuse):

  - GRIEG_EVENTS: the melody line of "In the Hall of the Mountain King"
    (Peer Gynt Suite No. 1, Op. 46 No. 4, 1875), from
    mutopiaproject.org piece 1888.
  - BACH_EVENTS: the opening ~32 seconds of "Toccata and Fugue in D minor"
    BWV 565 (source: Bach-Gesellschaft Ausgabe, 1867), from
    mutopiaproject.org piece 1780. This is the piece used in the intro of
    the 1986 Mac game Dark Castle.

Both compositions are long out of copyright (Grieg d. 1907, Bach d. 1750);
the event data below is just pitch/timing numbers extracted from those free
transcriptions. The actual sound -- timbre, harmonics, tremolo, envelopes,
transposition, the crescendo curve -- is original synthesis code below, not
a reproduction of any particular recording or arrangement.

In-app playback synthesizes everything directly to WAV instead of relying on
the system's MIDI playback (SDL_mixer's native MIDI backend needs an
external synth like Timidity/FluidSynth plus a soundfont, neither of which
is guaranteed to be installed on an escape-room display box). A standalone
Standard MIDI File (format 0) writer is also included to export the Grieg
piece as a real .mid file.
"""

import io
import math
import os
import random
import wave

import numpy as np
import pygame

SAMPLE_RATE = 44100
ASSETS_DIR = os.path.join(os.path.dirname(__file__), "assets")

# Each event: (pitches: tuple[int], duration_seconds, velocity 0-1, rest_after_seconds)
# Extracted from mutopiaproject.org piece 1888 (Grieg), "right:solo" track.
GRIEG_EVENTS = [
    ((66,), 1.522, 0.54, 0.217), ((35,), 0.109, 0.49, 0.109), ((37,), 0.109, 0.49, 0.108), ((38,), 0.109, 0.49, 0.108),
    ((40,), 0.109, 0.49, 0.109), ((42,), 0.109, 0.49, 0.108), ((38,), 0.109, 0.49, 0.108), ((42,), 0.217, 0.49, 0.218),
    ((41,), 0.109, 0.49, 0.109), ((37,), 0.109, 0.49, 0.108), ((41,), 0.217, 0.49, 0.218), ((40,), 0.109, 0.49, 0.108),
    ((36,), 0.109, 0.49, 0.109), ((40,), 0.217, 0.49, 0.217), ((35,), 0.109, 0.49, 0.109), ((37,), 0.109, 0.49, 0.108),
    ((38,), 0.109, 0.49, 0.109), ((40,), 0.109, 0.49, 0.108), ((42,), 0.109, 0.49, 0.108), ((38,), 0.109, 0.49, 0.109),
    ((42,), 0.109, 0.49, 0.108), ((47,), 0.109, 0.49, 0.109), ((45,), 0.109, 0.49, 0.108), ((42,), 0.109, 0.49, 0.108),
    ((38,), 0.109, 0.49, 0.109), ((42,), 0.109, 0.49, 0.108), ((45,), 0.761, 0.49, 0.109), ((47,), 0.109, 0.49, 0.108),
    ((49,), 0.109, 0.49, 0.108), ((50,), 0.109, 0.49, 0.109), ((52,), 0.109, 0.49, 0.108), ((54,), 0.109, 0.49, 0.109),
    ((50,), 0.109, 0.49, 0.108), ((54,), 0.217, 0.49, 0.218), ((53,), 0.109, 0.49, 0.108), ((49,), 0.109, 0.49, 0.109),
    ((53,), 0.217, 0.49, 0.217), ((52,), 0.109, 0.49, 0.109), ((48,), 0.109, 0.49, 0.108), ((52,), 0.217, 0.49, 0.218),
    ((47,), 0.109, 0.49, 0.108), ((49,), 0.109, 0.49, 0.109), ((50,), 0.109, 0.49, 0.108), ((52,), 0.109, 0.49, 0.108),
    ((54,), 0.109, 0.49, 0.109), ((50,), 0.109, 0.49, 0.108), ((54,), 0.109, 0.49, 0.109), ((59,), 0.109, 0.49, 0.108),
    ((57,), 0.109, 0.49, 0.108), ((54,), 0.109, 0.49, 0.109), ((50,), 0.109, 0.49, 0.108), ((54,), 0.109, 0.49, 0.109),
    ((57,), 0.761, 0.49, 0.108), ((42,), 0.109, 0.49, 0.109), ((44,), 0.109, 0.49, 0.108), ((46,), 0.109, 0.49, 0.108),
    ((47,), 0.109, 0.49, 0.109), ((49,), 0.109, 0.49, 0.108), ((46,), 0.109, 0.49, 0.108), ((49,), 0.217, 0.49, 0.218),
    ((50,), 0.109, 0.49, 0.109), ((46,), 0.109, 0.49, 0.108), ((50,), 0.217, 0.49, 0.218), ((49,), 0.109, 0.49, 0.108),
    ((46,), 0.109, 0.49, 0.109), ((49,), 0.217, 0.49, 0.217), ((42,), 0.109, 0.49, 0.109), ((44,), 0.109, 0.49, 0.108),
    ((46,), 0.109, 0.49, 0.109), ((47,), 0.109, 0.49, 0.108), ((49,), 0.109, 0.49, 0.108), ((46,), 0.109, 0.49, 0.109),
    ((49,), 0.217, 0.49, 0.218), ((50,), 0.109, 0.49, 0.108), ((46,), 0.109, 0.49, 0.108), ((50,), 0.217, 0.49, 0.218),
    ((49,), 0.761, 0.49, 0.109), ((54,), 0.109, 0.49, 0.108), ((56,), 0.109, 0.49, 0.108), ((58,), 0.109, 0.49, 0.109),
    ((59,), 0.109, 0.49, 0.108), ((61,), 0.109, 0.49, 0.109), ((58,), 0.109, 0.49, 0.108), ((61,), 0.217, 0.49, 0.218),
    ((62,), 0.109, 0.49, 0.108), ((58,), 0.109, 0.49, 0.109), ((62,), 0.217, 0.49, 0.217), ((61,), 0.109, 0.49, 0.109),
    ((58,), 0.109, 0.49, 0.108), ((61,), 0.217, 0.49, 0.218), ((54,), 0.109, 0.49, 0.108), ((56,), 0.109, 0.49, 0.109),
    ((58,), 0.109, 0.49, 0.108), ((59,), 0.109, 0.49, 0.108), ((61,), 0.109, 0.49, 0.109), ((58,), 0.109, 0.49, 0.108),
    ((61,), 0.217, 0.49, 0.218), ((62,), 0.109, 0.49, 0.108), ((58,), 0.109, 0.49, 0.109), ((62,), 0.217, 0.49, 0.218),
    ((61,), 0.761, 0.49, 0.108), ((35,), 0.109, 0.49, 0.109), ((37,), 0.109, 0.49, 0.108), ((38,), 0.109, 0.49, 0.108),
    ((40,), 0.109, 0.49, 0.109), ((42,), 0.109, 0.49, 0.108), ((38,), 0.109, 0.49, 0.109), ((42,), 0.217, 0.49, 0.217),
    ((41,), 0.109, 0.49, 0.109), ((37,), 0.109, 0.49, 0.108), ((41,), 0.217, 0.49, 0.218), ((40,), 0.109, 0.49, 0.108),
    ((36,), 0.109, 0.49, 0.109), ((40,), 0.217, 0.49, 0.0),
]

# Extracted from mutopiaproject.org piece 1780 (Bach), "RH:1" track -- the
# famous opening flourish, the dramatic 3.75s pause, the chord entrance, and
# the ascending sequence that follows.
BACH_EVENTS = [
    ((69, 81), 0.5, 0.71, 0.125), ((67, 79), 0.062, 0.71, 0.001), ((65, 77), 0.062, 0.71, 0.0), ((64, 76), 0.062, 0.71, 0.0),
    ((62, 74), 0.062, 0.71, 0.001), ((61, 73), 0.125, 0.71, 0.0), ((62, 74), 0.25, 0.71, 0.75), ((69,), 0.5, 0.71, 0.125),
    ((64,), 0.125, 0.71, 0.0), ((65,), 0.125, 0.71, 0.0), ((61,), 0.125, 0.71, 0.0), ((62,), 0.25, 0.71, 3.75),
    ((58, 61, 64), 2.0, 0.71, 0.0), ((57, 62), 1.0, 0.71, 1.75), ((61,), 0.25, 0.71, 0.0), ((62,), 0.167, 0.71, 0.0),
    ((64,), 0.167, 0.71, 0.0), ((61,), 0.167, 0.71, 0.0), ((62,), 0.167, 0.71, 0.0), ((64,), 0.167, 0.71, 0.0),
    ((61,), 0.167, 0.71, 0.0), ((62,), 0.167, 0.71, 0.0), ((64,), 0.167, 0.71, 0.0), ((61,), 0.167, 0.71, 0.0),
    ((62,), 0.25, 0.71, 0.0), ((64,), 0.25, 0.71, 0.0), ((65,), 0.167, 0.71, 0.0), ((67,), 0.167, 0.71, 0.0),
    ((64,), 0.167, 0.71, 0.0), ((65,), 0.167, 0.71, 0.0), ((67,), 0.167, 0.71, 0.0), ((64,), 0.167, 0.71, 0.0),
    ((65,), 0.167, 0.71, 0.0), ((67,), 0.167, 0.71, 0.0), ((64,), 0.167, 0.71, 0.0), ((65,), 0.25, 0.71, 0.0),
    ((67,), 0.25, 0.71, 0.0), ((69,), 0.167, 0.71, 0.0), ((70,), 0.167, 0.71, 0.0), ((67,), 0.167, 0.71, 0.0),
    ((69,), 0.167, 0.71, 0.0), ((70,), 0.167, 0.71, 0.0), ((67,), 0.167, 0.71, 0.0), ((69,), 0.167, 0.71, 0.0),
    ((70,), 0.167, 0.71, 0.0), ((67,), 0.167, 0.71, 0.0), ((69,), 0.25, 0.71, 2.0), ((73,), 0.25, 0.71, 0.0),
    ((74,), 0.167, 0.71, 0.0), ((76,), 0.167, 0.71, 0.0), ((73,), 0.167, 0.71, 0.0), ((74,), 0.167, 0.71, 0.0),
    ((76,), 0.167, 0.71, 0.0), ((73,), 0.167, 0.71, 0.0), ((74,), 0.167, 0.71, 0.0), ((76,), 0.167, 0.71, 0.0),
    ((73,), 0.167, 0.71, 0.0), ((74,), 0.25, 0.71, 0.0), ((76,), 0.25, 0.71, 0.0), ((77,), 0.167, 0.71, 0.0),
    ((79,), 0.167, 0.71, 0.0), ((76,), 0.167, 0.71, 0.0), ((77,), 0.167, 0.71, 0.0), ((79,), 0.167, 0.71, 0.0),
    ((76,), 0.167, 0.71, 0.0), ((77,), 0.167, 0.71, 0.0), ((79,), 0.167, 0.71, 0.0), ((76,), 0.167, 0.71, 0.0),
    ((77,), 0.25, 0.71, 0.0), ((79,), 0.25, 0.71, 0.0), ((81,), 0.167, 0.71, 0.0), ((82,), 0.167, 0.71, 0.0),
    ((79,), 0.167, 0.71, 0.0), ((81,), 0.167, 0.71, 0.0), ((82,), 0.167, 0.71, 0.0), ((79,), 0.167, 0.71, 0.0),
    ((81,), 0.167, 0.71, 0.0), ((82,), 0.167, 0.71, 0.0), ((79,), 0.167, 0.71, 0.0), ((81,), 0.25, 0.71, 2.0),
    ((81,), 0.25, 0.71, 0.0), ((79,), 0.167, 0.71, 0.0), ((82,), 0.167, 0.71, 0.0), ((76,), 0.167, 0.71, 0.0),
    ((79,), 0.167, 0.71, 0.0), ((82,), 0.167, 0.71, 0.0), ((76,), 0.167, 0.71, 0.0), ((77,), 0.167, 0.71, 0.0),
    ((81,), 0.167, 0.71, 0.0), ((74,), 0.167, 0.71, 0.0), ((77,), 0.167, 0.71, 0.0), ((81,), 0.167, 0.71, 0.0),
    ((74,), 0.167, 0.71, 0.0), ((76,), 0.167, 0.71, 0.0), ((79,), 0.167, 0.71, 0.0), ((72,), 0.167, 0.71, 0.0),
    ((76,), 0.167, 0.71, 0.0), ((79,), 0.167, 0.71, 0.0), ((72,), 0.167, 0.71, 0.0), ((74,), 0.167, 0.71, 0.0),
    ((77,), 0.167, 0.71, 0.0), ((70,), 0.167, 0.71, 0.0), ((74,), 0.167, 0.71, 0.0), ((77,), 0.167, 0.71, 0.0),
    ((70,), 0.167, 0.71, 0.0), ((72,), 0.167, 0.71, 0.0),
]


def _normalize(samples, peak: float = 0.9) -> np.ndarray:
    arr = np.asarray(samples, dtype=np.float64)
    loudest = np.max(np.abs(arr)) if arr.size else 0.0
    if loudest == 0:
        return arr
    return arr * (peak / loudest)


def _wav_bytes(samples) -> io.BytesIO:
    arr = np.asarray(samples, dtype=np.float64)
    pcm = np.clip(arr * 32767, -32767, 32767).astype("<i2")
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        w.writeframes(pcm.tobytes())
    buf.seek(0)
    return buf


def midi_to_freq(note: int) -> float:
    return 440.0 * (2 ** ((note - 69) / 12))


def _simple_tone(freq: float, t: np.ndarray) -> np.ndarray:
    return np.sin(2 * np.pi * freq * t) + 0.25 * np.sin(2 * np.pi * freq * 2 * t)


def _ghost_tone(freq: float, t: np.ndarray) -> np.ndarray:
    """Fundamental plus an octave-up and a fifth-up overtone -- gives the
    tone presence in a register small speakers actually reproduce, instead
    of burying it in a sub-bass octave that goes inaudible on most hardware."""
    return (
        np.sin(2 * np.pi * freq * t)
        + 0.30 * np.sin(2 * np.pi * freq * 2 * t)
        + 0.14 * np.sin(2 * np.pi * freq * 1.5 * t)
    )


def _render_events(
    events: list[tuple[tuple[int, ...], float, float, float]],
    transpose: int,
    tone_fn,
    attack: float,
    release: float,
    gain: float,
    tremolo_rate: float = 0.0,
    tremolo_depth: float = 0.0,
    velocity_curve=None,
) -> np.ndarray:
    """Render a (pitches, duration, velocity, rest_after) event sequence into
    one sample array -- true silence for rests, chords summed from multiple
    simultaneous pitches. Vectorized with numpy: this runs at app startup, so
    a per-sample Python loop here would stall the fullscreen window for
    several seconds before it can draw its first frame."""
    total = sum(dur + rest for _, dur, _, rest in events) or 1.0
    elapsed = 0.0
    attack_n = max(1, int(attack * SAMPLE_RATE))
    release_n = max(1, int(release * SAMPLE_RATE))
    chunks: list[np.ndarray] = []
    for pitches, dur, vel, rest in events:
        n = int(SAMPLE_RATE * dur)
        if n > 0:
            idx = np.arange(n)
            t = idx / SAMPLE_RATE
            env = np.minimum(1, idx / attack_n) * np.minimum(1, (n - idx) / release_n)
            if tremolo_rate:
                env = env * (1 + tremolo_depth * np.sin(2 * np.pi * tremolo_rate * t))
            freqs = [midi_to_freq(p + transpose) for p in pitches]
            tone = sum(tone_fn(f, t) for f in freqs) / len(freqs)
            eff_vel = vel * (velocity_curve(elapsed / total) if velocity_curve else 1.0)
            chunks.append(env * eff_vel * gain * tone)
        rest_n = int(SAMPLE_RATE * rest)
        if rest_n > 0:
            chunks.append(np.zeros(rest_n))
        elapsed += dur + rest
    return np.concatenate(chunks) if chunks else np.array([])


def synth_mountain_king() -> io.BytesIO:
    """~33 seconds of Grieg's real melody line (see module docstring),
    transposed up two octaves into a bright register and given a gradual
    crescendo -- original synthesis, authentic notes and rhythm."""
    samples = _render_events(
        GRIEG_EVENTS,
        transpose=24,
        tone_fn=_simple_tone,
        attack=0.012,
        release=0.05,
        gain=0.55,
        velocity_curve=lambda p: 0.45 + 0.85 * p,
    )
    return _wav_bytes(_normalize(samples, peak=0.95))


def synth_failure_boom() -> io.BytesIO:
    dur = 1.3
    n = int(SAMPLE_RATE * dur)
    samples: list[float] = []
    for i in range(n):
        t = i / SAMPLE_RATE
        decay = math.exp(-t * 3.5)
        thump_freq = 150 - 110 * min(1, t / 0.4)
        thump = 0.7 * math.sin(2 * math.pi * thump_freq * t) * math.exp(-t * 8)
        noise = (random.random() * 2 - 1) * decay * 0.5
        samples.append(max(-1, min(1, thump + noise)))
    return _wav_bytes(samples)


def synth_fuse_hiss() -> io.BytesIO:
    """A sizzling, slowly intensifying hiss for the 2-second burning fuse --
    high-passed noise with occasional sparky crackles."""
    dur = 2.0
    n = int(SAMPLE_RATE * dur)
    samples: list[float] = []
    prev = 0.0
    for i in range(n):
        progress = i / n
        raw = random.random() * 2 - 1
        hp = raw - prev  # simple one-sample high-pass: emphasizes hiss, cuts rumble
        prev = raw
        spark = (random.random() * 2 - 1) * 0.6 if random.random() < 0.02 + 0.04 * progress else 0.0
        env = 0.5 + 0.5 * progress  # rises in intensity as the fuse burns down
        samples.append(env * (hp * 0.6 + spark))
    return _wav_bytes(_normalize(samples, peak=0.6))


def synth_thunder() -> io.BytesIO:
    """A rolling, roaring rumble -- low-passed noise plus sub-bass tones,
    swelling in then slowly decaying -- meant to layer under synth_failure_boom
    while the blast visual grows to fill the screen."""
    dur = 2.8
    n = int(SAMPLE_RATE * dur)
    samples: list[float] = []
    lp = 0.0
    alpha = 0.035  # one-pole low-pass coefficient; small = darker/rumblier noise
    for i in range(n):
        t = i / SAMPLE_RATE
        env = min(1, t / 0.4) * math.exp(-t * 0.55)
        noise = random.random() * 2 - 1
        lp += alpha * (noise - lp)
        low_tone = 0.5 * math.sin(2 * math.pi * 42 * t) + 0.3 * math.sin(2 * math.pi * 58 * t + 0.6)
        samples.append(env * (low_tone * 0.6 + lp * 3.0))
    return _wav_bytes(_normalize(samples))


QUARTER_REST_SECONDS = 1.0  # a quarter note at the piece's real tempo (60 BPM)


def _cap_long_rests(events, max_rest: float = QUARTER_REST_SECONDS):
    """Bach's real score has some long rests (including a famous 3.75s
    dramatic pause) -- fine for WAV playback, but long rests don't translate
    well through MIDI note-on/off timing and can confuse simple players.
    Shorten anything longer than a quarter note down to a quarter rest."""
    return [
        (pitches, dur, vel, min(rest, max_rest))
        for pitches, dur, vel, rest in events
    ]


def synth_ghost_bass() -> io.BytesIO:
    """~27 seconds of Bach's real opening passage (see module docstring) --
    including the famous flourish, chord entrance, and ascending sequence --
    transposed down an octave with a tremolo for a ghostly quality. Original
    synthesis, authentic notes and rhythm; long rests capped to a quarter
    rest (see _cap_long_rests)."""
    samples = _render_events(
        _cap_long_rests(BACH_EVENTS),
        transpose=-12,
        tone_fn=_ghost_tone,
        attack=0.02,
        release=0.07,
        gain=0.6,
        tremolo_rate=5.0,
        tremolo_depth=0.22,
    )
    return _wav_bytes(_normalize(samples, peak=0.97))


def load_sound(override_path: str | None, synth_fn) -> pygame.mixer.Sound:
    if override_path and os.path.isfile(override_path):
        return pygame.mixer.Sound(override_path)
    return pygame.mixer.Sound(synth_fn())


def _vlq(value: int) -> bytes:
    """MIDI variable-length quantity encoding."""
    out = [value & 0x7F]
    value >>= 7
    while value:
        out.insert(0, (value & 0x7F) | 0x80)
        value >>= 7
    return bytes(out)


def write_midi_file(
    path: str,
    events: list[tuple[tuple[int, ...], float, float, float]],
    transpose: int = 0,
    ppqn: int = 480,
    bpm: int = 120,
) -> None:
    """Write a single-track Standard MIDI File (format 0) built from a
    (pitches, duration_seconds, velocity 0-1, rest_after_seconds) event
    sequence -- the same schema as GRIEG_EVENTS/BACH_EVENTS. Chords (more
    than one pitch per event) become simultaneous note-on/off groups; rests
    become a delta-time gap before the next note-on, which is how MIDI
    represents silence (there's no explicit "rest" message)."""
    seconds_per_tick = (60.0 / bpm) / ppqn
    track = bytearray()

    micros_per_quarter = int(60_000_000 / bpm)
    track += _vlq(0) + bytes([0xFF, 0x51, 0x03]) + micros_per_quarter.to_bytes(3, "big")

    pending_ticks = 0
    for pitches, duration, velocity, rest in events:
        ticks = max(1, round(duration / seconds_per_tick))
        vel = max(1, min(127, int(velocity * 127)))
        for i, pitch in enumerate(pitches):
            track += _vlq(pending_ticks if i == 0 else 0) + bytes([0x90, pitch + transpose, vel])
        pending_ticks = 0
        for i, pitch in enumerate(pitches):
            track += _vlq(ticks if i == 0 else 0) + bytes([0x80, pitch + transpose, 0])
        pending_ticks += max(0, round(rest / seconds_per_tick))

    track += _vlq(pending_ticks) + bytes([0xFF, 0x2F, 0x00])  # end of track

    header = (
        b"MThd"
        + (6).to_bytes(4, "big")
        + (0).to_bytes(2, "big")  # format 0: single multi-channel track
        + (1).to_bytes(2, "big")  # ntrks
        + ppqn.to_bytes(2, "big")
    )
    track_chunk = b"MTrk" + len(track).to_bytes(4, "big") + bytes(track)

    with open(path, "wb") as f:
        f.write(header + track_chunk)


if __name__ == "__main__":
    os.makedirs(ASSETS_DIR, exist_ok=True)

    grieg_path = os.path.join(ASSETS_DIR, "mountain_king.mid")
    write_midi_file(grieg_path, GRIEG_EVENTS, transpose=24)
    print(f"Wrote {grieg_path}")

    bach_path = os.path.join(ASSETS_DIR, "toccata_fugue.mid")
    write_midi_file(bach_path, _cap_long_rests(BACH_EVENTS), transpose=-12, bpm=60)
    print(f"Wrote {bach_path}")

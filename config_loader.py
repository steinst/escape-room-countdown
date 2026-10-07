"""Load and validate config.toml for the escape-room countdown clock."""

import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path

DEFAULT_CONFIG_PATH = Path.home() / "escape-countdown" / "config.toml"
MIN_STOP_WORD_LENGTH = 3
DEFAULT_TAGLINE = "AFTENGIÐ SPRENGJUNA ÁÐUR EN TÍMINN RENNUR ÚT"
DEFAULT_TAGLINE_SUCCESS = "SPRENGJAN ER AFTENGD!"
DEFAULT_TAGLINE_FAILURE = "YKKUR MISTÓKST — ALLT ER SPRUNGIÐ!"


@dataclass
class Config:
    stop_word: str
    success_sound_path: str | None
    failure_sound_path: str | None
    tagline: str
    tagline_success: str
    tagline_failure: str


def load_config(path: str | None) -> Config:
    config_path = Path(path) if path else DEFAULT_CONFIG_PATH

    if not config_path.is_file():
        sys.exit(f"Config file not found: {config_path}")

    try:
        with config_path.open("rb") as f:
            data = tomllib.load(f)
    except tomllib.TOMLDecodeError as e:
        sys.exit(f"Could not parse config file {config_path}: {e}")

    stop_word = data.get("stop_word", "")
    if not isinstance(stop_word, str) or len(stop_word.strip()) < MIN_STOP_WORD_LENGTH:
        sys.exit(
            f"Config file {config_path} must set 'stop_word' to a string of at "
            f"least {MIN_STOP_WORD_LENGTH} characters."
        )

    sounds = data.get("sounds", {})
    success_path = sounds.get("success") or None
    failure_path = sounds.get("failure") or None
    tagline = data.get("tagline") or DEFAULT_TAGLINE
    tagline_success = data.get("tagline_success") or DEFAULT_TAGLINE_SUCCESS
    tagline_failure = data.get("tagline_failure") or DEFAULT_TAGLINE_FAILURE

    return Config(
        stop_word=stop_word.strip(),
        success_sound_path=success_path,
        failure_sound_path=failure_path,
        tagline=tagline,
        tagline_success=tagline_success,
        tagline_failure=tagline_failure,
    )

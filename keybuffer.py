"""Sliding-window stop-word matcher for raw keystroke capture."""

from collections import deque


class StopWordMatcher:
    def __init__(self, stop_word: str):
        self.target = stop_word.lower()
        self.buf: deque[str] = deque(maxlen=len(self.target))

    def feed(self, unicode_char: str) -> bool:
        """Call once per KEYDOWN with event.unicode. Returns True on match."""
        if not unicode_char or not unicode_char.isprintable():
            return False
        self.buf.append(unicode_char.lower())
        return len(self.buf) == self.buf.maxlen and "".join(self.buf) == self.target

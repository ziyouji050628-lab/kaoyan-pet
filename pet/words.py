"""Word bank: loads bundled words.json, or a user override in the data dir."""
import json
import random

from .paths import assets_dir, user_words_file

FALLBACK = [{"w": "abandon", "m": "v. 放弃；抛弃"}]


def _read(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None
    items = data.get("words") if isinstance(data, dict) else data
    if not isinstance(items, list):
        return None
    out = []
    for it in items:
        if isinstance(it, dict) and it.get("w") and it.get("m"):
            out.append({"w": str(it["w"]).strip(), "m": str(it["m"]).strip()})
    return out or None


class WordBank:
    """Serves words in shuffled order, cycling without repeats within a pass."""

    def __init__(self):
        self.words = (
            _read(user_words_file())
            or _read(assets_dir() / "words" / "words.json")
            or list(FALLBACK)
        )
        self._queue = []

    def next(self) -> dict:
        if not self._queue:
            self._queue = list(self.words)
            random.shuffle(self._queue)
        return self._queue.pop()

    def __len__(self):
        return len(self.words)

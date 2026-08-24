"""Settings + study stats persistence. Plain JSON, tolerant of missing/corrupt files."""
import json
from datetime import date

from .paths import settings_file, stats_file

DEFAULTS = {
    "pos": None,              # [x, y] or None for first-run default placement
    "scale": 0.38,            # pet render scale (frames are ~421x531)
    "fps": 12,                # idle animation frame rate
    "focus_minutes": 25,
    "break_minutes": 5,
    "word_interval_sec": 90,  # how often an unprompted word bubble appears
    "launch_at_login": False,
    "muted": False,
}


def _load_json(path, fallback):
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return dict(fallback)
        return data
    except (OSError, json.JSONDecodeError):
        return dict(fallback)


def _save_json(path, data):
    tmp = path.with_suffix(path.suffix + ".tmp")
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        tmp.replace(path)
    except OSError:
        pass


class Settings:
    def __init__(self):
        self._d = dict(DEFAULTS)
        self._d.update(_load_json(settings_file(), DEFAULTS))
        # drop unknown keys from older versions, keep defaults for new ones
        self._d = {k: self._d.get(k, v) for k, v in DEFAULTS.items()}

    def __getitem__(self, k):
        return self._d[k]

    def __setitem__(self, k, v):
        self._d[k] = v
        self.save()

    def get(self, k, default=None):
        return self._d.get(k, default)

    def save(self):
        _save_json(settings_file(), self._d)


class Stats:
    """Tracks focused-study seconds per calendar day."""

    def __init__(self):
        self._d = _load_json(stats_file(), {})

    def _today(self):
        return date.today().isoformat()

    def add_seconds(self, secs: int):
        k = self._today()
        self._d[k] = int(self._d.get(k, 0)) + int(secs)
        _save_json(stats_file(), self._d)

    def today_seconds(self) -> int:
        return int(self._d.get(self._today(), 0))

    def today_text(self) -> str:
        s = self.today_seconds()
        h, m = s // 3600, (s % 3600) // 60
        if h:
            return f"今日专注 {h} 小时 {m} 分"
        return f"今日专注 {m} 分钟"

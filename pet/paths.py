"""Resource and data path resolution, works both from source and PyInstaller bundle."""
import os
import sys
from pathlib import Path

APP_NAME = "KaoyanPet"

IS_WINDOWS = sys.platform.startswith("win")
IS_MAC = sys.platform == "darwin"


def resource_root() -> Path:
    """Read-only bundled assets (frames, fonts, default word bank)."""
    if getattr(sys, "frozen", False):
        # PyInstaller puts --add-data payload in _MEIPASS
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent


def assets_dir() -> Path:
    return resource_root() / "assets"


def frames_dir(state: str = "idle") -> Path:
    return assets_dir() / "frames" / state


def font_path() -> Path:
    return assets_dir() / "fonts" / "pet-font.ttf"


def data_dir() -> Path:
    """Per-user writable dir for settings and study stats."""
    if IS_WINDOWS:
        base = os.environ.get("APPDATA")
        d = Path(base) / APP_NAME if base else Path.home() / f".{APP_NAME}"
    elif IS_MAC:
        d = Path.home() / "Library" / "Application Support" / APP_NAME
    else:
        base = os.environ.get("XDG_CONFIG_HOME")
        d = (Path(base) if base else Path.home() / ".config") / APP_NAME
    d.mkdir(parents=True, exist_ok=True)
    return d


def settings_file() -> Path:
    return data_dir() / "settings.json"


def stats_file() -> Path:
    return data_dir() / "stats.json"


def user_words_file() -> Path:
    """Optional user-supplied word bank; overrides bundled one if present."""
    return data_dir() / "words.json"

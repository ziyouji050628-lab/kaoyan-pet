"""Launch-at-login. Windows: HKCU Run registry key. macOS: LaunchAgent plist."""
import plistlib
import subprocess
import sys
from pathlib import Path

from .paths import IS_MAC, IS_WINDOWS

LABEL = "com.local.kaoyanpet"
RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
RUN_NAME = "KaoyanPet"


# ---------------------------------------------------------------- shared
def _launch_command() -> list[str]:
    """The command that starts this app, however it's currently running."""
    if getattr(sys, "frozen", False):
        exe = Path(sys.executable).resolve()
        if IS_MAC:
            # inside Foo.app/Contents/MacOS/Foo -> open the .app bundle
            app = exe.parent.parent.parent
            if app.suffix == ".app":
                return ["/usr/bin/open", "-a", str(app)]
        return [str(exe)]

    main = Path(__file__).resolve().parent.parent / "main.py"
    exe = sys.executable
    if IS_WINDOWS:
        # pythonw.exe runs without a console window
        pythonw = Path(exe).with_name("pythonw.exe")
        if pythonw.exists():
            exe = str(pythonw)
    return [exe, str(main)]


# kept for the test suite / older callers
def _program_args() -> list[str]:
    return _launch_command()


def _quote(args: list[str]) -> str:
    return " ".join(f'"{a}"' if " " in a else a for a in args)


# ---------------------------------------------------------------- windows
def _win_is_enabled() -> bool:
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as k:
            winreg.QueryValueEx(k, RUN_NAME)
        return True
    except (FileNotFoundError, OSError):
        return False


def _win_set(enabled: bool) -> tuple[bool, str]:
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0,
                            winreg.KEY_SET_VALUE) as k:
            if enabled:
                winreg.SetValueEx(k, RUN_NAME, 0, winreg.REG_SZ,
                                  _quote(_launch_command()))
                return True, "已开启开机自启"
            try:
                winreg.DeleteValue(k, RUN_NAME)
            except FileNotFoundError:
                pass
            return True, "已关闭开机自启"
    except OSError as e:
        return False, f"设置失败：{e}"


# ---------------------------------------------------------------- macos
def plist_path() -> Path:
    return Path.home() / "Library" / "LaunchAgents" / f"{LABEL}.plist"


def _mac_set(enabled: bool) -> tuple[bool, str]:
    p = plist_path()
    try:
        if enabled:
            p.parent.mkdir(parents=True, exist_ok=True)
            with open(p, "wb") as f:
                plistlib.dump({
                    "Label": LABEL,
                    "ProgramArguments": _launch_command(),
                    "RunAtLoad": True,
                    "ProcessType": "Interactive",
                }, f)
            subprocess.run(["launchctl", "unload", str(p)],
                           capture_output=True, check=False)
            subprocess.run(["launchctl", "load", str(p)],
                           capture_output=True, check=False)
            return True, "已开启开机自启"
        if p.exists():
            subprocess.run(["launchctl", "unload", str(p)],
                           capture_output=True, check=False)
            p.unlink()
        return True, "已关闭开机自启"
    except OSError as e:
        return False, f"设置失败：{e}"


# ---------------------------------------------------------------- api
def is_supported() -> bool:
    return IS_WINDOWS or IS_MAC


def is_enabled() -> bool:
    if IS_WINDOWS:
        return _win_is_enabled()
    if IS_MAC:
        return plist_path().exists()
    return False


def set_enabled(enabled: bool) -> tuple[bool, str]:
    if IS_WINDOWS:
        return _win_set(enabled)
    if IS_MAC:
        return _mac_set(enabled)
    return False, "当前系统不支持开机自启"

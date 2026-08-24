"""Build a standalone app: .exe on Windows, .app on macOS.

Usage:
    python build.py

Output lands in dist/.
"""
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
IS_WINDOWS = sys.platform.startswith("win")
IS_MAC = sys.platform == "darwin"
APP_NAME = "KaoyanPet"
SEP = ";" if IS_WINDOWS else ":"   # PyInstaller --add-data separator differs


def main():
    if not (IS_WINDOWS or IS_MAC):
        print("This script supports Windows and macOS only.")
        return 1

    try:
        import PyInstaller  # noqa: F401
    except ImportError:
        print("PyInstaller not installed. Run:  pip install pyinstaller PyQt6")
        return 1

    assets = ROOT / "assets"
    if not (assets / "fonts" / "pet-font.ttf").exists():
        print("Missing assets/fonts/pet-font.ttf")
        return 1

    frames = assets / "frames" / "idle"
    frame_count = len([p for p in frames.glob("*") if p.suffix.lower() in (".png", ".webp")]) \
        if frames.is_dir() else 0
    if frame_count == 0:
        print("! No frames in assets/frames/idle — packaging with the placeholder pet.")
    else:
        print(f"  {frame_count} idle frames found.")

    for d in ("build", "dist"):
        shutil.rmtree(ROOT / d, ignore_errors=True)

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm", "--clean",
        "--windowed",                       # no console window
        "--name", APP_NAME,
        "--add-data", f"{assets}{SEP}assets",
        "--osx-bundle-identifier", "com.local.kaoyanpet",
    ]

    icon_ico = ROOT / "assets" / "icon.ico"
    icon_icns = ROOT / "assets" / "icon.icns"
    if IS_WINDOWS and icon_ico.exists():
        cmd += ["--icon", str(icon_ico)]
    elif IS_MAC and icon_icns.exists():
        cmd += ["--icon", str(icon_icns)]

    if IS_WINDOWS:
        cmd.append("--onefile")             # single portable .exe
    cmd.append(str(ROOT / "main.py"))

    print("Building...")
    result = subprocess.run(cmd, cwd=ROOT)
    if result.returncode != 0:
        print("Build failed.")
        return result.returncode

    if IS_WINDOWS:
        out = ROOT / "dist" / f"{APP_NAME}.exe"
        print(f"\nDone: {out}")
        print("Copy this single .exe anywhere. No install needed.")
        print("SmartScreen may warn on first run: More info -> Run anyway.")
    else:
        out = ROOT / "dist" / f"{APP_NAME}.app"
        print(f"\nDone: {out}")
        print("Unsigned: first launch needs right-click -> Open.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

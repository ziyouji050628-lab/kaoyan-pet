"""Headless smoke test: exercises real widgets on the offscreen Qt platform."""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtCore import QPoint, QTimer  # noqa: E402
from PyQt6.QtWidgets import QApplication  # noqa: E402

from pet.bubble import Bubble  # noqa: E402
from pet.frames import load_frames, placeholder_frames  # noqa: E402
from pet.paths import font_path, settings_file, stats_file  # noqa: E402
from pet.pomodoro import Phase, Pomodoro  # noqa: E402
from pet.store import Settings, Stats  # noqa: E402
from pet.window import PetWindow  # noqa: E402
from pet.words import WordBank  # noqa: E402

failures = []


def check(label, cond, detail=""):
    if cond:
        print(f"  ok   {label}")
    else:
        print(f"  FAIL {label} {detail}")
        failures.append(label)


app = QApplication(sys.argv)

print("paths & font")
check("font bundled", font_path().exists(), str(font_path()))
from PyQt6.QtGui import QFontDatabase
fid = QFontDatabase.addApplicationFont(str(font_path()))
fams = QFontDatabase.applicationFontFamilies(fid) if fid != -1 else []
check("font loads in Qt", bool(fams), f"id={fid}")
print(f"       family = {fams[0] if fams else 'N/A'}")

print("word bank")
wb = WordBank()
check("word count >= 300", len(wb) >= 300, f"got {len(wb)}")
seen = [wb.next()["w"] for _ in range(len(wb))]
check("full cycle no repeats", len(set(seen)) == len(wb), f"{len(set(seen))}/{len(wb)}")
check("cycle refills", wb.next() is not None)

print("frames")
ph = placeholder_frames()
check("placeholder frames built", len(ph) == 8 and not ph[0].isNull())
real = load_frames("idle")
HAS_ART = bool(real)
if HAS_ART:
    check("real frames load", len(real) >= 2, f"{len(real)} frames")
    sizes = {(f.width(), f.height()) for f in real}
    check("all frames same size", len(sizes) == 1, str(sizes))
    check("frames have alpha", real[0].hasAlphaChannel())
    print(f"       {len(real)} frames @ {real[0].width()}x{real[0].height()}")
else:
    check("no art yet -> placeholder path", real == [])

print("settings & stats")
s = Settings()
check("defaults present", s["focus_minutes"] == 25 and s["fps"] == 12)
s["focus_minutes"] = 1
check("persists", Settings()["focus_minutes"] == 1)
s["focus_minutes"] = 25

st = Stats()
before = st.today_seconds()
st.add_seconds(120)
check("stats accumulate", Stats().today_seconds() == before + 120)
check("stats text", "分" in st.today_text(), st.today_text())

print("pomodoro")
pomo = Pomodoro(s, st)
check("starts idle", pomo.phase is Phase.IDLE and not pomo.running)
pomo.start_focus()
check("focus running", pomo.phase is Phase.FOCUS and pomo.running)
check("remaining format", pomo.remaining_text() == "25:00", pomo.remaining_text())
pomo.pause()
check("pause stops", not pomo.running and pomo.phase is Phase.FOCUS)
pomo.resume()
check("resume restarts", pomo.running)
pomo.stop()
check("stop -> idle", pomo.phase is Phase.IDLE and not pomo.running)

# drive a 1-second focus to completion, verify signal + stats flush
s["focus_minutes"] = 1
fired = {"focus": False}
pomo.finished_focus.connect(lambda: fired.__setitem__("focus", True))
pomo.start_focus()
pomo._remaining = 1  # fast-forward instead of waiting 60s
base = Stats().today_seconds()
loop_done = {"v": False}
QTimer.singleShot(1400, lambda: loop_done.__setitem__("v", True))
while not loop_done["v"]:
    app.processEvents()
check("focus completion signal", fired["focus"])
check("focus flushed to stats", Stats().today_seconds() >= base + 1,
      f"{Stats().today_seconds()} vs {base}")
pomo.stop()
s["focus_minutes"] = 25

print("bubble")
b = Bubble(fams[0] if fams else "Helvetica")
b.set_word("abandon", "v. 放弃；抛弃")
w1, h1 = b.width(), b.height()
check("sized to content", w1 > 60 and h1 > 40, f"{w1}x{h1}")
check("hint shown pre-reveal", b._lines()[1][0] == "点一下看释义")
check("reveal consumes click", b.reveal() is True)
check("meaning shown", b._lines()[1][0] == "v. 放弃；抛弃")
check("second reveal is no-op", b.reveal() is False)
b.set_message("开始专注，我陪你")
check("message needs no reveal", b.reveal() is False)
b.show()
b.repaint()   # would raise if paintEvent is broken
check("paints without error", True)

print("pet window")
pw = PetWindow(s)
check("has frames", len(pw._frames) > 0)
check("sized to frame", pw.width() > 0 and pw.height() > 0, f"{pw.width()}x{pw.height()}")
check("using placeholder flag", pw.using_placeholder is (not HAS_ART))
check("pet render size sane", 100 < pw.height() < 400, f"{pw.width()}x{pw.height()}")
pw.show()
pw.repaint()
check("pet paints", True)

pw.move(400, 400)
pw.save_position()
check("position saved", Settings()["pos"] == [400, 400], str(Settings()["pos"]))

pw._go_to_sleep()
check("sleeps", pw.sleeping)
pw.wake()
check("wakes", not pw.sleeping)

s["scale"] = 0.5
half = int(pw._frames_raw[0].width() * 0.5)
pw.apply_settings()
check("scale applied", abs(pw._frames[0].width() - half) <= 1,
      f"{pw._frames[0].width()} vs {half}")
s["scale"] = 0.38
pw.apply_settings()

print("app controller")
from pet.app import PetApp, _tray_icon  # noqa: E402
check("tray icon builds", not _tray_icon().isNull())

pa = PetApp(app)
check("controller constructs", pa.pet is not None and pa.bubble is not None)
pa.show_random_word()
check("word bubble visible", pa.bubble.isVisible())
pa.reposition_bubble()
check("bubble positioned", pa.bubble.x() != 0 or pa.bubble.y() != 0)
pa.on_pet_clicked()
check("pet click reveals", pa.bubble._revealed)
pa.hide_bubble()
check("bubble hides", not pa.bubble.isVisible())
pa._rebuild_menu()
check("menu builds", len(pa.menu.actions()) > 5, f"{len(pa.menu.actions())} actions")
pa.toggle_visible()
check("hides pet", not pa.pet.isVisible())
pa.toggle_visible()
check("shows pet", pa.pet.isVisible())
pa.toggle_pomodoro()
check("pomodoro starts from menu", pa.pomodoro.phase is Phase.FOCUS)
pa.pomodoro.stop()

print("autostart (dry, no launchctl)")
from pet import autostart  # noqa: E402
args = autostart._program_args()
check("program args sane", len(args) >= 2 and args[0], str(args))

print()
if failures:
    print(f"{len(failures)} FAILED: {failures}")
    sys.exit(1)
print("all checks passed")
sys.exit(0)

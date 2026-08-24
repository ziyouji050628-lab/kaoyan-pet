"""App controller: wires pet window, bubble, pomodoro, tray and settings together."""
import random

from PyQt6.QtCore import QPoint, QTimer, Qt
from PyQt6.QtGui import (QAction, QColor, QFontDatabase, QIcon, QPainter, QPen,
                         QPixmap)
from PyQt6.QtWidgets import QApplication, QMenu, QMessageBox, QSystemTrayIcon

from . import autostart
from .bubble import Bubble
from .paths import IS_MAC, font_path
from .pomodoro import Phase, Pomodoro
from .settings_dialog import SettingsDialog
from .store import Settings, Stats
from .window import PetWindow
from .words import WordBank

BUBBLE_MS = 9000        # how long an unprompted word stays up
BUBBLE_REVEALED_MS = 7000
NOTICE_MS = 6000
GAP = 8                 # px between bubble and pet


def _load_font() -> str:
    fp = font_path()
    if fp.exists():
        fid = QFontDatabase.addApplicationFont(str(fp))
        fams = QFontDatabase.applicationFontFamilies(fid) if fid != -1 else []
        if fams:
            return fams[0]
    return QApplication.font().family()


def _tray_icon() -> QIcon:
    pm = QPixmap(22, 22)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    # macOS template icons are monochrome; Windows/Linux trays need real color
    body = QColor(70, 70, 80) if IS_MAC else QColor(255, 145, 170)
    p.setBrush(body)
    p.setPen(QPen(body, 1))
    p.drawRoundedRect(3, 4, 16, 14, 5, 5)
    p.setBrush(QColor(255, 255, 255))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawEllipse(7, 9, 3, 3)
    p.drawEllipse(13, 9, 3, 3)
    p.end()
    icon = QIcon(pm)
    if IS_MAC:
        icon.setIsMask(True)   # adapts to light/dark menu bar
    return icon


class PetApp:
    def __init__(self, app: QApplication):
        self.app = app
        self.settings = Settings()
        self.stats = Stats()
        self.words = WordBank()
        self.font_family = _load_font()

        self.pet = PetWindow(self.settings)
        self.bubble = Bubble(self.font_family)
        self.pomodoro = Pomodoro(self.settings, self.stats)

        self.pet.clicked.connect(self.on_pet_clicked)
        self.pet.double_clicked.connect(self.open_settings)
        self.pet.context_requested.connect(self.show_menu)
        self.pet.moved.connect(self.reposition_bubble)

        self.pomodoro.phase_changed.connect(self.on_phase_changed)
        self.pomodoro.tick.connect(self.on_tick)
        self.pomodoro.finished_focus.connect(self.on_focus_done)
        self.pomodoro.finished_break.connect(self.on_break_done)

        self._hide_timer = QTimer()
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self.hide_bubble)

        self._word_timer = QTimer()
        self._word_timer.timeout.connect(self.show_random_word)

        self.bubble.dismissed.connect(self._restart_word_timer)

        self._build_tray()
        self.pet.show()
        self._restart_word_timer()

        if self.pet.using_placeholder:
            QTimer.singleShot(600, lambda: self.notice("占位形象：把帧放进 assets/frames/idle"))

    # ---------- tray ----------
    def _build_tray(self):
        self.tray = QSystemTrayIcon(_tray_icon())
        self.tray.setToolTip("考研桌宠")
        self.menu = QMenu()
        self._rebuild_menu()
        self.tray.setContextMenu(self.menu)
        self.tray.activated.connect(self._on_tray_activated)
        self.tray.show()

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.toggle_visible()

    def _rebuild_menu(self):
        self.menu.clear()

        running = self.pomodoro.running
        phase = self.pomodoro.phase
        if phase is Phase.IDLE:
            label = "开始专注"
        elif phase is Phase.FOCUS:
            label = f"暂停专注 {self.pomodoro.remaining_text()}" if running else f"继续专注 {self.pomodoro.remaining_text()}"
        else:
            label = f"休息中 {self.pomodoro.remaining_text()}"
        act = QAction(label, self.menu)
        act.triggered.connect(self.toggle_pomodoro)
        self.menu.addAction(act)

        if phase is not Phase.IDLE:
            stop = QAction("结束当前计时", self.menu)
            stop.triggered.connect(self.pomodoro.stop)
            self.menu.addAction(stop)

        self.menu.addSeparator()

        word = QAction("背一个单词", self.menu)
        word.triggered.connect(self.show_random_word)
        self.menu.addAction(word)

        stats = QAction(self.stats.today_text(), self.menu)
        stats.setEnabled(False)
        self.menu.addAction(stats)

        self.menu.addSeparator()

        vis = QAction("隐藏桌宠" if self.pet.isVisible() else "显示桌宠", self.menu)
        vis.triggered.connect(self.toggle_visible)
        self.menu.addAction(vis)

        st = QAction("设置…", self.menu)
        st.triggered.connect(self.open_settings)
        self.menu.addAction(st)

        self.menu.addSeparator()
        quit_act = QAction("退出", self.menu)
        quit_act.triggered.connect(self.quit)
        self.menu.addAction(quit_act)

    def show_menu(self, global_pos: QPoint):
        self._rebuild_menu()
        self.menu.popup(global_pos)

    # ---------- bubble ----------
    def reposition_bubble(self):
        if not self.bubble.isVisible():
            return
        pet_geo = self.pet.frameGeometry()
        screen = (self.pet.screen() or QApplication.primaryScreen()).availableGeometry()

        x = pet_geo.left() - 20
        y = pet_geo.top() - self.bubble.height() - GAP
        if y < screen.top():                      # no room above -> below
            y = pet_geo.bottom() + GAP
        x = max(screen.left() + 4, min(x, screen.right() - self.bubble.width() - 4))
        self.bubble.move(x, y)

    def _show_bubble(self, ms: int):
        self.bubble.show()
        self.reposition_bubble()
        self.bubble.raise_()
        self._hide_timer.start(ms)

    def hide_bubble(self):
        self.bubble.hide()

    def notice(self, text: str):
        self.bubble.set_message(text)
        self._show_bubble(NOTICE_MS)

    def show_random_word(self):
        if not self.pet.isVisible():
            return
        w = self.words.next()
        self.bubble.set_word(w["w"], w["m"])
        self._show_bubble(BUBBLE_MS)

    def _restart_word_timer(self):
        interval = max(10, int(self.settings["word_interval_sec"])) * 1000
        self._word_timer.start(interval)

    # ---------- interactions ----------
    def on_pet_clicked(self):
        # if a word is up and unrevealed, clicking the pet reveals it too
        if self.bubble.isVisible() and self.bubble.reveal():
            self.reposition_bubble()
            self._hide_timer.start(BUBBLE_REVEALED_MS)
            return
        self.show_random_word()

    def on_phase_changed(self, _phase):
        self._rebuild_menu()

    def on_tick(self, _remaining):
        # keep the menu label fresh only while it's open
        if self.menu.isVisible():
            self._rebuild_menu()

    def toggle_pomodoro(self):
        self.pomodoro.toggle()
        phase = self.pomodoro.phase
        if phase is Phase.FOCUS:
            self.notice("开始专注，我陪你" if self.pomodoro.running else "先歇会儿，随时继续")
        self._rebuild_menu()

    def on_focus_done(self):
        self.notice(f"一轮结束！{self.stats.today_text()}")
        self._beep()
        self.pomodoro.start_break()

    def on_break_done(self):
        self.notice("休息结束，继续背单词")
        self._beep()
        self._rebuild_menu()

    def _beep(self):
        if self.settings["muted"]:
            return
        QApplication.beep()

    def toggle_visible(self):
        if self.pet.isVisible():
            self.pet.hide()
            self.hide_bubble()
        else:
            self.pet.show()
            self.pet.wake()
        self._rebuild_menu()

    def open_settings(self):
        prev_autostart = bool(self.settings["launch_at_login"])
        dlg = SettingsDialog(self.settings, self.stats, self.font_family)
        dlg.changed.connect(lambda: self._apply_settings(prev_autostart))
        dlg.exec()

    def _apply_settings(self, prev_autostart: bool):
        self.pet.apply_settings()
        self._restart_word_timer()
        now = bool(self.settings["launch_at_login"])
        if now != prev_autostart:
            ok, msg = autostart.set_enabled(now)
            if not ok:
                QMessageBox.warning(None, "考研桌宠", msg)
                self.settings["launch_at_login"] = prev_autostart
            else:
                self.notice(msg)
        self._rebuild_menu()

    def quit(self):
        self.pomodoro.pause()
        self.pet.save_position()
        self.tray.hide()
        self.app.quit()

"""Pomodoro timer: focus/break cycles, emits state changes and accumulates study time."""
from enum import Enum

from PyQt6.QtCore import QObject, QTimer, pyqtSignal


class Phase(Enum):
    IDLE = "idle"
    FOCUS = "focus"
    BREAK = "break"


class Pomodoro(QObject):
    phase_changed = pyqtSignal(object)   # Phase
    tick = pyqtSignal(int)               # remaining seconds
    finished_focus = pyqtSignal()
    finished_break = pyqtSignal()

    def __init__(self, settings, stats, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.stats = stats
        self.phase = Phase.IDLE
        self._remaining = 0
        self._accum = 0  # focused seconds not yet flushed to stats

        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self._on_tick)

    # --- state queries ---
    @property
    def running(self) -> bool:
        return self._timer.isActive()

    def remaining(self) -> int:
        return self._remaining

    def remaining_text(self) -> str:
        m, s = divmod(max(0, self._remaining), 60)
        return f"{m:02d}:{s:02d}"

    # --- control ---
    def start_focus(self):
        self._remaining = max(1, int(self.settings["focus_minutes"])) * 60
        self._set_phase(Phase.FOCUS)
        self._timer.start()

    def start_break(self):
        self._remaining = max(1, int(self.settings["break_minutes"])) * 60
        self._set_phase(Phase.BREAK)
        self._timer.start()

    def pause(self):
        if self._timer.isActive():
            self._timer.stop()
            self._flush()

    def resume(self):
        if self.phase is not Phase.IDLE and not self._timer.isActive():
            self._timer.start()

    def toggle(self):
        if self.phase is Phase.IDLE:
            self.start_focus()
        elif self._timer.isActive():
            self.pause()
        else:
            self.resume()

    def stop(self):
        self._timer.stop()
        self._flush()
        self._remaining = 0
        self._set_phase(Phase.IDLE)

    # --- internals ---
    def _set_phase(self, phase: Phase):
        if phase is not self.phase:
            self.phase = phase
            self.phase_changed.emit(phase)

    def _flush(self):
        if self._accum:
            self.stats.add_seconds(self._accum)
            self._accum = 0

    def _on_tick(self):
        self._remaining -= 1
        if self.phase is Phase.FOCUS:
            self._accum += 1
            if self._accum >= 60:
                self._flush()
        self.tick.emit(self._remaining)

        if self._remaining <= 0:
            self._timer.stop()
            self._flush()
            if self.phase is Phase.FOCUS:
                self._set_phase(Phase.IDLE)
                self.finished_focus.emit()
            else:
                self._set_phase(Phase.IDLE)
                self.finished_break.emit()

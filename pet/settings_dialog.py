"""Settings panel."""
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (QCheckBox, QDialog, QDoubleSpinBox, QFormLayout,
                             QHBoxLayout, QLabel, QPushButton, QSpinBox, QVBoxLayout)

from . import autostart as autostart_mod


class SettingsDialog(QDialog):
    changed = pyqtSignal()

    def __init__(self, settings, stats, font_family, parent=None):
        super().__init__(parent)
        self.setWindowTitle("桌宠设置")
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        self.settings = settings
        self.stats = stats

        form = QFormLayout()

        self.focus = QSpinBox()
        self.focus.setRange(1, 180)
        self.focus.setValue(int(settings["focus_minutes"]))
        self.focus.setSuffix(" 分钟")
        form.addRow("专注时长", self.focus)

        self.brk = QSpinBox()
        self.brk.setRange(1, 60)
        self.brk.setValue(int(settings["break_minutes"]))
        self.brk.setSuffix(" 分钟")
        form.addRow("休息时长", self.brk)

        self.interval = QSpinBox()
        self.interval.setRange(10, 3600)
        self.interval.setSingleStep(10)
        self.interval.setValue(int(settings["word_interval_sec"]))
        self.interval.setSuffix(" 秒")
        form.addRow("单词间隔", self.interval)

        self.fps = QSpinBox()
        self.fps.setRange(1, 60)
        self.fps.setValue(int(settings["fps"]))
        form.addRow("动画帧率", self.fps)

        self.scale = QDoubleSpinBox()
        self.scale.setRange(0.3, 3.0)
        self.scale.setSingleStep(0.1)
        self.scale.setValue(float(settings["scale"]))
        form.addRow("宠物大小", self.scale)

        self.muted = QCheckBox("静音提醒")
        self.muted.setChecked(bool(settings["muted"]))
        form.addRow("", self.muted)

        self.autostart = QCheckBox("开机自动启动")
        self.autostart.setChecked(bool(settings["launch_at_login"]))
        if not autostart_mod.is_supported():
            self.autostart.setEnabled(False)
            self.autostart.setToolTip("当前系统不支持")
        form.addRow("", self.autostart)

        root = QVBoxLayout(self)
        root.addLayout(form)

        self.stats_label = QLabel(stats.today_text())
        self.stats_label.setStyleSheet("color:#777;")
        root.addWidget(self.stats_label)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        cancel = QPushButton("取消")
        cancel.clicked.connect(self.reject)
        ok = QPushButton("保存")
        ok.setDefault(True)
        ok.clicked.connect(self._save)
        buttons.addWidget(cancel)
        buttons.addWidget(ok)
        root.addLayout(buttons)

    def _save(self):
        s = self.settings
        s._d.update({
            "focus_minutes": self.focus.value(),
            "break_minutes": self.brk.value(),
            "word_interval_sec": self.interval.value(),
            "fps": self.fps.value(),
            "scale": round(self.scale.value(), 2),
            "muted": self.muted.isChecked(),
            "launch_at_login": self.autostart.isChecked(),
        })
        s.save()
        self.changed.emit()
        self.accept()

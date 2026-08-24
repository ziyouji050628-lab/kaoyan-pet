"""Frameless speech bubble: shows a word, reveals its meaning on click."""
from PyQt6.QtCore import QRectF, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import QWidget

PAD_X, PAD_Y = 16, 12
TAIL_H = 10
RADIUS = 14
MAX_W = 340


class Bubble(QWidget):
    """Click to reveal meaning; click again (or auto-timeout) to dismiss."""

    dismissed = pyqtSignal()

    def __init__(self, font_family: str, parent=None):
        super().__init__(parent, Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint
                         | Qt.WindowType.WindowStaysOnTopHint
                         | Qt.WindowType.NoDropShadowWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

        self._family = font_family
        self._word = ""
        self._meaning = ""
        self._revealed = False
        self._hint = "点一下看释义"

    def set_word(self, word: str, meaning: str):
        self._word = word
        self._meaning = meaning
        self._revealed = False
        self._relayout()

    def set_message(self, text: str):
        """Plain message with no reveal step (pomodoro notices)."""
        self._word = text
        self._meaning = ""
        self._revealed = True
        self._relayout()

    def reveal(self) -> bool:
        """Returns True if this click consumed the reveal step."""
        if self._meaning and not self._revealed:
            self._revealed = True
            self._relayout()
            return True
        return False

    def _fonts(self):
        big = QFont(self._family, 20)
        small = QFont(self._family, 13)
        return big, small

    def _lines(self):
        if self._revealed and self._meaning:
            return [(self._word, 0), (self._meaning, 1)]
        return [(self._word, 0), (self._hint, 1)]

    def _relayout(self):
        big, small = self._fonts()
        fm_big = self.fontMetrics_for(big)
        fm_small = self.fontMetrics_for(small)

        w = 0
        h = 0
        for text, kind in self._lines():
            fm = fm_big if kind == 0 else fm_small
            w = max(w, min(MAX_W, fm.horizontalAdvance(text)))
            h += fm.height() + 2

        self.resize(w + PAD_X * 2, h + PAD_Y * 2 + TAIL_H)
        self.update()

    def fontMetrics_for(self, font: QFont):
        from PyQt6.QtGui import QFontMetrics
        return QFontMetrics(font)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        body = QRectF(0, 0, self.width(), self.height() - TAIL_H)
        path = QPainterPath()
        path.addRoundedRect(body, RADIUS, RADIUS)
        # tail pointing down-left toward the pet
        tail_x = min(34.0, body.width() / 2)
        path.moveTo(tail_x, body.bottom() - 1)
        path.lineTo(tail_x + 9, body.bottom() + TAIL_H)
        path.lineTo(tail_x + 20, body.bottom() - 1)
        path.closeSubpath()

        p.setBrush(QColor(255, 255, 255, 246))
        p.setPen(QPen(QColor(120, 110, 120, 90), 1.4))
        p.drawPath(path)

        big, small = self._fonts()
        y = PAD_Y
        for text, kind in self._lines():
            font = big if kind == 0 else small
            p.setFont(font)
            if kind == 0:
                p.setPen(QColor(40, 35, 45))
            else:
                p.setPen(QColor(150, 145, 155) if not self._revealed else QColor(90, 85, 100))
            fm = self.fontMetrics_for(font)
            rect = QRectF(PAD_X, y, self.width() - PAD_X * 2, fm.height())
            p.drawText(rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, text)
            y += fm.height() + 2
        p.end()

    def mousePressEvent(self, e):
        if not self.reveal():
            self.hide()
            self.dismissed.emit()
        e.accept()

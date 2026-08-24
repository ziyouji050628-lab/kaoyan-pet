"""Frame-sequence loader with placeholder fallback when no art is present yet."""
from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QColor, QPainter, QPen, QPixmap

from .paths import frames_dir

EXTS = (".png", ".webp")


def _numeric_key(p):
    """Sort idle_2.png before idle_10.png."""
    digits = "".join(ch for ch in p.stem if ch.isdigit())
    return (int(digits) if digits else 0, p.stem)


def load_frames(state: str = "idle") -> list[QPixmap]:
    d = frames_dir(state)
    if not d.is_dir():
        return []
    files = sorted(
        (p for p in d.iterdir() if p.suffix.lower() in EXTS and not p.name.startswith(".")),
        key=_numeric_key,
    )
    frames = []
    for p in files:
        pm = QPixmap(str(p))
        if not pm.isNull():
            frames.append(pm)
    return frames


def placeholder_frames(size: QSize = QSize(160, 160), count: int = 8) -> list[QPixmap]:
    """Breathing rounded square, so window/drag/bubble logic is testable pre-art."""
    frames = []
    for i in range(count):
        # simple ease in/out so the pulse doesn't look linear
        t = i / max(1, count - 1)
        pulse = 1.0 - abs(2 * t - 1)
        inset = 6 + int(pulse * 8)

        pm = QPixmap(size)
        pm.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pm)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = pm.rect().adjusted(inset, inset, -inset, -inset)
        painter.setBrush(QColor(255, 145, 170, 235))
        painter.setPen(QPen(QColor(255, 255, 255, 220), 3))
        painter.drawRoundedRect(rect, 26, 26)
        # eyes, so orientation is obvious while dragging
        painter.setBrush(QColor(60, 40, 50))
        painter.setPen(Qt.PenStyle.NoPen)
        eye_y = rect.top() + rect.height() // 3
        r = max(4, rect.width() // 14)
        painter.drawEllipse(rect.left() + rect.width() // 3 - r, eye_y - r, r * 2, r * 2)
        painter.drawEllipse(rect.right() - rect.width() // 3 - r, eye_y - r, r * 2, r * 2)
        painter.end()
        frames.append(pm)
    return frames

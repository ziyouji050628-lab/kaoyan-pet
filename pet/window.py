"""The pet window itself: frameless, transparent, always-on-top, draggable."""
from PyQt6.QtCore import QPoint, QSize, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QPainter, QPixmap
from PyQt6.QtWidgets import QApplication, QWidget

from .frames import load_frames, placeholder_frames

SNAP_MARGIN = 24      # px from screen edge that triggers snapping
IDLE_SLEEP_MS = 120_000   # no interaction for this long -> sleep
SLEEP_FPS = 3
DRAG_THRESHOLD = 4    # px before a press becomes a drag, so clicks still register


class PetWindow(QWidget):
    clicked = pyqtSignal()
    double_clicked = pyqtSignal()
    context_requested = pyqtSignal(QPoint)
    moved = pyqtSignal()

    def __init__(self, settings, parent=None):
        super().__init__(parent, Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint
                         | Qt.WindowType.WindowStaysOnTopHint
                         | Qt.WindowType.NoDropShadowWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setCursor(Qt.CursorShape.OpenHandCursor)

        self.settings = settings
        self._frames_raw = load_frames("idle") or placeholder_frames()
        self.using_placeholder = not load_frames("idle")
        self._frames = []
        self._index = 0
        self._sleeping = False

        self._press_pos = None
        self._drag_offset = QPoint()
        self._dragging = False

        self._anim = QTimer(self)
        self._anim.timeout.connect(self._advance)

        self._sleep_timer = QTimer(self)
        self._sleep_timer.setSingleShot(True)
        self._sleep_timer.timeout.connect(self._go_to_sleep)

        self._rescale()
        self._restore_position()
        self._apply_fps(int(self.settings["fps"]))
        self._sleep_timer.start(IDLE_SLEEP_MS)

    # --- appearance ---
    def _rescale(self):
        scale = float(self.settings["scale"])
        self._frames = []
        for pm in self._frames_raw:
            if scale == 1.0:
                self._frames.append(pm)
            else:
                self._frames.append(pm.scaled(
                    QSize(int(pm.width() * scale), int(pm.height() * scale)),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                ))
        if self._frames:
            self.resize(self._frames[0].size())
        self._index = min(self._index, max(0, len(self._frames) - 1))
        self.update()

    def reload_frames(self):
        found = load_frames("idle")
        self._frames_raw = found or placeholder_frames()
        self.using_placeholder = not found
        self._rescale()

    def apply_settings(self):
        self._rescale()
        self._apply_fps(int(self.settings["fps"]))

    def _apply_fps(self, fps: int):
        fps = max(1, min(60, fps))
        if len(self._frames) <= 1:
            self._anim.stop()
            return
        self._anim.start(int(1000 / fps))

    def _advance(self):
        if not self._frames:
            return
        self._index = (self._index + 1) % len(self._frames)
        self.update()

    def paintEvent(self, _):
        if not self._frames:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        pm: QPixmap = self._frames[self._index]
        x = (self.width() - pm.width()) // 2
        y = (self.height() - pm.height()) // 2
        p.drawPixmap(x, y, pm)
        p.end()

    # --- sleep handling ---
    def _go_to_sleep(self):
        self._sleeping = True
        self._apply_fps(SLEEP_FPS)

    def wake(self):
        if self._sleeping:
            self._sleeping = False
            self._apply_fps(int(self.settings["fps"]))
        self._sleep_timer.start(IDLE_SLEEP_MS)

    @property
    def sleeping(self) -> bool:
        return self._sleeping

    # --- geometry ---
    def _available(self):
        screen = self.screen() or QApplication.primaryScreen()
        return screen.availableGeometry()

    def _restore_position(self):
        pos = self.settings["pos"]
        geo = self._available()
        if isinstance(pos, (list, tuple)) and len(pos) == 2:
            pt = QPoint(int(pos[0]), int(pos[1]))
            # if the saved spot is off-screen (monitor changed), fall back
            if geo.adjusted(-self.width() // 2, -self.height() // 2, 0, 0).contains(pt):
                self.move(pt)
                return
        self.move(geo.right() - self.width() - 60, geo.bottom() - self.height() - 80)

    def _clamp_and_snap(self):
        geo = self._available()
        x, y = self.x(), self.y()
        x = max(geo.left(), min(x, geo.right() - self.width()))
        y = max(geo.top(), min(y, geo.bottom() - self.height()))
        if x - geo.left() < SNAP_MARGIN:
            x = geo.left()
        elif geo.right() - (x + self.width()) < SNAP_MARGIN:
            x = geo.right() - self.width()
        if y - geo.top() < SNAP_MARGIN:
            y = geo.top()
        elif geo.bottom() - (y + self.height()) < SNAP_MARGIN:
            y = geo.bottom() - self.height()
        self.move(x, y)

    def save_position(self):
        self.settings["pos"] = [self.x(), self.y()]

    # --- input ---
    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._press_pos = e.globalPosition().toPoint()
            self._drag_offset = self._press_pos - self.frameGeometry().topLeft()
            self._dragging = False
            self.wake()
            e.accept()

    def mouseMoveEvent(self, e):
        if self._press_pos is None:
            return
        gp = e.globalPosition().toPoint()
        if not self._dragging and (gp - self._press_pos).manhattanLength() > DRAG_THRESHOLD:
            self._dragging = True
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        if self._dragging:
            self.move(gp - self._drag_offset)
            self.moved.emit()
            e.accept()

    def mouseReleaseEvent(self, e):
        if e.button() != Qt.MouseButton.LeftButton:
            return
        was_drag = self._dragging
        self._press_pos = None
        self._dragging = False
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        if was_drag:
            self._clamp_and_snap()
            self.save_position()
            self.moved.emit()
        else:
            self.clicked.emit()
        e.accept()

    def mouseDoubleClickEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.wake()
            self.double_clicked.emit()
            e.accept()

    def contextMenuEvent(self, e):
        self.wake()
        self.context_requested.emit(e.globalPos())
        e.accept()

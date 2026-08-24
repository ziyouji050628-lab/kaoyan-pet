"""Entry point for 考研桌宠."""
import sys

from PyQt6.QtWidgets import QApplication, QMessageBox, QSystemTrayIcon

from pet.app import PetApp


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("KaoyanPet")
    app.setQuitOnLastWindowClosed(False)   # tray keeps it alive

    if not QSystemTrayIcon.isSystemTrayAvailable():
        QMessageBox.critical(None, "考研桌宠", "系统托盘不可用，无法运行。")
        return 1

    pet_app = PetApp(app)
    _ = pet_app  # keep a reference so it isn't GC'd
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())

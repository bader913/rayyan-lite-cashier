import sys
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from app.db.database import Database
from app.services.settings_service import SettingsService
from app.ui.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setLayoutDirection(Qt.RightToLeft)
    app.setApplicationName("Rayyan Lite")
    app.setOrganizationName("Rayyan")
    app.setFont(QFont("Segoe UI", 10))

    db = Database.create_default()
    db.initialize()
    SettingsService(db).ensure_defaults()

    win = MainWindow(db)
    win.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

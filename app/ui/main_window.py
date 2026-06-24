from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QMainWindow, QStackedWidget, QVBoxLayout, QWidget

from app.db.database import Database
from app.services.settings_service import SettingsService
from app.ui.pages.dashboard_page import DashboardPage
from app.ui.pages.products_page import ProductsPage
from app.ui.pages.pos_page import PosPage
from app.ui.pages.reports_page import ReportsPage
from app.ui.pages.settings_page import SettingsPage
from app.ui.theme import build_app_stylesheet


class MainWindow(QMainWindow):
    def __init__(self, db: Database):
        super().__init__()
        self.db = db
        self.settings = SettingsService(db)
        self.setWindowTitle("Rayyan Lite - كاشير خفيف")
        self.resize(1280, 790)
        self.setMinimumSize(1080, 700)
        self.setLayoutDirection(Qt.RightToLeft)

        root = QWidget()
        main_layout = QHBoxLayout(root)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.sidebar = QListWidget()
        self.sidebar.setFixedWidth(235)
        self.sidebar.setObjectName("sidebar")
        self.sidebar.addItem(QListWidgetItem("لوحة اليوم"))
        self.sidebar.addItem(QListWidgetItem("بيع سريع"))
        self.sidebar.addItem(QListWidgetItem("المنتجات"))
        self.sidebar.addItem(QListWidgetItem("التقارير"))
        self.sidebar.addItem(QListWidgetItem("الإعدادات والنسخ"))

        side_frame = QFrame()
        side_frame.setObjectName("sideFrame")
        side_layout = QVBoxLayout(side_frame)
        side_layout.setContentsMargins(16, 20, 16, 16)
        side_layout.setSpacing(8)
        title = QLabel("Rayyan Lite")
        title.setObjectName("appTitle")
        subtitle = QLabel("كاشير خفيف للمحلات الصغيرة")
        subtitle.setObjectName("appSubtitle")
        side_layout.addWidget(title)
        side_layout.addWidget(subtitle)
        side_layout.addSpacing(18)
        side_layout.addWidget(self.sidebar, 1)

        self.stack = QStackedWidget()
        self.dashboard_page = DashboardPage(db)
        self.pos_page = PosPage(db, on_sale_saved=self.refresh_all)
        self.products_page = ProductsPage(db, on_products_changed=self.refresh_all)
        self.reports_page = ReportsPage(db)
        self.settings_page = SettingsPage(db, on_settings_changed=self.refresh_all)

        for page in [self.dashboard_page, self.pos_page, self.products_page, self.reports_page, self.settings_page]:
            self.stack.addWidget(page)

        main_layout.addWidget(side_frame)
        main_layout.addWidget(self.stack, 1)
        self.setCentralWidget(root)

        self.sidebar.currentRowChanged.connect(self.on_page_changed)
        self.sidebar.setCurrentRow(0)
        self.apply_style()

    def on_page_changed(self, index: int) -> None:
        self.stack.setCurrentIndex(index)
        page = self.stack.currentWidget()
        if hasattr(page, "refresh"):
            page.refresh()

    def refresh_all(self) -> None:
        self.apply_style()
        for page in [self.dashboard_page, self.products_page, self.pos_page, self.reports_page, self.settings_page]:
            if hasattr(page, "refresh"):
                page.refresh()

    def apply_style(self) -> None:
        values = self.settings.get_all()
        self.setStyleSheet(build_app_stylesheet(values.get('theme_mode', 'light')))

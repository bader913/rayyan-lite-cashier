from __future__ import annotations

from PySide6.QtWidgets import QAbstractItemView, QLabel, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget

from app.core.currency import money_label
from app.core.money import display_qty
from app.db.database import Database
from app.services.products_service import ProductsService
from app.services.reports_service import ReportsService
from app.services.settings_service import SettingsService


class ReportsPage(QWidget):
    def __init__(self, db: Database):
        super().__init__()
        self.reports = ReportsService(db)
        self.products = ProductsService(db)
        self.settings = SettingsService(db)
        self.current_settings = self.settings.get_all()

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        title = QLabel("التقارير")
        title.setObjectName("pageTitle")
        root.addWidget(title)
        refresh_btn = QPushButton("تحديث")
        refresh_btn.setObjectName("secondary")
        refresh_btn.clicked.connect(self.refresh)
        root.addWidget(refresh_btn)

        root.addWidget(QLabel("الأكثر مبيعاً اليوم"))
        self.top_table = QTableWidget(0, 4)
        self.top_table.setHorizontalHeaderLabels(["المنتج", "الكمية", "المبيعات", "الربح"])
        self.top_table.horizontalHeader().setStretchLastSection(True)
        self.top_table.setAlternatingRowColors(True)
        self.top_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.top_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        root.addWidget(self.top_table, 1)

        root.addWidget(QLabel("المنتجات الناقصة"))
        self.low_table = QTableWidget(0, 4)
        self.low_table.setHorizontalHeaderLabels(["المنتج", "الكمية", "حد التنبيه", "سعر البيع"])
        self.low_table.horizontalHeader().setStretchLastSection(True)
        self.low_table.setAlternatingRowColors(True)
        self.low_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.low_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        root.addWidget(self.low_table, 1)
        self.refresh()

    def refresh(self) -> None:
        self.current_settings = self.settings.get_all()
        top = self.reports.top_products_today()
        self.top_table.setRowCount(len(top))
        for r, row in enumerate(top):
            values = [row["name"], display_qty(row["qty_sold"]), money_label(row["total_sales"], self.current_settings), money_label(row["profit"], self.current_settings)]
            for c, value in enumerate(values):
                self.top_table.setItem(r, c, QTableWidgetItem(str(value)))

        low = self.products.low_stock()
        self.low_table.setRowCount(len(low))
        for r, row in enumerate(low):
            values = [row["name"], display_qty(row["stock_quantity"]), display_qty(row["min_stock_level"]), money_label(row["retail_price"], self.current_settings)]
            for c, value in enumerate(values):
                self.low_table.setItem(r, c, QTableWidgetItem(str(value)))

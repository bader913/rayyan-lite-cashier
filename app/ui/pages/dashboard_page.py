from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QAbstractItemView, QFrame, QGridLayout, QLabel, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget

from app.core.currency import money_label, settings_from_sale_snapshot
from app.db.database import Database
from app.services.products_service import ProductsService
from app.services.sales_service import SalesService
from app.services.settings_service import SettingsService
from app.ui.dialogs.invoice_dialog import InvoiceDialog
from app.ui.widgets import show_error


class DashboardPage(QWidget):
    def __init__(self, db: Database):
        super().__init__()
        self.db = db
        self.sales = SalesService(db)
        self.products = ProductsService(db)
        self.settings = SettingsService(db)
        self.current_settings = self.settings.get_all()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)
        title = QLabel("لوحة اليوم")
        title.setObjectName("pageTitle")
        layout.addWidget(title)

        cards = QGridLayout()
        cards.setSpacing(12)
        self.card_sales = self._make_card("مبيعات اليوم")
        self.card_profit = self._make_card("ربح اليوم التقريبي")
        self.card_invoices = self._make_card("عدد الفواتير")
        self.card_low_stock = self._make_card("منتجات ناقصة")
        cards.addWidget(self.card_sales["frame"], 0, 0)
        cards.addWidget(self.card_profit["frame"], 0, 1)
        cards.addWidget(self.card_invoices["frame"], 0, 2)
        cards.addWidget(self.card_low_stock["frame"], 0, 3)
        layout.addLayout(cards)

        refresh_btn = QPushButton("تحديث")
        refresh_btn.setObjectName("secondary")
        refresh_btn.clicked.connect(self.refresh)
        layout.addWidget(refresh_btn)

        layout.addWidget(QLabel("آخر الفواتير - اضغط مرتين لفتح الفاتورة"))
        self.sales_table = QTableWidget(0, 6)
        self.sales_table.setHorizontalHeaderLabels(["#", "رقم الفاتورة", "الإجمالي", "الربح", "الدفع", "التاريخ"])
        self.sales_table.horizontalHeader().setStretchLastSection(True)
        self.sales_table.setAlternatingRowColors(True)
        self.sales_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.sales_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.sales_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.sales_table.cellDoubleClicked.connect(self.open_invoice_from_row)
        layout.addWidget(self.sales_table, 1)
        self.refresh()

    def _make_card(self, label: str) -> dict[str, QLabel | QFrame]:
        frame = QFrame()
        frame.setObjectName("card")
        lay = QVBoxLayout(frame)
        lay.setContentsMargins(16, 14, 16, 14)
        title = QLabel(label)
        title.setObjectName("cardTitle")
        value = QLabel("0")
        value.setObjectName("cardValue")
        lay.addWidget(title)
        lay.addWidget(value)
        return {"frame": frame, "value": value}

    def refresh(self) -> None:
        self.current_settings = self.settings.get_all()
        summary = self.sales.today_summary()
        low = self.products.low_stock()
        self.card_sales["value"].setText(money_label(summary["total_sales"], self.current_settings))
        self.card_profit["value"].setText(money_label(summary["gross_profit"], self.current_settings))
        self.card_invoices["value"].setText(str(summary["invoice_count"]))
        self.card_low_stock["value"].setText(str(len(low)))

        rows = self.sales.recent_sales(20)
        self.sales_table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            row_settings = settings_from_sale_snapshot(row, self.current_settings)
            edited_mark = " ✎" if int(row.get("edit_count") or 0) else ""
            values = [
                row["id"],
                f"{row['invoice_number']}{edited_mark}",
                money_label(row["total_amount"], row_settings),
                money_label(row.get("gross_profit") or 0, row_settings),
                "نقدي" if row["payment_method"] == "cash" else "بطاقة",
                row["created_at"],
            ]
            for c, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                if c == 0:
                    item.setData(Qt.UserRole, int(row["id"]))
                if c in {0, 2, 3, 4}:
                    item.setTextAlignment(Qt.AlignCenter)
                self.sales_table.setItem(i, c, item)

    def open_invoice_from_row(self, row: int, _column: int) -> None:
        id_item = self.sales_table.item(row, 0)
        if not id_item:
            return
        try:
            sale_id = int(id_item.text())
            InvoiceDialog(self, self.db, sale_id).exec()
        except Exception as exc:
            show_error(self, "خطأ", str(exc))

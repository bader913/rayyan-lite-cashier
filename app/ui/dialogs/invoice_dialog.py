from __future__ import annotations

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from app.core.currency import exchange_hint, money_label
from app.core.money import display_qty
from app.db.database import Database
from app.printing.receipt_printer import print_thermal_receipt, write_receipt_html_preview
from app.services.sales_service import SalesService
from app.services.settings_service import SettingsService
from app.ui.widgets import show_error, show_info


class InvoiceDialog(QDialog):
    def __init__(self, parent, db: Database, sale_id: int):
        super().__init__(parent)
        self.db = db
        self.sales = SalesService(db)
        self.settings_service = SettingsService(db)
        self.details = self.sales.get_sale_details(sale_id)
        self.settings = self.settings_service.get_all()

        self.setWindowTitle("تفاصيل الفاتورة")
        self.resize(760, 580)
        self.setLayoutDirection(Qt.RightToLeft)

        sale = self.details["sale"]
        items = self.details["items"]

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(12)

        header = QFrame()
        header.setObjectName("dialogHeader")
        header_layout = QGridLayout(header)
        title = QLabel(f"فاتورة {sale['invoice_number']}")
        title.setObjectName("dialogTitle")
        header_layout.addWidget(title, 0, 0, 1, 2)
        header_layout.addWidget(QLabel(f"التاريخ: {sale['created_at']}"), 1, 0)
        payment = "نقدي" if sale.get("payment_method") == "cash" else "بطاقة"
        header_layout.addWidget(QLabel(f"طريقة الدفع: {payment}"), 1, 1)
        root.addWidget(header)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["المنتج", "الكمية", "السعر", "الخصم", "الإجمالي"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        root.addWidget(self.table, 1)

        self.table.setRowCount(len(items))
        for r, item in enumerate(items):
            values = [
                item["product_name"],
                display_qty(item["quantity"]),
                money_label(item["unit_price"], self.settings),
                money_label(item["discount"], self.settings),
                money_label(item["total_price"], self.settings),
            ]
            for c, value in enumerate(values):
                table_item = QTableWidgetItem(str(value))
                if c in {1, 2, 3, 4}:
                    table_item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(r, c, table_item)

        summary = QFrame()
        summary.setObjectName("summaryBox")
        summary_layout = QGridLayout(summary)
        summary_layout.addWidget(QLabel("الإجمالي"), 0, 0)
        total_label = QLabel(money_label(sale["total_amount"], self.settings))
        total_label.setObjectName("totalStrong")
        summary_layout.addWidget(total_label, 0, 1)
        summary_layout.addWidget(QLabel("المدفوع"), 1, 0)
        summary_layout.addWidget(QLabel(money_label(sale["paid_amount"], self.settings)), 1, 1)
        hint = exchange_hint(sale["total_amount"], self.settings)
        if hint:
            summary_layout.addWidget(QLabel("سعر الصرف"), 2, 0)
            summary_layout.addWidget(QLabel(hint), 2, 1)
        root.addWidget(summary)

        actions = QHBoxLayout()
        print_btn = QPushButton("طباعة حراري")
        print_btn.setObjectName("success")
        print_btn.clicked.connect(self.print_receipt)
        preview_btn = QPushButton("معاينة HTML")
        preview_btn.setObjectName("secondary")
        preview_btn.clicked.connect(self.open_preview)
        close_btn = QPushButton("إغلاق")
        close_btn.setObjectName("secondary")
        close_btn.clicked.connect(self.accept)
        actions.addWidget(print_btn)
        actions.addWidget(preview_btn)
        actions.addStretch(1)
        actions.addWidget(close_btn)
        root.addLayout(actions)

    def print_receipt(self) -> None:
        try:
            ok = print_thermal_receipt(self, self.details["sale"], self.details["items"], self.settings)
            if ok:
                show_info(self, "تم", "تم إرسال الفاتورة للطباعة")
        except Exception as exc:
            show_error(self, "خطأ في الطباعة", str(exc))

    def open_preview(self) -> None:
        try:
            path = write_receipt_html_preview(self.details["sale"], self.details["items"], self.settings)
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))
        except Exception as exc:
            show_error(self, "خطأ في المعاينة", str(exc))

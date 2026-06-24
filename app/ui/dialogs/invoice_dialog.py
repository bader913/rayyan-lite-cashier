from __future__ import annotations

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from app.core.currency import exchange_hint, money_label, settings_from_sale_snapshot
from app.core.money import display, display_qty, money
from app.db.database import Database
from app.printing.receipt_printer import print_thermal_receipt, write_receipt_html_preview
from app.services.sales_service import SalesService
from app.services.settings_service import SettingsService
from app.ui.widgets import show_error, show_info


class EditInvoiceDialog(QDialog):
    def __init__(self, parent, db: Database, details: dict, invoice_settings: dict[str, str]):
        super().__init__(parent)
        self.db = db
        self.sales = SalesService(db)
        self.details = details
        self.invoice_settings = invoice_settings
        self.setWindowTitle("تعديل / مرتجع الفاتورة")
        self.resize(840, 620)
        self.setLayoutDirection(Qt.RightToLeft)

        sale = self.details["sale"]
        items = self.details["items"]

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(10)

        title = QLabel(f"تعديل الفاتورة {sale['invoice_number']}")
        title.setObjectName("dialogTitle")
        root.addWidget(title)

        hint = QLabel("لعمل مرتجع جزئي: خفّض الكمية. لحذف بند بالكامل: ضع الكمية 0. سيتم تعديل الفاتورة الأصلية وتسجيل حركة المخزون تلقائياً.")
        hint.setObjectName("hintText")
        hint.setWordWrap(True)
        root.addWidget(hint)

        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(["ItemID", "ProductID", "المنتج", "الكمية", "السعر", "الخصم", "الإجمالي"])
        self.table.setColumnHidden(0, True)
        self.table.setColumnHidden(1, True)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setAlternatingRowColors(True)
        root.addWidget(self.table, 1)

        self.table.setRowCount(len(items))
        for row, item in enumerate(items):
            values = [
                item["id"],
                item["product_id"],
                item["product_name"],
                display_qty(item["quantity"]),
                display(item["unit_price"]),
                display(item["discount"]),
                money_label(item["total_price"], self.invoice_settings),
            ]
            for col, value in enumerate(values):
                table_item = QTableWidgetItem(str(value))
                if col in {0, 1, 2, 6}:
                    table_item.setFlags(table_item.flags() & ~Qt.ItemIsEditable)
                if col in {3, 4, 5, 6}:
                    table_item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, col, table_item)

        payment_row = QHBoxLayout()
        payment_row.addWidget(QLabel("طريقة الدفع"))
        self.payment_method = QComboBox()
        self.payment_method.addItem("نقدي", "cash")
        self.payment_method.addItem("بطاقة", "card")
        idx = self.payment_method.findData(sale.get("payment_method") or "cash")
        self.payment_method.setCurrentIndex(max(idx, 0))
        payment_row.addWidget(self.payment_method)

        payment_row.addWidget(QLabel("المدفوع"))
        self.paid_amount = QLineEdit(display(sale.get("paid_amount", "0")))
        self.paid_amount.setMinimumWidth(160)
        payment_row.addWidget(self.paid_amount)

        calc_btn = QPushButton("حساب الإجمالي")
        calc_btn.setObjectName("secondary")
        calc_btn.clicked.connect(self.recalculate_preview)
        payment_row.addWidget(calc_btn)

        self.total_preview = QLabel("")
        self.total_preview.setObjectName("totalStrong")
        payment_row.addWidget(self.total_preview, 1)
        root.addLayout(payment_row)

        buttons = QDialogButtonBox()
        self.save_btn = buttons.addButton("حفظ التعديل", QDialogButtonBox.AcceptRole)
        self.save_btn.setObjectName("success")
        cancel_btn = buttons.addButton("إلغاء", QDialogButtonBox.RejectRole)
        cancel_btn.setObjectName("secondary")
        buttons.accepted.connect(self.save)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)
        self.recalculate_preview()

    def _row_payload(self) -> list[dict]:
        payload: list[dict] = []
        for row in range(self.table.rowCount()):
            item_id = int(self.table.item(row, 0).text())
            product_id = int(self.table.item(row, 1).text())
            name = self.table.item(row, 2).text()
            quantity = self.table.item(row, 3).text()
            unit_price = self.table.item(row, 4).text()
            discount = self.table.item(row, 5).text()
            payload.append(
                {
                    "sale_item_id": item_id,
                    "product_id": product_id,
                    "name": name,
                    "quantity": quantity,
                    "unit_price": unit_price,
                    "discount": discount,
                }
            )
        return payload

    def recalculate_preview(self) -> None:
        try:
            total = money("0")
            payload = self._row_payload()
            for row, raw in enumerate(payload):
                quantity = money(raw["quantity"])
                unit_price = money(raw["unit_price"])
                discount = money(raw["discount"])
                line_total = money((quantity * unit_price) - discount)
                self.table.item(row, 6).setText(money_label(line_total, self.invoice_settings))
                total = money(total + line_total)
            self.total_preview.setText(f"الإجمالي الجديد: {money_label(total, self.invoice_settings)}")
        except Exception as exc:
            self.total_preview.setText(f"خطأ بالحساب: {exc}")

    def save(self) -> None:
        try:
            self.sales.update_sale(
                int(self.details["sale"]["id"]),
                self._row_payload(),
                payment_method=str(self.payment_method.currentData() or "cash"),
                paid_amount=self.paid_amount.text().strip() or "0",
                reason="تعديل/مرتجع من نافذة الفاتورة",
            )
            self.accept()
        except Exception as exc:
            show_error(self, "خطأ في تعديل الفاتورة", str(exc))


class InvoiceDialog(QDialog):
    def __init__(self, parent, db: Database, sale_id: int):
        super().__init__(parent)
        self.db = db
        self.sale_id = sale_id
        self.sales = SalesService(db)
        self.settings_service = SettingsService(db)
        self.details: dict = {}
        self.settings: dict[str, str] = {}

        self.setWindowTitle("تفاصيل الفاتورة")
        self.resize(800, 610)
        self.setLayoutDirection(Qt.RightToLeft)

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(12)

        self.header = QFrame()
        self.header.setObjectName("dialogHeader")
        header_layout = QGridLayout(self.header)
        self.title_label = QLabel("")
        self.title_label.setObjectName("dialogTitle")
        self.date_label = QLabel("")
        self.payment_label = QLabel("")
        self.edit_label = QLabel("")
        self.edit_label.setObjectName("hintText")
        header_layout.addWidget(self.title_label, 0, 0, 1, 2)
        header_layout.addWidget(self.date_label, 1, 0)
        header_layout.addWidget(self.payment_label, 1, 1)
        header_layout.addWidget(self.edit_label, 2, 0, 1, 2)
        root.addWidget(self.header)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["المنتج", "الكمية", "السعر", "الخصم", "الإجمالي", "الربح"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setAlternatingRowColors(True)
        root.addWidget(self.table, 1)

        self.summary = QFrame()
        self.summary.setObjectName("summaryBox")
        summary_layout = QGridLayout(self.summary)
        summary_layout.addWidget(QLabel("الإجمالي"), 0, 0)
        self.total_label = QLabel("")
        self.total_label.setObjectName("totalStrong")
        summary_layout.addWidget(self.total_label, 0, 1)
        summary_layout.addWidget(QLabel("المدفوع"), 1, 0)
        self.paid_label = QLabel("")
        summary_layout.addWidget(self.paid_label, 1, 1)
        summary_layout.addWidget(QLabel("فرق/باقي"), 2, 0)
        self.change_label = QLabel("")
        summary_layout.addWidget(self.change_label, 2, 1)
        summary_layout.addWidget(QLabel("ربح الفاتورة"), 3, 0)
        self.profit_label = QLabel("")
        self.profit_label.setObjectName("totalStrong")
        summary_layout.addWidget(self.profit_label, 3, 1)
        summary_layout.addWidget(QLabel("سعر الصرف التاريخي"), 4, 0)
        self.exchange_label = QLabel("")
        self.exchange_label.setWordWrap(True)
        summary_layout.addWidget(self.exchange_label, 4, 1)
        root.addWidget(self.summary)

        actions = QHBoxLayout()
        edit_btn = QPushButton("تعديل / مرتجع")
        edit_btn.setObjectName("accent")
        edit_btn.clicked.connect(self.edit_invoice)
        print_btn = QPushButton("طباعة حراري")
        print_btn.setObjectName("success")
        print_btn.clicked.connect(self.print_receipt)
        preview_btn = QPushButton("معاينة HTML")
        preview_btn.setObjectName("secondary")
        preview_btn.clicked.connect(self.open_preview)
        close_btn = QPushButton("إغلاق")
        close_btn.setObjectName("secondary")
        close_btn.clicked.connect(self.accept)
        actions.addWidget(edit_btn)
        actions.addWidget(print_btn)
        actions.addWidget(preview_btn)
        actions.addStretch(1)
        actions.addWidget(close_btn)
        root.addLayout(actions)

        self.reload()

    def reload(self) -> None:
        self.details = self.sales.get_sale_details(self.sale_id)
        current_settings = self.settings_service.get_all()
        self.settings = settings_from_sale_snapshot(self.details["sale"], current_settings)
        self.render()

    def render(self) -> None:
        sale = self.details["sale"]
        items = self.details["items"]
        self.title_label.setText(f"فاتورة {sale['invoice_number']}")
        self.date_label.setText(f"التاريخ: {sale['created_at']}")
        payment = "نقدي" if sale.get("payment_method") == "cash" else "بطاقة"
        self.payment_label.setText(f"طريقة الدفع: {payment}")
        edit_count = int(sale.get("edit_count") or 0)
        edited_at = str(sale.get("edited_at") or "").strip()
        reason = str(sale.get("last_edit_reason") or "").strip()
        self.edit_label.setText(f"معدلة {edit_count} مرة — {edited_at} — {reason}" if edit_count else "الفاتورة غير معدلة")

        self.table.setRowCount(len(items))
        for r, item in enumerate(items):
            values = [
                item["product_name"],
                display_qty(item["quantity"]),
                money_label(item["unit_price"], self.settings),
                money_label(item["discount"], self.settings),
                money_label(item["total_price"], self.settings),
                money_label(item.get("profit_amount") or 0, self.settings),
            ]
            for c, value in enumerate(values):
                table_item = QTableWidgetItem(str(value))
                if c in {1, 2, 3, 4, 5}:
                    table_item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(r, c, table_item)

        total = money(sale["total_amount"])
        paid = money(sale["paid_amount"])
        change = money(paid - total)
        self.total_label.setText(money_label(total, self.settings))
        self.paid_label.setText(money_label(paid, self.settings))
        if change == 0:
            self.change_label.setText("0")
        elif change > 0:
            self.change_label.setText(f"باقي/مرتجع للزبون: {money_label(change, self.settings)}")
        else:
            self.change_label.setText(f"متبقي: {money_label(abs(change), self.settings)}")
        self.profit_label.setText(money_label(sale.get("gross_profit") or 0, self.settings))
        hint = exchange_hint(total, self.settings)
        self.exchange_label.setText(hint or "لا يوجد سعر صرف تاريخي مختلف")

    def edit_invoice(self) -> None:
        try:
            dialog = EditInvoiceDialog(self, self.db, self.details, self.settings)
            if dialog.exec() == QDialog.Accepted:
                self.reload()
                show_info(self, "تم", "تم تعديل الفاتورة الأصلية وتسجيل حركة المخزون")
        except Exception as exc:
            show_error(self, "خطأ في التعديل", str(exc))

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

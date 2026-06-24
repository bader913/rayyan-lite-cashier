from __future__ import annotations

from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.core.currency import exchange_hint, money_label
from app.core.money import display, display_qty, money, qty
from app.db.database import Database
from app.services.products_service import ProductsService
from app.services.sales_service import SalesService
from app.services.settings_service import SettingsService
from app.ui.dialogs.invoice_dialog import InvoiceDialog
from app.ui.widgets import show_error


class PosPage(QWidget):
    def __init__(self, db: Database, on_sale_saved: Callable[[], None] | None = None):
        super().__init__()
        self.db = db
        self.products = ProductsService(db)
        self.sales = SalesService(db)
        self.settings = SettingsService(db)
        self.current_settings = self.settings.get_all()
        self.on_sale_saved = on_sale_saved
        self.cart: list[dict] = []
        self.search_results: list[dict] = []

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(12)
        title = QLabel("بيع سريع")
        title.setObjectName("pageTitle")
        root.addWidget(title)

        search_card = QFrame()
        search_card.setObjectName("contentCard")
        search_box = QVBoxLayout(search_card)
        search_box.setContentsMargins(14, 14, 14, 14)
        search_row = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("اكتب اسم المنتج أو امسح الباركود ثم Enter")
        self.search.returnPressed.connect(self.add_first_result)
        self.search.textChanged.connect(self.refresh_search_results)
        search_row.addWidget(self.search, 1)
        self.qty_input = QLineEdit("1")
        self.qty_input.setFixedWidth(110)
        search_row.addWidget(QLabel("الكمية"))
        search_row.addWidget(self.qty_input)
        add_btn = QPushButton("إضافة للسلة")
        add_btn.clicked.connect(self.add_selected_result)
        search_row.addWidget(add_btn)
        search_box.addLayout(search_row)

        self.results = QListWidget()
        self.results.setFixedHeight(105)
        self.results.itemDoubleClicked.connect(lambda _: self.add_selected_result())
        search_box.addWidget(self.results)
        root.addWidget(search_card)

        self.cart_table = QTableWidget(0, 6)
        self.cart_table.setHorizontalHeaderLabels(["المنتج", "الكمية", "السعر", "الخصم", "الإجمالي", "ID"])
        self.cart_table.setColumnHidden(5, True)
        self.cart_table.horizontalHeader().setStretchLastSection(True)
        self.cart_table.setAlternatingRowColors(True)
        self.cart_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.cart_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        root.addWidget(self.cart_table, 1)

        bottom = QHBoxLayout()
        totals = QVBoxLayout()
        self.total_label = QLabel("الإجمالي: 0")
        self.total_label.setObjectName("cardValue")
        self.exchange_label = QLabel("")
        self.exchange_label.setObjectName("hintText")
        totals.addWidget(self.total_label)
        totals.addWidget(self.exchange_label)
        bottom.addLayout(totals, 1)
        self.payment_method = QComboBox()
        self.payment_method.addItem("نقدي", "cash")
        self.payment_method.addItem("بطاقة", "card")
        bottom.addWidget(self.payment_method)
        self.paid_amount = QLineEdit("")
        self.paid_amount.setPlaceholderText("المدفوع - اتركه فارغاً = الإجمالي")
        self.paid_amount.setFixedWidth(230)
        bottom.addWidget(self.paid_amount)
        remove_btn = QPushButton("حذف سطر")
        remove_btn.setObjectName("danger")
        remove_btn.clicked.connect(self.remove_selected_cart_row)
        bottom.addWidget(remove_btn)
        save_btn = QPushButton("حفظ وفتح الفاتورة")
        save_btn.setObjectName("success")
        save_btn.clicked.connect(self.save_sale)
        bottom.addWidget(save_btn)
        root.addLayout(bottom)
        self.refresh_search_results()

    def refresh(self) -> None:
        self.current_settings = self.settings.get_all()
        self.refresh_search_results()
        self.refresh_cart()

    def refresh_search_results(self) -> None:
        term = self.search.text().strip()
        self.search_results = self.products.list_products(term, active_only=True, limit=30) if term else self.products.list_products("", active_only=True, limit=20)
        self.results.clear()
        for product in self.search_results:
            item = QListWidgetItem(
                f"{product['name']} | باركود: {product.get('barcode') or '-'} | سعر: {money_label(product['retail_price'], self.current_settings)} | مخزون: {display_qty(product['stock_quantity'])}"
            )
            item.setData(Qt.UserRole, int(product["id"]))
            self.results.addItem(item)

    def selected_product(self) -> dict | None:
        item = self.results.currentItem()
        if item:
            product_id = int(item.data(Qt.UserRole))
            return next((p for p in self.search_results if int(p["id"]) == product_id), None)
        return self.search_results[0] if self.search_results else None

    def add_first_result(self) -> None:
        if self.search_results:
            self.results.setCurrentRow(0)
            self.add_selected_result()

    def add_selected_result(self) -> None:
        product = self.selected_product()
        if not product:
            show_error(self, "تنبيه", "لم يتم العثور على منتج")
            return
        try:
            quantity = qty(self.qty_input.text())
            if quantity <= 0:
                raise ValueError("الكمية يجب أن تكون أكبر من صفر")
        except Exception as exc:
            show_error(self, "خطأ", str(exc))
            return

        product_id = int(product["id"])
        for line in self.cart:
            if line["product_id"] == product_id:
                line["quantity"] = qty(line["quantity"] + quantity)
                self.refresh_cart()
                self.search.clear()
                self.search.setFocus()
                return
        self.cart.append(
            {
                "product_id": product_id,
                "name": product["name"],
                "quantity": quantity,
                "unit_price": money(product["retail_price"]),
                "discount": money("0"),
            }
        )
        self.refresh_cart()
        self.search.clear()
        self.search.setFocus()

    def refresh_cart(self) -> None:
        self.current_settings = self.settings.get_all()
        self.cart_table.setRowCount(len(self.cart))
        total = money("0")
        for r, line in enumerate(self.cart):
            line_total = money(line["quantity"] * line["unit_price"] - line["discount"])
            total = money(total + line_total)
            values = [
                line["name"],
                display_qty(line["quantity"]),
                money_label(line["unit_price"], self.current_settings),
                money_label(line["discount"], self.current_settings),
                money_label(line_total, self.current_settings),
                line["product_id"],
            ]
            for c, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                if c in {1, 2, 3, 4}:
                    item.setTextAlignment(Qt.AlignCenter)
                self.cart_table.setItem(r, c, item)
        self.total_label.setText(f"الإجمالي: {money_label(total, self.current_settings)}")
        self.exchange_label.setText(exchange_hint(total, self.current_settings))

    def remove_selected_cart_row(self) -> None:
        row = self.cart_table.currentRow()
        if row < 0 or row >= len(self.cart):
            return
        self.cart.pop(row)
        self.refresh_cart()

    def save_sale(self) -> None:
        try:
            paid_text = self.paid_amount.text().strip()
            paid = paid_text if paid_text else "0"
            result = self.sales.create_sale(
                self.cart,
                payment_method=self.payment_method.currentData(),
                paid_amount=paid,
            )
            sale_id = int(result["sale_id"])
            self.cart.clear()
            self.paid_amount.clear()
            self.refresh_cart()
            self.refresh_search_results()
            if self.on_sale_saved:
                self.on_sale_saved()
            InvoiceDialog(self, self.db, sale_id).exec()
        except Exception as exc:
            show_error(self, "خطأ في حفظ الفاتورة", str(exc))

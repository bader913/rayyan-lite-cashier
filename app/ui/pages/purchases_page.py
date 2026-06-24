from __future__ import annotations

from typing import Callable

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
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

from app.core.currency import money_label
from app.core.money import display, display_qty, money, qty
from app.db.database import Database
from app.services.products_service import ProductsService
from app.services.purchases_service import PurchasesService
from app.services.settings_service import SettingsService
from app.ui.widgets import show_error, show_info


class PurchaseCartTableWidget(QTableWidget):
    delete_row_requested = Signal()
    move_next_requested = Signal()
    edit_requested = Signal()

    def keyPressEvent(self, event):  # noqa: N802 - Qt override
        key = event.key()
        if key == Qt.Key_Delete:
            self.delete_row_requested.emit()
            event.accept()
            return
        if key in {Qt.Key_Return, Qt.Key_Enter}:
            self.move_next_requested.emit()
            event.accept()
            return
        if key == Qt.Key_F2:
            self.edit_requested.emit()
            event.accept()
            return
        super().keyPressEvent(event)


class PurchasesPage(QWidget):
    EDITABLE_CART_COLUMNS = {1, 2}

    def __init__(self, db: Database, on_purchase_saved: Callable[[], None] | None = None):
        super().__init__()
        self.db = db
        self.products = ProductsService(db)
        self.purchases = PurchasesService(db)
        self.settings = SettingsService(db)
        self.current_settings = self.settings.get_all()
        self.on_purchase_saved = on_purchase_saved
        self.cart: list[dict] = []
        self.search_results: list[dict] = []
        self._syncing_cart_table = False

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(12)

        title = QLabel("المشتريات")
        title.setObjectName("pageTitle")
        root.addWidget(title)

        search_card = QFrame()
        search_card.setObjectName("contentCard")
        search_box = QVBoxLayout(search_card)
        search_box.setContentsMargins(14, 14, 14, 14)

        supplier_row = QHBoxLayout()
        self.supplier_name = QLineEdit()
        self.supplier_name.setPlaceholderText("اسم المورد - اختياري")
        supplier_row.addWidget(QLabel("المورد"))
        supplier_row.addWidget(self.supplier_name, 1)
        self.paid_amount = QLineEdit("")
        self.paid_amount.setPlaceholderText("المدفوع - اتركه فارغاً = الإجمالي")
        self.paid_amount.setFixedWidth(260)
        supplier_row.addWidget(QLabel("المدفوع"))
        supplier_row.addWidget(self.paid_amount)
        search_box.addLayout(supplier_row)

        search_row = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("اكتب اسم المنتج أو امسح الباركود ثم Enter")
        self.search.returnPressed.connect(self.add_first_result)
        self.search.textChanged.connect(self.refresh_search_results)
        search_row.addWidget(self.search, 1)

        self.qty_input = QLineEdit("1")
        self.qty_input.setFixedWidth(110)
        self.qty_input.returnPressed.connect(self.add_first_result)
        search_row.addWidget(QLabel("الكمية"))
        search_row.addWidget(self.qty_input)

        add_btn = QPushButton("إضافة للفاتورة")
        add_btn.clicked.connect(self.add_selected_result)
        search_row.addWidget(add_btn)
        search_box.addLayout(search_row)

        hint = QLabel(
            "هذه الصفحة لإدخال البضاعة نظامياً بدل تعديل المخزون اليدوي. عدّل الكمية وسعر الشراء من الجدول، ثم احفظ فاتورة المشتريات."
        )
        hint.setObjectName("hintText")
        hint.setWordWrap(True)
        search_box.addWidget(hint)

        self.results = QListWidget()
        self.results.setFixedHeight(100)
        self.results.itemDoubleClicked.connect(lambda _: self.add_selected_result())
        search_box.addWidget(self.results)

        root.addWidget(search_card)

        self.cart_table = PurchaseCartTableWidget(0, 5)
        self.cart_table.setHorizontalHeaderLabels(["المنتج", "الكمية", "سعر الشراء", "الإجمالي", "ID"])
        self.cart_table.setColumnHidden(4, True)
        self.cart_table.horizontalHeader().setStretchLastSection(True)
        self.cart_table.setAlternatingRowColors(True)
        self.cart_table.setEditTriggers(
            QAbstractItemView.DoubleClicked
            | QAbstractItemView.EditKeyPressed
            | QAbstractItemView.AnyKeyPressed
            | QAbstractItemView.SelectedClicked
        )
        self.cart_table.setSelectionBehavior(QAbstractItemView.SelectItems)
        self.cart_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.cart_table.setTabKeyNavigation(True)
        self.cart_table.cellChanged.connect(self.on_cart_cell_changed)
        self.cart_table.delete_row_requested.connect(self.remove_selected_cart_row)
        self.cart_table.move_next_requested.connect(self.move_to_next_editable_cell)
        self.cart_table.edit_requested.connect(self.edit_current_cart_cell)
        root.addWidget(self.cart_table, 1)

        bottom = QHBoxLayout()
        totals = QVBoxLayout()
        self.total_label = QLabel("الإجمالي: 0")
        self.total_label.setObjectName("cardValue")
        self.helper_label = QLabel("Enter للتنقل، F2 للتعديل، Delete لحذف سطر، Ctrl+S لحفظ فاتورة المشتريات، F3 للبحث.")
        self.helper_label.setObjectName("hintText")
        totals.addWidget(self.total_label)
        totals.addWidget(self.helper_label)
        bottom.addLayout(totals, 1)

        self.update_cost_checkbox = QCheckBox("تحديث سعر الشراء في بطاقة المنتج")
        self.update_cost_checkbox.setChecked(True)
        bottom.addWidget(self.update_cost_checkbox)

        remove_btn = QPushButton("حذف سطر")
        remove_btn.setObjectName("danger")
        remove_btn.clicked.connect(self.remove_selected_cart_row)
        bottom.addWidget(remove_btn)

        save_btn = QPushButton("حفظ المشتريات وزيادة المخزون")
        save_btn.setObjectName("success")
        save_btn.clicked.connect(self.save_purchase)
        bottom.addWidget(save_btn)
        root.addLayout(bottom)

        history_title = QLabel("آخر فواتير المشتريات")
        history_title.setObjectName("sectionTitle")
        root.addWidget(history_title)

        self.history_table = QTableWidget(0, 6)
        self.history_table.setHorizontalHeaderLabels(["الرقم", "المورد", "عدد البنود", "الكمية", "الإجمالي", "التاريخ"])
        self.history_table.horizontalHeader().setStretchLastSection(True)
        self.history_table.setAlternatingRowColors(True)
        self.history_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.history_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.history_table.setFixedHeight(180)
        root.addWidget(self.history_table)

        QShortcut(QKeySequence("Ctrl+S"), self, activated=self.save_purchase)
        QShortcut(QKeySequence("F3"), self, activated=self.focus_search)
        self.refresh()

    def refresh(self) -> None:
        self.current_settings = self.settings.get_all()
        self.refresh_search_results()
        self.refresh_cart()
        self.refresh_history()

    def refresh_search_results(self) -> None:
        term = self.search.text().strip()
        self.search_results = self.products.list_products(term, active_only=True, limit=30) if term else self.products.list_products("", active_only=True, limit=20)
        self.results.clear()
        for product in self.search_results:
            item = QListWidgetItem(
                f"{product['name']} | باركود: {product.get('barcode') or '-'} | آخر شراء: {money_label(product['purchase_price'], self.current_settings)} | مخزون: {display_qty(product['stock_quantity'])}"
            )
            item.setData(Qt.UserRole, int(product["id"]))
            self.results.addItem(item)

    def refresh_history(self) -> None:
        purchases = self.purchases.list_recent_purchases(50)
        self.history_table.setRowCount(len(purchases))
        for r, purchase in enumerate(purchases):
            values = [
                purchase["invoice_number"],
                purchase.get("supplier_name") or "-",
                purchase.get("items_count") or 0,
                display_qty(purchase.get("total_quantity") or 0),
                money_label(purchase["total_amount"], self.current_settings),
                purchase["created_at"],
            ]
            for c, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                if c in {2, 3, 4}:
                    item.setTextAlignment(Qt.AlignCenter)
                self.history_table.setItem(r, c, item)

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
        for index, line in enumerate(self.cart):
            if line["product_id"] == product_id:
                line["quantity"] = qty(line["quantity"] + quantity)
                self.refresh_cart(select_row=index, select_col=1)
                self.search.clear()
                self.focus_search()
                return

        self.cart.append(
            {
                "product_id": product_id,
                "name": product["name"],
                "quantity": quantity,
                "unit_price": money(product["purchase_price"]),
            }
        )
        self.refresh_cart(select_row=len(self.cart) - 1, select_col=1)
        self.search.clear()
        self.focus_search()

    def _make_cart_item(self, value: object, *, editable: bool = False, align_center: bool = False) -> QTableWidgetItem:
        item = QTableWidgetItem(str(value))
        flags = Qt.ItemIsSelectable | Qt.ItemIsEnabled
        if editable:
            flags |= Qt.ItemIsEditable
        item.setFlags(flags)
        if align_center:
            item.setTextAlignment(Qt.AlignCenter)
        return item

    def refresh_cart(self, *, select_row: int | None = None, select_col: int | None = None) -> None:
        current_row = self.cart_table.currentRow()
        current_col = self.cart_table.currentColumn()
        if select_row is None:
            select_row = current_row if current_row >= 0 else 0
        if select_col is None:
            select_col = current_col if current_col >= 0 else 1

        self.current_settings = self.settings.get_all()
        self._syncing_cart_table = True
        try:
            self.cart_table.setRowCount(len(self.cart))
            total = money("0")
            for r, line in enumerate(self.cart):
                line_total = money(line["quantity"] * line["unit_price"])
                total = money(total + line_total)
                values = [
                    line["name"],
                    display_qty(line["quantity"]),
                    display(line["unit_price"]),
                    money_label(line_total, self.current_settings),
                    line["product_id"],
                ]
                for c, value in enumerate(values):
                    item = self._make_cart_item(
                        value,
                        editable=c in self.EDITABLE_CART_COLUMNS,
                        align_center=c in {1, 2, 3},
                    )
                    if c in self.EDITABLE_CART_COLUMNS:
                        item.setToolTip("يمكن تعديل هذه الخانة مباشرة من الكيبورد")
                    self.cart_table.setItem(r, c, item)
            self.total_label.setText(f"الإجمالي: {money_label(total, self.current_settings)}")
        finally:
            self._syncing_cart_table = False

        if self.cart:
            select_row = max(0, min(select_row, len(self.cart) - 1))
            if select_col not in self.EDITABLE_CART_COLUMNS:
                select_col = 1
            self.cart_table.setCurrentCell(select_row, select_col)

    def on_cart_cell_changed(self, row: int, column: int) -> None:
        if self._syncing_cart_table or column not in self.EDITABLE_CART_COLUMNS:
            return
        if row < 0 or row >= len(self.cart):
            return
        item = self.cart_table.item(row, column)
        if not item:
            return

        line = self.cart[row]
        try:
            if column == 1:
                value = qty(item.text())
                if value <= 0:
                    raise ValueError("الكمية يجب أن تكون أكبر من صفر")
                line["quantity"] = value
            elif column == 2:
                value = money(item.text())
                if value < 0:
                    raise ValueError("سعر الشراء لا يمكن أن يكون سالباً")
                line["unit_price"] = value
        except Exception as exc:
            show_error(self, "قيمة غير صالحة", str(exc))
            self.refresh_cart(select_row=row, select_col=column)
            return

        self.refresh_cart(select_row=row, select_col=column)

    def edit_current_cart_cell(self) -> None:
        row = self.cart_table.currentRow()
        col = self.cart_table.currentColumn()
        if row < 0 or col not in self.EDITABLE_CART_COLUMNS:
            return
        item = self.cart_table.item(row, col)
        if item:
            self.cart_table.editItem(item)

    def move_to_next_editable_cell(self) -> None:
        if not self.cart:
            return
        row = self.cart_table.currentRow()
        col = self.cart_table.currentColumn()
        if row < 0:
            row = 0
        editable_cols = [1, 2]
        if col not in editable_cols:
            next_row, next_col = row, 1
        else:
            idx = editable_cols.index(col)
            if idx < len(editable_cols) - 1:
                next_row, next_col = row, editable_cols[idx + 1]
            else:
                next_row, next_col = row + 1, editable_cols[0]
                if next_row >= len(self.cart):
                    self.focus_search()
                    return
        self.cart_table.setCurrentCell(next_row, next_col)
        self.edit_current_cart_cell()

    def focus_search(self) -> None:
        self.search.setFocus()
        self.search.selectAll()

    def remove_selected_cart_row(self) -> None:
        row = self.cart_table.currentRow()
        if row < 0 or row >= len(self.cart):
            return
        self.cart.pop(row)
        next_row = min(row, len(self.cart) - 1)
        self.refresh_cart(select_row=next_row, select_col=1)
        if not self.cart:
            self.focus_search()

    def save_purchase(self) -> None:
        try:
            paid_text = self.paid_amount.text().strip()
            paid = paid_text if paid_text else "0"
            result = self.purchases.create_purchase(
                self.cart,
                supplier_name=self.supplier_name.text(),
                paid_amount=paid,
                update_product_cost=self.update_cost_checkbox.isChecked(),
            )
            self.cart.clear()
            self.paid_amount.clear()
            self.search.clear()
            self.refresh()
            if self.on_purchase_saved:
                self.on_purchase_saved()
            show_info(
                self,
                "تم حفظ المشتريات",
                f"تم حفظ فاتورة {result['invoice_number']} وزيادة المخزون بنجاح.",
            )
            self.focus_search()
        except Exception as exc:
            show_error(self, "خطأ في حفظ المشتريات", str(exc))

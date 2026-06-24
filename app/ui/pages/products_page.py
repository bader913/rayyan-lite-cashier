from __future__ import annotations

from pathlib import Path
from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.core.currency import money_label
from app.core.money import display, display_qty, money
from app.db.database import Database
from app.services.product_excel_service import ProductExcelService
from app.services.products_service import ProductsService
from app.services.settings_service import SettingsService
from app.ui.widgets import show_error, show_info, show_warning


class ProductsPage(QWidget):
    def __init__(self, db: Database, on_products_changed: Callable[[], None] | None = None):
        super().__init__()
        self.service = ProductsService(db)
        self.excel = ProductExcelService(db)
        self.settings = SettingsService(db)
        self.current_settings = self.settings.get_all()
        self.on_products_changed = on_products_changed
        self.selected_product_id: int | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        title = QLabel("المنتجات")
        title.setObjectName("pageTitle")
        root.addWidget(title)

        top = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("بحث بالاسم أو الباركود أو الفئة")
        self.search.textChanged.connect(self.refresh)
        top.addWidget(self.search, 1)
        import_btn = QPushButton("استيراد Excel")
        import_btn.setObjectName("accent")
        import_btn.clicked.connect(self.import_excel)
        top.addWidget(import_btn)
        export_btn = QPushButton("تصدير Excel")
        export_btn.setObjectName("success")
        export_btn.clicked.connect(self.export_excel)
        top.addWidget(export_btn)
        refresh_btn = QPushButton("تحديث")
        refresh_btn.setObjectName("secondary")
        refresh_btn.clicked.connect(self.refresh)
        top.addWidget(refresh_btn)
        root.addLayout(top)

        body = QHBoxLayout()
        self.table = QTableWidget(0, 10)
        self.table.setHorizontalHeaderLabels(["ID", "الباركود", "الاسم", "الفئة", "الوحدة", "شراء", "بيع", "ربح", "الكمية", "حد التنبيه"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.itemSelectionChanged.connect(self.load_selected)
        body.addWidget(self.table, 2)

        form_wrap = QWidget()
        form = QFormLayout(form_wrap)
        self.name = QLineEdit()
        self.barcode = QLineEdit()
        self.category = QLineEdit()
        self.supplier = QLineEdit()
        self.unit = QLineEdit("قطعة")
        self.purchase_price = QLineEdit("0")
        self.retail_price = QLineEdit("0")
        self.wholesale_price = QLineEdit("0")
        self.stock_quantity = QLineEdit("0")
        self.min_stock_level = QLineEdit("0")
        self.notes = QTextEdit()
        self.notes.setFixedHeight(70)
        form.addRow("اسم المنتج", self.name)
        form.addRow("باركود", self.barcode)
        form.addRow("الفئة", self.category)
        form.addRow("المورد", self.supplier)
        form.addRow("الوحدة", self.unit)
        form.addRow("سعر الشراء", self.purchase_price)
        form.addRow("سعر البيع مفرق", self.retail_price)
        form.addRow("سعر البيع جملة", self.wholesale_price)
        form.addRow("الكمية", self.stock_quantity)
        form.addRow("حد التنبيه", self.min_stock_level)
        form.addRow("ملاحظات", self.notes)

        buttons = QHBoxLayout()
        add_btn = QPushButton("إضافة")
        add_btn.setObjectName("success")
        add_btn.clicked.connect(self.add_product)
        update_btn = QPushButton("حفظ تعديل")
        update_btn.clicked.connect(self.update_product)
        clear_btn = QPushButton("تفريغ")
        clear_btn.setObjectName("secondary")
        clear_btn.clicked.connect(self.clear_form)
        buttons.addWidget(add_btn)
        buttons.addWidget(update_btn)
        buttons.addWidget(clear_btn)
        form.addRow(buttons)
        body.addWidget(form_wrap, 1)
        root.addLayout(body, 1)
        self.refresh()

    def form_data(self) -> dict:
        return {
            "name": self.name.text(),
            "barcode": self.barcode.text(),
            "category": self.category.text(),
            "supplier": self.supplier.text(),
            "unit": self.unit.text(),
            "purchase_price": self.purchase_price.text(),
            "retail_price": self.retail_price.text(),
            "wholesale_price": self.wholesale_price.text(),
            "stock_quantity": self.stock_quantity.text(),
            "min_stock_level": self.min_stock_level.text(),
            "notes": self.notes.toPlainText(),
        }

    def clear_form(self) -> None:
        self.selected_product_id = None
        self.name.clear()
        self.barcode.clear()
        self.category.clear()
        self.supplier.clear()
        self.unit.setText("قطعة")
        self.purchase_price.setText("0")
        self.retail_price.setText("0")
        self.wholesale_price.setText("0")
        self.stock_quantity.setText("0")
        self.min_stock_level.setText("0")
        self.notes.clear()
        self.table.clearSelection()

    def refresh(self) -> None:
        self.current_settings = self.settings.get_all()
        rows = self.service.list_products(self.search.text())
        self.table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            profit = money(row["retail_price"]) - money(row["purchase_price"])
            values = [
                row["id"],
                row.get("barcode") or "",
                row["name"],
                row.get("category") or "",
                row["unit"],
                money_label(row["purchase_price"], self.current_settings),
                money_label(row["retail_price"], self.current_settings),
                money_label(profit, self.current_settings),
                display_qty(row["stock_quantity"]),
                display_qty(row["min_stock_level"]),
            ]
            for c, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                if c == 0:
                    item.setData(Qt.UserRole, int(row["id"]))
                if c in {0, 5, 6, 7, 8, 9}:
                    item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(r, c, item)

    def load_selected(self) -> None:
        selected = self.table.selectedItems()
        if not selected:
            return
        row_index = selected[0].row()
        id_item = self.table.item(row_index, 0)
        if not id_item:
            return
        product_id = int(id_item.text())
        product = self.service.get_product(product_id)
        if not product:
            return
        self.selected_product_id = product_id
        self.name.setText(product["name"])
        self.barcode.setText(product.get("barcode") or "")
        self.category.setText(product.get("category") or "")
        self.supplier.setText(product.get("supplier") or "")
        self.unit.setText(product.get("unit") or "قطعة")
        self.purchase_price.setText(display(product["purchase_price"]))
        self.retail_price.setText(display(product["retail_price"]))
        self.wholesale_price.setText(display(product.get("wholesale_price") or "0"))
        self.stock_quantity.setText(display_qty(product["stock_quantity"]))
        self.min_stock_level.setText(display_qty(product["min_stock_level"]))
        self.notes.setPlainText(product.get("notes") or "")

    def add_product(self) -> None:
        try:
            self.service.create_product(self.form_data())
            self.clear_form()
            self.refresh()
            if self.on_products_changed:
                self.on_products_changed()
            show_info(self, "تم", "تمت إضافة المنتج بنجاح")
        except Exception as exc:
            show_error(self, "خطأ", str(exc))

    def update_product(self) -> None:
        if not self.selected_product_id:
            show_error(self, "تنبيه", "اختر منتجاً من الجدول أولاً")
            return
        try:
            self.service.update_product(self.selected_product_id, self.form_data())
            self.refresh()
            if self.on_products_changed:
                self.on_products_changed()
            show_info(self, "تم", "تم حفظ التعديل بنجاح")
        except Exception as exc:
            show_error(self, "خطأ", str(exc))

    def import_excel(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "اختر ملف منتجات Excel",
            str(Path.home() / "Downloads"),
            "Excel Files (*.xlsx)",
        )
        if not path:
            return
        try:
            result = self.excel.import_excel(path)
            self.refresh()
            if self.on_products_changed:
                self.on_products_changed()
            message = (
                f"تم الاستيراد\n"
                f"جديد: {result['created']}\n"
                f"محدث: {result['updated']}\n"
                f"متجاهل: {result['skipped']}"
            )
            if result["errors"]:
                message += "\n\nأخطاء أولية:\n" + "\n".join(result["errors"][:8])
                show_warning(self, "تم مع ملاحظات", message)
            else:
                show_info(self, "تم", message)
        except Exception as exc:
            show_error(self, "خطأ في استيراد المنتجات", str(exc))

    def export_excel(self) -> None:
        default = Path.home() / "Downloads" / "products_export_lite.xlsx"
        path, _ = QFileDialog.getSaveFileName(
            self,
            "حفظ ملف المنتجات",
            str(default),
            "Excel Files (*.xlsx)",
        )
        if not path:
            return
        try:
            out = self.excel.export_excel(path)
            show_info(self, "تم", f"تم تصدير المنتجات هنا:\n{out}")
        except Exception as exc:
            show_error(self, "خطأ في تصدير المنتجات", str(exc))

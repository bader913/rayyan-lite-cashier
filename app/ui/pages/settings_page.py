from __future__ import annotations

from typing import Callable

from PySide6.QtWidgets import QCheckBox, QFrame, QFormLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget

from app.db.database import Database
from app.services.backup_service import BackupService
from app.services.settings_service import SettingsService
from app.ui.widgets import show_error, show_info


class SettingsPage(QWidget):
    def __init__(self, db: Database, on_settings_changed: Callable[[], None] | None = None):
        super().__init__()
        self.settings = SettingsService(db)
        self.backups = BackupService(db)
        self.on_settings_changed = on_settings_changed

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(12)
        title = QLabel("الإعدادات والنسخ الاحتياطي")
        title.setObjectName("pageTitle")
        root.addWidget(title)

        store_card = QFrame()
        store_card.setObjectName("contentCard")
        form = QFormLayout(store_card)
        form.setContentsMargins(16, 16, 16, 16)
        self.store_name = QLineEdit()
        self.allow_negative = QCheckBox("السماح بالبيع حتى لو المخزون غير كافٍ")
        form.addRow("اسم المحل", self.store_name)
        form.addRow("المخزون", self.allow_negative)
        root.addWidget(store_card)

        currency_title = QLabel("إعدادات العملة وسعر الصرف")
        currency_title.setObjectName("sectionTitle")
        root.addWidget(currency_title)

        currency_card = QFrame()
        currency_card.setObjectName("contentCard")
        currency_form = QFormLayout(currency_card)
        currency_form.setContentsMargins(16, 16, 16, 16)
        self.currency_name = QLineEdit()
        self.currency_symbol = QLineEdit()
        self.exchange_currency_name = QLineEdit()
        self.exchange_currency_symbol = QLineEdit()
        self.exchange_rate = QLineEdit()
        self.exchange_rate.setPlaceholderText("مثال: 14000 إذا كل 1 دولار = 14000 ل.س")
        currency_form.addRow("العملة الأساسية", self.currency_name)
        currency_form.addRow("رمز العملة", self.currency_symbol)
        currency_form.addRow("عملة المقارنة", self.exchange_currency_name)
        currency_form.addRow("رمز عملة المقارنة", self.exchange_currency_symbol)
        currency_form.addRow("سعر الصرف", self.exchange_rate)
        root.addWidget(currency_card)

        save_btn = QPushButton("حفظ الإعدادات")
        save_btn.clicked.connect(self.save_settings)
        root.addWidget(save_btn)

        backup_btn = QPushButton("إنشاء نسخة احتياطية ZIP")
        backup_btn.setObjectName("success")
        backup_btn.clicked.connect(self.create_backup)
        root.addWidget(backup_btn)
        root.addStretch(1)
        self.refresh()

    def refresh(self) -> None:
        values = self.settings.get_all()
        self.store_name.setText(values.get("store_name", "Rayyan Lite"))
        self.allow_negative.setChecked(values.get("allow_negative_stock", "false") == "true")
        self.currency_name.setText(values.get("currency_name", "ليرة سورية"))
        self.currency_symbol.setText(values.get("currency_symbol", "ل.س"))
        self.exchange_currency_name.setText(values.get("exchange_currency_name", "دولار"))
        self.exchange_currency_symbol.setText(values.get("exchange_currency_symbol", "$"))
        self.exchange_rate.setText(values.get("exchange_rate", "1.0000"))

    def save_settings(self) -> None:
        try:
            self.settings.set("store_name", self.store_name.text().strip() or "Rayyan Lite")
            self.settings.set("allow_negative_stock", "true" if self.allow_negative.isChecked() else "false")
            self.settings.save_currency_settings(
                currency_name=self.currency_name.text(),
                currency_symbol=self.currency_symbol.text(),
                exchange_currency_name=self.exchange_currency_name.text(),
                exchange_currency_symbol=self.exchange_currency_symbol.text(),
                exchange_rate=self.exchange_rate.text(),
            )
            if self.on_settings_changed:
                self.on_settings_changed()
            show_info(self, "تم", "تم حفظ الإعدادات")
        except Exception as exc:
            show_error(self, "خطأ", str(exc))

    def create_backup(self) -> None:
        try:
            path = self.backups.create_backup()
            show_info(self, "تم إنشاء النسخة", f"تم إنشاء النسخة هنا:\n{path}")
        except Exception as exc:
            show_error(self, "خطأ", str(exc))

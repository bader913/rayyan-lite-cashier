from __future__ import annotations

from pathlib import Path
from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QInputDialog,
    QSizePolicy,
)

from app.db.database import Database
from app.services.backup_service import BackupService
from app.services.settings_service import SettingsService
from app.ui.widgets import confirm, show_error, show_info, show_warning


class SettingsPage(QWidget):
    def __init__(self, db: Database, on_settings_changed: Callable[[], None] | None = None):
        super().__init__()
        self.settings = SettingsService(db)
        self.backups = BackupService(db)
        self.on_settings_changed = on_settings_changed

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(14)
        title = QLabel("الإعدادات والنسخ الاحتياطي")
        title.setObjectName("pageTitle")
        root.addWidget(title)

        def make_wide_field(widget) -> None:
            widget.setMinimumWidth(430)
            widget.setMinimumHeight(40)
            widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        store_card = QFrame()
        store_card.setObjectName("contentCard")
        form = QFormLayout(store_card)
        form.setContentsMargins(16, 16, 16, 16)
        form.setSpacing(12)
        form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        form.setLabelAlignment(Qt.AlignRight)
        self.store_name = QLineEdit()
        self.allow_negative = QCheckBox("السماح بالبيع حتى لو المخزون غير كافٍ")
        self.theme_mode = QComboBox()
        self.theme_mode.addItem("فاتح", "light")
        self.theme_mode.addItem("داكن", "dark")
        make_wide_field(self.store_name)
        make_wide_field(self.theme_mode)
        form.addRow("اسم المحل", self.store_name)
        form.addRow("سمة الواجهة", self.theme_mode)
        form.addRow("المخزون", self.allow_negative)
        root.addWidget(store_card)

        currency_title = QLabel("إعدادات العملة وسعر الصرف")
        currency_title.setObjectName("sectionTitle")
        root.addWidget(currency_title)

        currency_card = QFrame()
        currency_card.setObjectName("contentCard")
        currency_form = QFormLayout(currency_card)
        currency_form.setContentsMargins(16, 16, 16, 16)
        currency_form.setSpacing(12)
        currency_form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        currency_form.setLabelAlignment(Qt.AlignRight)
        self.currency_name = QLineEdit()
        self.currency_symbol = QLineEdit()
        self.exchange_currency_name = QLineEdit()
        self.exchange_currency_symbol = QLineEdit()
        self.exchange_rate = QLineEdit()
        self.exchange_rate.setPlaceholderText("مثال: 14000 إذا كل 1 دولار = 14000 ل.س")
        for field in [
            self.currency_name,
            self.currency_symbol,
            self.exchange_currency_name,
            self.exchange_currency_symbol,
            self.exchange_rate,
        ]:
            make_wide_field(field)
        self.exchange_rate.setMinimumWidth(520)
        currency_form.addRow("العملة الأساسية", self.currency_name)
        currency_form.addRow("رمز العملة", self.currency_symbol)
        currency_form.addRow("عملة المقارنة", self.exchange_currency_name)
        currency_form.addRow("رمز عملة المقارنة", self.exchange_currency_symbol)
        currency_form.addRow("سعر الصرف", self.exchange_rate)
        root.addWidget(currency_card)

        save_btn = QPushButton("حفظ الإعدادات")
        save_btn.clicked.connect(self.save_settings)
        root.addWidget(save_btn)

        backup_title = QLabel("النسخ الاحتياطي وإدارة البيانات")
        backup_title.setObjectName("sectionTitle")
        root.addWidget(backup_title)

        backup_card = QFrame()
        backup_card.setObjectName("contentCard")
        backup_layout = QVBoxLayout(backup_card)
        backup_layout.setContentsMargins(16, 16, 16, 16)
        backup_layout.setSpacing(10)

        hint = QLabel("يمكنك إنشاء نسخة احتياطية ZIP، واستيرادها لاحقاً، أو مسح البيانات التجارية بعد أخذ نسخة آمنة تلقائياً.")
        hint.setWordWrap(True)
        hint.setObjectName("hintText")
        backup_layout.addWidget(hint)

        row1 = QHBoxLayout()
        backup_btn = QPushButton("تصدير نسخة احتياطية ZIP")
        backup_btn.setObjectName("success")
        backup_btn.clicked.connect(self.create_backup)
        restore_btn = QPushButton("استيراد نسخة احتياطية")
        restore_btn.setObjectName("accent")
        restore_btn.clicked.connect(self.restore_backup)
        row1.addWidget(backup_btn)
        row1.addWidget(restore_btn)
        backup_layout.addLayout(row1)

        clear_btn = QPushButton("مسح البيانات التجارية")
        clear_btn.setObjectName("danger")
        clear_btn.clicked.connect(self.clear_business_data)
        backup_layout.addWidget(clear_btn)

        clear_hint = QLabel("المسح التجاري يبقي الإعدادات والمنتجات والزبائن، لكنه يزيل الفواتير والحركات ويصفر المخزون والأرصدة ويعيد ترقيم الفواتير. يتم أخذ نسخة احتياطية تلقائياً قبل التنفيذ.")
        clear_hint.setWordWrap(True)
        clear_hint.setObjectName("hintText")
        backup_layout.addWidget(clear_hint)

        root.addWidget(backup_card)
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
        theme_mode = values.get("theme_mode", "light")
        idx = self.theme_mode.findData(theme_mode)
        self.theme_mode.setCurrentIndex(max(idx, 0))

    def save_settings(self) -> None:
        try:
            self.settings.set("store_name", self.store_name.text().strip() or "Rayyan Lite")
            self.settings.set("allow_negative_stock", "true" if self.allow_negative.isChecked() else "false")
            self.settings.set("theme_mode", str(self.theme_mode.currentData() or "light"))
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

    def restore_backup(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "اختر نسخة احتياطية",
            str(Path.home() / "Downloads"),
            "ZIP Backup (*.zip)",
        )
        if not path:
            return
        if not confirm(self, "تأكيد الاستيراد", "سيتم استيراد النسخة المحددة وأخذ نسخة احتياطية تلقائية من الوضع الحالي قبل الاستبدال. هل تريد المتابعة؟"):
            return
        try:
            restored_path = self.backups.restore_backup(path)
            if self.on_settings_changed:
                self.on_settings_changed()
            self.refresh()
            show_warning(
                self,
                "تم الاستيراد",
                f"تم استيراد النسخة الاحتياطية إلى:\n{restored_path}\n\nتم تحديث البيانات، ويفضل إغلاق البرنامج وفتحه من جديد للتأكد من تحميل كل الشاشات بأحدث حالة.",
            )
        except Exception as exc:
            show_error(self, "خطأ في الاستيراد", str(exc))

    def clear_business_data(self) -> None:
        if not confirm(self, "تحذير شديد", "سيتم مسح البيانات التجارية الحالية بعد أخذ نسخة احتياطية تلقائية. هل تريد المتابعة؟"):
            return
        confirm_text, ok = QInputDialog.getText(self, "تأكيد نهائي", "اكتب كلمة مسح للتأكيد النهائي:")
        if not ok:
            return
        if confirm_text.strip() != "مسح":
            show_warning(self, "تم الإلغاء", "لم يتم تنفيذ المسح لأن كلمة التأكيد غير صحيحة")
            return
        try:
            backup_path = self.backups.clear_business_data()
            if self.on_settings_changed:
                self.on_settings_changed()
            show_info(self, "تم المسح", f"تم مسح البيانات التجارية بنجاح.\nتم إنشاء نسخة احتياطية تلقائية هنا:\n{backup_path}")
        except Exception as exc:
            show_error(self, "خطأ في المسح", str(exc))

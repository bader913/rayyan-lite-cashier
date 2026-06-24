from __future__ import annotations

from html import escape
from pathlib import Path
from tempfile import gettempdir
from typing import Any, Mapping

from PySide6.QtCore import QMarginsF, QSizeF
from PySide6.QtGui import QPageLayout, QPageSize, QTextDocument
from PySide6.QtPrintSupport import QPrintDialog, QPrinter
from PySide6.QtWidgets import QWidget

from app.core.currency import exchange_hint, money_label
from app.core.money import display_qty


def build_simple_receipt_text(invoice_number: str, items: list[dict], total: str) -> str:
    lines = ["Rayyan Lite", f"فاتورة: {invoice_number}", "-" * 32]
    for item in items:
        lines.append(f"{item.get('name','')} x {item.get('quantity','')} = {item.get('total','')}")
    lines.extend(["-" * 32, f"الإجمالي: {total}"])
    return "\n".join(lines)


def build_thermal_receipt_html(sale: Mapping[str, Any], items: list[Mapping[str, Any]], settings: Mapping[str, str]) -> str:
    store_name = escape(settings.get("store_name") or "Rayyan Lite")
    invoice_number = escape(str(sale.get("invoice_number") or ""))
    created_at = escape(str(sale.get("created_at") or ""))
    payment = "نقدي" if sale.get("payment_method") == "cash" else "بطاقة"
    total = money_label(sale.get("total_amount", "0"), settings)
    paid = money_label(sale.get("paid_amount", "0"), settings)
    equiv = exchange_hint(sale.get("total_amount", "0"), settings)

    rows: list[str] = []
    for index, item in enumerate(items, start=1):
        name = escape(str(item.get("product_name") or ""))
        qty_text = escape(display_qty(item.get("quantity", "0")))
        unit_price = escape(money_label(item.get("unit_price", "0"), settings))
        total_price = escape(money_label(item.get("total_price", "0"), settings))
        rows.append(
            f"""
            <tr>
              <td class="idx">{index}</td>
              <td class="name">{name}<div class="muted">{qty_text} × {unit_price}</div></td>
              <td class="total">{total_price}</td>
            </tr>
            """
        )

    equiv_html = f"<div class='exchange'>{escape(equiv)}</div>" if equiv else ""

    return f"""<!doctype html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<style>
  @page {{ size: 80mm auto; margin: 3mm; }}
  body {{
    width: 72mm;
    margin: 0 auto;
    direction: rtl;
    font-family: 'Segoe UI', 'Tahoma', sans-serif;
    color: #111;
    font-size: 10.5pt;
  }}
  .center {{ text-align: center; }}
  .store {{ font-size: 15pt; font-weight: 800; margin-bottom: 2mm; }}
  .muted {{ color: #555; font-size: 8.8pt; margin-top: 1mm; }}
  .line {{ border-top: 1px dashed #333; margin: 2.5mm 0; }}
  table {{ width: 100%; border-collapse: collapse; }}
  td {{ vertical-align: top; padding: 1.2mm 0; }}
  td.idx {{ width: 6mm; color: #555; }}
  td.name {{ text-align: right; }}
  td.total {{ text-align: left; white-space: nowrap; font-weight: 700; }}
  .summary-row {{ display: flex; justify-content: space-between; gap: 4mm; margin: 1.2mm 0; }}
  .grand {{ font-size: 13pt; font-weight: 900; }}
  .exchange {{ text-align: center; color: #333; margin-top: 1.5mm; font-size: 9.2pt; }}
  .footer {{ text-align: center; margin-top: 3mm; font-size: 9pt; }}
</style>
</head>
<body>
  <div class="center store">{store_name}</div>
  <div class="center">فاتورة بيع</div>
  <div class="center muted">{invoice_number}</div>
  <div class="center muted">{created_at}</div>
  <div class="line"></div>
  <table>
    <tbody>
      {''.join(rows)}
    </tbody>
  </table>
  <div class="line"></div>
  <div class="summary-row grand"><span>الإجمالي</span><span>{escape(total)}</span></div>
  <div class="summary-row"><span>المدفوع</span><span>{escape(paid)}</span></div>
  <div class="summary-row"><span>الدفع</span><span>{payment}</span></div>
  {equiv_html}
  <div class="line"></div>
  <div class="footer">شكراً لزيارتكم</div>
</body>
</html>
"""


def write_receipt_preview(invoice_number: str, text: str) -> Path:
    path = Path(gettempdir()) / f"rayyan_lite_receipt_{invoice_number}.txt"
    path.write_text(text, encoding="utf-8")
    return path


def write_receipt_html_preview(sale: Mapping[str, Any], items: list[Mapping[str, Any]], settings: Mapping[str, str]) -> Path:
    safe_invoice = str(sale.get("invoice_number") or "receipt").replace("/", "-").replace("\\", "-")
    path = Path(gettempdir()) / f"rayyan_lite_receipt_{safe_invoice}.html"
    path.write_text(build_thermal_receipt_html(sale, items, settings), encoding="utf-8")
    return path


def print_thermal_receipt(parent: QWidget, sale: Mapping[str, Any], items: list[Mapping[str, Any]], settings: Mapping[str, str]) -> bool:
    printer = QPrinter(QPrinter.HighResolution)
    printer.setDocName(f"Rayyan Lite {sale.get('invoice_number', '')}")
    printer.setPageSize(QPageSize(QSizeF(80, 220), QPageSize.Millimeter, "80mm Thermal"))
    printer.setPageMargins(QMarginsF(3, 3, 3, 3), QPageLayout.Millimeter)

    dialog = QPrintDialog(printer, parent)
    dialog.setWindowTitle("طباعة الفاتورة الحرارية")
    if dialog.exec() != QPrintDialog.Accepted:
        return False

    doc = QTextDocument()
    doc.setHtml(build_thermal_receipt_html(sale, items, settings))
    doc.print_(printer)
    return True

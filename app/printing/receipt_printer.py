from __future__ import annotations

from html import escape
from pathlib import Path
from tempfile import gettempdir
from typing import Any, Mapping

from PySide6.QtCore import QMarginsF, QSizeF
from PySide6.QtGui import QPageLayout, QPageSize, QTextDocument
from PySide6.QtPrintSupport import QPrintDialog, QPrinter
from PySide6.QtWidgets import QWidget

from app.core.currency import exchange_hint, exchange_label, money_label
from app.core.money import dec, display, display_qty, money


def build_simple_receipt_text(invoice_number: str, items: list[dict], total: str) -> str:
    lines = ["Rayyan Lite", f"فاتورة: {invoice_number}", "-" * 32]
    for item in items:
        lines.append(f"{item.get('name','')} x {item.get('quantity','')} = {item.get('total','')}")
    lines.extend(["-" * 32, f"الإجمالي: {total}"])
    return "\n".join(lines)


def _format_change(sale: Mapping[str, Any], settings: Mapping[str, str]) -> str:
    paid = money(sale.get("paid_amount", "0"))
    total = money(sale.get("total_amount", "0"))
    diff = money(paid - total)
    if diff == dec("0"):
        return ""
    label = "باقي/مرتجع للزبون" if diff > 0 else "متبقي"
    return f"<div class='summary-row'><span>{label}</span><span>{escape(money_label(abs(diff), settings))}</span></div>"


def build_thermal_receipt_html(sale: Mapping[str, Any], items: list[Mapping[str, Any]], settings: Mapping[str, str]) -> str:
    store_name = escape(settings.get("store_name") or "Rayyan Lite")
    invoice_number = escape(str(sale.get("invoice_number") or ""))
    created_at = escape(str(sale.get("created_at") or ""))
    edited_at = str(sale.get("edited_at") or "").strip()
    edit_count = int(sale.get("edit_count") or 0)
    payment = "نقدي" if sale.get("payment_method") == "cash" else "بطاقة"
    total = money_label(sale.get("total_amount", "0"), settings)
    paid = money_label(sale.get("paid_amount", "0"), settings)
    equiv = exchange_hint(sale.get("total_amount", "0"), settings)
    exchange_rate_text = ""
    if equiv:
        exchange_rate_text = f"كل 1 {escape(settings.get('exchange_currency_symbol') or '$')} = {escape(str(settings.get('exchange_rate') or '1'))} {escape(settings.get('currency_symbol') or 'ل.س')}"

    rows: list[str] = []
    for index, item in enumerate(items, start=1):
        name = escape(str(item.get("product_name") or ""))
        unit = escape(str(item.get("unit") or ""))
        qty_text = escape(display_qty(item.get("quantity", "0")))
        unit_price = escape(money_label(item.get("unit_price", "0"), settings))
        total_price = escape(money_label(item.get("total_price", "0"), settings))
        discount_value = money(item.get("discount", "0"))
        discount_html = ""
        if discount_value > 0:
            discount_html = f"<div class='muted'>خصم: {escape(money_label(discount_value, settings))}</div>"
        rows.append(
            f"""
            <tr>
              <td class="idx">{index}</td>
              <td class="name">
                <div class="product-name">{name}</div>
                <div class="muted">{qty_text} {unit} × {unit_price}</div>
                {discount_html}
              </td>
              <td class="total">{total_price}</td>
            </tr>
            """
        )

    equiv_html = f"<div class='exchange'>{escape(equiv)}</div>" if equiv else ""
    rate_html = f"<div class='muted center'>{exchange_rate_text}</div>" if exchange_rate_text else ""
    edited_html = ""
    if edit_count > 0:
        edited_html = f"<div class='edited'>فاتورة معدلة × {edit_count}{' — ' + escape(edited_at) if edited_at else ''}</div>"
    change_html = _format_change(sale, settings)

    return f"""<!doctype html>
<html lang="ar" dir="rtl">
<head>
<meta charset="utf-8">
<style>
  @page {{ size: 80mm auto; margin: 3mm; }}
  * {{ box-sizing: border-box; }}
  body {{
    width: 72mm;
    margin: 0 auto;
    direction: rtl;
    font-family: 'Segoe UI', 'Tahoma', sans-serif;
    color: #111827;
    font-size: 10.2pt;
  }}
  .center {{ text-align: center; }}
  .store {{
    font-size: 15.5pt;
    font-weight: 900;
    margin-bottom: 1mm;
    letter-spacing: .2px;
  }}
  .doc-title {{
    display: inline-block;
    border: 1px solid #111827;
    border-radius: 999px;
    padding: 1mm 4mm;
    font-weight: 900;
    margin: 1mm 0;
  }}
  .muted {{ color: #4b5563; font-size: 8.7pt; margin-top: .8mm; }}
  .edited {{
    color: #7c2d12;
    background: #ffedd5;
    border: 1px solid #fed7aa;
    border-radius: 2mm;
    text-align: center;
    padding: 1mm;
    font-size: 8.5pt;
    font-weight: 800;
    margin: 1.5mm 0;
  }}
  .line {{ border-top: 1px dashed #111827; margin: 2.4mm 0; }}
  .meta {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1mm 2mm;
    font-size: 9pt;
  }}
  .meta div {{ white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
  table {{ width: 100%; border-collapse: collapse; }}
  td {{ vertical-align: top; padding: 1.35mm 0; border-bottom: 1px dotted #d1d5db; }}
  td.idx {{ width: 5.5mm; color: #6b7280; text-align: center; }}
  td.name {{ text-align: right; }}
  .product-name {{ font-weight: 900; line-height: 1.35; }}
  td.total {{ text-align: left; white-space: nowrap; font-weight: 900; }}
  .summary-row {{
    display: flex;
    justify-content: space-between;
    gap: 4mm;
    margin: 1.3mm 0;
  }}
  .summary-row span:last-child {{ font-weight: 800; text-align: left; direction: ltr; }}
  .grand {{
    font-size: 13pt;
    font-weight: 900;
    padding: 1.5mm 0;
    border-top: 1px solid #111827;
    border-bottom: 1px solid #111827;
  }}
  .exchange {{
    text-align: center;
    color: #111827;
    margin-top: 1.5mm;
    font-size: 9.2pt;
    font-weight: 800;
  }}
  .footer {{
    text-align: center;
    margin-top: 3mm;
    font-size: 9pt;
    color: #374151;
  }}
  .brand {{
    text-align:center;
    font-size: 7.5pt;
    color:#6b7280;
    margin-top: 1.5mm;
  }}
</style>
</head>
<body>
  <div class="center store">{store_name}</div>
  <div class="center"><span class="doc-title">فاتورة بيع</span></div>
  <div class="center muted">{invoice_number}</div>
  {edited_html}
  <div class="line"></div>
  <div class="meta">
    <div>التاريخ: {created_at}</div>
    <div>الدفع: {payment}</div>
  </div>
  <div class="line"></div>
  <table>
    <tbody>
      {''.join(rows)}
    </tbody>
  </table>
  <div class="line"></div>
  <div class="summary-row grand"><span>الإجمالي</span><span>{escape(total)}</span></div>
  <div class="summary-row"><span>المدفوع</span><span>{escape(paid)}</span></div>
  {change_html}
  <div class="summary-row"><span>طريقة الدفع</span><span>{payment}</span></div>
  {equiv_html}
  {rate_html}
  <div class="line"></div>
  <div class="footer">شكراً لزيارتكم</div>
  <div class="brand">تمت الطباعة بواسطة Rayyan Lite</div>
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
    printer.setPageSize(QPageSize(QSizeF(80, 240), QPageSize.Millimeter, "80mm Thermal"))
    printer.setPageMargins(QMarginsF(3, 3, 3, 3), QPageLayout.Millimeter)

    dialog = QPrintDialog(printer, parent)
    dialog.setWindowTitle("طباعة الفاتورة الحرارية")
    if dialog.exec() != QPrintDialog.Accepted:
        return False

    doc = QTextDocument()
    doc.setHtml(build_thermal_receipt_html(sale, items, settings))
    doc.print_(printer)
    return True

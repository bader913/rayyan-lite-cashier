from __future__ import annotations

from decimal import Decimal
from typing import Any

from app.core.money import db_text, display, money, qty, qty_text, require_non_negative
from app.db.database import Database
from app.services.settings_service import SettingsService


class SalesService:
    def __init__(self, db: Database):
        self.db = db
        self.settings = SettingsService(db)

    def _next_invoice_number(self, conn, prefix: str = "SALE") -> str:
        row = conn.execute("SELECT last_number FROM invoice_sequences WHERE prefix = ?", (prefix,)).fetchone()
        if not row:
            conn.execute("INSERT INTO invoice_sequences(prefix, last_number) VALUES (?, 0)", (prefix,))
            last_number = 0
        else:
            last_number = int(row["last_number"])
        next_number = last_number + 1
        conn.execute("UPDATE invoice_sequences SET last_number = ? WHERE prefix = ?", (next_number, prefix))
        return f"{prefix}-{next_number:06d}"

    def create_sale(self, items: list[dict[str, Any]], payment_method: str = "cash", paid_amount: object = "0", notes: str = "") -> dict[str, Any]:
        if not items:
            raise ValueError("السلة فارغة")
        if payment_method not in {"cash", "card"}:
            raise ValueError("طريقة الدفع غير مدعومة في النسخة الخفيفة حالياً")

        paid = require_non_negative(money(paid_amount), "المبلغ المدفوع")
        allow_negative_stock = self.settings.get("allow_negative_stock", "false") == "true"

        with self.db.transaction() as conn:
            invoice_number = self._next_invoice_number(conn, "SALE")
            normalized_items: list[dict[str, Any]] = []
            subtotal = Decimal("0.0000")
            total = Decimal("0.0000")
            total_profit = Decimal("0.0000")

            for raw in items:
                product_id = int(raw["product_id"])
                quantity = require_non_negative(qty(raw.get("quantity", "1")), "الكمية")
                if quantity <= 0:
                    raise ValueError("الكمية يجب أن تكون أكبر من صفر")

                row = conn.execute(
                    "SELECT * FROM products WHERE id = ? AND is_active = 1",
                    (product_id,),
                ).fetchone()
                if not row:
                    raise ValueError("منتج غير موجود أو غير فعال")

                stock_before = qty(row["stock_quantity"])
                if not allow_negative_stock and stock_before < quantity:
                    raise ValueError(f"المخزون غير كافٍ للمنتج: {row['name']}")

                unit_price = require_non_negative(money(raw.get("unit_price", row["retail_price"])), "سعر البيع")
                unit_cost = require_non_negative(money(row["purchase_price"]), "تكلفة المنتج")
                discount = require_non_negative(money(raw.get("discount", "0")), "خصم السطر")
                line_before_discount = money(unit_price * quantity)
                if discount > line_before_discount:
                    raise ValueError(f"خصم السطر أكبر من قيمة المنتج: {row['name']}")
                line_total = money(line_before_discount - discount)
                line_profit = money(((unit_price - unit_cost) * quantity) - discount)
                stock_after = qty(stock_before - quantity)

                normalized_items.append(
                    {
                        "product_id": product_id,
                        "name": row["name"],
                        "quantity": quantity,
                        "unit_price": unit_price,
                        "unit_cost": unit_cost,
                        "discount": discount,
                        "line_total": line_total,
                        "line_profit": line_profit,
                        "stock_before": stock_before,
                        "stock_after": stock_after,
                    }
                )
                subtotal = money(subtotal + line_before_discount)
                total = money(total + line_total)
                total_profit = money(total_profit + line_profit)

            if paid == Decimal("0.0000"):
                paid = total
            if paid < total and payment_method in {"cash", "card"}:
                raise ValueError("المبلغ المدفوع أقل من إجمالي الفاتورة")

            sale_cur = conn.execute(
                """
                INSERT INTO sales(invoice_number, subtotal, discount, total_amount, paid_amount, payment_method, notes)
                VALUES (?, ?, '0.0000', ?, ?, ?, ?)
                """,
                (invoice_number, db_text(subtotal), db_text(total), db_text(paid), payment_method, notes.strip() or None),
            )
            sale_id = int(sale_cur.lastrowid)

            for item in normalized_items:
                conn.execute(
                    """
                    INSERT INTO sale_items
                      (sale_id, product_id, quantity, unit_price, unit_cost, discount, total_price, profit_amount)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        sale_id,
                        item["product_id"],
                        qty_text(item["quantity"]),
                        db_text(item["unit_price"]),
                        db_text(item["unit_cost"]),
                        db_text(item["discount"]),
                        db_text(item["line_total"]),
                        db_text(item["line_profit"]),
                    ),
                )
                conn.execute(
                    "UPDATE products SET stock_quantity = ?, updated_at = datetime('now','localtime') WHERE id = ?",
                    (qty_text(item["stock_after"]), item["product_id"]),
                )
                conn.execute(
                    """
                    INSERT INTO stock_movements
                      (product_id, movement_type, quantity_change, quantity_before, quantity_after, reference_id, reference_type, note)
                    VALUES (?, 'sale', ?, ?, ?, ?, 'sale', ?)
                    """,
                    (
                        item["product_id"],
                        qty_text(-item["quantity"]),
                        qty_text(item["stock_before"]),
                        qty_text(item["stock_after"]),
                        sale_id,
                        f"فاتورة {invoice_number}",
                    ),
                )

            return {
                "sale_id": sale_id,
                "invoice_number": invoice_number,
                "subtotal": db_text(subtotal),
                "total_amount": db_text(total),
                "paid_amount": db_text(paid),
                "profit_amount": db_text(total_profit),
            }

    def today_summary(self) -> dict[str, Any]:
        with self.db.connect() as conn:
            row = conn.execute(
                """
                SELECT
                  COALESCE(SUM(CAST(total_amount AS REAL)), 0) AS total_sales,
                  COALESCE(SUM(CAST(paid_amount AS REAL)), 0) AS total_paid,
                  COUNT(*) AS invoice_count
                FROM sales
                WHERE date(created_at) = date('now','localtime')
                """
            ).fetchone()
            profit_row = conn.execute(
                """
                SELECT COALESCE(SUM(CAST(si.profit_amount AS REAL)), 0) AS gross_profit
                FROM sale_items si
                JOIN sales s ON s.id = si.sale_id
                WHERE date(s.created_at) = date('now','localtime')
                """
            ).fetchone()
        return {
            "total_sales": row["total_sales"] if row else 0,
            "total_paid": row["total_paid"] if row else 0,
            "invoice_count": row["invoice_count"] if row else 0,
            "gross_profit": profit_row["gross_profit"] if profit_row else 0,
        }

    def recent_sales(self, limit: int = 50) -> list[dict[str, Any]]:
        with self.db.connect() as conn:
            rows = conn.execute(
                """
                SELECT id, invoice_number, total_amount, paid_amount, payment_method, created_at
                FROM sales
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]

    def get_sale_details(self, sale_id: int) -> dict[str, Any]:
        with self.db.connect() as conn:
            sale = conn.execute(
                """
                SELECT id, invoice_number, subtotal, discount, total_amount, paid_amount, payment_method, notes, created_at
                FROM sales
                WHERE id = ?
                """,
                (sale_id,),
            ).fetchone()
            if not sale:
                raise ValueError("الفاتورة غير موجودة")
            items = conn.execute(
                """
                SELECT
                  si.id, si.product_id, p.name AS product_name, p.barcode, p.unit,
                  si.quantity, si.unit_price, si.unit_cost, si.discount, si.total_price, si.profit_amount
                FROM sale_items si
                JOIN products p ON p.id = si.product_id
                WHERE si.sale_id = ?
                ORDER BY si.id ASC
                """,
                (sale_id,),
            ).fetchall()
        return {"sale": dict(sale), "items": [dict(r) for r in items]}

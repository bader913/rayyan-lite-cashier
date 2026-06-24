from __future__ import annotations

import json
from decimal import Decimal
from typing import Any

from app.core.currency import sale_currency_snapshot
from app.core.money import db_text, money, qty, qty_text, require_non_negative
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

    def _current_currency_snapshot(self) -> dict[str, str]:
        return sale_currency_snapshot(self.settings.get_all())

    def create_sale(self, items: list[dict[str, Any]], payment_method: str = "cash", paid_amount: object = "0", notes: str = "") -> dict[str, Any]:
        if not items:
            raise ValueError("السلة فارغة")
        if payment_method not in {"cash", "card"}:
            raise ValueError("طريقة الدفع غير مدعومة في النسخة الخفيفة حالياً")

        paid = require_non_negative(money(paid_amount), "المبلغ المدفوع")
        allow_negative_stock = self.settings.get("allow_negative_stock", "false") == "true"
        currency_snapshot = self._current_currency_snapshot()

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
                INSERT INTO sales(
                  invoice_number, subtotal, discount, total_amount, paid_amount, payment_method,
                  currency_name, currency_symbol, exchange_currency_name, exchange_currency_symbol, exchange_rate,
                  notes
                )
                VALUES (?, ?, '0.0000', ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    invoice_number,
                    db_text(subtotal),
                    db_text(total),
                    db_text(paid),
                    payment_method,
                    currency_snapshot["currency_name"],
                    currency_snapshot["currency_symbol"],
                    currency_snapshot["exchange_currency_name"],
                    currency_snapshot["exchange_currency_symbol"],
                    currency_snapshot["exchange_rate"],
                    notes.strip() or None,
                ),
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

    def update_sale(
        self,
        sale_id: int,
        items: list[dict[str, Any]],
        *,
        payment_method: str = "cash",
        paid_amount: object = "0",
        reason: str = "تعديل/مرتجع من شاشة الفاتورة",
    ) -> dict[str, Any]:
        if payment_method not in {"cash", "card"}:
            raise ValueError("طريقة الدفع غير مدعومة في النسخة الخفيفة حالياً")
        if not items:
            raise ValueError("لا توجد بنود للتعديل")

        paid = require_non_negative(money(paid_amount), "المبلغ المدفوع")
        allow_negative_stock = self.settings.get("allow_negative_stock", "false") == "true"

        with self.db.transaction() as conn:
            sale = conn.execute("SELECT * FROM sales WHERE id = ?", (sale_id,)).fetchone()
            if not sale:
                raise ValueError("الفاتورة غير موجودة")

            existing_rows = conn.execute(
                """
                SELECT si.*, p.name AS product_name, p.stock_quantity AS current_stock
                FROM sale_items si
                JOIN products p ON p.id = si.product_id
                WHERE si.sale_id = ?
                ORDER BY si.id ASC
                """,
                (sale_id,),
            ).fetchall()
            existing = {int(row["id"]): row for row in existing_rows}
            submitted_ids = {int(raw.get("sale_item_id") or 0) for raw in items}

            existing_ids = set(existing.keys())
            if submitted_ids != existing_ids:
                raise ValueError("يجب إرسال كل بنود الفاتورة عند التعديل حفاظاً على دقة الإجمالي والمخزون")

            normalized: list[dict[str, Any]] = []
            subtotal = Decimal("0.0000")
            total = Decimal("0.0000")
            total_profit = Decimal("0.0000")
            changed = False

            for raw in items:
                sale_item_id = int(raw["sale_item_id"])
                old = existing[sale_item_id]
                product_id = int(old["product_id"])
                old_qty = qty(old["quantity"])
                new_qty = require_non_negative(qty(raw.get("quantity", old["quantity"])), "الكمية")
                unit_price = require_non_negative(money(raw.get("unit_price", old["unit_price"])), "سعر البيع")
                unit_cost = require_non_negative(money(old["unit_cost"]), "تكلفة المنتج")
                discount = require_non_negative(money(raw.get("discount", old["discount"])), "خصم السطر")

                line_before_discount = money(unit_price * new_qty)
                if discount > line_before_discount and new_qty > 0:
                    raise ValueError(f"خصم السطر أكبر من قيمة المنتج: {old['product_name']}")
                if new_qty == Decimal("0.0000") and discount > 0:
                    raise ValueError(f"لا يمكن وضع خصم على بند كميته صفر: {old['product_name']}")

                line_total = money(line_before_discount - discount)
                line_profit = money(((unit_price - unit_cost) * new_qty) - discount)

                if new_qty > 0:
                    subtotal = money(subtotal + line_before_discount)
                    total = money(total + line_total)
                    total_profit = money(total_profit + line_profit)

                qty_delta = qty(new_qty - old_qty)
                if qty_delta != Decimal("0.0000"):
                    product = conn.execute("SELECT stock_quantity FROM products WHERE id = ?", (product_id,)).fetchone()
                    if not product:
                        raise ValueError(f"المنتج غير موجود: {old['product_name']}")
                    stock_before = qty(product["stock_quantity"])
                    # Increasing invoice quantity means more stock goes out.
                    stock_after = qty(stock_before - qty_delta)
                    if not allow_negative_stock and stock_after < 0:
                        raise ValueError(f"المخزون غير كافٍ لتعديل المنتج: {old['product_name']}")
                    movement_type = "adjustment_out" if qty_delta > 0 else "sale_return"
                    note_action = "زيادة كمية ضمن تعديل الفاتورة" if qty_delta > 0 else "مرتجع ضمن تعديل الفاتورة"
                    conn.execute(
                        "UPDATE products SET stock_quantity = ?, updated_at = datetime('now','localtime') WHERE id = ?",
                        (qty_text(stock_after), product_id),
                    )
                    conn.execute(
                        """
                        INSERT INTO stock_movements
                          (product_id, movement_type, quantity_change, quantity_before, quantity_after, reference_id, reference_type, note)
                        VALUES (?, ?, ?, ?, ?, ?, 'sale_edit', ?)
                        """,
                        (
                            product_id,
                            movement_type,
                            qty_text(-qty_delta),
                            qty_text(stock_before),
                            qty_text(stock_after),
                            sale_id,
                            f"{note_action} - فاتورة {sale['invoice_number']}",
                        ),
                    )
                    changed = True

                old_unit_price = money(old["unit_price"])
                old_discount = money(old["discount"])
                if new_qty != old_qty or unit_price != old_unit_price or discount != old_discount:
                    changed = True

                normalized.append(
                    {
                        "sale_item_id": sale_item_id,
                        "product_id": product_id,
                        "quantity": new_qty,
                        "unit_price": unit_price,
                        "unit_cost": unit_cost,
                        "discount": discount,
                        "line_total": line_total,
                        "line_profit": line_profit,
                    }
                )

            if paid == Decimal("0.0000"):
                paid = total
            if paid < total:
                raise ValueError("المبلغ المدفوع أقل من إجمالي الفاتورة بعد التعديل")

            if money(sale["paid_amount"]) != paid or str(sale["payment_method"]) != payment_method:
                changed = True

            for item in normalized:
                if item["quantity"] == Decimal("0.0000"):
                    conn.execute("DELETE FROM sale_items WHERE id = ? AND sale_id = ?", (item["sale_item_id"], sale_id))
                else:
                    conn.execute(
                        """
                        UPDATE sale_items
                        SET quantity = ?, unit_price = ?, unit_cost = ?, discount = ?, total_price = ?, profit_amount = ?
                        WHERE id = ? AND sale_id = ?
                        """,
                        (
                            qty_text(item["quantity"]),
                            db_text(item["unit_price"]),
                            db_text(item["unit_cost"]),
                            db_text(item["discount"]),
                            db_text(item["line_total"]),
                            db_text(item["line_profit"]),
                            item["sale_item_id"],
                            sale_id,
                        ),
                    )

            conn.execute(
                """
                UPDATE sales
                SET subtotal = ?,
                    discount = '0.0000',
                    total_amount = ?,
                    paid_amount = ?,
                    payment_method = ?,
                    edited_at = CASE WHEN ? THEN datetime('now','localtime') ELSE edited_at END,
                    edit_count = edit_count + CASE WHEN ? THEN 1 ELSE 0 END,
                    last_edit_reason = CASE WHEN ? THEN ? ELSE last_edit_reason END
                WHERE id = ?
                """,
                (
                    db_text(subtotal),
                    db_text(total),
                    db_text(paid),
                    payment_method,
                    1 if changed else 0,
                    1 if changed else 0,
                    1 if changed else 0,
                    reason,
                    sale_id,
                ),
            )
            if changed:
                conn.execute(
                    "INSERT INTO app_logs(level, message, context) VALUES ('info', ?, ?)",
                    (
                        f"تم تعديل الفاتورة {sale['invoice_number']}",
                        json.dumps({"sale_id": sale_id, "reason": reason}, ensure_ascii=False),
                    ),
                )

            return {
                "sale_id": sale_id,
                "invoice_number": str(sale["invoice_number"]),
                "subtotal": db_text(subtotal),
                "total_amount": db_text(total),
                "paid_amount": db_text(paid),
                "profit_amount": db_text(total_profit),
                "changed": changed,
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
                SELECT
                  id, invoice_number, total_amount, paid_amount, payment_method, created_at,
                  currency_name, currency_symbol, exchange_currency_name, exchange_currency_symbol, exchange_rate,
                  edit_count, edited_at, last_edit_reason
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
                SELECT
                  id, invoice_number, subtotal, discount, total_amount, paid_amount, payment_method,
                  currency_name, currency_symbol, exchange_currency_name, exchange_currency_symbol, exchange_rate,
                  edit_count, edited_at, last_edit_reason,
                  notes, created_at
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

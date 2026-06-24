from __future__ import annotations

from decimal import Decimal
from typing import Any

from app.core.money import db_text, money, qty, qty_text, require_non_negative
from app.db.database import Database


class PurchasesService:
    def __init__(self, db: Database):
        self.db = db

    def _next_invoice_number(self, conn, prefix: str = "PUR") -> str:
        row = conn.execute("SELECT last_number FROM invoice_sequences WHERE prefix = ?", (prefix,)).fetchone()
        if not row:
            conn.execute("INSERT INTO invoice_sequences(prefix, last_number) VALUES (?, 0)", (prefix,))
            last_number = 0
        else:
            last_number = int(row["last_number"])
        next_number = last_number + 1
        conn.execute("UPDATE invoice_sequences SET last_number = ? WHERE prefix = ?", (next_number, prefix))
        return f"{prefix}-{next_number:06d}"

    def create_purchase(
        self,
        items: list[dict[str, Any]],
        *,
        supplier_name: str = "",
        paid_amount: object = "0",
        notes: str = "",
        update_product_cost: bool = True,
    ) -> dict[str, Any]:
        if not items:
            raise ValueError("فاتورة المشتريات فارغة")

        supplier = supplier_name.strip() or None
        paid = require_non_negative(money(paid_amount), "المبلغ المدفوع")

        with self.db.transaction() as conn:
            invoice_number = self._next_invoice_number(conn, "PUR")
            normalized_items: list[dict[str, Any]] = []
            total = Decimal("0.0000")

            for raw in items:
                product_id = int(raw["product_id"])
                quantity = require_non_negative(qty(raw.get("quantity", "1")), "الكمية")
                if quantity <= 0:
                    raise ValueError("الكمية يجب أن تكون أكبر من صفر")

                product = conn.execute(
                    "SELECT * FROM products WHERE id = ? AND is_active = 1",
                    (product_id,),
                ).fetchone()
                if not product:
                    raise ValueError("منتج غير موجود أو غير فعال")

                unit_price = require_non_negative(money(raw.get("unit_price", product["purchase_price"])), "سعر الشراء")
                line_total = money(quantity * unit_price)
                stock_before = qty(product["stock_quantity"])
                stock_after = qty(stock_before + quantity)

                normalized_items.append(
                    {
                        "product_id": product_id,
                        "product_name": product["name"],
                        "quantity": quantity,
                        "unit_price": unit_price,
                        "line_total": line_total,
                        "stock_before": stock_before,
                        "stock_after": stock_after,
                    }
                )
                total = money(total + line_total)

            if paid == Decimal("0.0000"):
                paid = total

            cur = conn.execute(
                """
                INSERT INTO purchases(invoice_number, supplier_name, total_amount, paid_amount, notes)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    invoice_number,
                    supplier,
                    db_text(total),
                    db_text(paid),
                    notes.strip() or None,
                ),
            )
            purchase_id = int(cur.lastrowid)

            for item in normalized_items:
                conn.execute(
                    """
                    INSERT INTO purchase_items(purchase_id, product_id, quantity, unit_price, total_price)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        purchase_id,
                        item["product_id"],
                        qty_text(item["quantity"]),
                        db_text(item["unit_price"]),
                        db_text(item["line_total"]),
                    ),
                )

                if update_product_cost and supplier:
                    conn.execute(
                        """
                        UPDATE products
                        SET stock_quantity = ?,
                            purchase_price = ?,
                            supplier = COALESCE(NULLIF(supplier, ''), ?),
                            updated_at = datetime('now','localtime')
                        WHERE id = ?
                        """,
                        (
                            qty_text(item["stock_after"]),
                            db_text(item["unit_price"]),
                            supplier,
                            item["product_id"],
                        ),
                    )
                elif update_product_cost:
                    conn.execute(
                        """
                        UPDATE products
                        SET stock_quantity = ?,
                            purchase_price = ?,
                            updated_at = datetime('now','localtime')
                        WHERE id = ?
                        """,
                        (
                            qty_text(item["stock_after"]),
                            db_text(item["unit_price"]),
                            item["product_id"],
                        ),
                    )
                else:
                    conn.execute(
                        """
                        UPDATE products
                        SET stock_quantity = ?,
                            updated_at = datetime('now','localtime')
                        WHERE id = ?
                        """,
                        (
                            qty_text(item["stock_after"]),
                            item["product_id"],
                        ),
                    )

                conn.execute(
                    """
                    INSERT INTO stock_movements
                      (product_id, movement_type, quantity_change, quantity_before, quantity_after, reference_id, reference_type, note)
                    VALUES (?, 'purchase', ?, ?, ?, ?, 'purchase', ?)
                    """,
                    (
                        item["product_id"],
                        qty_text(item["quantity"]),
                        qty_text(item["stock_before"]),
                        qty_text(item["stock_after"]),
                        purchase_id,
                        f"فاتورة مشتريات {invoice_number}",
                    ),
                )

            return {
                "purchase_id": purchase_id,
                "invoice_number": invoice_number,
                "total_amount": db_text(total),
                "paid_amount": db_text(paid),
            }

    def list_recent_purchases(self, limit: int = 100) -> list[dict[str, Any]]:
        with self.db.connect() as conn:
            rows = conn.execute(
                """
                SELECT
                  p.*,
                  COUNT(pi.id) AS items_count,
                  COALESCE(SUM(CAST(pi.quantity AS REAL)), 0) AS total_quantity
                FROM purchases p
                LEFT JOIN purchase_items pi ON pi.purchase_id = p.id
                GROUP BY p.id
                ORDER BY p.created_at DESC, p.id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def get_purchase_details(self, purchase_id: int) -> dict[str, Any] | None:
        with self.db.connect() as conn:
            purchase = conn.execute("SELECT * FROM purchases WHERE id = ?", (purchase_id,)).fetchone()
            if not purchase:
                return None
            items = conn.execute(
                """
                SELECT pi.*, pr.name AS product_name, pr.barcode
                FROM purchase_items pi
                JOIN products pr ON pr.id = pi.product_id
                WHERE pi.purchase_id = ?
                ORDER BY pi.id ASC
                """,
                (purchase_id,),
            ).fetchall()
        return {"purchase": dict(purchase), "items": [dict(item) for item in items]}

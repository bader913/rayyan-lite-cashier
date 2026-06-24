from __future__ import annotations

from decimal import Decimal
from typing import Any

from app.core.money import db_text, dec, display, display_qty, money, qty, qty_text, require_non_negative
from app.db.database import Database


class ProductsService:
    def __init__(self, db: Database):
        self.db = db

    def list_products(self, search: str = "", active_only: bool = True, limit: int = 500) -> list[dict[str, Any]]:
        params: list[Any] = []
        where: list[str] = []
        if active_only:
            where.append("is_active = 1")
        term = search.strip()
        if term:
            where.append("(name LIKE ? OR barcode LIKE ?)")
            like = f"%{term}%"
            params.extend([like, like])
        sql = "SELECT * FROM products"
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY updated_at DESC, id DESC LIMIT ?"
        params.append(limit)
        with self.db.connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [dict(row) for row in rows]

    def get_product(self, product_id: int) -> dict[str, Any] | None:
        with self.db.connect() as conn:
            row = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
        return dict(row) if row else None

    def create_product(self, data: dict[str, Any]) -> int:
        name = str(data.get("name") or "").strip()
        if not name:
            raise ValueError("اسم المنتج مطلوب")

        barcode = str(data.get("barcode") or "").strip() or None
        unit = str(data.get("unit") or "قطعة").strip() or "قطعة"
        purchase_price = require_non_negative(money(data.get("purchase_price", "0")), "سعر الشراء")
        retail_price = require_non_negative(money(data.get("retail_price", "0")), "سعر البيع")
        stock_quantity = require_non_negative(qty(data.get("stock_quantity", "0")), "الكمية")
        min_stock_level = require_non_negative(qty(data.get("min_stock_level", "0")), "حد التنبيه")
        notes = str(data.get("notes") or "").strip() or None

        with self.db.transaction() as conn:
            cur = conn.execute(
                """
                INSERT INTO products
                  (barcode, name, unit, purchase_price, retail_price, stock_quantity, min_stock_level, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    barcode,
                    name,
                    unit,
                    db_text(purchase_price),
                    db_text(retail_price),
                    qty_text(stock_quantity),
                    qty_text(min_stock_level),
                    notes,
                ),
            )
            product_id = int(cur.lastrowid)
            if stock_quantity != Decimal("0.0000"):
                conn.execute(
                    """
                    INSERT INTO stock_movements
                      (product_id, movement_type, quantity_change, quantity_before, quantity_after, reference_type, note)
                    VALUES (?, 'initial', ?, '0.0000', ?, 'product', 'رصيد افتتاحي')
                    """,
                    (product_id, qty_text(stock_quantity), qty_text(stock_quantity)),
                )
            return product_id

    def update_product(self, product_id: int, data: dict[str, Any]) -> None:
        name = str(data.get("name") or "").strip()
        if not name:
            raise ValueError("اسم المنتج مطلوب")

        barcode = str(data.get("barcode") or "").strip() or None
        unit = str(data.get("unit") or "قطعة").strip() or "قطعة"
        purchase_price = require_non_negative(money(data.get("purchase_price", "0")), "سعر الشراء")
        retail_price = require_non_negative(money(data.get("retail_price", "0")), "سعر البيع")
        next_qty = require_non_negative(qty(data.get("stock_quantity", "0")), "الكمية")
        min_stock_level = require_non_negative(qty(data.get("min_stock_level", "0")), "حد التنبيه")
        notes = str(data.get("notes") or "").strip() or None

        with self.db.transaction() as conn:
            row = conn.execute("SELECT stock_quantity FROM products WHERE id = ?", (product_id,)).fetchone()
            if not row:
                raise ValueError("المنتج غير موجود")
            before = qty(row["stock_quantity"])
            delta = next_qty - before
            conn.execute(
                """
                UPDATE products
                SET barcode = ?, name = ?, unit = ?, purchase_price = ?, retail_price = ?,
                    stock_quantity = ?, min_stock_level = ?, notes = ?, updated_at = datetime('now','localtime')
                WHERE id = ?
                """,
                (
                    barcode,
                    name,
                    unit,
                    db_text(purchase_price),
                    db_text(retail_price),
                    qty_text(next_qty),
                    qty_text(min_stock_level),
                    notes,
                    product_id,
                ),
            )
            if delta != Decimal("0.0000"):
                movement_type = "adjustment_in" if delta > 0 else "adjustment_out"
                conn.execute(
                    """
                    INSERT INTO stock_movements
                      (product_id, movement_type, quantity_change, quantity_before, quantity_after, reference_type, note)
                    VALUES (?, ?, ?, ?, ?, 'product', 'تعديل يدوي من شاشة المنتجات')
                    """,
                    (product_id, movement_type, qty_text(delta), qty_text(before), qty_text(next_qty)),
                )

    def set_active(self, product_id: int, active: bool) -> None:
        with self.db.transaction() as conn:
            conn.execute(
                "UPDATE products SET is_active = ?, updated_at = datetime('now','localtime') WHERE id = ?",
                (1 if active else 0, product_id),
            )

    def low_stock(self) -> list[dict[str, Any]]:
        with self.db.connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM products
                WHERE is_active = 1
                  AND CAST(stock_quantity AS REAL) <= CAST(min_stock_level AS REAL)
                ORDER BY CAST(stock_quantity AS REAL) ASC, name ASC
                LIMIT 100
                """
            ).fetchall()
        return [dict(r) for r in rows]

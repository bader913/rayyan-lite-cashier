from __future__ import annotations

from decimal import Decimal
from typing import Any

from app.core.money import db_text, display, display_qty, money, qty, qty_text, require_non_negative
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
            where.append("(name LIKE ? OR barcode LIKE ? OR extra_scan_code LIKE ? OR category LIKE ?)")
            like = f"%{term}%"
            params.extend([like, like, like, like])
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

    def _normalize_product_data(self, data: dict[str, Any]) -> dict[str, Any]:
        name = str(data.get("name") or "").strip()
        if not name:
            raise ValueError("اسم المنتج مطلوب")

        purchase_price = require_non_negative(money(data.get("purchase_price", "0")), "سعر الشراء")
        retail_price = require_non_negative(money(data.get("retail_price", "0")), "سعر البيع")
        wholesale_price = require_non_negative(money(data.get("wholesale_price", "0")), "سعر الجملة")
        stock_quantity = require_non_negative(qty(data.get("stock_quantity", "0")), "الكمية")
        min_stock_level = require_non_negative(qty(data.get("min_stock_level", "0")), "حد التنبيه")
        parts_per_unit = require_non_negative(qty(data.get("parts_per_unit", "1")), "عدد الأجزاء")
        wholesale_min_qty = require_non_negative(qty(data.get("wholesale_min_qty", "1")), "حد الجملة")

        return {
            "name": name,
            "barcode": str(data.get("barcode") or "").strip() or None,
            "extra_scan_code": str(data.get("extra_scan_code") or "").strip() or None,
            "category": str(data.get("category") or "").strip() or None,
            "supplier": str(data.get("supplier") or "").strip() or None,
            "unit": str(data.get("unit") or "قطعة").strip() or "قطعة",
            "is_weighted": 1 if str(data.get("is_weighted") or "0").strip().lower() in {"1", "true", "yes", "نعم", "صح"} else 0,
            "has_parts": 1 if str(data.get("has_parts") or "0").strip().lower() in {"1", "true", "yes", "نعم", "صح"} else 0,
            "part_name": str(data.get("part_name") or "").strip() or None,
            "parts_per_unit": parts_per_unit,
            "wholesale_price": wholesale_price,
            "wholesale_min_qty": wholesale_min_qty,
            "purchase_price": purchase_price,
            "retail_price": retail_price,
            "stock_quantity": stock_quantity,
            "min_stock_level": min_stock_level,
            "expiry_date": str(data.get("expiry_date") or "").strip() or None,
            "notes": str(data.get("notes") or "").strip() or None,
            "image_url": str(data.get("image_url") or "").strip() or None,
        }

    def create_product(self, data: dict[str, Any]) -> int:
        product = self._normalize_product_data(data)

        with self.db.transaction() as conn:
            cur = conn.execute(
                """
                INSERT INTO products
                  (barcode, name, unit, extra_scan_code, category, supplier, is_weighted, has_parts,
                   part_name, parts_per_unit, wholesale_price, wholesale_min_qty,
                   purchase_price, retail_price, stock_quantity, min_stock_level,
                   expiry_date, notes, image_url)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    product["barcode"],
                    product["name"],
                    product["unit"],
                    product["extra_scan_code"],
                    product["category"],
                    product["supplier"],
                    product["is_weighted"],
                    product["has_parts"],
                    product["part_name"],
                    qty_text(product["parts_per_unit"]),
                    db_text(product["wholesale_price"]),
                    qty_text(product["wholesale_min_qty"]),
                    db_text(product["purchase_price"]),
                    db_text(product["retail_price"]),
                    qty_text(product["stock_quantity"]),
                    qty_text(product["min_stock_level"]),
                    product["expiry_date"],
                    product["notes"],
                    product["image_url"],
                ),
            )
            product_id = int(cur.lastrowid)
            if product["stock_quantity"] != Decimal("0.0000"):
                conn.execute(
                    """
                    INSERT INTO stock_movements
                      (product_id, movement_type, quantity_change, quantity_before, quantity_after, reference_type, note)
                    VALUES (?, 'initial', ?, '0.0000', ?, 'product', 'رصيد افتتاحي')
                    """,
                    (product_id, qty_text(product["stock_quantity"]), qty_text(product["stock_quantity"])),
                )
            return product_id

    def update_product(self, product_id: int, data: dict[str, Any]) -> None:
        product = self._normalize_product_data(data)

        with self.db.transaction() as conn:
            row = conn.execute("SELECT stock_quantity FROM products WHERE id = ?", (product_id,)).fetchone()
            if not row:
                raise ValueError("المنتج غير موجود")
            before = qty(row["stock_quantity"])
            delta = product["stock_quantity"] - before
            conn.execute(
                """
                UPDATE products
                SET barcode = ?, name = ?, unit = ?, extra_scan_code = ?, category = ?, supplier = ?,
                    is_weighted = ?, has_parts = ?, part_name = ?, parts_per_unit = ?,
                    wholesale_price = ?, wholesale_min_qty = ?,
                    purchase_price = ?, retail_price = ?, stock_quantity = ?, min_stock_level = ?,
                    expiry_date = ?, notes = ?, image_url = ?, updated_at = datetime('now','localtime')
                WHERE id = ?
                """,
                (
                    product["barcode"],
                    product["name"],
                    product["unit"],
                    product["extra_scan_code"],
                    product["category"],
                    product["supplier"],
                    product["is_weighted"],
                    product["has_parts"],
                    product["part_name"],
                    qty_text(product["parts_per_unit"]),
                    db_text(product["wholesale_price"]),
                    qty_text(product["wholesale_min_qty"]),
                    db_text(product["purchase_price"]),
                    db_text(product["retail_price"]),
                    qty_text(product["stock_quantity"]),
                    qty_text(product["min_stock_level"]),
                    product["expiry_date"],
                    product["notes"],
                    product["image_url"],
                    product_id,
                ),
            )
            if delta != Decimal("0.0000"):
                movement_type = "adjustment_in" if delta > 0 else "adjustment_out"
                conn.execute(
                    """
                    INSERT INTO stock_movements
                      (product_id, movement_type, quantity_change, quantity_before, quantity_after, reference_type, note)
                    VALUES (?, ?, ?, ?, ?, 'product', 'تعديل يدوي/استيراد Excel من شاشة المنتجات')
                    """,
                    (product_id, movement_type, qty_text(delta), qty_text(before), qty_text(product["stock_quantity"])),
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

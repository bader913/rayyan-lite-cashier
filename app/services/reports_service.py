from __future__ import annotations

from typing import Any

from app.db.database import Database


class ReportsService:
    def __init__(self, db: Database):
        self.db = db

    def top_products_today(self, limit: int = 10) -> list[dict[str, Any]]:
        with self.db.connect() as conn:
            rows = conn.execute(
                """
                SELECT p.name,
                       SUM(CAST(si.quantity AS REAL)) AS qty_sold,
                       SUM(CAST(si.total_price AS REAL)) AS total_sales,
                       SUM(CAST(si.profit_amount AS REAL)) AS profit
                FROM sale_items si
                JOIN sales s ON s.id = si.sale_id
                JOIN products p ON p.id = si.product_id
                WHERE date(s.created_at) = date('now','localtime')
                GROUP BY p.id, p.name
                ORDER BY qty_sold DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]

    def stock_movements(self, limit: int = 100) -> list[dict[str, Any]]:
        with self.db.connect() as conn:
            rows = conn.execute(
                """
                SELECT sm.*, p.name AS product_name
                FROM stock_movements sm
                JOIN products p ON p.id = sm.product_id
                ORDER BY sm.id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]

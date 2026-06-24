from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from app.core.paths import default_db_path, project_root


class Database:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    @classmethod
    def create_default(cls) -> "Database":
        return cls(default_db_path())

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA busy_timeout = 5000")
        return conn

    def initialize(self) -> None:
        schema_path = project_root() / "app" / "db" / "schema.sql"
        with self.connect() as conn:
            conn.executescript(schema_path.read_text(encoding="utf-8"))
            self._apply_lightweight_migrations(conn)
            conn.commit()

    def _table_columns(self, conn: sqlite3.Connection, table: str) -> set[str]:
        rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
        return {str(row["name"]) for row in rows}

    def _add_column_if_missing(self, conn: sqlite3.Connection, table: str, column: str, ddl: str) -> None:
        if column not in self._table_columns(conn, table):
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {ddl}")

    def _apply_lightweight_migrations(self, conn: sqlite3.Connection) -> None:
        # SQLite CREATE TABLE IF NOT EXISTS will not add new columns to existing DBs.
        # Keep safe additive migrations here.
        self._add_column_if_missing(conn, "products", "extra_scan_code", "extra_scan_code TEXT")
        self._add_column_if_missing(conn, "products", "category", "category TEXT")
        self._add_column_if_missing(conn, "products", "supplier", "supplier TEXT")
        self._add_column_if_missing(conn, "products", "is_weighted", "is_weighted INTEGER NOT NULL DEFAULT 0")
        self._add_column_if_missing(conn, "products", "has_parts", "has_parts INTEGER NOT NULL DEFAULT 0")
        self._add_column_if_missing(conn, "products", "part_name", "part_name TEXT")
        self._add_column_if_missing(conn, "products", "parts_per_unit", "parts_per_unit TEXT NOT NULL DEFAULT '1.0000'")
        self._add_column_if_missing(conn, "products", "wholesale_price", "wholesale_price TEXT NOT NULL DEFAULT '0.0000'")
        self._add_column_if_missing(conn, "products", "wholesale_min_qty", "wholesale_min_qty TEXT NOT NULL DEFAULT '1.0000'")
        self._add_column_if_missing(conn, "products", "expiry_date", "expiry_date TEXT")
        self._add_column_if_missing(conn, "products", "image_url", "image_url TEXT")

        self._add_column_if_missing(conn, "sales", "currency_name", "currency_name TEXT")
        self._add_column_if_missing(conn, "sales", "currency_symbol", "currency_symbol TEXT")
        self._add_column_if_missing(conn, "sales", "exchange_currency_name", "exchange_currency_name TEXT")
        self._add_column_if_missing(conn, "sales", "exchange_currency_symbol", "exchange_currency_symbol TEXT")
        self._add_column_if_missing(conn, "sales", "exchange_rate", "exchange_rate TEXT NOT NULL DEFAULT '1.0000'")
        self._add_column_if_missing(conn, "sales", "edited_at", "edited_at TEXT")
        self._add_column_if_missing(conn, "sales", "edit_count", "edit_count INTEGER NOT NULL DEFAULT 0")
        self._add_column_if_missing(conn, "sales", "last_edit_reason", "last_edit_reason TEXT")

        conn.execute("CREATE INDEX IF NOT EXISTS idx_purchases_created_at ON purchases(created_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_purchases_invoice_number ON purchases(invoice_number)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_purchase_items_purchase_id ON purchase_items(purchase_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_purchase_items_product_id ON purchase_items(product_id)")

        # Backfill historical currency snapshot for old invoices from current settings.
        conn.execute(
            """
            UPDATE sales
            SET
              currency_name = COALESCE(NULLIF(currency_name, ''), (SELECT value FROM settings WHERE key = 'currency_name')),
              currency_symbol = COALESCE(NULLIF(currency_symbol, ''), (SELECT value FROM settings WHERE key = 'currency_symbol')),
              exchange_currency_name = COALESCE(NULLIF(exchange_currency_name, ''), (SELECT value FROM settings WHERE key = 'exchange_currency_name')),
              exchange_currency_symbol = COALESCE(NULLIF(exchange_currency_symbol, ''), (SELECT value FROM settings WHERE key = 'exchange_currency_symbol')),
              exchange_rate = COALESCE(NULLIF(exchange_rate, ''), (SELECT value FROM settings WHERE key = 'exchange_rate'), '1.0000')
            WHERE
              currency_name IS NULL OR currency_name = ''
              OR currency_symbol IS NULL OR currency_symbol = ''
              OR exchange_currency_name IS NULL OR exchange_currency_name = ''
              OR exchange_currency_symbol IS NULL OR exchange_currency_symbol = ''
              OR exchange_rate IS NULL OR exchange_rate = ''
            """
        )

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        conn = self.connect()
        try:
            conn.execute("BEGIN IMMEDIATE")
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

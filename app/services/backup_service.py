from __future__ import annotations

import gc
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path
from tempfile import mkdtemp
from zipfile import ZIP_DEFLATED, ZipFile

from app.core.paths import backups_dir
from app.db.database import Database


class BackupService:
    BACKUP_DB_MEMBER = "data/cashier_lite.sqlite"

    def __init__(self, db: Database):
        self.db = db

    def _cleanup_sqlite_sidecars(self) -> None:
        for suffix in ("-wal", "-shm"):
            sidecar = Path(str(self.db.path) + suffix)
            if sidecar.exists():
                sidecar.unlink(missing_ok=True)

    def _export_snapshot_db(self, snapshot_path: Path) -> None:
        if not self.db.path.exists():
            raise FileNotFoundError(f"Database not found: {self.db.path}")

        snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        source = sqlite3.connect(str(self.db.path))
        target = sqlite3.connect(str(snapshot_path))
        try:
            try:
                source.execute("PRAGMA wal_checkpoint(PASSIVE)")
            except sqlite3.DatabaseError:
                pass
            source.backup(target)
            target.commit()
        finally:
            target.close()
            source.close()
            gc.collect()

    def _remove_temp_dir_later_safe(self, temp_dir: Path) -> None:
        # On Windows, SQLite or antivirus may hold the temp db for a short moment.
        # Cleanup must never fail the user operation after the ZIP was created/restored.
        try:
            gc.collect()
            shutil.rmtree(temp_dir, ignore_errors=True)
        except Exception:
            pass

    def create_backup(self, *, label: str | None = None) -> Path:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_label = f"_{label.strip().replace(' ', '_')}" if label else ""
        out = backups_dir() / f"cashier_lite_backup{safe_label}_{stamp}.zip"

        temp_dir = Path(mkdtemp(prefix="cashier_lite_backup_"))
        try:
            temp_db = temp_dir / "cashier_lite.sqlite"
            self._export_snapshot_db(temp_db)
            with ZipFile(out, "w", ZIP_DEFLATED) as zf:
                zf.write(temp_db, self.BACKUP_DB_MEMBER)
                zf.writestr(
                    "README_BACKUP.txt",
                    "Rayyan Lite SQLite backup. You can restore it from the Settings page.\n",
                )
        finally:
            self._remove_temp_dir_later_safe(temp_dir)

        return out

    def restore_backup(self, backup_zip: str | Path) -> Path:
        backup_path = Path(backup_zip)
        if not backup_path.exists():
            raise FileNotFoundError(f"Backup file not found: {backup_path}")

        temp_dir = Path(mkdtemp(prefix="cashier_lite_restore_"))
        try:
            with ZipFile(backup_path, "r") as zf:
                members = set(zf.namelist())
                if self.BACKUP_DB_MEMBER not in members:
                    raise ValueError("النسخة الاحتياطية لا تحتوي قاعدة البيانات المطلوبة")
                zf.extract(self.BACKUP_DB_MEMBER, temp_dir)

            extracted_db = temp_dir / self.BACKUP_DB_MEMBER
            validate_conn = sqlite3.connect(str(extracted_db))
            try:
                validate_conn.execute("SELECT name FROM sqlite_master LIMIT 1")
            finally:
                validate_conn.close()
                gc.collect()

            self.create_backup(label="before_restore")
            self._cleanup_sqlite_sidecars()
            self.db.path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(extracted_db, self.db.path)
            self._cleanup_sqlite_sidecars()
        finally:
            self._remove_temp_dir_later_safe(temp_dir)

        return self.db.path

    def clear_business_data(self) -> Path:
        backup_path = self.create_backup(label="before_clear")
        with self.db.transaction() as conn:
            conn.execute("DELETE FROM sale_items")
            conn.execute("DELETE FROM sales")
            conn.execute("DELETE FROM purchase_items")
            conn.execute("DELETE FROM purchases")
            conn.execute("DELETE FROM stock_movements")
            conn.execute("DELETE FROM app_logs")
            conn.execute(
                "UPDATE invoice_sequences SET last_number = 0 WHERE prefix IN ('SALE','PUR')"
            )
            conn.execute(
                "UPDATE products SET stock_quantity = '0.0000', updated_at = datetime('now','localtime')"
            )
            conn.execute(
                "UPDATE customers SET balance = '0.0000', updated_at = datetime('now','localtime')"
            )
        self._cleanup_sqlite_sidecars()
        return backup_path

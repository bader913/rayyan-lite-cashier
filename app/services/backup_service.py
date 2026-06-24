from __future__ import annotations

from datetime import datetime
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from app.core.paths import backups_dir
from app.db.database import Database


class BackupService:
    def __init__(self, db: Database):
        self.db = db

    def create_backup(self) -> Path:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out = backups_dir() / f"cashier_lite_backup_{stamp}.zip"
        if not self.db.path.exists():
            raise FileNotFoundError(f"Database not found: {self.db.path}")
        with ZipFile(out, "w", ZIP_DEFLATED) as zf:
            zf.write(self.db.path, "data/cashier_lite.sqlite")
            zf.writestr("README_BACKUP.txt", "Rayyan Lite SQLite backup. Restore manually only after closing the app.\n")
        return out

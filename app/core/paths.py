from __future__ import annotations

from pathlib import Path


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def data_dir() -> Path:
    path = project_root() / "data"
    path.mkdir(parents=True, exist_ok=True)
    return path


def backups_dir() -> Path:
    path = project_root() / "backups"
    path.mkdir(parents=True, exist_ok=True)
    return path


def default_db_path() -> Path:
    return data_dir() / "cashier_lite.sqlite"

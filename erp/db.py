"""Base de dades SQLite que fa de "ERP" de l'empresa de treball temporal."""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "erp.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS clients (
    id TEXT PRIMARY KEY,
    name TEXT,
    cif TEXT,
    city TEXT,
    updated_at TEXT
);
CREATE TABLE IF NOT EXISTS candidates (
    id TEXT PRIMARY KEY,
    first_name TEXT,
    last_name TEXT,
    email TEXT,
    phone TEXT,
    nif TEXT,
    city TEXT,
    updated_at TEXT
);
CREATE TABLE IF NOT EXISTS placements (
    id TEXT PRIMARY KEY,
    client_id TEXT,
    candidate_id TEXT,
    position TEXT,
    start_date TEXT,
    end_date TEXT,
    status TEXT,
    hourly_rate TEXT,
    updated_at TEXT
);
"""

TABLES = ("clients", "candidates", "placements")


def connect(path: Path = DB_PATH) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn

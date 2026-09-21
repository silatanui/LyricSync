"""One-off migration: copy existing rows from the legacy SQLite DB into the
new MySQL (phpMyAdmin) database used by the app after enabling authentication.

Usage: python scratch/migrate_sqlite_to_mysql.py
"""
import sqlite3
from pathlib import Path

import pymysql

from config import Config

SQLITE_PATH = Path(__file__).resolve().parent.parent / "data" / "lyricsync.db"

TABLES_IN_ORDER = [
    "users",
    "projects",
    "media_assets",
    "transcriptions",
    "lyric_lines",
    "lyric_words",
    "render_jobs",
]


def main():
    if not SQLITE_PATH.exists():
        print(f"No SQLite DB found at {SQLITE_PATH}, nothing to migrate.")
        return

    sconn = sqlite3.connect(str(SQLITE_PATH))
    sconn.row_factory = sqlite3.Row
    existing_tables = {
        row[0]
        for row in sconn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }

    mconn = pymysql.connect(
        host=Config.MYSQL_HOST,
        port=int(Config.MYSQL_PORT),
        user=Config.MYSQL_USER,
        password=Config.MYSQL_PASSWORD,
        database=Config.MYSQL_DATABASE,
        charset="utf8mb4",
    )

    try:
        with mconn.cursor() as mcur:
            mcur.execute("SET FOREIGN_KEY_CHECKS=0")
            for table in TABLES_IN_ORDER:
                if table not in existing_tables:
                    continue
                rows = sconn.execute(f"SELECT * FROM {table}").fetchall()
                if not rows:
                    print(f"{table}: no rows to migrate")
                    continue
                columns = rows[0].keys()
                placeholders = ", ".join(["%s"] * len(columns))
                col_list = ", ".join(f"`{c}`" for c in columns)
                sql = f"INSERT IGNORE INTO `{table}` ({col_list}) VALUES ({placeholders})"
                values = [tuple(row[c] for c in columns) for row in rows]
                mcur.executemany(sql, values)
                print(f"{table}: migrated {len(values)} row(s)")
            mcur.execute("SET FOREIGN_KEY_CHECKS=1")
        mconn.commit()
    finally:
        mconn.close()
        sconn.close()

    print("Migration complete.")


if __name__ == "__main__":
    main()

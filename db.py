import sqlite3
import json
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).parent / "history.db"


def _get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with _get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS history (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                created         TEXT    NOT NULL,
                type            TEXT    NOT NULL,
                expr_input      TEXT    NOT NULL,
                problem_latex   TEXT    NOT NULL,
                result_latex    TEXT    NOT NULL,
                steps_json      TEXT    NOT NULL,
                limit_point     TEXT,
                limit_direction TEXT
            )
        """)
        # Add columns to existing DBs that were created before limit support
        for col, col_type in [("limit_point", "TEXT"), ("limit_direction", "TEXT")]:
            try:
                conn.execute(f"ALTER TABLE history ADD COLUMN {col} {col_type}")
            except Exception:
                pass
        conn.commit()


def add_entry(type_, expr_input, problem_latex, result_latex, steps,
              limit_point=None, limit_direction=None):
    with _get_conn() as conn:
        conn.execute(
            """INSERT INTO history
               (created, type, expr_input, problem_latex, result_latex,
                steps_json, limit_point, limit_direction)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                datetime.now(timezone.utc).isoformat(),
                type_,
                expr_input,
                problem_latex,
                result_latex,
                json.dumps(steps),
                limit_point,
                limit_direction,
            ),
        )
        conn.commit()


def get_all():
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM history ORDER BY created DESC"
        ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["steps"] = json.loads(d["steps_json"])
            del d["steps_json"]
            result.append(d)
        return result


def delete_entry(id_):
    with _get_conn() as conn:
        conn.execute("DELETE FROM history WHERE id = ?", (id_,))
        conn.commit()

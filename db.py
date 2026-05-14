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
        conn.execute("""
            CREATE TABLE IF NOT EXISTS exam_sessions (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                created         TEXT    NOT NULL,
                completed       TEXT,
                questions_json  TEXT    NOT NULL,
                answers_json    TEXT,
                score           INTEGER,
                total           INTEGER
            )
        """)
        for col, col_type in [("limit_point", "TEXT"), ("limit_direction", "TEXT")]:
            try:
                conn.execute(f"ALTER TABLE history ADD COLUMN {col} {col_type}")
            except Exception:
                pass
        conn.commit()


def create_exam(questions: list) -> int:
    with _get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO exam_sessions (created, questions_json, total)
               VALUES (?, ?, ?)""",
            (datetime.now(timezone.utc).isoformat(), json.dumps(questions), len(questions)),
        )
        conn.commit()
        return cur.lastrowid


def save_exam_result(exam_id: int, answers: list, score: int):
    with _get_conn() as conn:
        conn.execute(
            """UPDATE exam_sessions
               SET answers_json=?, score=?, completed=?
               WHERE id=?""",
            (json.dumps(answers), score, datetime.now(timezone.utc).isoformat(), exam_id),
        )
        conn.commit()


def get_exam(exam_id: int) -> dict | None:
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM exam_sessions WHERE id=?", (exam_id,)
        ).fetchone()
        if not row:
            return None
        d = dict(row)
        d["questions"] = json.loads(d["questions_json"])
        d["answers"] = json.loads(d["answers_json"]) if d["answers_json"] else []
        del d["questions_json"], d["answers_json"]
        return d


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

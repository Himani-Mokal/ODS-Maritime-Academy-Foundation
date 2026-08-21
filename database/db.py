import sqlite3

DATABASE = "database/certificate.db"

def get_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def _add_column_if_missing(cursor, table, column, definition):
    cursor.execute(f"PRAGMA table_info({table})")
    existing_columns = [row[1] for row in cursor.fetchall()]
    if column not in existing_columns:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def _table_exists(cursor, table):
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
    return cursor.fetchone() is not None


def _rename_table_if_needed(cursor, old_name, new_name):
    if _table_exists(cursor, old_name) and not _table_exists(cursor, new_name):
        cursor.execute(f"ALTER TABLE {old_name} RENAME TO {new_name}")


def _rename_column_if_needed(cursor, table, old_col, new_col):
    cursor.execute(f"PRAGMA table_info({table})")
    columns = [row[1] for row in cursor.fetchall()]
    if old_col in columns and new_col not in columns:
        cursor.execute(f"ALTER TABLE {table} RENAME COLUMN {old_col} TO {new_col}")


def run_schema_migrations():
    """
    Additive, idempotent schema upgrades. Safe to run on every app startup:
    only adds/renames what's missing, never drops or rewrites existing data
    (aside from the one-time Event -> Course rename below, and the removal
    of the email-automation feature's now-unused email_logs table).
    """
    conn = get_connection()
    cursor = conn.cursor()

    # --- Template Manager (SVG/PDF/PNG templates) ---
    _add_column_if_missing(cursor, "certificate_templates", "template_type", "TEXT DEFAULT 'image'")
    _add_column_if_missing(cursor, "certificate_templates", "description", "TEXT")
    _add_column_if_missing(cursor, "certificate_templates", "updated_at", "TEXT")

    # --- Event -> Course rename (table + columns) ---
    _rename_table_if_needed(cursor, "events", "courses")
    _rename_column_if_needed(cursor, "courses", "event_name", "course_name")
    _rename_column_if_needed(cursor, "courses", "event_date", "course_date")
    _add_column_if_missing(cursor, "courses", "template_id", "INTEGER")

    _rename_column_if_needed(cursor, "participants", "event_id", "course_id")
    _add_column_if_missing(cursor, "participants", "contact_no", "TEXT")

    _add_column_if_missing(cursor, "participants", "contact_no", "TEXT")
    _add_column_if_missing(cursor, "participants", "certificate_no", "TEXT")
    _add_column_if_missing(cursor, "participants", "date_of_birth", "TEXT")
    _add_column_if_missing(cursor, "participants", "cdc_no", "TEXT")
    _add_column_if_missing(cursor, "participants", "passport_no", "TEXT")
    _add_column_if_missing(cursor, "participants", "competency_grade", "TEXT")
    _add_column_if_missing(cursor, "participants", "competency_no", "TEXT")
    _add_column_if_missing(cursor, "participants", "indos_no", "TEXT")
    _add_column_if_missing(cursor, "participants", "held_from", "TEXT")
    _add_column_if_missing(cursor, "participants", "held_to", "TEXT")
    _add_column_if_missing(cursor, "participants", "issue_day_month", "TEXT")
    _add_column_if_missing(cursor, "participants", "issue_year", "TEXT")
    _add_column_if_missing(cursor, "participants", "course_name_text", "TEXT")
    _add_column_if_missing(cursor, "participants", "description_below", "TEXT")
    _add_column_if_missing(cursor, "participants", "qr_label", "TEXT")
   
    # --- Certificate export formats (SVG/PNG alongside the PDF) ---
    _add_column_if_missing(cursor, "certificates", "svg_file_name", "TEXT")
    _add_column_if_missing(cursor, "certificates", "png_file_name", "TEXT")

    # --- Detailed manual certificate fields (STCW-style course certificates) ---
    _add_column_if_missing(cursor, "certificates", "student_name", "TEXT")
    _add_column_if_missing(cursor, "certificates", "captain_name", "TEXT")
    _add_column_if_missing(cursor, "certificates", "organization_name", "TEXT")
    _add_column_if_missing(cursor, "certificates", "description_above", "TEXT")
    _add_column_if_missing(cursor, "certificates", "description_below", "TEXT")
    _add_column_if_missing(cursor, "certificates", "date_of_birth", "TEXT")
    _add_column_if_missing(cursor, "certificates", "held_from", "TEXT")
    _add_column_if_missing(cursor, "certificates", "held_to", "TEXT")
    _add_column_if_missing(cursor, "certificates", "passport_no", "TEXT")
    _add_column_if_missing(cursor, "certificates", "cdc_no", "TEXT")
    _add_column_if_missing(cursor, "certificates", "indos_no", "TEXT")
    _add_column_if_missing(cursor, "certificates", "competency_grade", "TEXT")
    _add_column_if_missing(cursor, "certificates", "course_name_snapshot", "TEXT")

    # --- Per-template placeholder position mapping (Template "Positions" editor) ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS template_field_positions(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            template_id INTEGER NOT NULL,
            field_key TEXT NOT NULL,
            x REAL NOT NULL,
            y REAL NOT NULL,
            width REAL NOT NULL,
            height REAL NOT NULL,
            font_size REAL DEFAULT 20,
            font_family TEXT DEFAULT 'Arial, Helvetica, sans-serif',
            color TEXT DEFAULT '#111111',
            align TEXT DEFAULT 'left',
            bold INTEGER DEFAULT 0,
            italic INTEGER DEFAULT 0,
            underline INTEGER DEFAULT 0,
            is_rich INTEGER DEFAULT 0,
            UNIQUE(template_id, field_key),
            FOREIGN KEY(template_id) REFERENCES certificate_templates(id)
        )
    """)

    # --- Email automation removed entirely: drop its now-unused table ---
    cursor.execute("DROP TABLE IF EXISTS email_logs")

    conn.commit()
    conn.close()
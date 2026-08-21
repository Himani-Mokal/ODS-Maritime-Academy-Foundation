import os
import sqlite3

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATABASE = os.path.join(BASE_DIR, "database", "certificate.db")


def get_connection():
    os.makedirs(os.path.dirname(DATABASE), exist_ok=True)
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def _add_column_if_missing(cursor, table, column, definition):
    if not _table_exists(cursor, table):
        return
    cursor.execute(f"PRAGMA table_info({table})")
    existing_columns = [row[1] for row in cursor.fetchall()]
    if column not in existing_columns:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def _table_exists(cursor, table):
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    )
    return cursor.fetchone() is not None


def _rename_table_if_needed(cursor, old_name, new_name):
    if _table_exists(cursor, old_name) and not _table_exists(cursor, new_name):
        cursor.execute(f"ALTER TABLE {old_name} RENAME TO {new_name}")


def _rename_column_if_needed(cursor, table, old_col, new_col):
    if not _table_exists(cursor, table):
        return
    cursor.execute(f"PRAGMA table_info({table})")
    columns = [row[1] for row in cursor.fetchall()]
    if old_col in columns and new_col not in columns:
        cursor.execute(f"ALTER TABLE {table} RENAME COLUMN {old_col} TO {new_col}")


def _create_base_tables(cursor):
    """Create core tables on empty DB (e.g. first Render deploy)."""

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            email TEXT NOT NULL,
            password TEXT NOT NULL,
            profile_pic TEXT,
            created_at TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_name TEXT NOT NULL,
            course_date TEXT,
            organizer TEXT,
            venue TEXT,
            description TEXT,
            template_name TEXT,
            status TEXT,
            created_at TEXT,
            template_id INTEGER
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS participants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            college TEXT,
            department TEXT,
            position TEXT,
            created_at TEXT,
            contact_no TEXT,
            certificate_no TEXT,
            date_of_birth TEXT,
            cdc_no TEXT,
            passport_no TEXT,
            competency_grade TEXT,
            competency_no TEXT,
            indos_no TEXT,
            held_from TEXT,
            held_to TEXT,
            issue_day_month TEXT,
            issue_year TEXT,
            course_name_text TEXT,
            description_below TEXT,
            qr_label TEXT,
            FOREIGN KEY(course_id) REFERENCES courses(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS certificates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            participant_id INTEGER NOT NULL,
            certificate_id TEXT UNIQUE,
            file_name TEXT,
            issue_date TEXT,
            qr_code TEXT,
            status TEXT,
            svg_file_name TEXT,
            png_file_name TEXT,
            student_name TEXT,
            captain_name TEXT,
            organization_name TEXT,
            description_above TEXT,
            description_below TEXT,
            date_of_birth TEXT,
            held_from TEXT,
            held_to TEXT,
            passport_no TEXT,
            cdc_no TEXT,
            indos_no TEXT,
            competency_grade TEXT,
            course_name_snapshot TEXT,
            FOREIGN KEY(participant_id) REFERENCES participants(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS certificate_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            template_name TEXT,
            file_name TEXT,
            uploaded_at TEXT,
            status TEXT,
            template_type TEXT DEFAULT 'image',
            description TEXT,
            updated_at TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS template_field_positions (
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


def run_schema_migrations():
    """
    Safe on empty DB (Render) and existing local DB.
    1) CREATE TABLE IF NOT EXISTS base tables
    2) Rename legacy event_* → course_*
    3) ADD missing columns
    """
    conn = get_connection()
    cursor = conn.cursor()

    # 1) Base tables first (fixes "no such table" on Render)
    _create_base_tables(cursor)

    # 2) Legacy renames (old local DBs that still have events)
    _rename_table_if_needed(cursor, "events", "courses")
    _rename_column_if_needed(cursor, "courses", "event_name", "course_name")
    _rename_column_if_needed(cursor, "courses", "event_date", "course_date")
    _rename_column_if_needed(cursor, "participants", "event_id", "course_id")

    # 3) Extra columns on existing installs
    _add_column_if_missing(cursor, "courses", "template_id", "INTEGER")

    _add_column_if_missing(cursor, "certificate_templates", "template_type", "TEXT DEFAULT 'image'")
    _add_column_if_missing(cursor, "certificate_templates", "description", "TEXT")
    _add_column_if_missing(cursor, "certificate_templates", "updated_at", "TEXT")

    for col in (
        "contact_no", "certificate_no", "date_of_birth", "cdc_no", "passport_no",
        "competency_grade", "competency_no", "indos_no", "held_from", "held_to",
        "issue_day_month", "issue_year", "course_name_text", "description_below", "qr_label",
    ):
        _add_column_if_missing(cursor, "participants", col, "TEXT")

    for col in (
        "svg_file_name", "png_file_name", "student_name", "captain_name",
        "organization_name", "description_above", "description_below", "date_of_birth",
        "held_from", "held_to", "passport_no", "cdc_no", "indos_no",
        "competency_grade", "course_name_snapshot",
    ):
        _add_column_if_missing(cursor, "certificates", col, "TEXT")

    cursor.execute("DROP TABLE IF EXISTS email_logs")

    conn.commit()
    conn.close()
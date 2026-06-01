from app.database.database import connect_db


def init_email_settings_table():
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS email_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            receiver_email TEXT NOT NULL,
            enabled INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("PRAGMA table_info(email_settings)")
    columns = [col[1] for col in cursor.fetchall()]

    if "receiver_email" not in columns:
        cursor.execute("ALTER TABLE email_settings ADD COLUMN receiver_email TEXT")

    if "enabled" not in columns:
        cursor.execute("ALTER TABLE email_settings ADD COLUMN enabled INTEGER DEFAULT 1")

    conn.commit()
    conn.close()


def save_email_settings(user_id: int, receiver_email: str, enabled: bool = True):
    init_email_settings_table()

    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM email_settings
        WHERE user_id = ?
    """, (user_id,))

    cursor.execute("""
        INSERT INTO email_settings (
            user_id,
            receiver_email,
            enabled,
            smtp_email,
            smtp_password
        )
        VALUES (?, ?, ?, '', '')
    """, (
        user_id,
        receiver_email,
        1 if enabled else 0
    ))

    conn.commit()
    conn.close()

    return True


def get_email_settings(user_id: int):
    init_email_settings_table()

    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT receiver_email, enabled
        FROM email_settings
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT 1
    """, (user_id,))

    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    return dict(row)
from app.database.database import connect_db
from app.services.email_service import send_app_email


IMPORTANT_TYPES = ["warning", "error", "critical"]


def init_notifications_table():
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT,
            message TEXT NOT NULL,
            type TEXT DEFAULT 'info',
            is_read INTEGER DEFAULT 0,
            email_sent INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("PRAGMA table_info(notifications)")
    columns = [col[1] for col in cursor.fetchall()]

    if "title" not in columns:
        cursor.execute("ALTER TABLE notifications ADD COLUMN title TEXT DEFAULT 'Notification'")

    if "email_sent" not in columns:
        cursor.execute("ALTER TABLE notifications ADD COLUMN email_sent INTEGER DEFAULT 0")

    if "is_read" not in columns:
        cursor.execute("ALTER TABLE notifications ADD COLUMN is_read INTEGER DEFAULT 0")

    if "type" not in columns:
        cursor.execute("ALTER TABLE notifications ADD COLUMN type TEXT DEFAULT 'info'")

    conn.commit()
    conn.close()


def get_user_email(user_id: int):
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT email
        FROM users
        WHERE id = ?
    """, (user_id,))

    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    try:
        return row["email"]
    except Exception:
        return row[0]


def create_notification(
    user_id: int,
    title: str,
    message: str,
    type: str = "info"
):
    init_notifications_table()

    type = (type or "info").lower()
    email_sent = 0

    if type in IMPORTANT_TYPES:
        receiver_email = get_user_email(user_id)

        if receiver_email:
            ok = send_app_email(
                receiver_email=receiver_email,
                subject=f"[NetAutoAI] {type.upper()} - {title}",
                body=f"""
Bonjour,

Une notification importante a été générée.

Type : {type.upper()}
Titre : {title}

Message :
{message}

Veuillez vérifier le dashboard NetAutoAI.

Cordialement,
NetAutoAI
"""
            )

            email_sent = 1 if ok else 0

    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO notifications (
            user_id, title, message, type, email_sent
        )
        VALUES (?, ?, ?, ?, ?)
    """, (user_id, title, message, type, email_sent))

    conn.commit()
    notification_id = cursor.lastrowid
    conn.close()

    return {
        "id": notification_id,
        "user_id": user_id,
        "title": title,
        "message": message,
        "type": type,
        "is_read": 0,
        "email_sent": email_sent
    }


def get_user_notifications(user_id: int):
    init_notifications_table()

    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, title, message, type, is_read, email_sent, created_at
        FROM notifications
        WHERE user_id = ?
        ORDER BY created_at DESC
        LIMIT 100
    """, (user_id,))

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def mark_notification_as_read(notification_id: int, user_id: int):
    init_notifications_table()

    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE notifications
        SET is_read = 1
        WHERE id = ? AND user_id = ?
    """, (notification_id, user_id))

    conn.commit()
    updated = cursor.rowcount
    conn.close()

    return updated > 0


def mark_as_read(notification_id: int, user_id: int):
    return mark_notification_as_read(notification_id, user_id)
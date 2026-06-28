from fastapi import HTTPException
from sqlite3 import IntegrityError
from app.database.database import connect_db
from core.gestion_utilisateurs.auth import hash_password, verify_password


def authenticate(username: str, password: str):
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT 
            u.id,
            u.username,
            u.password,
            u.email,
            u.role_id,
            r.name AS role
        FROM users u
        LEFT JOIN roles r ON u.role_id = r.id
        WHERE u.username = ?
    """, (username,))

    user = cursor.fetchone()
    conn.close()

    if not user:
        return None

    if verify_password(password, user["password"]):
        return {
            "id": user["id"],
            "username": user["username"],
            "password": user["password"],
            "email": user["email"],
            "role_id": user["role_id"],
            "role": user["role"] or "viewer"
        }

    return None


def create_user(username: str, password: str, role_name: str, email: str = None):
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM roles WHERE name = ?", (role_name,))
    role = cursor.fetchone()

    if not role:
        conn.close()
        raise HTTPException(status_code=404, detail="Role not found")

    hashed = hash_password(password)

    try:
        cursor.execute("""
            INSERT INTO users (username, password, email, role_id)
            VALUES (?, ?, ?, ?)
        """, (username, hashed, email, role["id"]))

        conn.commit()
        user_id = cursor.lastrowid

        cursor.execute("""
            SELECT 
                u.id,
                u.username,
                u.email,
                r.name AS role_name
            FROM users u
            LEFT JOIN roles r ON u.role_id = r.id
            WHERE u.id = ?
        """, (user_id,))

        new_user = cursor.fetchone()
        conn.close()

        return dict(new_user)

    except IntegrityError:
        conn.close()
        raise HTTPException(status_code=400, detail="Username already exists")
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr

from app.database.database import connect_db
from core.gestion_utilisateurs.security import get_current_user


router = APIRouter(prefix="/email-settings", tags=["Email Settings"])


class EmailSettingsRequest(BaseModel):
    email: EmailStr


@router.post("/save")
def save_settings(
    payload: EmailSettingsRequest,
    current_user: dict = Depends(get_current_user)
):
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE users
        SET email = ?
        WHERE id = ?
    """, (payload.email, current_user["id"]))

    conn.commit()
    updated = cursor.rowcount
    conn.close()

    if updated == 0:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")

    return {
        "success": True,
        "message": "Email utilisateur sauvegardé",
        "email": payload.email
    }


@router.get("")
def load_settings(current_user: dict = Depends(get_current_user)):
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT email
        FROM users
        WHERE id = ?
    """, (current_user["id"],))

    row = cursor.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")

    try:
        email = row["email"]
    except Exception:
        email = row[0]

    return {
        "success": True,
        "settings": {
            "email": email,
            "enabled": bool(email)
        }
    }
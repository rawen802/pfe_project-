# core/gestion_utilisateurs/security.py
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from app.database.database import connect_db
from core.gestion_utilisateurs.auth import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


# =========================
# GET CURRENT USER (avec permissions)
# =========================
def get_current_user(token: str = Depends(oauth2_scheme)):
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalide ou expiré"
        )

    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token sans user_id"
        )

    conn = connect_db()
    cursor = conn.cursor()

    try:
        # Informations utilisateur + rôle
        cursor.execute("""
            SELECT u.id, u.username, r.name AS role_name
            FROM users u
            LEFT JOIN roles r ON u.role_id = r.id
            WHERE u.id = ?
        """, (user_id,))

        user_row = cursor.fetchone()
        if not user_row:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Utilisateur non trouvé"
            )

        # Permissions
        cursor.execute("""
            SELECT p.name
            FROM permissions p
            JOIN role_permissions rp ON p.id = rp.permission_id
            WHERE rp.role_id = (
                SELECT role_id FROM users WHERE id = ?
            )
        """, (user_id,))

        permissions = [row[0] for row in cursor.fetchall()]

        return {
            "id": user_row[0],
            "username": user_row[1],
            "role": user_row[2],
            "permissions": permissions
        }

    finally:
        conn.close()


# =========================
# REQUIRE PERMISSION
# =========================
def require_permission(permission_name: str):
    """
    Vérifie que l'utilisateur a la permission demandée
    """
    def checker(current_user: dict = Depends(get_current_user)):
        

        if permission_name not in current_user.get("permissions", []):
            raise HTTPException(
                status_code=403,
                detail="Accès restreint selon vos permissions"
            )
        return current_user

    return checker
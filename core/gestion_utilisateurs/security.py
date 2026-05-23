from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from app.database.database import connect_db
from core.gestion_utilisateurs.auth import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


# =========================
#  GET CURRENT USER
# =========================
def get_current_user(token: str = Depends(oauth2_scheme)):
    payload = decode_access_token(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )

    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )

    conn = connect_db()
    conn.row_factory = lambda cursor, row: row  
    cursor = conn.cursor()

    # user info
    cursor.execute("""
        SELECT u.id, u.username, r.name AS role_name
        FROM users u
        LEFT JOIN roles r ON u.role_id = r.id
        WHERE u.id = ?
    """, (user_id,))

    user_row = cursor.fetchone()

    if not user_row:
        conn.close()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    # permissions
    cursor.execute("""
        SELECT p.name
        FROM role_permissions rp
        JOIN permissions p ON p.id = rp.permission_id
        JOIN users u ON u.role_id = rp.role_id
        WHERE u.id = ?
    """, (user_id,))

    permissions_rows = cursor.fetchall()
    conn.close()

    permissions = [row[0] for row in permissions_rows]

    return {
        "id": user_row[0],
        "username": user_row[1],
        "role": user_row[2],
        "permissions": permissions
    }


# =========================
# PERMISSION CHECKER
# =========================
def require_permission(permission_name: str):
    def checker(current_user: dict = Depends(get_current_user)):

        
        if permission_name not in current_user["permissions"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission '{permission_name}' denied"
            )

        return current_user

    return checker
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer

from app.services.user_service import authenticate
from app.database.database import connect_db, add_log
from core.gestion_utilisateurs.auth import create_access_token, decode_access_token
from app.api.shémas import CreateUserRequest
from app.services.user_service import create_user

router = APIRouter(prefix="/auth", tags=["Auth"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends()):

    user = authenticate(form_data.username, form_data.password)

    if not user:
        add_log(
            action="LOGIN_FAILED",
            user_id=None,
            module="AUTH",
            status="FAILED",
            extra={
                "username": form_data.username,
                "reason": "Invalid username or password"
            }
        )

        raise HTTPException(
            status_code=401,
            detail="Invalid username or password"
        )

    conn = connect_db()
    cursor = conn.cursor()

    # ===== RECUPERATION DES PERMISSIONS =====
    cursor.execute("""
        SELECT p.name
        FROM permissions p
        JOIN role_permissions rp ON rp.permission_id = p.id
        JOIN roles r ON r.id = rp.role_id
        WHERE r.name = ?
    """, (user["role"],))

    permissions = [row[0] for row in cursor.fetchall()]

    conn.close()

    # ===== TOKEN =====
    token = create_access_token({
        "user_id": user["id"],
        "username": user["username"],
        "role": user["role"]
    })

    add_log(
        action="LOGIN_SUCCESS",
        user_id=user["id"],
        module="AUTH",
        status="SUCCESS",
        extra={
            "username": user["username"],
            "role": user["role"]
        }
    )

    return {
        "success": True,
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "username": user["username"],
            "role": user["role"],
            "permissions": permissions
        }
    }
@router.get("/me")
def get_me(token: str = Depends(oauth2_scheme)):
    payload = decode_access_token(token)

    if not payload:
        add_log(
            action="GET_ME",
            user_id=None,
            module="AUTH",
            status="FAILED",
            extra={
                "reason": "Invalid or expired token"
            }
        )

        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token"
        )

    user_id = payload.get("user_id")
    username = payload.get("username")
    role = payload.get("role", "viewer")

    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT p.name
        FROM permissions p
        JOIN role_permissions rp ON rp.permission_id = p.id
        JOIN roles r ON r.id = rp.role_id
        WHERE r.name = ?
    """, (role,))

    permissions = [row[0] for row in cursor.fetchall()]

    conn.close()

    add_log(
        action="GET_CURRENT_USER",
        user_id=user_id,
        module="AUTH",
        status="SUCCESS",
        extra={
            "username": username,
            "role": role,
            "permissions_count": len(permissions)
        }
    )

    return {
        "id": user_id,
        "username": username,
        "role": role,
        "permissions": permissions
    }


@router.get("/has-admin")
def has_admin():
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT COUNT(*)
        FROM users u
        JOIN roles r ON u.role_id = r.id
        WHERE r.name = 'admin'
    """)

    count = cursor.fetchone()[0]
    conn.close()

    return {
        "success": True,
        "has_admin": count > 0
    }


@router.post("/setup-admin")
def setup_admin(data: CreateUserRequest):
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT COUNT(*)
        FROM users u
        JOIN roles r ON u.role_id = r.id
        WHERE r.name = 'admin'
    """)

    count = cursor.fetchone()[0]
    conn.close()

    if count > 0:
        raise HTTPException(
            status_code=403,
            detail="Admin account already exists"
        )

    user = create_user(
        data.username,
        data.password,
        "admin",
        data.email
    )

    return {
        "success": True,
        "message": "Admin account created successfully",
        "user": user
    }
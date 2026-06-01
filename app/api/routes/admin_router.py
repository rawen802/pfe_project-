from fastapi import APIRouter, Depends, HTTPException

from app.database.database import connect_db, add_log
from app.api.shémas import CreateUserRequest, UpdateRoleRequest
from app.services.user_service import create_user
from core.gestion_utilisateurs.security import require_permission

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.post("/create-user")
def admin_create_user(
    data: CreateUserRequest,
    current_user: dict = Depends(require_permission("manage_users"))
):
    user = create_user(
        data.username,
        data.password,
        data.role_name,
        data.email
    )

    add_log(
        action="CREATE_USER",
        user_id=current_user["id"],
        module="USER_MANAGEMENT",
        status="SUCCESS",
        extra={
            "created_username": data.username,
            "created_email": data.email,
            "created_role": data.role_name,
            "created_by": current_user["username"]
        }
    )

    return {
        "message": "User created",
        "created_by": current_user["username"],
        "user": user
    }


@router.get("/users")
def list_users(
    current_user: dict = Depends(require_permission("manage_users"))
):
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT 
            u.id,
            u.username,
            u.email,
            r.name AS role_name
        FROM users u
        LEFT JOIN roles r ON u.role_id = r.id
        ORDER BY u.id ASC
        """
    )

    users = [dict(row) for row in cursor.fetchall()]
    conn.close()

    add_log(
        action="LIST_USERS",
        user_id=current_user["id"],
        module="USER_MANAGEMENT",
        status="SUCCESS",
        extra={
            "viewed_by": current_user["username"],
            "count": len(users)
        }
    )

    return users


@router.put("/update-role/{user_id}")
def update_user_role(
    user_id: int,
    data: UpdateRoleRequest,
    current_user: dict = Depends(require_permission("manage_users"))
):
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id, username, email FROM users WHERE id = ?",
        (user_id,)
    )
    user = cursor.fetchone()

    if not user:
        conn.close()
        raise HTTPException(status_code=404, detail="User not found")

    cursor.execute(
        "SELECT id FROM roles WHERE name = ?",
        (data.role_name,)
    )
    role = cursor.fetchone()

    if not role:
        conn.close()
        raise HTTPException(status_code=404, detail="Role not found")

    cursor.execute(
        "UPDATE users SET role_id = ? WHERE id = ?",
        (role["id"], user_id)
    )

    conn.commit()

    cursor.execute(
        """
        SELECT 
            u.id,
            u.username,
            u.email,
            r.name AS role_name
        FROM users u
        LEFT JOIN roles r ON u.role_id = r.id
        WHERE u.id = ?
        """,
        (user_id,)
    )

    updated_user = dict(cursor.fetchone())
    conn.close()

    add_log(
        action="UPDATE_USER_ROLE",
        user_id=current_user["id"],
        module="USER_MANAGEMENT",
        status="SUCCESS",
        extra={
            "target_user_id": user_id,
            "target_username": updated_user.get("username"),
            "target_email": updated_user.get("email"),
            "new_role": data.role_name,
            "updated_by": current_user["username"]
        }
    )

    return {
        "message": "Role updated successfully",
        "updated_by": current_user["username"],
        "user": updated_user
    }


@router.delete("/delete-user/{user_id}")
def delete_user(
    user_id: int,
    current_user: dict = Depends(require_permission("manage_users"))
):
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id, username, email FROM users WHERE id = ?",
        (user_id,)
    )
    user = cursor.fetchone()

    if not user:
        conn.close()
        raise HTTPException(status_code=404, detail="User not found")

    deleted_user = dict(user)

    cursor.execute(
        "DELETE FROM users WHERE id = ?",
        (user_id,)
    )

    conn.commit()
    conn.close()

    add_log(
        action="DELETE_USER",
        user_id=current_user["id"],
        module="USER_MANAGEMENT",
        status="SUCCESS",
        extra={
            "deleted_user_id": user_id,
            "deleted_username": deleted_user.get("username"),
            "deleted_email": deleted_user.get("email"),
            "deleted_by": current_user["username"]
        }
    )

    return {
        "message": "User deleted successfully",
        "deleted_by": current_user["username"],
        "deleted_user_id": user_id
    }
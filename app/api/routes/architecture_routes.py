import json
from fastapi import APIRouter, Depends

from app.database.database import connect_db, add_log
from core.gestion_utilisateurs.security import get_current_user , require_permission

router = APIRouter(tags=["Architecture"])


@router.get("/architecture/sites")
def get_saved_sites(current_user: dict = Depends(require_permission("architecture_list"))):
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, site_name, created_at
        FROM architecture_reports
        WHERE user_id = ?
        ORDER BY created_at DESC
    """, (current_user["id"],))

    rows = cursor.fetchall()
    conn.close()

    add_log(
        action="VIEW_SAVED_ARCHITECTURES",
        user_id=current_user["id"],
        module="ARCHITECTURE",
        status="SUCCESS",
        extra={
            "username": current_user["username"],
            "count": len(rows)
        }
    )

    return {
        "success": True,
        "sites": [
            {
                "id": row[0],
                "site_name": row[1],
                "created_at": row[2]
            }
            for row in rows
        ]
    }


@router.get("/architecture/{report_id}")
def get_architecture_by_id(
    report_id: int,
    current_user: dict = Depends(require_permission("architecture_view"))
):
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, site_name, report_json, created_at
        FROM architecture_reports
        WHERE id = ? AND user_id = ?
    """, (report_id, current_user["id"]))

    row = cursor.fetchone()
    conn.close()

    if not row:
        add_log(
            action="VIEW_ARCHITECTURE",
            user_id=current_user["id"],
            module="ARCHITECTURE",
            status="FAILED",
            extra={
                "username": current_user["username"],
                "report_id": report_id,
                "reason": "Architecture introuvable"
            }
        )

        return {
            "success": False,
            "message": "Architecture introuvable."
        }

    add_log(
        action="VIEW_ARCHITECTURE",
        user_id=current_user["id"],
        module="ARCHITECTURE",
        status="SUCCESS",
        extra={
            "username": current_user["username"],
            "report_id": report_id,
            "site_name": row[1]
        }
    )

    return {
        "success": True,
        "id": row[0],
        "site_name": row[1],
        "report": json.loads(row[2]),
        "created_at": row[3]
    }


@router.delete("/architecture/{report_id}")
def delete_architecture(
    report_id: int,
    current_user: dict = Depends(require_permission("architecture_delete"))
):
    conn = connect_db()
    cursor = conn.cursor()

    try:
        # Vérifier existence
        cursor.execute("""
            SELECT site_name
            FROM architecture_reports
            WHERE id = ? AND user_id = ?
        """, (report_id, current_user["id"]))

        row = cursor.fetchone()

        if not row:
            add_log(
                action="DELETE_ARCHITECTURE",
                user_id=current_user["id"],
                module="ARCHITECTURE",
                status="FAILED",
                extra={
                    "username": current_user["username"],
                    "report_id": report_id,
                    "reason": "Not found or not authorized"
                }
            )

            return {
                "success": False,
                "message": "Architecture introuvable ou non autorisée."
            }

        #  Suppression
        cursor.execute("""
            DELETE FROM architecture_reports
            WHERE id = ? AND user_id = ?
        """, (report_id, current_user["id"]))

        conn.commit()

        add_log(
            action="DELETE_ARCHITECTURE",
            user_id=current_user["id"],
            module="ARCHITECTURE",
            status="SUCCESS",
            extra={
                "username": current_user["username"],
                "report_id": report_id,
                "site_name": row[0],
                "deleted": True
            }
        )

        return {
            "success": True,
            "message": "Architecture supprimée avec succès."
        }

    except Exception as e:
        conn.rollback()

        add_log(
            action="DELETE_ARCHITECTURE",
            user_id=current_user["id"],
            module="ARCHITECTURE",
            status="ERROR",
            extra={
                "error": str(e),
                "report_id": report_id
            }
        )

        raise HTTPException(status_code=500, detail="Erreur serveur")

    finally:
        conn.close()
import json
from fastapi import APIRouter, Depends, HTTPException

from app.database.database import connect_db, add_log
from core.gestion_utilisateurs.security import require_permission

router = APIRouter(tags=["Architecture"])


@router.get("/architecture/sites")
def get_saved_sites(current_user: dict = Depends(require_permission("architecture_list"))):
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT 
            ar.id,
            ar.site_name,
            ar.created_at,
            ar.user_id,
            u.username AS created_by
        FROM architecture_reports ar
        LEFT JOIN users u ON u.id = ar.user_id
        ORDER BY ar.created_at DESC
    """)

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
                "created_at": row[2],
                "created_by_id": row[3],
                "created_by": row[4] if row[4] else "unknown"
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
        SELECT 
            ar.id,
            ar.site_name,
            ar.report_json,
            ar.created_at,
            ar.user_id,
            u.username AS created_by
        FROM architecture_reports ar
        LEFT JOIN users u ON u.id = ar.user_id
        WHERE ar.id = ?
    """, (report_id,))

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
            "site_name": row[1],
            "created_by": row[5] if row[5] else "unknown"
        }
    )

    return {
        "success": True,
        "id": row[0],
        "site_name": row[1],
        "report": json.loads(row[2]),
        "created_at": row[3],
        "created_by_id": row[4],
        "created_by": row[5] if row[5] else "unknown"
    }


@router.delete("/architecture/{report_id}")
def delete_architecture(
    report_id: int,
    current_user: dict = Depends(require_permission("architecture_delete"))
):
    conn = connect_db()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT site_name
            FROM architecture_reports
            WHERE id = ?
        """, (report_id,))

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
                    "reason": "Architecture introuvable"
                }
            )

            return {
                "success": False,
                "message": "Architecture introuvable."
            }

        site_name = row[0]

        cursor.execute("""
            DELETE FROM architecture_reports
            WHERE id = ?
        """, (report_id,))

        conn.commit()

        add_log(
            action="DELETE_ARCHITECTURE",
            user_id=current_user["id"],
            module="ARCHITECTURE",
            status="SUCCESS",
            extra={
                "username": current_user["username"],
                "report_id": report_id,
                "site_name": site_name,
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
from fastapi import APIRouter, Depends, HTTPException

from app.database.database import connect_db
from core.gestion_utilisateurs.security import require_permission

router = APIRouter(
    prefix="/security",
    tags=["Security Analytics"]
)


CRITICAL_ACTIONS = [
    "LOGIN_FAILED",
    "DELETE_USER",
    "UPDATE_USER_ROLE",
    "DEPLOY_NETWORK_CONFIGS",
    "DEPLOY_ACL_CONFIGS",
    "APPLY_AI_FIX",
    "VALIDATE_AI_FIX"
]


@router.get("/analytics")
def get_security_analytics(
    current_user: dict = Depends(require_permission("view_security_analytics"))
):
    conn = connect_db()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT COUNT(*) FROM logs")
        total_logs = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(*)
            FROM logs
            WHERE action = 'LOGIN_FAILED'
        """)
        failed_logins = cursor.fetchone()[0]

        placeholders = ",".join(["?"] * len(CRITICAL_ACTIONS))
        cursor.execute(f"""
            SELECT COUNT(*)
            FROM logs
            WHERE action IN ({placeholders})
        """, CRITICAL_ACTIONS)
        critical_actions = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(*)
            FROM logs
            WHERE module = 'AI_SECURITY'
        """)
        ai_actions = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(*)
            FROM logs
            WHERE module = 'DEPLOYMENT'
        """)
        deployments = cursor.fetchone()[0]

        cursor.execute("""
            SELECT 
                COALESCE(users.username, 'unknown') AS username,
                COUNT(logs.id) AS action_count
            FROM logs
            LEFT JOIN users ON users.id = logs.user_id
            GROUP BY username
            ORDER BY action_count DESC
            LIMIT 10
        """)
        top_users = [
            {
                "username": row["username"],
                "action_count": row["action_count"]
            }
            for row in cursor.fetchall()
        ]

        cursor.execute("""
            SELECT 
                DATE(created_at) AS day,
                COUNT(*) AS count
            FROM logs
            GROUP BY DATE(created_at)
            ORDER BY day ASC
            LIMIT 30
        """)
        timeline = [
            {
                "date": row["day"],
                "count": row["count"]
            }
            for row in cursor.fetchall()
        ]

        cursor.execute(f"""
            SELECT 
                logs.id,
                logs.action,
                logs.module,
                logs.status,
                logs.extra,
                logs.created_at,
                COALESCE(users.username, 'unknown') AS username
            FROM logs
            LEFT JOIN users ON users.id = logs.user_id
            WHERE logs.action IN ({placeholders})
            ORDER BY logs.created_at DESC
            LIMIT 20
        """, CRITICAL_ACTIONS)

        recent_critical_actions = [
            {
                "id": row["id"],
                "username": row["username"],
                "action": row["action"],
                "module": row["module"],
                "status": row["status"],
                "extra": row["extra"],
                "created_at": row["created_at"]
            }
            for row in cursor.fetchall()
        ]

        cursor.execute("""
            SELECT 
                module,
                COUNT(*) AS count
            FROM logs
            WHERE module IS NOT NULL
            GROUP BY module
            ORDER BY count DESC
        """)
        actions_by_module = [
            {
                "module": row["module"],
                "count": row["count"]
            }
            for row in cursor.fetchall()
        ]

        cursor.execute("""
            SELECT 
                status,
                COUNT(*) AS count
            FROM logs
            WHERE status IS NOT NULL
            GROUP BY status
            ORDER BY count DESC
        """)
        actions_by_status = [
            {
                "status": row["status"],
                "count": row["count"]
            }
            for row in cursor.fetchall()
        ]

        risk_score = min(
            100,
            failed_logins * 5 + critical_actions * 8
        )

        if risk_score >= 70:
            risk_level = "HIGH"
        elif risk_score >= 35:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"

        return {
            "success": True,
            "data": {
                "total_logs": total_logs,
                "failed_logins": failed_logins,
                "critical_actions": critical_actions,
                "ai_actions": ai_actions,
                "deployments": deployments,
                "risk_score": risk_score,
                "risk_level": risk_level,
                "top_users": top_users,
                "timeline": timeline,
                "recent_critical_actions": recent_critical_actions,
                "actions_by_module": actions_by_module,
                "actions_by_status": actions_by_status
            }
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

    finally:
        conn.close()
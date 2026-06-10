from fastapi import APIRouter, Depends
from app.database.database import connect_db, add_log
from core.gestion_utilisateurs.security import get_current_user
import json

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


def safe_count(cursor, table_name):
    try:
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        return cursor.fetchone()[0]
    except Exception:
        return 0


def normalize_score(value):
    try:
        score = float(value)
    except Exception:
        return 0

    if 0 < score <= 1:
        score = score * 100

    score = int(round(score))
    return max(0, min(100, score))


def get_row_value(row, key, index, default=None):
    try:
        return row[key]
    except Exception:
        try:
            return row[index]
        except Exception:
            return default


def get_last_architecture_counts(cursor, user_id):
    device_count = 0
    link_count = 0
    vlan_count = 0

    try:
        cursor.execute(
            """
            SELECT report_json
            FROM architecture_reports
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (user_id,)
        )

        row = cursor.fetchone()

        if not row:
            return device_count, link_count, vlan_count

        report_json_raw = get_row_value(row, "report_json", 0, "{}")

        if isinstance(report_json_raw, str):
            report = json.loads(report_json_raw)
        else:
            report = report_json_raw

        summary = report.get("summary", {})
        topology = report.get("topology", {})
        network_context = report.get("network_context", {})

        device_count = int(
            summary.get("device_count")
            or len(topology.get("devices", []))
            or 0
        )

        link_count = int(
            summary.get("link_count")
            or len(topology.get("links", []))
            or 0
        )

        vlan_count = int(
            summary.get("vlan_count")
            or len(network_context.get("vlans", []))
            or 0
        )

    except Exception as e:
        print("Erreur last architecture summary:", e)

    return device_count, link_count, vlan_count


@router.get("/summary")
def dashboard_summary(current_user: dict = Depends(get_current_user)):
    conn = connect_db()
    cursor = conn.cursor()

    try:
        user_id = current_user["id"]

        users_count = safe_count(cursor, "users")

        device_count, link_count, vlan_count = get_last_architecture_counts(
            cursor,
            user_id
        )

        try:
            cursor.execute(
                "SELECT COUNT(*) FROM notifications WHERE user_id = ?",
                (user_id,)
            )
            notifications_count = cursor.fetchone()[0]
        except Exception:
            notifications_count = 0

        try:
            cursor.execute(
                "SELECT COUNT(*) FROM notifications WHERE user_id = ? AND is_read = 0",
                (user_id,)
            )
            unread_notifications = cursor.fetchone()[0]
        except Exception:
            unread_notifications = 0

        try:
            cursor.execute(
                """
                SELECT COUNT(*) FROM notifications
                WHERE user_id = ? AND LOWER(type) IN ('critical', 'error')
                """,
                (user_id,)
            )
            critical_count = cursor.fetchone()[0]
        except Exception:
            critical_count = 0

        try:
            cursor.execute(
                """
                SELECT COUNT(*) FROM notifications
                WHERE user_id = ? AND LOWER(type) = 'warning'
                """,
                (user_id,)
            )
            warning_count = cursor.fetchone()[0]
        except Exception:
            warning_count = 0

        ai_history = []

        try:
            cursor.execute(
                """
                SELECT score, created_at
                FROM (
                    SELECT id, score, created_at 
                    FROM ai_scores
                    WHERE user_id = ?
                    ORDER BY id DESC
                    LIMIT 30
                )
                ORDER BY id ASC
                """,
                (user_id,)
            )

            rows = cursor.fetchall()

            for row in rows:
                score_raw = get_row_value(row, "score", 0, 0)
                created_at = get_row_value(row, "created_at", 1, "")

                score_value = normalize_score(score_raw)

                if score_value > 0:
                    ai_history.append({
                        "score": score_value,
                        "created_at": created_at
                    })

        except Exception as e:
            print("Erreur ai_history:", e)
            ai_history = []

        if ai_history:
            ai_score = ai_history[-1]["score"]
            ai_analysis_count = len(ai_history)
        else:
            ai_score = 0
            ai_analysis_count = 0

        health_percent = ai_score
        healthy_percent = ai_score

        total_alerts = critical_count + warning_count
        risk_percent = max(0, 100 - healthy_percent)

        if total_alerts == 0:
            critical_percent = 0
            warning_percent = 0
            unknown_percent = risk_percent
        else:
            critical_percent = int(round((critical_count / total_alerts) * risk_percent))
            warning_percent = risk_percent - critical_percent
            unknown_percent = 0

        result = {
            "success": True,
            "data": {
                "users_count": users_count,
                "notifications_count": notifications_count,
                "unread_notifications": unread_notifications,

                "device_count": device_count,
                "link_count": link_count,
                "vlan_count": vlan_count,

                "critical_count": critical_count,
                "warning_count": warning_count,

                "ai_score": ai_score,
                "ai_analysis_count": ai_analysis_count,
                "ai_predictions_count": ai_analysis_count,
                "automation_count": device_count + vlan_count,
                "ai_history": ai_history,

                "health_percent": health_percent,
                "healthy_percent": healthy_percent,
                "warning_percent": warning_percent,
                "critical_percent": critical_percent,
                "unknown_percent": unknown_percent,

                "role": current_user.get("role", "viewer"),
                "username": current_user.get("username", "")
            }
        }

        add_log(
            action="VIEW_DASHBOARD_SUMMARY",
            user_id=user_id,
            module="DASHBOARD",
            status="SUCCESS",
            extra={
                "username": current_user.get("username", ""),
                "device_count": device_count,
                "vlan_count": vlan_count,
                "ai_score": ai_score,
                "unread_notifications": unread_notifications
            }
        )

        return result

    finally:
        conn.close()
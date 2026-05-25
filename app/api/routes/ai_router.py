from fastapi import APIRouter, WebSocket
from fastapi import WebSocketDisconnect

from app.websocket.manager import active_connections
from app.services.ai_service import run_ai_agent_from_report
from app.api.shémas import (
    AIReportRequest,
    ScoreHistoryResponse
)
from app.database.database import (
    create_notification,
    save_score,
    add_log,
    connect_db
)

router = APIRouter(prefix="/ai", tags=["AI"])


@router.post("/validate")
def validate_discovery_report(request: AIReportRequest):
    print("REQUEST:", request.dict())

    result = run_ai_agent_from_report(
        discovery_report=request.discovery_report,
        user_input_text=request.user_input_text,
        user_id=request.user_id,
        create_notification=create_notification
    )

    print("AI RESULT:", result)

    score = result.get("score", 0)
    save_score(request.user_id, int(score))

    add_log(
        action="VALIDATE_AI",
        user_id=request.user_id,
        module="AI_SECURITY",
        status="SUCCESS",
        extra={
            "score": score,
            "message": "Discovery report analyzed successfully"
        }
    )

    return {
        "status": "success",
        "message": "Discovery report analyzed successfully",
        "data": result
    }


@router.post("/validate-fix")
def validate_fix(data: dict):
    confirm = data.get("confirm")

    add_log(
        action="VALIDATE_AI_FIX",
        user_id=data.get("user_id"),
        module="AI_SECURITY",
        status="APPROVED" if confirm else "REJECTED",
        extra={"confirm": confirm}
    )

    return {
        "status": "APPROVED" if confirm else "REJECTED"
    }


@router.post("/apply-fix")
def apply_fix(data: dict):
    fixes = data.get("fixes", [])
    executed_commands = []

    for fix in fixes:
        for command in fix.get("commands", []):
            print(f"Executing: {command}")
            executed_commands.append(command)

    add_log(
        action="APPLY_AI_FIX",
        user_id=data.get("user_id"),
        module="AI_SECURITY",
        status="APPLIED",
        extra={
            "fix_count": len(fixes),
            "commands": executed_commands
        }
    )

    return {
        "status": "APPLIED"
    }


@router.websocket("/ws/notifications/{user_id}")
async def notifications_ws(websocket: WebSocket, user_id: int):
    await websocket.accept()
    active_connections[user_id] = websocket

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        active_connections.pop(user_id, None)
    except Exception:
        active_connections.pop(user_id, None)


@router.get("/score-history/{user_id}", response_model=ScoreHistoryResponse)
def get_score_history(user_id: int):
    conn = connect_db()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ai_scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            score INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute(
        """
        SELECT score, created_at
        FROM ai_scores
        WHERE user_id = ?
        ORDER BY created_at ASC
        """,
        (user_id,)
    )

    rows = cursor.fetchall()
    conn.commit()
    conn.close()

    add_log(
        action="VIEW_AI_SCORE_HISTORY",
        user_id=user_id,
        module="AI_SECURITY",
        status="SUCCESS",
        extra={"count": len(rows)}
    )

    return {
        "user_id": user_id,
        "history": [
            {
                "score": row["score"],
                "timestamp": row["created_at"]
            }
            for row in rows
        ]
    }
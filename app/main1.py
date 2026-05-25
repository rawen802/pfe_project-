from fastapi import FastAPI
from fastapi import WebSocket, WebSocketDisconnect, Query, Depends

from app.database.database import init_database

from app.api.routes.auth_router import router as auth_router
from app.api.routes.admin_router import router as admin_router
from app.api.routes.network_router import router as network_router
from app.api.routes.ai_router import router as ai_router
from app.api.routes.dashboard_router import router as dashboard_router
from app.api.routes.architecture_routes import router as architecture_routes
from app.api.routes.audit_routes import router as audit_routes
from app.api.routes.security_analytics_routes import router as security_analytics_routes
from app.api.routes.reports_routes import router as reports_router

from app.api.notification_router import router as notification_router
from app.api.email_settings_router import router as email_settings_router

from app.websocket.manager import connect, disconnect, send_notification
from core.gestion_utilisateurs.security import require_permission


app = FastAPI(title="Network Automation API")


@app.on_event("startup")
def startup_event():
    init_database()


app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(network_router)
app.include_router(architecture_routes)
app.include_router(ai_router)
app.include_router(notification_router)
app.include_router(email_settings_router)
app.include_router(dashboard_router)
app.include_router(audit_routes)
app.include_router(security_analytics_routes)
app.include_router(reports_router)


@app.get("/")
def root():
    return {"message": "API running"}


@app.websocket("/ws/notifications/{user_id}")
async def websocket_notifications(websocket: WebSocket, user_id: int):
    await connect(user_id, websocket)

    try:
        while True:
            await websocket.receive_text()

    except WebSocketDisconnect:
        disconnect(user_id)


@app.get("/notification-ws")
async def notification_ws(
    message: str = Query("Test notification"),
    type: str = Query("INFO"),
    hostname: str = Query(None),
    current_user: dict = Depends(require_permission("view_dashboard"))
):
    await send_notification(
        user_id=current_user["id"],
        message=message,
        type=type.upper(),
        hostname=hostname
    )

    return {
        "status": "sent",
        "user": current_user["username"],
        "message": message,
        "type": type
    }
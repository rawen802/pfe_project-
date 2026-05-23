from fastapi import APIRouter, Depends
from core.gestion_utilisateurs.security import get_current_user
from app.services.notification_service import (
    get_user_notifications,
    mark_notification_as_read,
    create_notification
)

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("")
def list_notifications(current_user: dict = Depends(get_current_user)):
    return {
        "success": True,
        "notifications": get_user_notifications(current_user["id"])
    }


@router.put("/{notification_id}/read")
def mark_as_read(
    notification_id: int,
    current_user: dict = Depends(get_current_user)
):
    mark_notification_as_read(notification_id, current_user["id"])

    return {
        "success": True,
        "message": "Notification marquée comme lue"
    }


@router.post("/test-normal")
def test_normal_notification(current_user: dict = Depends(get_current_user)):
    notif = create_notification(
        user_id=current_user["id"],
        title="Test notification normale",
        message="Cette notification reste uniquement dans l’application.",
        type="success"
    )

    return {
        "success": True,
        "notification": notif
    }


@router.post("/test-important")
def test_important_notification(current_user: dict = Depends(get_current_user)):
    notif = create_notification(
        user_id=current_user["id"],
        title="Test notification importante",
        message="Ceci est une notification critique de test envoyée depuis NetAutoAI.",
        type="critical"
    )

    return {
        "success": True,
        "notification": notif
    }
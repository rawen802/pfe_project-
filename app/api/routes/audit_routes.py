from fastapi import APIRouter, Depends, HTTPException

from app.database.database import get_audit_logs
from core.gestion_utilisateurs.security import (
    get_current_user,
    require_permission
)

router = APIRouter(
    prefix="/audit",
    tags=["Audit Logs"]
)


@router.get("/logs")
def read_audit_logs(
    limit: int = 100,
    current_user: dict = Depends(
        require_permission("view_audit_logs")
    )
):
    try:
        logs = get_audit_logs(limit)

        return {
            "success": True,
            "count": len(logs),
            "logs": logs
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
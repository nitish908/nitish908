from fastapi import APIRouter, Depends

from app.api.deps import require_owner
from app.core.audit import record_audit
from app.core.csrf import verify_csrf
from app.core.db import SessionLocal
from app.models.user import User
from app.workers.tasks import run_daily_workflow_sync

router = APIRouter(prefix="/api/workflow", tags=["workflow"], dependencies=[Depends(verify_csrf)])


@router.post("/run-now")
def run_now(user: User = Depends(require_owner)):
    """Runs the daily workflow synchronously (not via Celery) so it can be
    demoed without waiting for the scheduled beat tick. In production this
    same logic runs on the 'daily-lead-workflow' Celery beat schedule."""
    summary = run_daily_workflow_sync()
    db = SessionLocal()
    try:
        record_audit(db, actor_id=user.id, action="daily_workflow_run_manual", object_type="workflow", detail=str(summary.get("errors", [])))
        db.commit()
    finally:
        db.close()
    return summary

from celery import Celery
from celery.schedules import crontab

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery("hermes_leadgen", broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)
celery_app.conf.beat_schedule = {
    "daily-lead-workflow": {
        "task": "app.workers.tasks.run_daily_workflow",
        # 07:00 UTC daily; adjust to your team's morning per docs/DEPLOYMENT_UBUNTU.md.
        "schedule": crontab(hour=7, minute=0),
    },
}

celery_app.autodiscover_tasks(["app.workers"])

from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery("meridian", broker=settings.redis_url, backend=settings.redis_url)
celery_app.autodiscover_tasks(["app.workers"])

celery_app.conf.beat_schedule = {
    "run-sla-check": {
        "task": "app.workers.tasks.run_sla_check",
        "schedule": 300.0,  # every 5 minutes, per ARCHITECTURE.md
    },
    "run-scan-session": {
        "task": "app.workers.tasks.run_scan_session",
        "schedule": crontab(minute=0),  # hourly
    },
}

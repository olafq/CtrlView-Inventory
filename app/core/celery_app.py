import os
from celery import Celery

ENV = os.getenv("ENV", "dev")

celery_app = Celery(
    "inventory",
    broker=os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0"),
)

# ✅ DEV on Windows: corre tasks en el mismo proceso (sin worker)
if ENV == "dev":
    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = True

"""Celery configuration for asynchronous tasks."""
from celery import Celery

from app.core.config import settings

# Initialize Celery app
app = Celery(
    "psycho_backend",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.workers.context_worker",
        # Will be populated as workers are implemented
        # "app.workers.llm_worker",
        # "app.workers.diary_worker",
        # "app.workers.tarot_worker", 
        # "app.workers.astro_worker",
    ]
)

# Configure Celery
app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Europe/Moscow",
    enable_utc=True,
    
    # Define task routing
    task_routes={
        "app.workers.llm_worker.*": {"queue": "llm_queue"},
        "app.workers.context_worker.*": {"queue": "context_queue"},
        "app.workers.diary_worker.*": {"queue": "db_queue"},
        "app.workers.tarot_worker.*": {"queue": "tarot_queue"},
        "app.workers.astro_worker.*": {"queue": "astro_queue"},
    }
)

# If this module is the main program, start a worker
if __name__ == "__main__":
    app.start() 
from celery import Celery

celery = Celery(
    "tasks",
    broker="redis://redis:6379/0",  # для Docker, иначе localhost
    backend="redis://redis:6379/0",
)

celery.conf.timezone = 'UTC'

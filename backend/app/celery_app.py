"""Celery application factory for background tasks."""
import os
from celery import Celery

def make_celery(app=None):
    """Create and configure Celery app."""
    celery = Celery(
        app.import_name if app else 'app',
        backend=os.getenv('CELERY_BROKER_URL', 'redis://redis:6379/0'),
        broker=os.getenv('CELERY_BROKER_URL', 'redis://redis:6379/0'),
    )
    
    if app:
        class ContextTask(celery.Task):
            def __call__(self, *args, **kwargs):
                with app.app_context():
                    return self.run(*args, **kwargs)
        
        celery.Task = ContextTask
    
    return celery

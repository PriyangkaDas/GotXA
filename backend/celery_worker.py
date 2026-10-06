#!/usr/bin/env python3
"""
Celery worker entrypoint for background report generation tasks
"""

import os
import sys

# Add app directory to path
sys.path.insert(0, os.path.dirname(__file__))

from main import create_app
from app.celery_app import make_celery
from app import tasks  # Import to register task definitions

# Create Flask app
app = create_app()

# Make Celery app
celery = make_celery(app)

if __name__ == '__main__':
    celery.start()

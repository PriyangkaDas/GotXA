#!/usr/bin/env python3
"""
WSGI entry point for production deployment.
"""

import os
import sys
import logging

# Add app directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from main import create_app

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    app = create_app()
    logger.info("✓ Application initialized successfully")
except Exception as e:
    logger.error(f"✗ Failed to initialize application: {e}")
    raise

if __name__ == '__main__':
    app.run()

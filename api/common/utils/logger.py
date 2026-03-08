# utils/logger.py
import logging

# Create logger instance
logger = logging.getLogger("apps")

# Don't log directly here because Django may not have started yet
# Instead, log after Django has started


def setup_logging():
    """Call this function after Django has started"""
    from django.conf import settings
    logger.info("=" * 50)
    logger.info("Application logging system initialized")
    logger.info(f"DEBUG mode: {settings.DEBUG}")
    logger.info(f"Log level: {logging.getLevelName(logger.level)}")
    logger.info("=" * 50)
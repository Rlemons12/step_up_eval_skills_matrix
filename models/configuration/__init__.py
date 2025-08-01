# models/configuration/__init__.py

# Always import config as it has no dependencies
from .config import *

# Try to import logging functions, but make Flask dependencies optional
try:
    from .log_config import logger, debug_id, info_id, warning_id, error_id, critical_id
    from .log_config import with_request_id, set_request_id, get_request_id, clear_request_id
    from .log_config import log_timed_operation, request_id_middleware

    HAS_LOGGING = True
except ImportError as e:
    # Flask/Werkzeug not available - provide simple fallbacks
    import logging
    import uuid

    logger = logging.getLogger(__name__)


    def debug_id(message, request_id=None):
        logger.debug(f"[{request_id or 'no-req'}] {message}")


    def info_id(message, request_id=None):
        logger.info(f"[{request_id or 'no-req'}] {message}")


    def warning_id(message, request_id=None):
        logger.warning(f"[{request_id or 'no-req'}] {message}")


    def error_id(message, request_id=None):
        logger.error(f"[{request_id or 'no-req'}] {message}")


    def critical_id(message, request_id=None):
        logger.critical(f"[{request_id or 'no-req'}] {message}")


    def set_request_id(request_id=None):
        return request_id or str(uuid.uuid4())[:8]


    def get_request_id():
        return str(uuid.uuid4())[:8]


    def clear_request_id():
        pass


    def with_request_id(func):
        return func


    def log_timed_operation(operation_name, request_id=None):
        class DummyContext:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

        return DummyContext()


    def request_id_middleware(app):
        return app


    HAS_LOGGING = False
    print(f"Warning: Flask logging unavailable, using fallback logging. Error: {e}")

# Export everything that might be imported
__all__ = [
    # Config variables (from config.py)
    'BASE_DIR', 'DATABASE_DIR', 'DATABASE_URL', 'TEMPLATE_FOLDER_PATH',
    'TRAINING_PLANS_CSV', 'TRAINING_PLANS_XLSX', 'FLASH_CARDS_HTML',
    'UPLOAD_FOLDER', 'IMAGES_FOLDER', 'TEMPORARY_FILES', 'ALLOWED_EXTENSIONS',

    # Logging functions
    'logger', 'debug_id', 'info_id', 'warning_id', 'error_id', 'critical_id',
    'set_request_id', 'get_request_id', 'clear_request_id', 'with_request_id',
    'log_timed_operation', 'request_id_middleware', 'HAS_LOGGING'
]
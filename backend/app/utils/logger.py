import logging
import sys
from logging.handlers import RotatingFileHandler
import os

def setup_logger():
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # Remove existing handlers to avoid duplicates
    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    # File handler with UTF-8 encoding
    file_handler = RotatingFileHandler(
        'logs/app.log',
        maxBytes=10240000,
        backupCount=10,
        encoding='utf-8'
    )
    file_formatter = logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    )
    file_handler.setFormatter(file_formatter)
    file_handler.setLevel(logging.INFO)
    
    # Console handler with UTF-8 encoding (Windows compatible)
    console_handler = logging.StreamHandler(sys.stdout)
    console_formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] %(message)s'
    )
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(logging.INFO)
    
    # Force UTF-8 encoding for Windows console (only if needed)
    if sys.platform == 'win32':
        try:
            import codecs
            if hasattr(sys.stdout, 'buffer') and not isinstance(sys.stdout, codecs.StreamReaderWriter):
                sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
                sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')
        except (AttributeError, TypeError):
            pass
    
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # Get app logger and return it
    logger = logging.getLogger("app")
    logger.setLevel(logging.INFO)
    logger.info('Application logger initialized')
    return logger

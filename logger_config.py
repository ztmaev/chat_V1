import os
import logging
from logging.handlers import RotatingFileHandler

def setup_logger(name='chat_api'):
    # Configure Logging
    LOG_FOLDER = os.getenv('LOG_FOLDER', 'logs')
    os.makedirs(LOG_FOLDER, exist_ok=True)
    LOG_FILE = os.path.join(LOG_FOLDER, 'chat_api.log')

    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # Prevent adding handlers multiple times
    if not logger.handlers:
        # Create rotating file handler (10MB per file, keep 5 backups)
        file_handler = RotatingFileHandler(LOG_FILE, maxBytes=10*1024*1024, backupCount=5)
        file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(file_formatter)

        # Create console handler
        console_handler = logging.StreamHandler()
        console_formatter = logging.Formatter('%(levelname)s: %(message)s')
        console_handler.setFormatter(console_formatter)

        # Add handlers to logger
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    return logger

# Create a default logger instance
logger = setup_logger()

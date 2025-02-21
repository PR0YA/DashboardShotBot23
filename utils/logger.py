import logging
import sys

def setup_logger():
    logger = logging.getLogger('DashboardSJBot')
    logger.setLevel(logging.INFO)

    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Console handler with detailed formatting
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler with more detailed formatting for debugging
    file_handler = logging.FileHandler('bot.log')
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s - [%(filename)s:%(lineno)d]'
    ))
    logger.addHandler(file_handler)

    return logger

logger = setup_logger()
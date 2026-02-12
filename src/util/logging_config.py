
import logging

from pathlib import Path

def setup_logging() -> None:
    """
    Configure logging for the Whispers of the Abyss project.
    - Console handler for real-time output.
    - Optional file handler for persistent logs.
    - Custom formatter with timestamps, levels and messages.
    """
    log_level = "DEBUG"
    log_to_file = False

    # Create logger
    logger = logging.getLogger()
    logger.setLevel(log_level)

    if logger.hasHandlers():
        logger.handlers.clear()

    # logger format
    formatter = logging.Formatter('(%(asctime)s) [%(levelname)s] <%(filename)s> %(message)s')

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler (optional, logs to project root)
    if log_to_file:
        log_dir = Path(__file__).parent.parent.parent / "logs"
        log_dir.mkdir(exist_ok=True)
        file_handler = logging.FileHandler(log_dir / "ocean.log")
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    # Suppress noisy Panda3D logs if needed
    logging.getLogger('panda3d').setLevel(log_level)

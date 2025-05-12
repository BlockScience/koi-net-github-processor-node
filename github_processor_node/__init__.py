import logging
from rich.logging import RichHandler

log_level = "DEBUG"  # Default level

# Setup root logger
logger = logging.getLogger()  # Get root logger
logger.setLevel(log_level.upper())  # Set level for root logger

# Remove existing handlers to avoid duplicates if this module is reloaded
for handler in logger.handlers[:]:
    logger.removeHandler(handler)

# Setup RichHandler for console output
rich_handler = RichHandler(
    rich_tracebacks=True, show_path=False, log_time_format="%Y-%m-%d %H:%M:%S"
)
rich_handler.setLevel(log_level)
rich_handler.setFormatter(
    logging.Formatter(
        fmt="%(name)s - %(message)s",
        datefmt="[%X]",
    )
)
logger.addHandler(rich_handler)

# Add file handler to write logs to node.proc.log
file_handler = logging.FileHandler("node.proc.log")
file_handler.setLevel(log_level.upper())
file_handler.setFormatter(
    logging.Formatter(
        fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
)
logger.addHandler(file_handler)

logger.info(
    f"Logging initialized for HackMD Processor Node. Level: {log_level.upper()}."
)

# Re-export the node instance
from .core import node

__all__ = ["node"]

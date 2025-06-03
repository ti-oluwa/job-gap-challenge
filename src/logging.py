from pathlib import PurePath, Path
import typing
import logging
from logging.handlers import TimedRotatingFileHandler
import sys
import os
from rich.logging import RichHandler
from rich.console import Console


def get_rotating_file_handler(
    log_file: typing.Union[str, PurePath],
    create: bool = False,
    **handler_kwargs,
) -> TimedRotatingFileHandler:
    """
    Get a rotating file handler for logging.

    :param log_file: Path to the log file.
    :param create: Create the log file if it does not exist.
    :param handler_kwargs: Additional keyword arguments for the handler.
    :return: Rotating file handler.
    """
    if not os.path.exists(log_file) and create:
        os.makedirs(os.path.dirname(log_file), exist_ok=True, mode=0o755)
    return TimedRotatingFileHandler(
        log_file,
        **handler_kwargs,
    )


def setup_logger(
    logger: typing.Union[str, logging.Logger] = "abs_crawler",
    log_file: typing.Optional[typing.Union[str, PurePath]] = None,
    console: typing.Optional[typing.IO[str]] = sys.stdout,
    base_level: typing.Union[int, str] = logging.DEBUG,
    format: typing.Optional[typing.Union[str, logging.Formatter]] = None,
    *handlers: logging.Handler,
) -> logging.Logger:
    """
    Simple interface to set up a logger. Returns the configured logger.

    :param log_file: Path to the log file if file logging is desired.
        A rotating file handler will be created if the file does not exist.
    :param console: Console stream to log to.
    :param base_level: Base logging level.
    :param format: Log message format.
    :param logger: Name of the logger or `logging.Logger` object.
    :param handlers: Additional handlers to add to the logger.
    :return: Configured logger.
    """
    logger = logging.getLogger(logger) if isinstance(logger, str) else logger
    logger.setLevel(base_level)
    logger.handlers.clear()

    if not isinstance(format, logging.Formatter):
        formatter = logging.Formatter(
            format or "[%(asctime)s] %(levelname)s: %(message)s",
            datefmt="%d/%b/%Y %H:%M:%S%z",
        )
    else:
        formatter = format

    if console:
        console_handler = RichHandler(
            console=Console(file=console), show_time=False, show_level=False
        )
        console_handler.setFormatter(formatter)
        console_handler.setLevel(base_level)
        logger.addHandler(console_handler)

    if log_file:
        file_handler = get_rotating_file_handler(
            log_file,
            create=True,
            when="midnight",
            backupCount=7,
            encoding="utf-8",
            utc=True,
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(base_level)
        logger.addHandler(file_handler)

    for handler in handlers:
        logger.addHandler(handler)
    return logger


log_dir = os.getenv("LOGS_DIR")
if log_dir:
    log_file = Path(log_dir).resolve() / "job_gap_application.log"
else:
    log_file = None
logger = setup_logger(base_level=logging.DEBUG, log_file=log_file)

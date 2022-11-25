"""
To use, install termcolor using pip:
$ python -m pip install termcolor

copy and paste the following in your code
# region Logging
import logging
from colored_logger import get_logger

fname = Path(__file__).stem
logger = get_logger(name=__name__, log_file_name=fname, level=logging.DEBUG, file_level=logging.DEBUG)
# endregion
"""

import logging
import logging.config
from logging import addLevelName, setLoggerClass, NOTSET
from pathlib import Path


BASE_DIR = Path(".").resolve()
project_name = BASE_DIR.name
LOGS_FOLDER = BASE_DIR / "logs"
DEFAULT_LOGGING_NAME = project_name
DEFAULT_LOG_FILE_NAME = f"{project_name}.log"
# https://docs.python.org/3/library/logging.html#logging.LogRecord
LOGGING_FORMAT = "[%(name)s]: [%(asctime)s] [%(levelname)s] {%(short_filename)s:%(lineno)d} %(funcName)s # %(message)s"
LOGGING_DATE_FORMAT = "%d/%b/%Y %H:%M:%S"


class CustomLogger(logging.Logger):
    DEBUG_LEVELV_NUM = 60

    def __init__(self, name, level=NOTSET):
        super().__init__(name, level)

        addLevelName(self.DEBUG_LEVELV_NUM, "DEBUGV")

    def debugv(self, msg, *args, **kwargs):
        if self.isEnabledFor(self.DEBUG_LEVELV_NUM):
            self._log(self.DEBUG_LEVELV_NUM, msg, args, **kwargs)


# this is for django based loggers to skip media file requests in logs
def skip_static_or_media_requests(record):
    message = record.getMessage()
    if "GET /static" in message or "GET /media" in message or "GET /prod_static" in message:  # filter whatever you want
        return False
    return True


class CallbackFilter(logging.Filter):
    """
    A logging filter that checks the return value of a given callable (which
    takes the record-to-be-logged as its only parameter) to decide whether to
    log a record.
    """

    def __init__(self, callback):
        self.callback = callback

    def filter(self, record):
        if self.callback(record):
            return 1
        return 0


class AppFilter(CallbackFilter):
    def filter(self, record):
        max_len = 3
        short_filename_split = record.pathname.split("/")
        if len(short_filename_split) < max_len:
            record.short_filename = record.pathname
        else:
            record.short_filename = "/".join(short_filename_split[-max_len:])
        return True and super().filter(record)


# Deprecated
class ColorConsole:
    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"

    LOG_COLORS = {
        "info": [OKGREEN],
        "error": [FAIL],
        "warning": [WARNING],
        "exception": [FAIL],
        "header": [HEADER],
        "critical": [FAIL, BOLD, UNDERLINE],
        "ending": [ENDC],
    }


class ColorConsole2(ColorConsole):
    """Text colors:
    grey red green yellow blue magenta cyan white
    Text highlights:
    on_grey on_red on_green on_yellow on_blue on_magenta on_cyan on_white
    Attributes:
    bold dark underline blink reverse concealed"""

    ENDC = "\033[0m"
    try:
        from termcolor import colored
    except ImportError:
        raise ImportError("Please install termcolor: pip install termcolor")

    HEADER = colored("", color="magenta", on_color=None, attrs=["bold"]).split(ENDC)[0]
    OKBLUE = colored("", color="blue", on_color=None, attrs=None).split(ENDC)[0]
    OKCYAN = colored("", color="cyan", on_color=None, attrs=None).split(ENDC)[0]
    OKGREEN = colored("", color="green", on_color=None, attrs=None).split(ENDC)[0]
    DEBUG = colored("", color="grey", on_color=None, attrs=None).split(ENDC)[0]
    WARNING = colored("", color="yellow", on_color=None, attrs=None).split(ENDC)[0]
    ERROR = colored("", color="red", on_color=None, attrs=None).split(ENDC)[0]
    EXCEPTION = ERROR
    CRITICAL = colored("", color="white", on_color="on_red", attrs=None).split(ENDC)[0]
    BOLD = colored("", color=None, on_color=None, attrs=["bold"]).split(ENDC)[0]
    UNDERLINE = colored("", color=None, on_color=None, attrs=["underline"]).split(ENDC)[0]

    LOG_COLORS = {
        "header": [HEADER],
        "info": [OKGREEN],
        "debug": [DEBUG],
        "warning": [WARNING],
        "debugv": [DEBUG],
        "error": [ERROR],
        "exception": [EXCEPTION],
        "critical": [CRITICAL, BOLD, UNDERLINE],
        "level 60": [DEBUG],
        "ending": [ENDC],
    }


class CustomFormatter(logging.Formatter):

    console_class = ColorConsole2

    def get_formatted(self, msg, levelname):
        header, msg = msg.split("#", maxsplit=1)
        header_prefix = self.console_class.HEADER
        header_formatted = f"{header_prefix}{header}{self.console_class.ENDC}"
        msg_prefix = (
            "".join(self.console_class.LOG_COLORS.get(levelname.lower(), [self.console_class.OKBLUE])).strip()
            + ColorConsole.BOLD
        )
        msg_suffix = "".join(self.console_class.LOG_COLORS.get("ending", [self.console_class.ENDC]))
        msg_formatted = f"{msg_prefix}{msg}{msg_suffix}"
        return f"{header_formatted}:{msg_formatted}"

    def format(self, record):

        # Save the original format configured by the user
        # when the logger formatter was instantiated
        format_orig = self._style._fmt

        # self._style._fmt = self.get_format(record)

        # Call the original formatter class to do the grunt work
        result = logging.Formatter.format(self, record)
        result = self.get_formatted(result, record.levelname)

        # Restore the original format configured by the user
        self._style._fmt = format_orig

        return result


def get_logging_dict_config(log_file_path: Path, level: int = logging.DEBUG, file_level: int = logging.INFO) -> dict:
    config = {
        "version": 1,
        # Version of logging
        "disable_existing_loggers": False,
        "filters": {
            "app_filter": {
                "()": AppFilter,
                "callback": skip_static_or_media_requests,
            }
        },
        # disable logging
        "formatters": {
            "timestamp": {
                # 'format': '${pathname}s:${lineno}d $ {asctime} $ {levelname} $ {message}',
                "format": LOGGING_FORMAT,
                "datefmt": LOGGING_DATE_FORMAT,
            },
            "custom": {
                "format": LOGGING_FORMAT,
                "datefmt": LOGGING_DATE_FORMAT,
                "()": CustomFormatter,
            },
        },
        # Handlers #############################################################
        "handlers": {
            "file": {
                "level": file_level,
                "class": "logging.handlers.RotatingFileHandler",
                "filename": log_file_path,
                "formatter": "timestamp",
                "filters": ["app_filter"],
                "backupCount": 10,
                "maxBytes": 1024 * 1024 * 15,  # 1024 * 1024 * 15B = 15MB
            },
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "custom",
                "filters": ["app_filter"],
            },
        },
        "root": {
            "handlers": ["file", "console"],
            "level": level,
            "propagate": True,
        },
    }
    return config


# Level   Numeric value
# CRITICAL    50
# ERROR       40
# WARNING     30
# INFO        20
# DEBUG       10
# NOTSET      0


def get_logger(
    name: str = DEFAULT_LOGGING_NAME,
    log_file_name: str = DEFAULT_LOG_FILE_NAME,
    level: int = logging.DEBUG,
    file_level: int = logging.INFO,
) -> CustomLogger:
    if not log_file_name.endswith(".log"):
        log_file_name += ".log"
    log_file_path = LOGS_FOLDER / log_file_name
    log_file_path.parent.mkdir(parents=True, exist_ok=True)

    setLoggerClass(CustomLogger)
    logging.config.dictConfig(
        get_logging_dict_config(
            log_file_path=log_file_path,
            level=level,
            file_level=file_level,
        )
    )
    logger = logging.getLogger(name)
    logger.__class__ = CustomLogger

    return logger


# endregion

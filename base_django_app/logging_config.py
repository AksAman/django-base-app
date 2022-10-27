# To Import add this line in settings.py
# from .logging_config import *  # noqa: F403, F401
# logger in any module can be accessed by:
# from django.conf import settings
# logger = settings.LOGGER


# region LOGGING
from decouple import config
from django.conf import settings
import logging
from logging import addLevelName, setLoggerClass, NOTSET
from pathlib import Path

BASE_DIR = settings.BASE_DIR
LOG_FILE_NAME: str = str(config("LOG_FILE_NAME", default=f"logs/{BASE_DIR.name}.log"))
INTERNAL_LOG_FILE_NAME: str = str(config("INTERNAL_LOG_FILE_NAME", default=f"logs/{BASE_DIR.name}_internal.log"))
LOGGING_NAME = "django"
INTERNAL_LOGGING_NAME = "internal"

LOG_FILE_NAMES = [
    LOG_FILE_NAME,
    INTERNAL_LOG_FILE_NAME,
]

for log_file_name in LOG_FILE_NAMES:
    log_file_parent: Path = BASE_DIR.joinpath(Path(log_file_name).parent)
    log_file_parent.mkdir(parents=True, exist_ok=True)


from django.utils.log import CallbackFilter


class CustomLogger(logging.Logger):
    DEBUG_LEVELV_NUM = 60

    def __init__(self, name, level=NOTSET):
        super().__init__(name, level)

        addLevelName(self.DEBUG_LEVELV_NUM, "DEBUGV")

    def debugv(self, msg, *args, **kwargs):
        if self.isEnabledFor(self.DEBUG_LEVELV_NUM):
            self._log(self.DEBUG_LEVELV_NUM, msg, args, **kwargs)


setLoggerClass(CustomLogger)


def skip_static_or_media_requests(record):
    message = record.getMessage()
    if "GET /static" in message or "GET /media" in message or "GET /prod_static" in message:  # filter whatever you want
        return False
    return True


class AppFilter(CallbackFilter):
    def filter(self, record):
        max_len = 3
        short_filename_split = record.pathname.split("/")
        if len(short_filename_split) < max_len:
            record.short_filename = record.pathname
        else:
            record.short_filename = "/".join(short_filename_split[-max_len:])
        return True and super().filter(record)


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
    from termcolor import colored

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


# LOGGING_FORMAT = '[%(asctime)s] [%(levelname)s] [%(name)s] p%(process)s {%(short_filename)s:%(lineno)d} %(funcName)s # %(message)s'
LOGGING_FORMAT = "[%(asctime)s] [%(levelname)s] {%(short_filename)s:%(lineno)d} %(funcName)s # %(message)s"
LOGGING_DATE_FORMAT = "%d/%b/%Y %H:%M:%S"
LOGGING = {
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
            # 'style': '{',
        },
        "custom": {
            "format": LOGGING_FORMAT,
            "datefmt": LOGGING_DATE_FORMAT,
            "class": "base_django_app.logging_config.CustomFormatter",
        },
    },
    # Handlers #############################################################
    "handlers": {
        "file": {
            "level": "INFO",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": LOG_FILE_NAME,
            "formatter": "custom",
            "filters": ["app_filter"],
            "backupCount": 10,
            "maxBytes": 1024 * 1024 * 15,  # 1024 * 1024 * 15B = 15MB
        },
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "custom",
            "filters": ["app_filter"],
        },
        "internal_handler": {
            "level": "INFO",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": INTERNAL_LOG_FILE_NAME,
            "formatter": "custom",
            "filters": ["app_filter"],
            "backupCount": 10,
            "maxBytes": 1024 * 1024 * 15,  # 1024 * 1024 * 15B = 15MB
        },
    },
    # Loggers ####################################################################
    "loggers": {
        "django": {
            "handlers": ["file", "console"],
            "level": "INFO",
            "propagate": True,
        },
        INTERNAL_LOGGING_NAME: {
            "handlers": ["internal_handler", "console"],
            "level": "INFO",
            "propagate": True,
        },
    },
}

# Level   Numeric value
# CRITICAL    50
# ERROR       40
# WARNING     30
# INFO        20
# DEBUG       10
# NOTSET      0


LOG_VIEWER_MAX_READ_LINES = 1000  # total log lines will be read
LOG_VIEWER_PAGE_LENGTH = 25  # total log lines per-page
LOG_VIEWER_PATTERNS = ["]OFNI[", "]GUBED[", "]GNINRAW[", "]RORRE[", "]LACITIRC["]
LOGGER: CustomLogger = logging.getLogger(LOGGING_NAME)  # type: ignore
INTERNAL_LOGGER: CustomLogger = logging.getLogger(INTERNAL_LOGGING_NAME)  # type: ignore
# endregion

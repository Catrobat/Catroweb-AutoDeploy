# Source: https://stackoverflow.com/questions/384076/how-can-i-color-python-logging-output
import logging
import logging.handlers

from config import Config

BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE = range(8)
# The background is set with 40 plus the number of the color, and the foreground with 30

# These are the sequences need to get colored output
RESET_SEQ = "\033[0m"
COLOR_SEQ = "\033[1;%dm"
BOLD_SEQ = "\033[1m"

COLORS = {
    'WARNING': YELLOW,
    'INFO': WHITE,
    'DEBUG': BLUE,
    'CRITICAL': YELLOW,
    'ERROR': RED
}


class ColoredFormatter(logging.Formatter):
    def __init__(self, msg, use_color=True):
        logging.Formatter.__init__(self, msg)
        self.use_color = use_color

    def format(self, record):
        import copy
        record = copy.copy(record)
        levelname = record.levelname
        if self.use_color and levelname in COLORS:
            levelname_color = COLOR_SEQ % (30 + COLORS[levelname]) + levelname + RESET_SEQ
            record.levelname = levelname_color
        return logging.Formatter.format(self, record)


class ColoredLogger(logging.Logger):
    FILE_FORMAT = '%(asctime)s %(levelname)s: %(message)s'
    CONSOLE_FORMAT = "%(asctime)s [%(levelname)-18s] %(message)s"

    def __init__(self, name):
        logging.Logger.__init__(self, name, logging.DEBUG)

        color_formatter = ColoredFormatter(self.formatter_message(self.CONSOLE_FORMAT, True))
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(color_formatter)
        self.addHandler(console_handler)

        file_formatter = logging.Formatter(self.FILE_FORMAT)
        file_handler = logging.handlers.RotatingFileHandler(Config.LOG_FILE, maxBytes=512000, backupCount=3)
        file_handler.setLevel(logging.WARNING)
        file_handler.setFormatter(file_formatter)
        self.addHandler(file_handler)

        return

    @staticmethod
    def formatter_message(message, use_color=True):
        if use_color:
            message = message.replace("$RESET", RESET_SEQ).replace("$BOLD", BOLD_SEQ)
        else:
            message = message.replace("$RESET", "").replace("$BOLD", "")
        return message

    @staticmethod
    def create_file_handler(path: str):
        file_formatter = logging.Formatter(ColoredLogger.FILE_FORMAT)
        file_handler = logging.FileHandler(filename=path, mode='w')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(file_formatter)
        return file_handler

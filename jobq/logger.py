import logging
import sys

from siftlog import ColorPlainTextStreamHandler, SiftLog  # type: ignore

from jobq.constants import Const

core_logger = logging.getLogger(Const.LOG_NAME)
core_logger.setLevel(10)


color_handler = ColorPlainTextStreamHandler(sys.stdout)
color_handler.set_color(SiftLog.TRACE, fg=color_handler.BLACK, bg=color_handler.WHITE)
color_handler.set_color(logging.DEBUG, fg=color_handler.CYAN)
core_logger.addHandler(color_handler)

logger = SiftLog(
    core_logger,
)

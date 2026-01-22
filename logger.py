import logging
import os


def get_logger(name: str = "ai_booking") -> logging.Logger:
    log = logging.getLogger(name)
    if not log.handlers:
        log.setLevel(logging.INFO)
        fh = logging.FileHandler(os.path.join(os.path.dirname(__file__), "ai_booking.log"))
        fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
        fh.setFormatter(fmt)
        log.addHandler(fh)
    return log

"""
utils.py -- Shared utilities used across all automation modules.
"""
import sys, io
# Force UTF-8 on Windows stdout/stderr so Unicode symbols never crash
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

import os
import logging
import hashlib
from datetime import datetime
from colorama import Fore, Style, init

init(autoreset=True)


# --- Logging Factory ----------------------------------------------------------

def get_logger(name: str, log_file: str, level=logging.INFO) -> logging.Logger:
    """
    Create (or retrieve) a named logger that writes to both a rotating
    file and the console with coloured output.
    """
    logger = logging.getLogger(name)
    if logger.handlers:          # already configured -- reuse
        return logger

    logger.setLevel(level)
    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # File handler
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    # Console handler (coloured)
    ch = logging.StreamHandler()
    ch.setFormatter(_ColourFormatter(fmt))
    logger.addHandler(ch)

    return logger


class _ColourFormatter(logging.Formatter):
    """Adds ANSI colour to console log levels."""
    COLOURS = {
        logging.DEBUG:    Fore.CYAN,
        logging.INFO:     Fore.GREEN,
        logging.WARNING:  Fore.YELLOW,
        logging.ERROR:    Fore.RED,
        logging.CRITICAL: Fore.MAGENTA,
    }

    def __init__(self, base_fmt: logging.Formatter):
        super().__init__()
        self._base = base_fmt

    def format(self, record: logging.LogRecord) -> str:
        colour = self.COLOURS.get(record.levelno, "")
        msg = self._base.format(record)
        return f"{colour}{msg}{Style.RESET_ALL}"


# --- Hashing ------------------------------------------------------------------

def md5_of_file(path: str, chunk: int = 65536) -> str:
    """Return the MD5 hex-digest of a file, reading in *chunk*-byte blocks."""
    h = hashlib.md5()
    try:
        with open(path, "rb") as f:
            while data := f.read(chunk):
                h.update(data)
    except (PermissionError, OSError):
        return ""
    return h.hexdigest()


# --- Formatting helpers -------------------------------------------------------

def bytes_to_human(n: float) -> str:
    """Convert a byte count to a human-readable string (KB / MB / GB ...)."""
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(n) < 1024.0:
            return f"{n:6.2f} {unit}"
        n /= 1024.0
    return f"{n:.2f} PB"


def timestamp() -> str:
    """Return the current date-time as a compact string for filenames."""
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def section(title: str, width: int = 60) -> str:
    """Return a pretty section header string."""
    bar = "-" * width
    return f"\n{bar}\n  {title}\n{bar}"

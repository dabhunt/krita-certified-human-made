import sys
import os
from datetime import datetime

# Import config with fallback if not available
try:
    from .config import DEBUG_MODE, LOG_TO_CONSOLE, LOG_TO_FILE, DEBUG_LOG_FILE, LOGS_DIR
except ImportError:
    # Fallback if config not available
    DEBUG_MODE = os.environ.get('CHM_DEBUG', 'False').lower() in ('true', '1', 'yes')
    LOG_TO_CONSOLE = DEBUG_MODE
    LOG_TO_FILE = True
    LOGS_DIR = os.path.expanduser("~/.local/share/chm/logs")
    DEBUG_LOG_FILE = os.path.join(LOGS_DIR, "plugin_debug.log")


def log_message(message, prefix="CHM", level="INFO", force_console=False):
    """
    Log a message with configurable console/file output.
    
    Args:
        message: The message to log
        prefix: Prefix for the log message (default: "CHM")
        level: Log level (INFO, WARNING, ERROR, DEBUG)
        force_console: Force console output even if LOG_TO_CONSOLE is False
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    full_message = f"{prefix}: [{level}] {message}"
    
    # Console output (only in debug mode unless forced or it's an error)
    if LOG_TO_CONSOLE or force_console or level in ("ERROR", "WARNING"):
        print(full_message)
        sys.stdout.flush()
    
    # File output (always enabled for troubleshooting)
    if LOG_TO_FILE:
        try:
            os.makedirs(LOGS_DIR, exist_ok=True)
            with open(DEBUG_LOG_FILE, "a") as f:
                f.write(f"[{timestamp}] {full_message}\n")
        except Exception as e:
            # Fail silently - logging should never crash the plugin
            if LOG_TO_CONSOLE:
                print(f"[LOGGING-ERROR] Failed to write to log file: {e}")


def log_info(message, prefix="CHM"):
    """Log info message"""
    log_message(message, prefix=prefix, level="INFO")


def log_warning(message, prefix="CHM"):
    """Log warning message"""
    log_message(message, prefix=prefix, level="WARNING", force_console=True)


def log_error(message, prefix="CHM"):
    """Log error message"""
    log_message(message, prefix=prefix, level="ERROR", force_console=True)


def log_debug(message, prefix="CHM"):
    """Log debug message (only shown if DEBUG_MODE enabled)"""
    if DEBUG_MODE:
        log_message(message, prefix=prefix, level="DEBUG")



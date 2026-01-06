"""
Shared logging utility for CHM plugin modules

This module provides a centralized logging function that can be used
by standalone modules (like c2pa_builder, png_c2pa_embedder) that don't
have access to class-based _log() methods.
"""

import sys
import os
from datetime import datetime


def log_message(message, prefix="CHM"):
    """
    Log a message to both stdout and the debug log file.
    
    Args:
        message: The message to log
        prefix: Prefix for the log message (default: "CHM")
    """
    # Format message with timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    full_message = f"{prefix}: {message}"
    
    # Print to stdout
    print(full_message)
    sys.stdout.flush()
    
    # Write to debug file
    try:
        log_dir = os.path.expanduser("~/.local/share/chm")
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, "plugin_debug.log")
        
        with open(log_file, "a") as f:
            f.write(f"[{timestamp}] {full_message}\n")
    except Exception as e:
        # Fail silently - logging should never crash the plugin
        print(f"[LOGGING-ERROR] Failed to write to log file: {e}")



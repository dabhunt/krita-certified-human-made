import os

# =============================================================================
# PRODUCTION vs DEBUG MODE
# =============================================================================

# Set to False for production release
# Set to True for development/debugging
DEBUG_MODE = os.environ.get('CHM_DEBUG', 'False').lower() in ('true', '1', 'yes')

# Logging configuration
LOG_TO_FILE = True  # Always log to file for troubleshooting
LOG_TO_CONSOLE = DEBUG_MODE  # Only spam console in debug mode

# =============================================================================
# PATHS
# =============================================================================

# User data directory
USER_DATA_DIR = os.path.expanduser("~/.local/share/chm")

# Session storage
SESSIONS_DIR = os.path.join(USER_DATA_DIR, "sessions")

# Proof output
PROOFS_DIR = os.path.join(USER_DATA_DIR, "proofs")

# Logs
LOGS_DIR = os.path.join(USER_DATA_DIR, "logs")
DEBUG_LOG_FILE = os.path.join(LOGS_DIR, "plugin_debug.log")

# =============================================================================
# FEATURE FLAGS
# =============================================================================

# Event capture
ENABLE_STROKE_DETECTION = True
ENABLE_LAYER_DETECTION = True
ENABLE_IMPORT_DETECTION = True
ENABLE_UNDO_DETECTION = True

# AI detection
ENABLE_AI_PLUGIN_DETECTION = True

# Tracing detection (removed Jan 3, 2026 - kept for reference)
ENABLE_TRACING_DETECTION = False

# =============================================================================
# PERFORMANCE TUNING
# =============================================================================

# Polling interval (ms) for event detection
POLL_INTERVAL_MS = 500

# AFK detection threshold (number of polls without activity)
AFK_THRESHOLD_POLLS = 2  # 2 polls × 500ms = 1 second

# Import detection delay (polls to wait before checking pasted content)
IMPORT_CHECK_DELAY_POLLS = 6  # 6 polls × 500ms = 3 seconds

# =============================================================================
# API CONFIGURATION
# =============================================================================

# Backend API URL for server-side signing and timestamping
# Override with CHM_API_URL environment variable if needed
# Default: https://certified-human-made.org
# Development: https://YOUR-REPL-NAME.replit.app
API_URL = os.environ.get('CHM_API_URL', 'https://certified-human-made.org')

# API timeout (seconds)
API_TIMEOUT = 30

# =============================================================================
# CRYPTO & SECURITY
# =============================================================================

# Use Rust crypto if available, otherwise fall back to Python
PREFER_RUST_CRYPTO = True

# Refuse to finalize proofs if Rust crypto unavailable
REQUIRE_RUST_CRYPTO = False  # Set to True after implementing security recommendation

# Session encryption
SESSION_ENCRYPTION_ENABLED = True

# =============================================================================
# UI SETTINGS
# =============================================================================

# Show detailed metadata in proof dialogs
SHOW_DETAILED_METADATA = True

# Confirm before generating proof
CONFIRM_BEFORE_PROOF_GENERATION = True

# =============================================================================
# VENDOR DEPENDENCIES
# =============================================================================

# Whether to use vendored libraries (PIL, numpy, scipy)
# Note: Tracing detection removed, but libraries kept for future features
USE_VENDORED_LIBRARIES = True

# =============================================================================
# VERSION INFO
# =============================================================================

CHM_VERSION = "1.0.0-rc1"
MIN_KRITA_VERSION = "5.2.0"

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def ensure_directories():
    """Create necessary directories if they don't exist"""
    for directory in [USER_DATA_DIR, SESSIONS_DIR, PROOFS_DIR, LOGS_DIR]:
        os.makedirs(directory, exist_ok=True)

def is_debug_mode():
    """Check if running in debug mode"""
    return DEBUG_MODE

def should_log_to_console():
    """Check if should log to console"""
    return LOG_TO_CONSOLE


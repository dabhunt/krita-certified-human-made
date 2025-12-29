"""
Certified Human-Made (CHM) - Krita Plugin

This plugin captures art creation events to generate cryptographic proofs of human authorship.
"""

import sys
import os

# Log to both stdout AND a debug file for troubleshooting
def debug_log(message):
    """Write to both console and debug file"""
    print(message)
    sys.stdout.flush()  # Force flush to console
    
    # Also write to debug file
    try:
        import os
        log_dir = os.path.expanduser("~/.local/share/chm")
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, "plugin_debug.log")
        
        with open(log_file, "a") as f:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"[{timestamp}] {message}\n")
            f.flush()
    except Exception as e:
        print(f"CHM: Could not write to log file: {e}")

debug_log("=" * 60)
debug_log("CHM: __init__.py starting to load")
debug_log("=" * 60)

try:
    debug_log("CHM: Importing Krita")
    from krita import Krita
    debug_log("CHM: Krita imported successfully")
    
    debug_log("CHM: Importing CHMExtension")
    from .chm_extension import CHMExtension
    debug_log("CHM: CHMExtension imported successfully")
    
    debug_log("CHM: Getting Krita instance")
    krita_instance = Krita.instance()
    debug_log(f"CHM: Krita instance: {krita_instance}")
    
    debug_log("CHM: Creating CHMExtension")
    extension = CHMExtension(krita_instance)
    debug_log(f"CHM: CHMExtension created: {extension}")
    
    # Register the extension with Krita
    debug_log("CHM: Registering extension with Krita")
    krita_instance.addExtension(extension)
    debug_log("CHM: Plugin registered successfully")
    
except Exception as e:
    debug_log(f"CHM: FATAL ERROR during plugin load: {e}")
    import traceback
    error_details = traceback.format_exc()
    debug_log(f"CHM: Traceback:\n{error_details}")

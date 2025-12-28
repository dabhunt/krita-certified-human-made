"""
CHM Extension - Main plugin logic

This class extends Krita's Extension API and manages the lifecycle of CHM sessions.
"""

from krita import Extension
from PyQt5.QtWidgets import QMessageBox
import sys
import os

# Add the lib directory to Python path to import the compiled Rust library
# This will be populated with chm.so (Linux), chm.pyd (Windows), or chm.dylib (macOS)
lib_dir = os.path.join(os.path.dirname(__file__), "lib")
if os.path.exists(lib_dir):
    sys.path.insert(0, lib_dir)

try:
    import chm
    CHM_AVAILABLE = True
except ImportError as e:
    CHM_AVAILABLE = False
    print(f"CHM library not available: {e}")


class CHMExtension(Extension):
    """Main extension class for CHM Verifier plugin"""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.active_sessions = {}  # Map document pointer to CHMSession
        self.DEBUG_LOG = True  # Enable debug logging for MVP
        
    def setup(self):
        """Called when Krita initializes the plugin"""
        if self.DEBUG_LOG:
            print("CHM Verifier: Setup called")
        
        if not CHM_AVAILABLE:
            QMessageBox.warning(
                None,
                "CHM Verifier",
                "CHM Rust library not found. Please install the compiled library."
            )
            return
        
        # Verify library version
        version = chm.get_version()
        if self.DEBUG_LOG:
            print(f"CHM Verifier: Loaded CHM library version {version}")
        
        # Test basic functionality
        test_msg = chm.hello_from_rust()
        if self.DEBUG_LOG:
            print(f"CHM Verifier: {test_msg}")
    
    def createActions(self, window):
        """Create menu actions for the plugin"""
        if self.DEBUG_LOG:
            print("CHM Verifier: Creating actions")
        
        # TODO: Add menu actions in next task
        # - Start/Stop Recording
        # - View Proof
        # - Export with CHM Certification
        pass
    
    def _log(self, message):
        """Debug logging helper"""
        if self.DEBUG_LOG:
            print(f"CHM Verifier: {message}")


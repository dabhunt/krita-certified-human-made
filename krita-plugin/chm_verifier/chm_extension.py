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

from .chm_session_manager import CHMSessionManager
from .event_capture import EventCapture


class CHMExtension(Extension):
    """Main extension class for CHM Verifier plugin"""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.DEBUG_LOG = True  # Enable debug logging for MVP
        self.session_manager = None
        self.event_capture = None
        self.capture_active = False
        
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
        
        # Initialize session manager and event capture
        self.session_manager = CHMSessionManager(debug_log=self.DEBUG_LOG)
        self.event_capture = EventCapture(
            self.session_manager,
            debug_log=self.DEBUG_LOG
        )
        
        # Auto-start event capture
        self.start_capture()
        
        self._log("CHM Verifier initialized successfully")
    
    def createActions(self, window):
        """Create menu actions for the plugin"""
        if self.DEBUG_LOG:
            print("CHM Verifier: Creating actions")
        
        # TODO: Add menu actions in Task 1.8
        # - Start/Stop Recording
        # - View Proof
        # - Export with CHM Certification
        pass
    
    def start_capture(self):
        """Start event capture"""
        if self.capture_active:
            self._log("Event capture already active")
            return
        
        if not self.event_capture:
            self._log("Error: EventCapture not initialized")
            return
        
        try:
            self.event_capture.start_capture()
            self.capture_active = True
            self._log("Event capture started")
        except Exception as e:
            self._log(f"Error starting event capture: {e}")
    
    def stop_capture(self):
        """Stop event capture"""
        if not self.capture_active:
            self._log("Event capture not active")
            return
        
        if not self.event_capture:
            self._log("Error: EventCapture not initialized")
            return
        
        try:
            self.event_capture.stop_capture()
            self.capture_active = False
            self._log("Event capture stopped")
        except Exception as e:
            self._log(f"Error stopping event capture: {e}")
    
    def _log(self, message):
        """Debug logging helper"""
        if self.DEBUG_LOG:
            print(f"CHM Verifier: {message}")


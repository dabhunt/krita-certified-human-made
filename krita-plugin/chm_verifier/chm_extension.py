"""
CHM Extension - Main plugin logic

This class extends Krita's Extension API and manages the lifecycle of CHM sessions.
"""

from krita import Extension, InfoObject
from PyQt5.QtWidgets import QMessageBox
import sys
import os

# Import CHM library (Python implementation)
try:
    from .chm_loader import chm, CHM_IMPLEMENTATION
    CHM_AVAILABLE = True
    print(f"CHM: Loaded CHM library ({CHM_IMPLEMENTATION} implementation)")
except ImportError as e:
    CHM_AVAILABLE = False
    chm = None
    CHM_IMPLEMENTATION = None
    print(f"CHM: Failed to load library: {e}")

from .chm_session_manager import CHMSessionManager
from .event_capture import EventCapture
from .plugin_monitor import PluginMonitor
from .api_client import CHMApiClient
from .timestamp_service import TripleTimestampService
from .path_preferences import PathPreferences
from .session_storage import SessionStorage


class CHMExtension(Extension):
    """Main extension class for CHM plugin"""
    
    def __init__(self, parent):
        self._debug_log("CHMExtension.__init__() called")
        super().__init__(parent)
        self.DEBUG_LOG = True  # Enable debug logging for MVP
        self.session_manager = None
        self.event_capture = None
        self.plugin_monitor = None
        self.capture_active = False
        self._debug_log("CHMExtension.__init__() completed")
        
    def setup(self):
        """Called when Krita initializes the plugin"""
        self._debug_log("=" * 60)
        self._debug_log("CHM: setup() METHOD CALLED - THIS IS THE MAIN ENTRY POINT")
        self._debug_log("=" * 60)
        
        if not CHM_AVAILABLE:
            QMessageBox.warning(
                None,
                "CHM",
                "CHM Rust library not found. Please install the compiled library."
            )
            return
        
        # Verify library version
        version = chm.get_version()
        if self.DEBUG_LOG:
            print(f"CHM: Loaded CHM library version {version}")
        
        # Test basic functionality
        test_msg = chm.hello_from_rust()
        if self.DEBUG_LOG:
            print(f"CHM: {test_msg}")
        
        # Initialize plugin monitor
        self.plugin_monitor = PluginMonitor(debug_log=self.DEBUG_LOG)
        
        # Scan for plugins (Task 1.7)
        self._scan_installed_plugins()
        
        # Initialize session storage (Task 1.15.1)
        self.session_storage = SessionStorage(debug_log=self.DEBUG_LOG)
        
        # Initialize session manager and event capture
        self.session_manager = CHMSessionManager(debug_log=self.DEBUG_LOG)
        self.event_capture = EventCapture(
            self.session_manager,
            debug_log=self.DEBUG_LOG
        )
        
        # Initialize API client (Task 1.12)
        self.api_client = CHMApiClient(debug_log=self.DEBUG_LOG)
        
        # Initialize timestamp service (Task 1.13)
        self.timestamp_service = TripleTimestampService(debug_log=self.DEBUG_LOG)
        
        # Initialize path preferences
        self.path_prefs = PathPreferences()
        self._log(f"Path preferences initialized (default: {self.path_prefs.default_documents_path})")
        
        # Auto-start event capture
        self.start_capture()
        
        self._log("CHM initialized successfully")
    
    def createActions(self, window):
        """Create menu actions for the plugin"""
        if self.DEBUG_LOG:
            print("CHM: Creating actions")
        
        from PyQt5.QtWidgets import QAction
        
        # Main export action (Phase 2A)
        export_action = window.createAction(
            "chm_export_with_proof",
            "CHM: Export with Proof",
            "tools/scripts"
        )
        export_action.triggered.connect(self.export_with_proof)
        self._log("Action created: CHM: Export with Proof")
        
        # View proof action (check current session)
        view_proof_action = window.createAction(
            "chm_view_current_proof",
            "CHM: View Current Session",
            "tools/scripts"
        )
        view_proof_action.triggered.connect(self.view_current_session)
        self._log("Action created: CHM: View Current Session")
        
        # Test action to verify complete flow
        test_action = window.createAction(
            "chm_test_finalize",
            "CHM: Test Finalize & Show Proof",
            "tools/scripts"
        )
        test_action.triggered.connect(self.test_finalize_and_show_proof)
        self._log("Action created: CHM: Test Finalize & Show Proof")
    
    def export_with_proof(self):
        """Export current document with CHM proof (Phase 2A)"""
        self._log("[EXPORT] ========== EXPORT WITH CHM PROOF ==========")
        
        from krita import Krita
        from PyQt5.QtWidgets import QMessageBox, QFileDialog
        
        app = Krita.instance()
        doc = app.activeDocument()
        
        if not doc:
            QMessageBox.warning(
                None,
                "CHM Export",
                "No active document. Please create or open a document first."
            )
            return
        
        self._log(f"[EXPORT] Active document: {doc.name()}")
        
        # Get session
        session = self.session_manager.get_session(doc)
        if not session:
            reply = QMessageBox.question(
                None,
                "CHM Export",
                "No session found for this document.\n\n"
                "This might mean you haven't drawn anything yet, or the document "
                "was created before the plugin loaded.\n\n"
                "Would you like to create an empty session and continue?",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.No:
                return
            
            # Create session on-the-fly
            session = self.session_manager.create_session(doc)
            import platform
            session.set_metadata(
                document_name=doc.name(),
                canvas_width=doc.width(),
                canvas_height=doc.height(),
                krita_version=app.version(),
                os_info=f"{platform.system()} {platform.release()}"
            )
            self._log(f"[EXPORT] Created new session: {session.id}")
        
        self._log(f"[EXPORT] Session found: {session.id}, events: {session.event_count}")
        
        # Get default path from preferences (Documents folder or last used location)
        default_path = self.path_prefs.get_default_export_filename(doc.name())
        self._log(f"[EXPORT] Default save path: {default_path}")
        
        # Show file save dialog
        filename, _ = QFileDialog.getSaveFileName(
            None,
            "Export with CHM Proof",
            default_path,
            "PNG Images (*.png);;JPEG Images (*.jpg *.jpeg)"
        )
        
        if not filename:
            self._log("[EXPORT] User cancelled")
            return
        
        # Remember this directory for next time
        self.path_prefs.save_last_export_directory(filename)
        self._log(f"[EXPORT] Saved directory preference: {os.path.dirname(filename)}")
        
        self._log(f"[EXPORT] Export path: {filename}")
        
        try:
            # Get AI plugins detected (Task 1.7 integration)
            ai_plugins = self.plugin_monitor.get_enabled_ai_plugins() if self.plugin_monitor else []
            if ai_plugins:
                self._log(f"[EXPORT] ⚠️  {len(ai_plugins)} AI plugin(s) are enabled - artwork will be classified as AIAssisted")
            
            # Export image FIRST (so we can compute dual-hash during finalization)
            # Note: exportImage() uses default export settings (no configuration needed)
            self._log(f"[EXPORT] Exporting image to {filename}...")
            success = doc.exportImage(filename, InfoObject())
            
            if not success:
                raise Exception("Krita exportImage() returned False")
            
            self._log(f"[EXPORT] ✓ Image exported successfully")
            
            # Finalize session WITH artwork path (computes file hash for duplicate detection)
            self._log("[EXPORT] Finalizing session with file hash computation...")
            proof = self.session_manager.finalize_session(
                doc, 
                artwork_path=filename,  # ← Pass artwork path for dual-hash
                ai_plugins=ai_plugins
            )
            
            if not proof:
                raise Exception("Session finalization returned None")
            
            self._log(f"[EXPORT] Session finalized, proof generated with file hash")
            
            # Save proof JSON (for web app submission - contains file hash for duplicate detection)
            # The web app will use file_hash from this proof to store in DB
            import json
            proof_filename = filename.replace('.png', '_proof.json').replace('.jpg', '_proof.json').replace('.jpeg', '_proof.json')
            proof_dict = proof.to_dict()
            with open(proof_filename, 'w') as f:
                json.dump(proof_dict, f, indent=2)
            
            self._log(f"[EXPORT] ✓ Proof saved to {proof_filename}")
            
            # Log file hash result
            fhash = proof_dict.get('file_hash', 'N/A')
            fhash_display = fhash[:20] + "..." if fhash and len(fhash) > 20 else fhash
            self._log(f"[EXPORT] ✓ File hash computed:")
            self._log(f"[EXPORT]   • File hash (SHA-256): {fhash_display}")
            
            # Check for duplicate artwork (Task 1.12)
            duplicate = None
            if fhash and fhash != 'N/A' and fhash != 'unavailable_missing_dependencies':
                duplicate = self.api_client.check_duplicate(fhash)
                if duplicate:
                    self._log(f"[EXPORT] ⚠️  Duplicate artwork detected!")
                    self._log(f"[EXPORT]   Existing session: {duplicate.get('session_id')}")
                    self._log(f"[EXPORT]   Classification: {duplicate.get('classification')}")
                    
                    reply = QMessageBox.question(
                        None,
                        "Duplicate Artwork Detected",
                        f"⚠️  This artwork already has a CHM proof!\n\n"
                        f"Existing proof:\n"
                        f"• Session ID: {duplicate.get('session_id', 'unknown')}\n"
                        f"• Classification: {duplicate.get('classification', 'unknown')}\n"
                        f"• Submitted: {duplicate.get('submitted_at', 'unknown')}\n\n"
                        f"Would you like to submit a new proof anyway?\n"
                        f"(This might indicate duplicate submission or artwork modification)",
                        QMessageBox.Yes | QMessageBox.No
                    )
                    
                    if reply == QMessageBox.No:
                        self._log("[EXPORT] User cancelled due to duplicate")
                        return
            
            # Submit proof hash to triple timestamp services (Task 1.13)
            import hashlib
            proof_hash = hashlib.sha256(json.dumps(proof_dict, sort_keys=True).encode()).hexdigest()
            timestamp_results = None
            timestamp_status = "Not timestamped"
            
            try:
                self._log(f"[EXPORT] Submitting proof hash to timestamp services...")
                self._log(f"[EXPORT] Proof hash: {proof_hash[:32]}...")
                
                timestamp_results = self.timestamp_service.submit_proof_hash(proof_hash, proof_dict)
                
                success_count = timestamp_results['success_count']
                self._log(f"[EXPORT] ✓ Timestamps: {success_count}/2 services succeeded")
                
                # Add timestamps to proof dict
                proof_dict['timestamps'] = {
                    'proof_hash': proof_hash,
                    'github': timestamp_results.get('github'),
                    'wayback': timestamp_results.get('wayback'),
                    'chm_log': timestamp_results.get('chm_log'),
                    'success_count': success_count
                }
                
                # Re-save proof JSON with timestamps
                with open(proof_filename, 'w') as f:
                    json.dump(proof_dict, f, indent=2)
                
                self._log(f"[EXPORT] ✓ Proof updated with timestamps")
                
                if success_count > 0:
                    timestamp_status = f"✓ Timestamped ({success_count}/2 services)"
                    if timestamp_results.get('github'):
                        self._log(f"[EXPORT]   • GitHub Gist: {timestamp_results['github']['url']}")
                    if timestamp_results.get('chm_log'):
                        self._log(f"[EXPORT]   • CHM Log: index {timestamp_results['chm_log']['log_index']}")
                else:
                    timestamp_status = "⚠️  All timestamp services failed"
                    
            except Exception as e:
                self._log(f"[EXPORT] ⚠️  Timestamp submission failed (non-fatal): {e}")
                timestamp_status = f"⚠️  Timestamp failed: {e}"
                # Non-fatal - proof still valid without timestamps
            
            # Submit proof to API/database (Task 1.12)
            submission_status = "Not submitted"
            try:
                self._log("[EXPORT] Submitting proof to CHM database...")
                submit_result = self.api_client.submit_proof(proof_dict)
                
                if submit_result['status'] == 'success':
                    self._log(f"[EXPORT] ✓ Proof submitted: {submit_result['proof_id']}")
                    submission_status = f"✓ Submitted ({submit_result.get('message', 'success')})"
                else:
                    self._log(f"[EXPORT] ⚠️  Submission warning: {submit_result['message']}")
                    submission_status = f"⚠️  {submit_result['message']}"
                    
            except Exception as e:
                self._log(f"[EXPORT] ⚠️  Proof submission failed (non-fatal): {e}")
                submission_status = f"⚠️  Submission failed: {e}"
                # Non-fatal - proof still saved locally
            
            # Show success message with timestamp URLs
            message = (
                f"✅ Image exported with CHM proof!\n\n"
                f"Image: {filename}\n"
                f"Proof: {proof_filename}\n\n"
                f"Classification: {proof.to_dict().get('classification', 'Unknown')}\n"
                f"Strokes: {proof.to_dict().get('event_summary', {}).get('stroke_count', 0)}\n"
                f"Duration: {proof.to_dict().get('event_summary', {}).get('session_duration_secs', 0)}s\n\n"
                f"Timestamps: {timestamp_status}\n"
                f"Database: {submission_status}"
            )
            
            # Add clickable GitHub URL if available
            if timestamp_results and timestamp_results.get('github'):
                message += f"\n\nGitHub Gist:\n{timestamp_results['github']['url']}"
            
            QMessageBox.information(
                None,
                "CHM Export Successful",
                message
            )
            
            self._log("[EXPORT] ========== EXPORT COMPLETE ==========")
            
        except Exception as e:
            import traceback
            self._log(f"[EXPORT] ❌ ERROR: {e}")
            self._log(f"[EXPORT] Traceback: {traceback.format_exc()}")
            
            QMessageBox.critical(
                None,
                "CHM Export Error",
                f"Error during export:\n\n{e}\n\nSee debug log for details."
            )
    
    def view_current_session(self):
        """View current session without finalizing"""
        self._log("[VIEW] ========== VIEW CURRENT SESSION ==========")
        
        from krita import Krita
        from PyQt5.QtWidgets import QMessageBox
        
        app = Krita.instance()
        doc = app.activeDocument()
        
        if not doc:
            QMessageBox.warning(
                None,
                "CHM View Session",
                "No active document."
            )
            return
        
        session = self.session_manager.get_session(doc)
        if not session:
            QMessageBox.information(
                None,
                "CHM View Session",
                f"No active session for document '{doc.name()}'.\n\n"
                f"The session may not have been created yet. Try drawing something first."
            )
            return
        
        # Show session info without finalizing
        QMessageBox.information(
            None,
            "CHM Current Session",
            f"Session ID: {session.id}\n\n"
            f"Events recorded: {session.event_count}\n"
            f"Document: {doc.name()}\n"
            f"Size: {doc.width()}x{doc.height()}\n\n"
            f"(Session is still active - not finalized)"
        )
        
        self._log(f"[VIEW] Session info displayed: {session.id}, {session.event_count} events")
    
    def test_finalize_and_show_proof(self):
        """Test action to finalize current session and show proof dialog"""
        self._log("[TEST] ========== TEST FINALIZE & SHOW PROOF ==========")
        
        from krita import Krita
        app = Krita.instance()
        doc = app.activeDocument()
        
        if not doc:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(
                None,
                "CHM Test",
                "No active document. Please create a document and draw some strokes first."
            )
            return
        
        self._log(f"[TEST] Active document: {doc.name()}")
        
        # Get session
        session = self.session_manager.get_session(doc)
        if not session:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(
                None,
                "CHM Test",
                "No session found for this document. The session may not have been created."
            )
            return
        
        self._log(f"[TEST] Session found: {session.id}, events: {session.event_count}")
        
        # Finalize session (this triggers FLOW-3)
        try:
            # Include AI plugins in finalization
            ai_plugins = self.plugin_monitor.get_enabled_ai_plugins() if self.plugin_monitor else []
            proof = self.session_manager.finalize_session(doc, ai_plugins=ai_plugins)
            
            if not proof:
                from PyQt5.QtWidgets import QMessageBox
                QMessageBox.warning(
                    None,
                    "CHM Test",
                    "Failed to finalize session (returned None)."
                )
                return
            
            self._log(f"[TEST] Proof finalized successfully")
            
            # Show verification dialog (this triggers FLOW-5)
            from .verification_dialog import VerificationDialog
            
            dialog = VerificationDialog(proof_data=proof)
            dialog.exec_()
            
            self._log("[TEST] ========== TEST COMPLETE ==========")
            
        except Exception as e:
            import traceback
            self._log(f"[TEST] ERROR: {e}")
            self._log(f"[TEST] Traceback: {traceback.format_exc()}")
            
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.critical(
                None,
                "CHM Test Error",
                f"Error during test: {e}\n\nSee debug log for details."
            )
    
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
    
    def _scan_installed_plugins(self):
        """Scan for installed plugins and detect AI plugins (Task 1.7)"""
        self._log("Scanning for installed plugins...")
        
        # Determine plugin directories based on platform
        plugin_directories = self._get_plugin_directories()
        
        if not plugin_directories:
            self._log("Warning: Could not find plugin directories")
            return
        
        # Scan directories
        plugins = self.plugin_monitor.scan_plugins(plugin_directories)
        
        # Log AI plugins detected
        ai_plugins = self.plugin_monitor.get_ai_plugins()
        if ai_plugins:
            self._log(f"⚠️  WARNING: {len(ai_plugins)} AI plugin(s) detected:")
            for plugin in ai_plugins:
                ai_type = plugin.get('ai_type', 'UNKNOWN')
                enabled = "ENABLED" if plugin.get('enabled', False) else "disabled"
                self._log(f"  - {plugin['display_name']} ({plugin['name']}) - {ai_type} - {enabled}")
            self._log("  → Artworks will be classified as 'AIAssisted' if created with these plugins active")
        else:
            self._log("✓ No AI plugins detected")
    
    def _get_plugin_directories(self):
        """Get platform-specific plugin directories"""
        import platform
        import os
        
        directories = []
        
        system = platform.system()
        if system == 'Darwin':  # macOS
            directories.append(os.path.expanduser("~/Library/Application Support/krita/pykrita"))
        elif system == 'Linux':
            directories.append(os.path.expanduser("~/.local/share/krita/pykrita"))
        elif system == 'Windows':
            appdata = os.environ.get('APPDATA', '')
            if appdata:
                directories.append(os.path.join(appdata, 'krita', 'pykrita'))
        
        self._log(f"Plugin directories for {system}: {directories}")
        return directories
    
    def _log(self, message):
        """Debug logging helper"""
        if self.DEBUG_LOG:
            self._debug_log(message)
    
    def _debug_log(self, message):
        """Write to both console and debug file"""
        import sys
        full_message = f"CHM: {message}"
        print(full_message)
        sys.stdout.flush()
        
        # Also write to debug file
        try:
            import os
            from datetime import datetime
            log_dir = os.path.expanduser("~/.local/share/chm")
            os.makedirs(log_dir, exist_ok=True)
            log_file = os.path.join(log_dir, "plugin_debug.log")
            
            with open(log_file, "a") as f:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                f.write(f"[{timestamp}] {full_message}\n")
                f.flush()
        except Exception as e:
            print(f"CHM: Could not write to log file: {e}")


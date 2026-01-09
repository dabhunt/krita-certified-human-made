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
from .chm_docker import CHMDockerWidget

# Import safe_flush utility for Windows compatibility
try:
    from .logging_util import safe_flush
except ImportError:
    # Fallback if logging_util not available
    def safe_flush():
        if sys.stdout is not None:
            try:
                safe_flush()
            except (AttributeError, ValueError):
                pass


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
        self.api_client = None  # CHM API client (server-side signing)
        self.docker_widget = None  # Docker panel reference
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
        if self.DEBUG_LOG:
            print(f"[CHM-INIT] SessionStorage initialized: {self.session_storage}")
        
        # Initialize session manager and event capture
        self.session_manager = CHMSessionManager(debug_log=self.DEBUG_LOG)
        self.event_capture = EventCapture(
            self.session_manager,
            session_storage=self.session_storage,  # CRITICAL: Pass session_storage for persistence!
            plugin_monitor=self.plugin_monitor,  # CRITICAL: Pass plugin_monitor for AI classification!
            debug_log=self.DEBUG_LOG
        )
        if self.DEBUG_LOG:
            print(f"[CHM-INIT] EventCapture initialized with session_storage: {self.event_capture.session_storage}")
        
        # Initialize API client for server-side signing + timestamp (Task 1.12)
        from . import config as chm_config
        api_config = {
            'api_url': chm_config.API_URL,
            'timeout': chm_config.API_TIMEOUT
        }
        self.api_client = CHMApiClient(config=api_config, debug_log=self.DEBUG_LOG)
        
        # Set global API client in chm_core (for server-side ED25519 signing)
        from . import chm_core
        chm_core.set_api_client(self.api_client)
        self._debug_log(f"[API-CLIENT] ✓ Environment: {chm_config.get_environment()}")
        self._debug_log(f"[API-CLIENT] ✓ API URL: {chm_config.API_URL}")
        
        # Initialize local CHM timestamp log (Task 1.13)
        # NOTE: GitHub timestamping now handled by server API (combined with signing)
        # This is just for local append-only log (offline fallback)
        timestamp_config = {
            'enable_chm_log': True  # Keep local log for offline backup
        }
        # Pass our logger function so timestamp service logs appear in debug file
        self.timestamp_service = TripleTimestampService(
            config=timestamp_config, 
            debug_log=self.DEBUG_LOG,
            logger_func=self._debug_log  # Pass our logging function
        )
        self._log("[TIMESTAMP] ✓ Local CHM log initialized (GitHub handled by server API)")
        
        # Initialize path preferences
        self.path_prefs = PathPreferences()
        self._log(f"Path preferences initialized (default: {self.path_prefs.default_documents_path})")
        
        # Initialize C2PA builder (Phase 3: C2PA Integration)
        self._log("[CHM-INIT] Initializing C2PA builder...")
        try:
            self._log("[CHM-INIT] Importing CHMtoC2PABuilder...")
            from .c2pa_builder import CHMtoC2PABuilder
            self._log("[CHM-INIT] Import successful, creating instance...")
            self.c2pa_builder = CHMtoC2PABuilder(debug_log=self.DEBUG_LOG)
            self.c2pa_enabled = True  # Can be toggled via settings
            self._log(f"[CHM-INIT] ✅ C2PA builder initialized (enabled: {self.c2pa_enabled})")
        except Exception as e:
            self._log(f"[CHM-INIT] ❌ C2PA builder not available: {e}")
            self._log(f"[CHM-INIT] Exception type: {type(e).__name__}")
            import traceback
            self._log(f"[CHM-INIT] Full traceback:\n{traceback.format_exc()}")
            self.c2pa_builder = None
            self.c2pa_enabled = False
            self._log("[CHM-INIT] C2PA disabled - plugin will continue without C2PA embedding")
        
        # Auto-start event capture
        self.start_capture()
        
        # Register Docker window
        self._register_docker()
        
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
        
        # Check if document is saved
        filepath = doc.fileName()
        if not filepath:
            self._log("[EXPORT] Document is not saved yet")
            QMessageBox.information(
                None,
                "CHM Export",
                "You must save your document before exporting with proof.\n\n"
                "Please save your document first (File → Save), then try exporting again."
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
            
            # Get AI plugins for classification
            ai_plugins_enabled = self.plugin_monitor.get_enabled_ai_plugins() if self.plugin_monitor else []
            ai_plugins_all = self.plugin_monitor.get_ai_plugins() if self.plugin_monitor else []
            
            # Create session on-the-fly WITH AI plugin detection
            session = self.session_manager.create_session(
                doc,
                ai_plugins=ai_plugins_enabled,
                ai_plugins_detected=len(ai_plugins_all) > 0
            )
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
            ai_plugins_enabled = self.plugin_monitor.get_enabled_ai_plugins() if self.plugin_monitor else []
            ai_plugins_all = self.plugin_monitor.get_ai_plugins() if self.plugin_monitor else []
            
            if ai_plugins_enabled:
                self._log(f"[EXPORT] ⚠️  {len(ai_plugins_enabled)} AI plugin(s) are enabled - artwork will be classified as AIAssisted")
            elif ai_plugins_all:
                self._log(f"[EXPORT] ℹ️  {len(ai_plugins_all)} AI plugin(s) detected but disabled")
            
            # Export image FIRST (so we can compute dual-hash during finalization)
            # Note: exportImage() uses default export settings (no configuration needed)
            self._log(f"[EXPORT] Exporting image to {filename}...")
            success = doc.exportImage(filename, InfoObject())
            
            if not success:
                raise Exception("Krita exportImage() returned False")
            
            self._log(f"[EXPORT] ✓ Image exported successfully")
            
            # Generate proof from session snapshot (keeps original session alive)
            # NOTE: This now includes server-side signing + GitHub timestamp!
            self._log("[EXPORT] Generating proof from session snapshot...")
            self._log("[EXPORT] → Server will sign with ED25519 and create GitHub timestamp")
            
            try:
                proof = self.session_manager.finalize_session(
                    doc, 
                    artwork_path=filename,  # ← Pass artwork path for file hash
                    ai_plugins=ai_plugins_enabled,
                    ai_plugins_detected=len(ai_plugins_all) > 0,  # ← Track if any AI plugins exist (enabled or not)
                    for_export=True,  # ← Create snapshot, don't destroy active session
                    import_tracker=self.event_capture.import_tracker  # ← Pass import tracker for MixedMedia check
                )
            except RuntimeError as e:
                # Server signing failed (no internet or server error)
                self._log(f"[EXPORT] ❌ Server signing failed: {e}")
                QMessageBox.critical(
                    None,
                    "CHM Export Error - Network Required",
                    f"Failed to sign proof with CHM server:\n\n{e}\n\n"
                    "Proof creation requires an internet connection to communicate "
                    "with api.certified-human-made.org for cryptographic signing.\n\n"
                    "Please check your internet connection and try again."
                )
                return
            
            if not proof:
                raise Exception("Session finalization returned None")
            
            self._log(f"[EXPORT] ✅ Session finalized (signed by server + GitHub timestamp created)")
            
            # Save proof JSON (for web app submission - contains file hash for duplicate detection)
            # The web app will use file_hash from this proof to store in DB
            import json
            proof_filename = filename.replace('.png', '_proof.json').replace('.jpg', '_proof.json').replace('.jpeg', '_proof.json')
            proof_dict = proof.to_dict()
            
            # TAMPER RESISTANCE: Verify ED25519 signature before saving (self-check)
            from . import chm_core
            if "signature" in proof_dict:
                self._log("[EXPORT] 🔐 Verifying ED25519 signature (self-check)...")
                is_valid = chm_core._verify_session_signature(proof_dict)
                if is_valid:
                    self._log("[EXPORT] ✅ ED25519 signature verification passed")
                else:
                    self._log("[EXPORT] ❌ CRITICAL: Signature verification FAILED!")
                    QMessageBox.critical(
                        None,
                        "CHM Export Error",
                        "Proof signature verification failed!\n\n"
                        "The server-signed proof is invalid.\n\n"
                        "Please report this bug."
                    )
                    return
            else:
                self._log("[EXPORT] ❌ CRITICAL: Proof has no signature!")
                QMessageBox.critical(
                    None,
                    "CHM Export Error",
                    "Proof was not signed by server!\n\n"
                    "This should never happen.\n\n"
                    "Please report this bug."
                )
                return
            
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
            
            # Add local CHM log timestamp (backup/offline fallback)
            # NOTE: GitHub timestamp already created by server during signing!
            import hashlib
            proof_hash = hashlib.sha256(json.dumps(proof_dict, sort_keys=True).encode()).hexdigest()
            
            # BUG FIX: Store file_hash for metadata, NOT proof_hash
            # proof_hash = hash of proof JSON (used for timestamping)
            # file_hash = hash of PNG file (used for verification)
            file_hash_for_metadata = proof_dict.get('file_hash', '')
            
            # Initialize variables for timestamp status
            timestamp_status = "Not timestamped"
            gist_url_for_metadata = None
            github_timestamp = None
            
            # Check if GitHub timestamp already exists from server
            if proof_dict.get('timestamps', {}).get('github'):
                github_timestamp = proof_dict['timestamps']['github']
                gist_url_for_metadata = github_timestamp.get('url')
                self._log(f"[EXPORT] ✓ GitHub timestamp (from server): {gist_url_for_metadata}")
            
            # Add local CHM log timestamp (append-only file backup)
            try:
                self._log(f"[EXPORT] Adding local CHM log timestamp...")
                self._log(f"[EXPORT] Proof hash: {proof_hash[:32]}...")
                
                # Submit to local CHM log only (GitHub already done)
                timestamp_results = self.timestamp_service.submit_proof_hash(proof_hash, proof_dict)
                
                # Add CHM log to timestamps section (GitHub already there from server)
                if 'timestamps' not in proof_dict:
                    proof_dict['timestamps'] = {}
                
                proof_dict['timestamps']['proof_hash'] = proof_hash
                proof_dict['timestamps']['chm_log'] = timestamp_results.get('chm_log')
                
                # Count successes
                success_count = 0
                if github_timestamp:
                    success_count += 1
                if timestamp_results.get('chm_log'):
                    success_count += 1
                
                proof_dict['timestamps']['success_count'] = success_count
                
                # Re-save proof JSON with local CHM log added
                with open(proof_filename, 'w') as f:
                    json.dump(proof_dict, f, indent=2)
                
                self._log(f"[EXPORT] ✓ Proof updated with local CHM log timestamp")
                
                # Build timestamp status message
                services = []
                if github_timestamp:
                    services.append("GitHub Gist (server)")
                if timestamp_results.get('chm_log'):
                    services.append("CHM Log (local)")
                    self._log(f"[EXPORT]   • CHM Log: index {timestamp_results['chm_log']['log_index']}")
                
                if success_count > 0:
                    timestamp_status = f"✓ Timestamped ({success_count}/2 services: {', '.join(services)})"
                else:
                    timestamp_status = "⚠️  All timestamp services failed"
                    
            except Exception as e:
                # BUG #013: Enhanced logging to diagnose timestamp failures
                import traceback
                self._log(f"[EXPORT] ⚠️  CHM log timestamp failed (non-fatal): {e}")
                self._log(f"[EXPORT] Exception type: {type(e).__name__}")
                self._log(f"[EXPORT] Exception details: {str(e)}")
                self._log(f"[EXPORT] Traceback:\n{traceback.format_exc()}")
                
                # Still show GitHub timestamp if we have it from server
                if github_timestamp:
                    timestamp_status = "✓ Timestamped (1/2 services: GitHub Gist - CHM log failed)"
                else:
                    timestamp_status = f"⚠️  Timestamp failed: {e}"
            
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
            
            # Embed C2PA manifest if enabled (Phase 3: C2PA Integration)
            c2pa_status = "Not embedded (disabled)"
            
            # BFROS: Detailed diagnostic logging
            self._log(f"[C2PA-DEBUG-1] c2pa_enabled={getattr(self, 'c2pa_enabled', 'ATTR_MISSING')}")
            self._log(f"[C2PA-DEBUG-2] c2pa_builder={getattr(self, 'c2pa_builder', 'ATTR_MISSING')}")
            
            if self.c2pa_enabled and self.c2pa_builder:
                try:
                    self._log("[EXPORT] Embedding C2PA Content Credentials...")
                    self._log(f"[C2PA-DEBUG-3] Starting manifest generation...")
                    self._log(f"[C2PA-DEBUG-4] proof_dict keys: {list(proof_dict.keys())}")
                    self._log(f"[C2PA-DEBUG-5] proof_dict size: {len(json.dumps(proof_dict))} bytes")
                    
                    # Generate C2PA manifest from proof
                    # Use ED25519 test certificates (self-signed for MVP)
                    cert_path = os.path.join(os.path.dirname(__file__), 'certs', 'chm_ed25519_cert.pem')
                    key_path = os.path.join(os.path.dirname(__file__), 'certs', 'chm_ed25519_key.pem')
                    
                    # Check if test certs exist
                    if not os.path.exists(cert_path) or not os.path.exists(key_path):
                        self._log(f"[C2PA] ⚠️ Test certificates not found:")
                        self._log(f"[C2PA]    Cert: {cert_path}")
                        self._log(f"[C2PA]    Key: {key_path}")
                        self._log("[C2PA] → Manifest will be unsigned")
                        cert_path = None
                        key_path = None
                    else:
                        self._log(f"[C2PA] ✅ Using test certificates for signing")
                    
                    manifest = self.c2pa_builder.generate_manifest(
                        session_proof_json=json.dumps(proof_dict),
                        cert_path=cert_path,
                        key_path=key_path,
                        privacy_mode="lite"  # Aggregate data only (privacy-preserving)
                    )
                    
                    self._log(f"[C2PA-DEBUG-6] Manifest generation result: {type(manifest)}")
                    self._log(f"[C2PA-DEBUG-7] Manifest is None: {manifest is None}")
                    
                    if manifest:
                        self._log(f"[C2PA-DEBUG-8] Manifest keys: {list(manifest.keys()) if isinstance(manifest, dict) else 'NOT_A_DICT'}")
                        self._log(f"[C2PA-DEBUG-9] Manifest size: {len(json.dumps(manifest))} bytes")
                        self._log(f"[C2PA-DEBUG-10] Target file: {filename}")
                        self._log(f"[C2PA-DEBUG-11] File exists: {os.path.exists(filename)}")
                        
                        # Embed manifest in exported image
                        self._log(f"[C2PA-DEBUG-12] Calling embed_in_image...")
                        success = self.c2pa_builder.embed_in_image(filename, manifest)
                        
                        self._log(f"[C2PA-DEBUG-13] Embedding result: {success}")
                        
                        if success:
                            self._log("[EXPORT] ✅ C2PA manifest embedded successfully")
                            # Check if manifest was signed
                            if 'c2pa_signature' in manifest:
                                sig_status = manifest['c2pa_signature'].get('status', 'unknown')
                                if sig_status == 'unsigned':
                                    c2pa_status = "✓ C2PA embedded (unsigned)"
                                elif sig_status == 'signing_failed':
                                    c2pa_status = "✓ C2PA embedded (signing failed)"
                                elif 'algorithm' in manifest['c2pa_signature']:
                                    # Successfully signed
                                    algo = manifest['c2pa_signature'].get('algorithm', 'unknown')
                                    c2pa_status = f"✓ C2PA embedded (signed: {algo})"
                                else:
                                    c2pa_status = "✓ C2PA embedded (unsigned)"
                            else:
                                c2pa_status = "✓ C2PA embedded (unsigned)"
                        else:
                            self._log("[EXPORT] ⚠️  C2PA embedding failed (returned False)")
                            c2pa_status = "⚠️  C2PA embedding failed"
                    else:
                        self._log("[EXPORT] ⚠️  C2PA manifest generation failed (returned None)")
                        c2pa_status = "⚠️  C2PA generation failed"
                        
                except Exception as e:
                    self._log(f"[EXPORT] ❌ C2PA error (non-fatal): {e}")
                    self._log(f"[C2PA-DEBUG-ERROR] Exception type: {type(e).__name__}")
                    import traceback
                    self._log(f"[C2PA-DEBUG-ERROR] Traceback:\n{traceback.format_exc()}")
                    c2pa_status = f"⚠️  C2PA error: {str(e)[:50]}"
                    # Non-fatal - proof still valid without C2PA
            else:
                self._log(f"[C2PA-DEBUG-SKIP] C2PA skipped - enabled={getattr(self, 'c2pa_enabled', False)}, builder={self.c2pa_builder is not None}")
            
            # Prepare export data for confirmation dialog
            export_data = {
                "image_path": filename,
                "proof_path": proof_filename,
                "proof_data": proof.to_dict(),
                "timestamp_status": timestamp_status,
                "database_status": submission_status,
                "c2pa_status": c2pa_status,
                "timestamp_url": gist_url_for_metadata,  # GitHub URL from server
                "timestamp_errors": []  # No longer needed (server handles GitHub)
            }
            
            # ===== PNG METADATA EMBEDDING (Pure Python - ROAA Option 1) =====
            # CRITICAL: Must happen AFTER C2PA embedding!
            # C2PA rewrites the PNG file, so metadata must be added last
            # Uses pure Python implementation (no PIL required - stdlib only!)
            if filename.lower().endswith('.png') and gist_url_for_metadata:
                try:
                    from .png_metadata_pure import add_chm_metadata
                    
                    self._log(f"[EXPORT] Embedding CHM metadata in PNG (AFTER C2PA)...")
                    self._log(f"[EXPORT]   • Using pure Python embedder (stdlib only, no PIL)")
                    self._log(f"[EXPORT]   • Gist URL: {gist_url_for_metadata}")
                    
                    metadata_success = add_chm_metadata(
                        png_path=filename,
                        gist_url=gist_url_for_metadata,
                        proof_hash=file_hash_for_metadata,  # BUG FIX: Use file_hash, not proof_hash
                        classification=proof_dict.get('classification', 'unknown'),
                        session_id=proof_dict.get('session_id')
                    )
                    
                    if metadata_success:
                        self._log(f"[EXPORT] ✓ CHM metadata embedded successfully!")
                        self._log(f"[EXPORT]   ✓ Verification will be immediate (no GitHub search delay)")
                    else:
                        self._log(f"[EXPORT] ⚠️ Metadata embedding returned False (non-fatal)")
                        self._log(f"[EXPORT]   Check png_metadata_pure.py logs for details")
                        self._log(f"[EXPORT]   Verification will still work via file hash search")
                        
                except Exception as e:
                    self._log(f"[EXPORT] ⚠️ Metadata embedding exception (non-fatal): {e}")
                    import traceback
                    self._log(f"[EXPORT] Exception traceback: {traceback.format_exc()}")
                    # Non-fatal - proof still works, just slower verification
            
            # GitHub URL already set in export_data from gist_url_for_metadata (from server response)
            if gist_url_for_metadata:
                self._log(f"[EXPORT] 🔗 Public timestamp proof: {gist_url_for_metadata}")
            
            # Show structured confirmation dialog
            from .export_confirmation_dialog import ExportConfirmationDialog
            dialog = ExportConfirmationDialog(export_data=export_data)
            dialog.exec_()
            
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
        from .session_info_dialog import SessionInfoDialog
        import platform
        
        app = Krita.instance()
        doc = app.activeDocument()
        
        if not doc:
            QMessageBox.warning(
                None,
                "CHM View Session",
                "No active document."
            )
            return
        
        # Check if document is saved
        filepath = doc.fileName()
        if not filepath:
            self._log("[VIEW] Document is not saved yet")
            QMessageBox.information(
                None,
                "CHM View Session",
                "You must save your document to preview the current session stats."
            )
            return
        
        # Get or create session (proactive creation for unsaved documents)
        session = self.session_manager.get_session(doc)
        if not session:
            self._log(f"[VIEW] No session found for document '{doc.name()}', creating new session...")
            
            # Get AI plugins for classification
            ai_plugins_enabled = self.plugin_monitor.get_enabled_ai_plugins() if self.plugin_monitor else []
            ai_plugins_all = self.plugin_monitor.get_ai_plugins() if self.plugin_monitor else []
            
            self._log(f"[VIEW-BFROS] Creating session with AI plugin detection:")
            self._log(f"[VIEW-BFROS]   - Enabled AI plugins: {len(ai_plugins_enabled)}")
            self._log(f"[VIEW-BFROS]   - Total AI plugins: {len(ai_plugins_all)}")
            
            # Create session proactively WITH AI plugin information
            session = self.session_manager.create_session(
                doc,
                ai_plugins=ai_plugins_enabled,
                ai_plugins_detected=len(ai_plugins_all) > 0
            )
            
            # Set metadata
            try:
                session.set_metadata(
                    document_name=doc.name(),
                    canvas_width=doc.width(),
                    canvas_height=doc.height(),
                    krita_version=app.version(),
                    os_info=f"{platform.system()} {platform.release()}"
                )
                self._log(f"[VIEW] ✓ Session created proactively: {session.id}")
            except Exception as e:
                self._log(f"[VIEW] ⚠️ Error setting metadata: {e}")
            
            # Log the document key for debugging
            doc_key = self.session_manager._get_document_key(doc)
            self._log(f"[VIEW] Document key: {doc_key[:32]}...")
        else:
            self._log(f"[VIEW] ✓ Found existing session: {session.id} ({session.event_count} events)")
        
        # Get comprehensive session info (without finalizing)
        # BUG#005 FIX: Use doc_key (session key) instead of doc_id
        doc_key = self.event_capture._get_doc_key(doc)
        
        # DEBUG: Log raw session data
        self._log(f"[VIEW-DEBUG] Session has {len(session.events)} events in events list")
        self._log(f"[VIEW-DEBUG] Session.event_count: {session.event_count}")
        
        # Count events by type
        stroke_count = sum(1 for e in session.events if e.get("type") == "stroke")
        import_count = sum(1 for e in session.events if e.get("type") == "import")
        # Only count undo operations (not redo) - stronger indicator of human creative process
        undo_count = sum(1 for e in session.events if e.get("type") == "undo_redo" and e.get("action") == "undo")
        
        # Count ACTUAL layers in document (not just events)
        layer_count = 0
        try:
            def count_all_layers(node):
                """Recursively count all layers"""
                count = 1  # Count this node
                for child in node.childNodes():
                    count += count_all_layers(child)
                return count
            
            for top_node in doc.topLevelNodes():
                layer_count += count_all_layers(top_node)
        except Exception as e:
            self._log(f"[VIEW-DEBUG] Error counting layers: {e}")
            # Fallback to event count if layer counting fails
            layer_count = sum(1 for e in session.events if e.get("type") in ["layer_created", "layer_added"])
        
        self._log(f"[VIEW-DEBUG] Counted: strokes={stroke_count}, layers={layer_count}, imports={import_count}, undos={undo_count}")
        
        # BFROS: Log metadata BEFORE classification
        metadata = session.get_metadata()
        self._log(f"[VIEW-BFROS] Metadata BEFORE _classify():")
        self._log(f"[VIEW-BFROS]   ai_tools_used: {metadata.get('ai_tools_used', False)}")
        self._log(f"[VIEW-BFROS]   ai_tools_list: {metadata.get('ai_tools_list', [])}")
        self._log(f"[VIEW-BFROS]   ai_plugins_detected: {metadata.get('ai_plugins_detected', False)}")
        
        # Get current classification (preview - not finalized)
        self._log(f"[VIEW-BFROS] Calling session._classify()...")
        classification = session._classify(
            doc=doc,
            doc_key=doc_key,
            import_tracker=self.event_capture.import_tracker
        )
        self._log(f"[VIEW-BFROS] Classification result: {classification}")
        
        # Get AI tools info
        ai_tools_used = session.metadata.get("ai_tools_used", False)
        ai_tools_list = session.metadata.get("ai_tools_list", [])
        
        self._log(f"[VIEW-BFROS] Final session data:")
        self._log(f"[VIEW-BFROS]   classification: {classification}")
        self._log(f"[VIEW-BFROS]   ai_tools_used: {ai_tools_used}")
        self._log(f"[VIEW-BFROS]   ai_tools_list: {ai_tools_list}")
        
        # Check if document has Mixed Media (any imports registered - sticky)
        imports_visible = None
        if import_count > 0:
            imports_visible = self.event_capture.import_tracker.has_mixed_media(doc_key)
        
        # Get time metrics
        session_duration = session.duration_secs if hasattr(session, 'duration_secs') else 0
        drawing_time = session.drawing_time_secs if hasattr(session, 'drawing_time_secs') else 0
        
        self._log(f"[VIEW-DEBUG] Time: duration={session_duration}s, drawing_time={drawing_time}s")
        self._log(f"[VIEW-DEBUG] Raw _drawing_time_secs: {session._drawing_time_secs if hasattr(session, '_drawing_time_secs') else 'N/A'}")
        
        # Build session data for dialog
        session_data = {
            "session_id": session.id,
            "document_name": doc.name(),
            "canvas_width": doc.width(),
            "canvas_height": doc.height(),
            "session_duration": session_duration,
            "drawing_time": drawing_time,
            "total_events": session.event_count,
            "stroke_count": stroke_count,
            "layer_count": layer_count,
            "import_count": import_count,
            "undo_count": undo_count,
            "classification": classification,
            "ai_tools_used": ai_tools_used,
            "ai_tools_list": ai_tools_list,
            "imports_visible": imports_visible
        }
        
        # Show in structured dialog
        dialog = SessionInfoDialog(session_data=session_data)
        dialog.exec_()
        
        self._log(f"[VIEW] Session info displayed: {session.id}, classification: {classification}, imports: {import_count}")
    
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
    
    # DEPRECATED: Signing now done server-side with ED25519
    # def _load_signing_key_DEPRECATED(self): ...
    # def _load_github_token_DEPRECATED(self): ...
    # def _validate_github_token_DEPRECATED(self): ...
    
    def _register_docker(self):
        """Register the CHM Docker window"""
        try:
            from krita import Krita, DockWidgetFactory, DockWidgetFactoryBase
            
            self._log("[DOCKER] Registering CHM Docker window...")
            
            # Create factory function that returns configured Docker instances
            def create_docker():
                docker = CHMDockerWidget()
                docker.set_extension(self)
                return docker
            
            # Register with Krita
            app = Krita.instance()
            factory = DockWidgetFactory(
                "chm_docker",  # Unique ID
                DockWidgetFactoryBase.DockRight,  # Default position (right side)
                create_docker  # Factory function
            )
            
            app.addDockWidgetFactory(factory)
            self._log("[DOCKER] ✅ Docker window registered successfully")
            
        except Exception as e:
            self._log(f"[DOCKER] ⚠️ Failed to register Docker: {e}")
            import traceback
            self._log(f"[DOCKER] Traceback:\n{traceback.format_exc()}")
            # Non-fatal - plugin continues without Docker
    
    def _log(self, message):
        """Debug logging helper"""
        if self.DEBUG_LOG:
            self._debug_log(message)
    
    def _debug_log(self, message):
        """Write to both console and debug file"""
        import sys
        full_message = f"CHM: {message}"
        print(full_message)
        safe_flush()
        
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


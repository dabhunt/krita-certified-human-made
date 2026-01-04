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
        self.signing_key = None  # Secret key for HMAC signing (loaded in setup())
        self._debug_log("CHMExtension.__init__() completed")
        
    def setup(self):
        """Called when Krita initializes the plugin"""
        self._debug_log("=" * 60)
        self._debug_log("CHM: setup() METHOD CALLED - THIS IS THE MAIN ENTRY POINT")
        self._debug_log("=" * 60)
        
        # CRITICAL: Load signing key first (required for tamper resistance)
        self.signing_key = self._load_signing_key()
        if not self.signing_key:
            QMessageBox.critical(
                None,
                "CHM Plugin - Setup Error",
                "Failed to load signing key!\n\n"
                "The CHM plugin requires a secret signing key for tamper resistance.\n\n"
                "To generate a key, run:\n"
                "  python3 scripts/generate-signing-key.py\n\n"
                "The key should be stored at:\n"
                "  ~/.config/chm/signing_key.txt\n\n"
                "Or set as environment variable:\n"
                "  export CHM_SIGNING_KEY='your_key_here'\n\n"
                "Plugin will not start without a valid key."
            )
            self._debug_log("❌ CRITICAL ERROR: No signing key found, plugin cannot start")
            return
        
        # Set global signing key in chm_core (for HMAC signatures)
        from . import chm_core
        chm_core.set_signing_key(self.signing_key)
        self._debug_log("[KEY-LOAD] ✓ Signing key set in chm_core module")
        
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
            debug_log=self.DEBUG_LOG
        )
        if self.DEBUG_LOG:
            print(f"[CHM-INIT] EventCapture initialized with session_storage: {self.event_capture.session_storage}")
        
        # Initialize API client (Task 1.12)
        self.api_client = CHMApiClient(debug_log=self.DEBUG_LOG)
        
        # Initialize timestamp service (Task 1.13)
        # Load GitHub token from environment or config file
        github_token = self._load_github_token()
        timestamp_config = {
            'github_token': github_token,
            'enable_github': True,
            'enable_wayback': False,
            'enable_chm_log': True
        }
        # Pass our logger function so timestamp service logs appear in debug file
        self.timestamp_service = TripleTimestampService(
            config=timestamp_config, 
            debug_log=self.DEBUG_LOG,
            logger_func=self._debug_log  # Pass our logging function
        )
        
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
            self._log("[EXPORT] Generating proof from session snapshot...")
            proof = self.session_manager.finalize_session(
                doc, 
                artwork_path=filename,  # ← Pass artwork path for file hash
                ai_plugins=ai_plugins_enabled,
                ai_plugins_detected=len(ai_plugins_all) > 0,  # ← Track if any AI plugins exist (enabled or not)
                for_export=True,  # ← Create snapshot, don't destroy active session
                import_tracker=self.event_capture.import_tracker  # ← Pass import tracker for MixedMedia check
            )
            
            if not proof:
                raise Exception("Session finalization returned None")
            
            self._log(f"[EXPORT] Session finalized, proof generated with file hash")
            
            # Save proof JSON (for web app submission - contains file hash for duplicate detection)
            # The web app will use file_hash from this proof to store in DB
            import json
            proof_filename = filename.replace('.png', '_proof.json').replace('.jpg', '_proof.json').replace('.jpeg', '_proof.json')
            proof_dict = proof.to_dict()
            
            # TAMPER RESISTANCE: Verify signature before saving (self-check)
            from . import chm_core
            if "signature" in proof_dict:
                self._log("[EXPORT] 🔐 Verifying proof signature (self-check)...")
                is_valid = chm_core._verify_session_signature(proof_dict)
                if is_valid:
                    self._log("[EXPORT] ✅ Signature verification passed")
                else:
                    self._log("[EXPORT] ❌ CRITICAL: Signature verification FAILED!")
                    QMessageBox.critical(
                        None,
                        "CHM Export Error",
                        "Proof signature verification failed!\n\n"
                        "This should never happen. The proof may be corrupted.\n\n"
                        "Please report this bug."
                    )
                    return
            else:
                self._log("[EXPORT] ⚠️ Proof has no signature (signing key may not be set)")
            
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
                    # Build timestamp status with service details
                    services = []
                    if timestamp_results.get('github'):
                        services.append("GitHub Gist")
                        self._log(f"[EXPORT]   • GitHub Gist: {timestamp_results['github']['url']}")
                    if timestamp_results.get('chm_log'):
                        services.append("CHM Log")
                        self._log(f"[EXPORT]   • CHM Log: index {timestamp_results['chm_log']['log_index']}")
                    
                    timestamp_status = f"✓ Timestamped ({success_count}/2 services: {', '.join(services)})"
                    
                    # ===== PNG METADATA EMBEDDING (ROAA Option 1) =====
                    # Embed gist URL in PNG metadata for immediate, robust verification
                    # This eliminates GitHub indexing delays and survives file modifications
                    if filename.lower().endswith('.png') and timestamp_results.get('github'):
                        try:
                            from .png_metadata import add_chm_metadata
                            
                            gist_url = timestamp_results['github']['url']
                            self._log(f"[EXPORT] Embedding CHM metadata in PNG...")
                            self._log(f"[EXPORT]   • Gist URL: {gist_url}")
                            
                            metadata_success = add_chm_metadata(
                                png_path=filename,
                                gist_url=gist_url,
                                proof_hash=proof_hash,
                                classification=proof_dict.get('classification', 'unknown'),
                                session_id=proof_dict.get('session_id')
                            )
                            
                            if metadata_success:
                                self._log(f"[EXPORT] ✓ CHM metadata embedded successfully!")
                                self._log(f"[EXPORT]   Verification will be immediate (no GitHub search delay)")
                            else:
                                self._log(f"[EXPORT] ⚠️ Metadata embedding failed (non-fatal)")
                                self._log(f"[EXPORT]   Verification will still work via file hash search")
                                
                        except Exception as e:
                            self._log(f"[EXPORT] ⚠️ Metadata embedding error (non-fatal): {e}")
                            # Non-fatal - proof still works, just slower verification
                    
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
                "timestamp_url": None
            }
            
            # Add clickable GitHub Gist URL if available (public timestamp proof)
            if timestamp_results and timestamp_results.get('github'):
                github_url = timestamp_results['github']['url']
                export_data["timestamp_url"] = github_url
                self._log(f"[EXPORT] 🔗 Public timestamp proof: {github_url}")
            
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
            
            # Create session proactively
            session = self.session_manager.create_session(doc)
            
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
        
        self._log(f"[VIEW-DEBUG] Counted: strokes={stroke_count}, layers={layer_count}, imports={import_count}")
        
        # Get current classification (preview - not finalized)
        classification = session._classify(
            doc=doc,
            doc_key=doc_key,
            import_tracker=self.event_capture.import_tracker
        )
        
        # Get tracing info
        tracing_detected = session.metadata.get("tracing_detected", False)
        tracing_percentage = session.metadata.get("tracing_percentage", 0.0)
        
        # Get AI tools info
        ai_tools_used = session.metadata.get("ai_tools_used", False)
        ai_tools_list = session.metadata.get("ai_tools_list", [])
        
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
            "classification": classification,
            "tracing_detected": tracing_detected,
            "tracing_percentage": tracing_percentage,
            "ai_tools_used": ai_tools_used,
            "ai_tools_list": ai_tools_list,
            "imports_visible": imports_visible
        }
        
        # Show in structured dialog
        dialog = SessionInfoDialog(session_data=session_data)
        dialog.exec_()
        
        self._log(f"[VIEW] Session info displayed: {session.id}, classification: {classification}, imports: {import_count}")
    
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
            proof = self.session_manager.finalize_session(
                doc,
                ai_plugins=ai_plugins,
                import_tracker=self.event_capture.import_tracker
            )
            
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
    
    def _load_github_token(self):
        """
        Load GitHub Personal Access Token for Gist API.
        
        Checks in order:
        1. Environment variable: CHM_GITHUB_TOKEN
        2. Config file: ~/.config/chm/github_token.txt
        3. Returns None (anonymous mode with rate limits)
        
        Returns:
            str or None: GitHub token if available
        """
        import os
        
        self._log("[GITHUB-TOKEN] === Starting token load process ===")
        
        # 1. Check environment variable
        self._log("[GITHUB-TOKEN] Step 1: Checking environment variable CHM_GITHUB_TOKEN...")
        token = os.environ.get('CHM_GITHUB_TOKEN')
        if token:
            self._log(f"[GITHUB-TOKEN] ✓ Loaded from environment variable (length: {len(token)})")
            return token
        else:
            self._log("[GITHUB-TOKEN] ✗ Environment variable not set")
        
        # 2. Check config file
        self._log("[GITHUB-TOKEN] Step 2: Checking config file...")
        config_dir = os.path.expanduser("~/.config/chm")
        token_file = os.path.join(config_dir, "github_token.txt")
        
        self._log(f"[GITHUB-TOKEN] Config dir: {config_dir}")
        self._log(f"[GITHUB-TOKEN] Token file path: {token_file}")
        self._log(f"[GITHUB-TOKEN] Config dir exists: {os.path.exists(config_dir)}")
        self._log(f"[GITHUB-TOKEN] Token file exists: {os.path.exists(token_file)}")
        
        if os.path.exists(token_file):
            try:
                self._log(f"[GITHUB-TOKEN] Attempting to read token file...")
                with open(token_file, 'r') as f:
                    token = f.read().strip()
                    self._log(f"[GITHUB-TOKEN] Read {len(token)} characters from file")
                    if token:
                        self._log(f"[GITHUB-TOKEN] ✓ Loaded from config file: {token_file}")
                        self._log(f"[GITHUB-TOKEN] Token length: {len(token)}, starts with: {token[:4]}...")
                        return token
                    else:
                        self._log(f"[GITHUB-TOKEN] ✗ Token file is empty")
            except Exception as e:
                self._log(f"[GITHUB-TOKEN] ✗ Error reading token file: {e}")
                import traceback
                self._log(f"[GITHUB-TOKEN] Traceback:\n{traceback.format_exc()}")
        
        # 3. No token found - will use anonymous mode
        self._log("[GITHUB-TOKEN] === Token load failed ===")
        self._log("[GITHUB-TOKEN] No token found - using anonymous mode (lower rate limits)")
        self._log(f"[GITHUB-TOKEN] To enable authenticated mode:")
        self._log(f"[GITHUB-TOKEN]   1. Create GitHub Personal Access Token at: https://github.com/settings/tokens")
        self._log(f"[GITHUB-TOKEN]   2. Save to: {token_file}")
        self._log(f"[GITHUB-TOKEN]   OR set environment variable: CHM_GITHUB_TOKEN=your_token")
        
        return None
    
    def _load_signing_key(self):
        """
        Load secret signing key for HMAC proof signatures.
        
        Checks in order:
        1. Environment variable: CHM_SIGNING_KEY
        2. Config file: ~/.config/chm/signing_key.txt
        3. Returns None (plugin refuses to start)
        
        Returns:
            str or None: Base64-encoded signing key if available
        """
        import os
        import base64
        
        self._debug_log("[KEY-LOAD] ========== LOADING SIGNING KEY ==========")
        
        # 1. Check environment variable
        self._debug_log("[KEY-LOAD] Step 1: Checking environment variable CHM_SIGNING_KEY...")
        key = os.environ.get('CHM_SIGNING_KEY')
        if key:
            # Validate key format (should be base64, ~44 chars for 32 bytes)
            try:
                decoded = base64.b64decode(key)
                if len(decoded) >= 16:  # At least 128 bits
                    self._debug_log(f"[KEY-LOAD] ✓ Loaded from environment variable (length: {len(decoded)} bytes)")
                    self._debug_log(f"[KEY-LOAD] Key fingerprint: {key[:8]}...{key[-8:]}")
                    return key
                else:
                    self._debug_log(f"[KEY-LOAD] ⚠️ Key from env var too short ({len(decoded)} bytes), need >= 16")
            except Exception as e:
                self._debug_log(f"[KEY-LOAD] ⚠️ Invalid base64 in env var: {e}")
        else:
            self._debug_log("[KEY-LOAD] ✗ Environment variable not set")
        
        # 2. Check config file
        self._debug_log("[KEY-LOAD] Step 2: Checking config file...")
        config_dir = os.path.expanduser("~/.config/chm")
        key_file = os.path.join(config_dir, "signing_key.txt")
        
        self._debug_log(f"[KEY-LOAD] Config file path: {key_file}")
        self._debug_log(f"[KEY-LOAD] File exists: {os.path.exists(key_file)}")
        
        if os.path.exists(key_file):
            try:
                self._debug_log(f"[KEY-LOAD] Reading key file...")
                with open(key_file, 'r') as f:
                    key = f.read().strip()
                    
                # Validate key
                decoded = base64.b64decode(key)
                if len(decoded) >= 16:
                    self._debug_log(f"[KEY-LOAD] ✓ Loaded from config file: {key_file}")
                    self._debug_log(f"[KEY-LOAD] Key length: {len(decoded)} bytes")
                    self._debug_log(f"[KEY-LOAD] Key fingerprint: {key[:8]}...{key[-8:]}")
                    return key
                else:
                    self._debug_log(f"[KEY-LOAD] ✗ Key file contains invalid key (too short)")
                    
            except Exception as e:
                self._debug_log(f"[KEY-LOAD] ✗ Error reading key file: {e}")
                import traceback
                self._debug_log(f"[KEY-LOAD] Traceback:\n{traceback.format_exc()}")
        else:
            self._debug_log(f"[KEY-LOAD] ✗ Key file not found")
        
        # 3. No key found - CRITICAL ERROR
        self._debug_log("[KEY-LOAD] ========== NO SIGNING KEY FOUND ==========")
        self._debug_log("[KEY-LOAD] ❌ CRITICAL: Plugin cannot start without signing key")
        self._debug_log(f"[KEY-LOAD] To generate a key:")
        self._debug_log(f"[KEY-LOAD]   python3 scripts/generate-signing-key.py")
        self._debug_log(f"[KEY-LOAD] Or set environment variable:")
        self._debug_log(f"[KEY-LOAD]   export CHM_SIGNING_KEY='your_key_here'")
        
        return None
    
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


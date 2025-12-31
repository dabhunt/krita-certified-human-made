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
            
            # Generate proof from session snapshot (keeps original session alive)
            self._log("[EXPORT] Generating proof from session snapshot...")
            proof = self.session_manager.finalize_session(
                doc, 
                artwork_path=filename,  # ← Pass artwork path for file hash
                ai_plugins=ai_plugins,
                for_export=True,  # ← Create snapshot, don't destroy active session
                tracing_detector=self.event_capture.tracing_detector  # ← Pass tracing detector for MixedMedia check
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
                    # Build timestamp status with service details
                    services = []
                    if timestamp_results.get('github'):
                        services.append("GitHub Gist")
                        self._log(f"[EXPORT]   • GitHub Gist: {timestamp_results['github']['url']}")
                    if timestamp_results.get('chm_log'):
                        services.append("CHM Log")
                        self._log(f"[EXPORT]   • CHM Log: index {timestamp_results['chm_log']['log_index']}")
                    
                    timestamp_status = f"✓ Timestamped ({success_count}/2 services: {', '.join(services)})"
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
            
            # Show success message with timestamp URLs
            message = (
                f"✅ Image exported with CHM proof!\n\n"
                f"Image: {filename}\n"
                f"Proof: {proof_filename}\n\n"
                f"Classification: {proof.to_dict().get('classification', 'Unknown')}\n"
                f"Strokes: {proof.to_dict().get('event_summary', {}).get('stroke_count', 0)}\n"
                f"Duration: {proof.to_dict().get('event_summary', {}).get('session_duration_secs', 0)}s\n\n"
                f"Timestamps: {timestamp_status}\n"
                f"Database: {submission_status}\n"
                f"C2PA: {c2pa_status}"
            )
            
            # Add clickable GitHub Gist URL if available (public timestamp proof)
            if timestamp_results and timestamp_results.get('github'):
                github_url = timestamp_results['github']['url']
                message += f"\n\n🔗 Public Timestamp:\n{github_url}"
                self._log(f"[EXPORT] 🔗 Public timestamp proof: {github_url}")
            
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
        
        # Get comprehensive session info (without finalizing)
        doc_id = str(id(doc))
        
        # Count events by type
        stroke_count = sum(1 for e in session.events if e.get("type") == "stroke")
        layer_count = sum(1 for e in session.events if e.get("type") in ["layer_created", "layer_added"])
        import_count = sum(1 for e in session.events if e.get("type") == "import")
        
        # Get current classification (preview - not finalized)
        classification = session._classify(
            doc=doc,
            doc_id=doc_id,
            tracing_detector=self.event_capture.tracing_detector
        )
        
        # Get tracing info
        tracing_detected = session.metadata.get("tracing_detected", False)
        tracing_percentage = session.metadata.get("tracing_percentage", 0.0)
        
        # Get AI tools info
        ai_tools_used = session.metadata.get("ai_tools_used", False)
        ai_tools_list = session.metadata.get("ai_tools_list", [])
        
        # Check if imports are visible (MixedMedia check)
        mixed_media_check = ""
        if import_count > 0:
            is_mixed = self.event_capture.tracing_detector.check_mixed_media(doc, doc_id)
            mixed_media_check = f"\nImports Visible: {'Yes (MixedMedia)' if is_mixed else 'No (Hidden references)'}"
        
        # Build comprehensive info message
        info_message = (
            f"📊 CURRENT SESSION STATUS\n"
            f"{'='*40}\n\n"
            f"🆔 Session ID: {session.id[:16]}...\n"
            f"📄 Document: {doc.name()}\n"
            f"📐 Canvas: {doc.width()}x{doc.height()}px\n"
            f"⏱️  Duration: {session.duration_secs}s ({session.duration_secs // 60}m {session.duration_secs % 60}s)\n\n"
            f"🎨 ACTIVITY\n"
            f"{'='*40}\n"
            f"Total Events: {session.event_count}\n"
            f"• Brush Strokes: {stroke_count}\n"
            f"• Layers Added: {layer_count}\n"
            f"• Images Imported: {import_count}\n\n"
            f"🏷️  CLASSIFICATION (Preview)\n"
            f"{'='*40}\n"
            f"Current: {classification}\n"
        )
        
        # Add tracing info if detected
        if tracing_detected:
            info_message += f"⚠️  Tracing Detected: {tracing_percentage*100:.1f}%\n"
        else:
            info_message += f"✓ No Tracing: 0.0%\n"
        
        # Add import visibility info
        if import_count > 0:
            info_message += mixed_media_check + "\n"
        
        # Add AI tools info
        if ai_tools_used:
            info_message += f"\n🤖 AI Tools: {', '.join(ai_tools_list)}\n"
        
        info_message += (
            f"\n{'='*40}\n"
            f"ℹ️  Session is still ACTIVE\n"
            f"Classification may change as you continue working.\n"
            f"Final classification determined on export."
        )
        
        # Show in dialog
        QMessageBox.information(
            None,
            "CHM Active Session",
            info_message
        )
        
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
                tracing_detector=self.event_capture.tracing_detector
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


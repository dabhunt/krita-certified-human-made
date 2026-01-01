"""
CHM Session Manager

Manages active CHM sessions per document.
Handles session lifecycle (create, update, finalize, resume).
"""

from .chm_loader import chm
import json


class CHMSessionManager:
    """Manages CHM sessions for multiple documents"""
    
    def __init__(self, debug_log=True):
        self.active_sessions = {}  # Map: stable_doc_key -> CHMSession
        self.DEBUG_LOG = debug_log
    
    def _get_document_key(self, document):
        """
        Get stable identifier for a document.
        
        Uses fileName() if available (most stable), otherwise falls back to id().
        This prevents session loss when Python creates new wrapper objects for same document.
        
        Args:
            document: Krita document
            
        Returns:
            str: Stable document identifier
        """
        filepath = document.fileName()
        if filepath:
            # Use filepath as stable key (same file = same key)
            return filepath
        else:
            # Unsaved document: use Python object ID
            # Note: This may change if document reference changes before save
            return f"unsaved_{id(document)}"
        
    def create_session(self, document, session_id=None):
        """
        Create a new session for a document.
        
        Args:
            document: Krita document
            session_id: Optional specific session ID (for resuming with same ID)
            
        Returns:
            CHMSession object
        """
        doc_key = self._get_document_key(document)
        
        if doc_key in self.active_sessions:
            self._log(f"Session already exists for document {doc_key}")
            return self.active_sessions[doc_key]
        
        # Create session with specific ID if provided (for continuity)
        if session_id:
            # Note: CHMSession constructor doesn't support custom ID yet
            # For now, create normal session and log the intended ID
            session = chm.CHMSession()
            self._log(f"[PERSIST] Created session with auto-generated ID: {session.id} (requested: {session_id})")
        else:
            session = chm.CHMSession()
        
        # Set metadata from document
        # Note: krita_version and os_info will be set by caller (extension/event_capture)
        session.set_metadata(
            document_name=document.name() if document.name() else None,
            canvas_width=document.width() if document.width() else None,
            canvas_height=document.height() if document.height() else None
        )
        
        self.active_sessions[doc_key] = session
        self._log(f"Created session {session.id} for document {doc_key}")
        
        return session
    
    def get_session(self, document):
        """Get existing session for a document"""
        doc_key = self._get_document_key(document)
        return self.active_sessions.get(doc_key)
    
    def finalize_session(self, document, artwork_path=None, ai_plugins=None, for_export=False, tracing_detector=None):
        """
        Finalize session and generate proof.
        
        For CHM export (for_export=True):  Creates snapshot, finalizes snapshot, returns proof
        For document close (for_export=False): Finalizes actual session, removes from memory
        
        Args:
            document: Krita document
            artwork_path: Optional path to exported artwork (for dual-hash computation)
            ai_plugins: Optional list of detected AI plugin dicts
                       (from PluginMonitor.get_enabled_ai_plugins())
            for_export: If True, create snapshot for proof (keeps original session alive)
            tracing_detector: Optional TracingDetector instance for MixedMedia detection
        
        Returns:
            CHMProof object or None
        """
        doc_key = self._get_document_key(document)
        session = self.active_sessions.get(doc_key)
        
        if not session:
            self._log(f"[FINALIZE-ERROR] ❌ No session found for document {doc_id}")
            return None
        
        self._log(f"[FINALIZE-1] Session {session.id} (events: {session.event_count}, for_export={for_export})")
        
        # For export: Create snapshot so original session stays alive
        if for_export:
            self._log(f"[FINALIZE-2] Creating session snapshot for proof generation...")
            if hasattr(session, 'create_snapshot'):
                session_to_finalize = session.create_snapshot()
                self._log(f"[FINALIZE-2a] ✓ Snapshot created (original session stays active)")
            else:
                # Fallback: Use session directly but don't remove from memory
                session_to_finalize = session
                self._log(f"[FINALIZE-2a] ⚠️ No snapshot support, using original session")
        else:
            # For document close: Finalize the actual session
            self._log(f"[FINALIZE-2] Finalizing actual session (document closing)...")
            session_to_finalize = session
        
        # Record AI plugins before finalizing
        if ai_plugins:
            self._log(f"[FINALIZE-3] Recording {len(ai_plugins)} AI plugin(s) used...")
            for plugin in ai_plugins:
                plugin_name = plugin.get('display_name', plugin.get('name', 'Unknown'))
                plugin_type = plugin.get('ai_type', 'AI_GENERATION')
                self._log(f"  → {plugin_name} ({plugin_type})")
                # Record on the session that will be finalized
                if hasattr(session_to_finalize, 'record_plugin_used'):
                    session_to_finalize.record_plugin_used(plugin_name, plugin_type)
        
        # BUG#005 FIX: Use doc_key (session key) instead of doc_id
        # Finalize with artwork path for dual-hash computation
        doc_key = self._get_document_key(document)
        if artwork_path:
            self._log(f"[FINALIZE-4] Computing file hash for: {artwork_path}")
            proof = session_to_finalize.finalize(
                artwork_path=artwork_path,
                doc=document,
                doc_key=doc_key,
                tracing_detector=tracing_detector
            )
        else:
            self._log(f"[FINALIZE-4] No artwork path (using placeholder hashes)")
            proof = session_to_finalize.finalize(
                doc=document,
                doc_key=doc_key,
                tracing_detector=tracing_detector
            )
        
        self._log(f"[FINALIZE-5] ✓ Proof generated: {len(proof.export_json())} bytes")
        
        # Only remove session from memory if document is closing (not for export)
        if not for_export:
            self._log(f"[FINALIZE-6] Removing session from memory (document closed)")
            del self.active_sessions[doc_key]
        else:
            self._log(f"[FINALIZE-6] Original session still active (can continue recording)")
        
        return proof
    
    def has_session(self, document):
        """Check if document has an active session"""
        doc_key = self._get_document_key(document)
        return doc_key in self.active_sessions
    
    def migrate_session_key(self, old_key, new_key):
        """
        Migrate a session from one key to another.
        
        Used when document changes from unsaved to saved state.
        This prevents session loss when a new document is saved for the first time.
        
        Args:
            old_key: Current key (e.g., "unsaved_12345")
            new_key: New key (e.g., "/path/to/file.kra")
        
        Returns:
            bool: True if migration successful, False otherwise
        """
        if self.DEBUG_LOG:
            self._log(f"[MIGRATE-1] Attempting migration: {old_key} → {new_key}")
        
        if old_key not in self.active_sessions:
            if self.DEBUG_LOG:
                self._log(f"[MIGRATE-2] ❌ No session under old key: {old_key}")
            return False
        
        if new_key in self.active_sessions:
            if self.DEBUG_LOG:
                self._log(f"[MIGRATE-3] ⚠️ Session already exists under new key: {new_key}")
            return False
        
        # Move session from old key to new key
        session = self.active_sessions[old_key]
        self.active_sessions[new_key] = session
        del self.active_sessions[old_key]
        
        if self.DEBUG_LOG:
            self._log(f"[MIGRATE-4] ✅ Session {session.id} migrated successfully")
            self._log(f"[MIGRATE-5] Active sessions now: {list(self.active_sessions.keys())}")
        
        return True
    
    def import_session(self, document, session_json):
        """
        Import session from JSON and associate with document.
        
        Restores full session state including all recorded events,
        allowing artists to continue accumulating events across sessions.
        
        Args:
            document: Krita document
            session_json: Session data as JSON string
            
        Returns:
            CHMSession object or None if import fails
        """
        try:
            doc_key = self._get_document_key(document)
            
            # Parse session JSON
            session_data = json.loads(session_json)
            
            self._log(f"[IMPORT-1] Importing session from JSON ({len(session_json)} bytes)")
            self._log(f"[IMPORT-2] Session data keys: {list(session_data.keys())}")
            
            # Create new session manually to restore full state
            from datetime import datetime
            
            session = chm.CHMSession()
            
            # Restore session properties
            if 'session_id' in session_data:
                session.id = session_data['session_id']
                session.session_id = session_data['session_id']
                self._log(f"[IMPORT-3] Restored session ID: {session.id}")
            
            if 'start_time' in session_data:
                # Parse ISO format timestamp
                start_time_str = session_data['start_time'].rstrip('Z')
                session.start_time = datetime.fromisoformat(start_time_str)
                self._log(f"[IMPORT-4] Restored start_time: {session.start_time}")
            
            if 'events' in session_data:
                session.events = session_data['events']
                self._log(f"[IMPORT-5] Restored {len(session.events)} events")
            else:
                self._log(f"[IMPORT-5] ⚠️ No events in saved session data")
            
            if 'metadata' in session_data:
                session.metadata = session_data['metadata']
                self._log(f"[IMPORT-6] Restored metadata: {list(session.metadata.keys())}")
            
            # BUG#008 FIX: Restore drawing time
            if 'drawing_time_secs' in session_data:
                session.set_drawing_time(int(session_data['drawing_time_secs']))
                self._log(f"[IMPORT-6a] Restored drawing_time: {session_data['drawing_time_secs']}s")
            elif 'active_drawing_time_secs' in session_data:
                # Backwards compatibility with old field name
                session.set_drawing_time(int(session_data['active_drawing_time_secs']))
                self._log(f"[IMPORT-6a] Restored drawing_time (legacy): {session_data['active_drawing_time_secs']}s")
            
            # Keep session unfinalized so it can continue recording
            session.finalized = False
            self._log(f"[IMPORT-7] Session ready (finalized=False)")
            
            # Associate with document using stable key
            self.active_sessions[doc_key] = session
            self._log(f"[IMPORT-7a] Stored session with key: {doc_key}")
            
            event_count = len(session.events) if hasattr(session, 'events') else 0
            self._log(f"[IMPORT-8] ✅ Session restored: {session.id} ({event_count} events)")
            
            return session
            
        except Exception as e:
            self._log(f"[IMPORT-ERROR] ❌ Error importing session: {e}")
            import traceback
            self._log(f"[IMPORT-ERROR] Traceback: {traceback.format_exc()}")
            return None
    
    def session_to_json(self, session):
        """
        Serialize session to JSON string for persistence.
        
        Uses session.to_dict() method for clean separation of concerns.
        Session class owns its data structure and serialization logic.
        
        Args:
            session: CHMSession object (must have to_dict() method)
            
        Returns:
            str: JSON string representation, or None if serialization fails
        """
        try:
            # Use session's own serialization method (DRY principle)
            session_data = session.to_dict()
            
            # Convert to JSON
            session_json = json.dumps(session_data, indent=2)
            
            self._log(f"[SERIALIZE] ✓ Session serialized: {len(session_json)} bytes")
            
            return session_json
            
        except AttributeError as e:
            # Session doesn't have to_dict() method - fall back to manual extraction
            self._log(f"[SERIALIZE] Session missing to_dict(), using manual extraction: {e}")
            try:
                session_data = {
                    'session_id': str(session.id),
                    'event_count': int(session.event_count),
                    'start_time': session.start_time.isoformat() + 'Z',
                    'duration_secs': int(session.duration_secs),
                    'drawing_time_secs': int(session.drawing_time_secs) if hasattr(session, 'drawing_time_secs') else 0,
                    'is_finalized': bool(session.is_finalized),
                    'public_key': str(session.public_key),
                    'metadata': session.get_metadata() if hasattr(session, 'get_metadata') else {}
                }
                session_json = json.dumps(session_data, indent=2)
                self._log(f"[SERIALIZE] ✓ Session serialized (fallback): {len(session_json)} bytes")
                return session_json
            except Exception as fallback_error:
                self._log(f"[SERIALIZE-ERROR] Fallback also failed: {fallback_error}")
                import traceback
                self._log(f"[SERIALIZE-ERROR] Traceback: {traceback.format_exc()}")
                return None
                
        except Exception as e:
            self._log(f"[SERIALIZE-ERROR] ❌ Error serializing session: {e}")
            import traceback
            self._log(f"[SERIALIZE-ERROR] Traceback: {traceback.format_exc()}")
            return None
    
    def _log(self, message):
        """Debug logging helper"""
        if self.DEBUG_LOG:
            import sys
            print(f"CHMSessionManager: {message}")
            sys.stdout.flush()


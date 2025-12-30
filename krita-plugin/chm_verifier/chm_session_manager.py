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
        self.active_sessions = {}  # Map: document_ptr -> CHMSession
        self.DEBUG_LOG = debug_log
        
    def create_session(self, document, session_id=None):
        """
        Create a new session for a document.
        
        Args:
            document: Krita document
            session_id: Optional specific session ID (for resuming with same ID)
            
        Returns:
            CHMSession object
        """
        doc_id = id(document)
        
        if doc_id in self.active_sessions:
            self._log(f"Session already exists for document {doc_id}")
            return self.active_sessions[doc_id]
        
        # Create session with specific ID if provided (for continuity)
        if session_id:
            # Note: CHMSession constructor doesn't support custom ID yet
            # For now, create normal session and log the intended ID
            session = chm.CHMSession()
            self._log(f"[PERSIST] Created session with auto-generated ID: {session.id} (requested: {session_id})")
        else:
            session = chm.CHMSession()
        
        # Set metadata from document
        session.set_metadata(
            document_name=document.name() if document.name() else None,
            canvas_width=document.width() if document.width() else None,
            canvas_height=document.height() if document.height() else None,
            krita_version=None,  # Will be set by extension
            os_info=None  # Will be set by extension
        )
        
        self.active_sessions[doc_id] = session
        self._log(f"Created session {session.id} for document {doc_id}")
        
        return session
    
    def get_session(self, document):
        """Get existing session for a document"""
        doc_id = id(document)
        return self.active_sessions.get(doc_id)
    
    def finalize_session(self, document, artwork_path=None, ai_plugins=None, for_export=False):
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
        
        Returns:
            CHMProof object or None
        """
        doc_id = id(document)
        session = self.active_sessions.get(doc_id)
        
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
        
        # Finalize with artwork path for dual-hash computation
        if artwork_path:
            self._log(f"[FINALIZE-4] Computing file hash for: {artwork_path}")
            proof = session_to_finalize.finalize(artwork_path)
        else:
            self._log(f"[FINALIZE-4] No artwork path (using placeholder hashes)")
            proof = session_to_finalize.finalize()
        
        self._log(f"[FINALIZE-5] ✓ Proof generated: {len(proof.export_json())} bytes")
        
        # Only remove session from memory if document is closing (not for export)
        if not for_export:
            self._log(f"[FINALIZE-6] Removing session from memory (document closed)")
            del self.active_sessions[doc_id]
        else:
            self._log(f"[FINALIZE-6] Original session still active (can continue recording)")
        
        return proof
    
    def has_session(self, document):
        """Check if document has an active session"""
        return id(document) in self.active_sessions
    
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
            doc_id = id(document)
            
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
            
            # Keep session unfinalized so it can continue recording
            session.finalized = False
            self._log(f"[IMPORT-7] Session ready (finalized=False)")
            
            # Associate with document
            self.active_sessions[doc_id] = session
            
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


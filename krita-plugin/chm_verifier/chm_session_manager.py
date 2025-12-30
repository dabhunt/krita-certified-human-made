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
    
    def finalize_session(self, document, artwork_path=None, ai_plugins=None):
        """
        Finalize and remove session for a document
        
        Args:
            document: Krita document
            artwork_path: Optional path to exported artwork (for dual-hash computation)
            ai_plugins: Optional list of detected AI plugin dicts
                       (from PluginMonitor.get_enabled_ai_plugins())
        
        Returns:
            CHMProof object or None
        """
        doc_id = id(document)
        session = self.active_sessions.get(doc_id)
        
        if not session:
            self._log(f"[FLOW-ERROR] ❌ No session found for document {doc_id}")
            return None
        
        self._log(f"[FLOW-3] 🔒 Finalizing session {session.id} (events: {session.event_count})")
        
        # Record AI plugins before finalizing (Task 1.7 integration)
        if ai_plugins:
            self._log(f"[FLOW-3a] Recording {len(ai_plugins)} AI plugin(s) used...")
            for plugin in ai_plugins:
                plugin_name = plugin.get('display_name', plugin.get('name', 'Unknown'))
                plugin_type = plugin.get('ai_type', 'AI_GENERATION')
                self._log(f"  → {plugin_name} ({plugin_type})")
                session.record_plugin_used(plugin_name, plugin_type)
        
        # Finalize with artwork path for dual-hash computation
        if artwork_path:
            self._log(f"[FLOW-3b] Computing dual-hash for: {artwork_path}")
            proof = session.finalize(artwork_path)
        else:
            self._log(f"[FLOW-3b] No artwork path provided - using placeholder hashes")
            proof = session.finalize()
        
        self._log(f"[FLOW-4] ✓ Session finalized, proof generated: {len(proof.export_json())} bytes")
        
        del self.active_sessions[doc_id]
        
        return proof
    
    def has_session(self, document):
        """Check if document has an active session"""
        return id(document) in self.active_sessions
    
    def import_session(self, document, session_json):
        """
        Import session from JSON and associate with document.
        
        This allows resuming sessions from previous Krita sessions.
        
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
            
            self._log(f"[PERSIST] Importing session from JSON ({len(session_json)} bytes)")
            
            # Try to reconstruct session from data
            # Note: This requires CHMSession to support deserialization
            # For now, create new session and attempt to restore basic state
            
            # Check if session has from_dict method (Python fallback)
            try:
                session = chm.CHMSession.from_dict(session_data)
                self._log(f"[PERSIST] ✓ Session imported via from_dict: {session.id}")
            except AttributeError:
                # Rust implementation might not have from_dict
                # Create new session and manually restore what we can
                session = chm.CHMSession()
                self._log(f"[PERSIST] ⚠️  from_dict not available, created new session: {session.id}")
                self._log(f"[PERSIST]    (Original session ID was: {session_data.get('session_id', 'unknown')})")
                
                # Restore metadata if available
                if 'metadata' in session_data:
                    session.set_metadata(**session_data['metadata'])
            
            # Associate with document
            self.active_sessions[doc_id] = session
            
            # Get event count for logging
            event_count = session_data.get('event_count', 0) if isinstance(session_data, dict) else 0
            self._log(f"[PERSIST] ✓ Session associated with document (events: {event_count})")
            
            return session
            
        except Exception as e:
            self._log(f"[PERSIST] ❌ Error importing session: {e}")
            import traceback
            self._log(f"[PERSIST] Traceback: {traceback.format_exc()}")
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


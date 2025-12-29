"""
CHM Session Manager

Manages active CHM sessions per document.
Handles session lifecycle (create, update, finalize).
"""

from .chm_loader import chm


class CHMSessionManager:
    """Manages CHM sessions for multiple documents"""
    
    def __init__(self, debug_log=True):
        self.active_sessions = {}  # Map: document_ptr -> CHMSession
        self.DEBUG_LOG = debug_log
        
    def create_session(self, document):
        """Create a new session for a document"""
        doc_id = id(document)
        
        if doc_id in self.active_sessions:
            self._log(f"Session already exists for document {doc_id}")
            return self.active_sessions[doc_id]
        
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
    
    def _log(self, message):
        """Debug logging helper"""
        if self.DEBUG_LOG:
            print(f"CHMSessionManager: {message}")


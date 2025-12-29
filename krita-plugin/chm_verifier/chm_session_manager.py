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
    
    def finalize_session(self, document):
        """Finalize and remove session for a document"""
        doc_id = id(document)
        session = self.active_sessions.get(doc_id)
        
        if not session:
            self._log(f"No session found for document {doc_id}")
            return None
        
        proof = session.finalize()
        del self.active_sessions[doc_id]
        
        self._log(f"Finalized session for document {doc_id}")
        return proof
    
    def has_session(self, document):
        """Check if document has an active session"""
        return id(document) in self.active_sessions
    
    def _log(self, message):
        """Debug logging helper"""
        if self.DEBUG_LOG:
            print(f"CHMSessionManager: {message}")


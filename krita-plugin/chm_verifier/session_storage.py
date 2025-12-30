"""
Session Storage Module

Persists CHM sessions to disk for resumption across file close/open cycles.
Implements ROAA Approach 1: Session data stored locally, session ID travels with file.
"""

import os
import json
import hashlib
from datetime import datetime


class SessionStorage:
    """
    Persists CHM sessions to disk.
    
    Sessions are stored as JSON files in ~/.local/share/chm/sessions/
    Each session file is named {session_id}.json
    
    This allows sessions to be resumed when .kra files are reopened,
    enabling artists to track cumulative work across multiple sessions.
    """
    
    def __init__(self, storage_dir=None, debug_log=True):
        """
        Initialize session storage.
        
        Args:
            storage_dir: Directory to store sessions (default: ~/.local/share/chm/sessions)
            debug_log: Enable debug logging
        """
        if storage_dir is None:
            storage_dir = os.path.expanduser("~/.local/share/chm/sessions")
        
        self.storage_dir = os.path.expanduser(storage_dir)
        self.DEBUG_LOG = debug_log
        
        # Create storage directory if it doesn't exist
        try:
            os.makedirs(self.storage_dir, exist_ok=True)
            self._log(f"Session storage initialized: {self.storage_dir}")
        except Exception as e:
            self._log(f"⚠️  Error creating storage directory: {e}")
    
    def save_session(self, session_id, session_json):
        """
        Save session to disk.
        
        Args:
            session_id: Unique session identifier
            session_json: Session data as JSON string
            
        Returns:
            bool: True if save successful, False otherwise
        """
        try:
            filepath = self._get_session_filepath(session_id)
            
            # Write session data
            with open(filepath, 'w') as f:
                f.write(session_json)
            
            if self.DEBUG_LOG:
                # Get file size for logging
                file_size = os.path.getsize(filepath)
                self._log(f"[PERSIST] ✓ Session saved: {session_id} ({file_size} bytes)")
            
            return True
            
        except Exception as e:
            self._log(f"[PERSIST] ❌ Error saving session {session_id}: {e}")
            import traceback
            self._log(f"[PERSIST] Traceback: {traceback.format_exc()}")
            return False
    
    def load_session(self, session_id):
        """
        Load session from disk.
        
        Args:
            session_id: Unique session identifier
            
        Returns:
            str: Session JSON string, or None if not found
        """
        try:
            filepath = self._get_session_filepath(session_id)
            
            if not os.path.exists(filepath):
                if self.DEBUG_LOG:
                    self._log(f"[PERSIST] Session file not found: {session_id}")
                return None
            
            # Read session data
            with open(filepath, 'r') as f:
                session_json = f.read()
            
            if self.DEBUG_LOG:
                file_size = os.path.getsize(filepath)
                self._log(f"[PERSIST] ✓ Session loaded: {session_id} ({file_size} bytes)")
            
            return session_json
            
        except Exception as e:
            self._log(f"[PERSIST] ❌ Error loading session {session_id}: {e}")
            import traceback
            self._log(f"[PERSIST] Traceback: {traceback.format_exc()}")
            return None
    
    def delete_session(self, session_id):
        """
        Delete session file from disk.
        
        Args:
            session_id: Unique session identifier
            
        Returns:
            bool: True if deletion successful, False otherwise
        """
        try:
            filepath = self._get_session_filepath(session_id)
            
            if os.path.exists(filepath):
                os.remove(filepath)
                self._log(f"[PERSIST] ✓ Session deleted: {session_id}")
                return True
            else:
                if self.DEBUG_LOG:
                    self._log(f"[PERSIST] Session file not found (already deleted?): {session_id}")
                return False
                
        except Exception as e:
            self._log(f"[PERSIST] ❌ Error deleting session {session_id}: {e}")
            return False
    
    def session_exists(self, session_id):
        """
        Check if session file exists on disk.
        
        Args:
            session_id: Unique session identifier
            
        Returns:
            bool: True if session file exists
        """
        filepath = self._get_session_filepath(session_id)
        return os.path.exists(filepath)
    
    def list_sessions(self):
        """
        List all session IDs in storage.
        
        Returns:
            list: List of session IDs (without .json extension)
        """
        try:
            if not os.path.exists(self.storage_dir):
                return []
            
            # List all .json files
            files = os.listdir(self.storage_dir)
            sessions = [f[:-5] for f in files if f.endswith('.json')]
            
            return sessions
            
        except Exception as e:
            self._log(f"[PERSIST] ❌ Error listing sessions: {e}")
            return []
    
    def cleanup_old_sessions(self, max_age_days=30):
        """
        Delete sessions older than specified age.
        
        Args:
            max_age_days: Maximum age in days (default: 30)
            
        Returns:
            int: Number of sessions deleted
        """
        try:
            deleted_count = 0
            current_time = datetime.now().timestamp()
            max_age_seconds = max_age_days * 24 * 60 * 60
            
            for session_id in self.list_sessions():
                filepath = self._get_session_filepath(session_id)
                
                # Check file modification time
                file_mtime = os.path.getmtime(filepath)
                age_seconds = current_time - file_mtime
                
                if age_seconds > max_age_seconds:
                    if self.delete_session(session_id):
                        deleted_count += 1
                        if self.DEBUG_LOG:
                            age_days = age_seconds / (24 * 60 * 60)
                            self._log(f"[CLEANUP] Deleted old session: {session_id} ({age_days:.1f} days old)")
            
            if deleted_count > 0:
                self._log(f"[CLEANUP] ✓ Cleaned up {deleted_count} old session(s)")
            
            return deleted_count
            
        except Exception as e:
            self._log(f"[CLEANUP] ❌ Error during cleanup: {e}")
            return 0
    
    def get_session_info(self, session_id):
        """
        Get metadata about a session file without loading full content.
        
        Args:
            session_id: Unique session identifier
            
        Returns:
            dict: Session metadata (size, modified_time, etc.) or None
        """
        try:
            filepath = self._get_session_filepath(session_id)
            
            if not os.path.exists(filepath):
                return None
            
            stat = os.stat(filepath)
            
            return {
                'session_id': session_id,
                'file_size': stat.st_size,
                'modified_time': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                'created_time': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                'filepath': filepath
            }
            
        except Exception as e:
            self._log(f"[PERSIST] ❌ Error getting session info {session_id}: {e}")
            return None
    
    def get_session_key_for_file(self, filepath):
        """
        Generate session key for a file (ROAA Approach 2: hash-based lookup).
        
        Uses hash of filepath + inode number as stable key.
        This allows resuming sessions without modifying the .kra file.
        
        CRITICAL FIX: Previously used st_ctime (change time), which updates on
        every save, causing session key to change. Now uses st_ino (inode),
        which is stable for the lifetime of the file on the same filesystem.
        
        Args:
            filepath: Full path to .kra file
            
        Returns:
            str: Session key (hash) or None if file doesn't exist
        """
        try:
            if not filepath or not os.path.exists(filepath):
                return None
            
            # Get file stats
            stat = os.stat(filepath)
            
            # Create stable key from path + inode number
            # Inode is stable unless file is moved/copied to different filesystem
            # This prevents session key from changing on every save (unlike st_ctime)
            key_data = f"{filepath}:{stat.st_ino}"
            session_key = hashlib.sha256(key_data.encode()).hexdigest()
            
            if self.DEBUG_LOG:
                self._log(f"[SESSION-KEY] Generated for {os.path.basename(filepath)}: {session_key[:16]}... (inode: {stat.st_ino})")
            
            return session_key
            
        except Exception as e:
            self._log(f"[SESSION-KEY] ❌ Error generating key: {e}")
            return None
    
    def _get_session_filepath(self, session_id):
        """Get full filepath for a session ID."""
        return os.path.join(self.storage_dir, f"{session_id}.json")
    
    def _log(self, message):
        """Debug logging helper."""
        if self.DEBUG_LOG:
            import sys
            from datetime import datetime
            
            full_message = f"SessionStorage: {message}"
            print(full_message)
            sys.stdout.flush()
            
            # Also write to debug file
            try:
                log_dir = os.path.expanduser("~/.local/share/chm")
                os.makedirs(log_dir, exist_ok=True)
                log_file = os.path.join(log_dir, "plugin_debug.log")
                
                with open(log_file, "a") as f:
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    f.write(f"[{timestamp}] CHM: {full_message}\n")
                    f.flush()
            except Exception as e:
                print(f"SessionStorage: Could not write to log file: {e}")


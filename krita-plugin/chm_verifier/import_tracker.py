"""
Import Tracker Module

Simplified import tracking for Mixed Media classification.

Mixed Media Logic (Updated Jan 3, 2026):
- If user imports any image (non-reference), document becomes Mixed Media
- Classification is STICKY: remains even if import is later deleted
- Reference imports (from Krita's Reference Images docker) do NOT trigger Mixed Media

This replaces the previous complex edge detection system with a simpler,
more straightforward approach.
"""

from typing import Optional
from PyQt5.QtGui import QImage


DEBUG_LOG = True


class ImportTracker:
    """Tracks image imports for Mixed Media classification"""
    
    def __init__(self, debug_log: bool = True):
        self.DEBUG_LOG = debug_log
        # Track which documents have had imports (STICKY)
        # doc_key -> bool (True if any import detected)
        self.has_imports = {}  # doc_key -> bool
        
        # Track which specific layers have been registered (prevent duplicates)
        # doc_key -> set of layer_names
        self.registered_layers = {}  # doc_key -> set(layer_name)
        
        if self.DEBUG_LOG:
            self._log(f"[INIT] ImportTracker initialized")
        
    def register_import(self, doc_key: str, layer_node, layer_name: str):
        """
        Register an imported image layer.
        
        Once registered, the document is marked as having imports (STICKY).
        This marking persists even if the import layer is later deleted.
        
        Returns True if this is a NEW import, False if already registered (duplicate).
        
        Args:
            doc_key: Document key (from session manager, e.g., filepath or unsaved_ID)
            layer_node: Krita layer node
            layer_name: Layer name for logging
        """
        try:
            if self.DEBUG_LOG:
                self._log(f"[IMPORT-REG] ========================================")
                self._log(f"[IMPORT-REG] CALLED: register_import()")
                self._log(f"[IMPORT-REG]   doc_key: {doc_key}")
                self._log(f"[IMPORT-REG]   layer_name: {layer_name}")
            
            # Check if already registered (prevent duplicates)
            if doc_key not in self.registered_layers:
                self.registered_layers[doc_key] = set()
            
            if layer_name in self.registered_layers[doc_key]:
                if self.DEBUG_LOG:
                    self._log(f"[IMPORT-REG] ⚠️  Already registered, skipping duplicate")
                    self._log(f"[IMPORT-REG] ========================================")
                return False  # Duplicate
            
            # Register this specific layer
            self.registered_layers[doc_key].add(layer_name)
            
            # Mark document as having imports (STICKY)
            self.has_imports[doc_key] = True
            
            if self.DEBUG_LOG:
                self._log(f"[IMPORT-REG] ✓ NEW import registered")
                self._log(f"[IMPORT-REG]   Registered layers: {self.registered_layers[doc_key]}")
                self._log(f"[IMPORT-REG] ========================================")
            
            return True  # New import
                
        except Exception as e:
            self._log(f"[IMPORT-REG] ❌ Error registering import: {e}")
            import traceback
            self._log(f"[IMPORT-REG] Traceback: {traceback.format_exc()}")
            return False
    
    def has_mixed_media(self, doc_key: str) -> bool:
        """
        Check if document has Mixed Media (any imports registered).
        
        Args:
            doc_key: Document key (from session manager)
            
        Returns:
            True if any imports have been registered (sticky), False otherwise
        """
        has_import = self.has_imports.get(doc_key, False)
        
        if self.DEBUG_LOG:
            self._log(f"[MIXED-MEDIA-CHECK] ========================================")
            self._log(f"[MIXED-MEDIA-CHECK] CALLED: has_mixed_media()")
            self._log(f"[MIXED-MEDIA-CHECK]   doc_key: {doc_key}")
            self._log(f"[MIXED-MEDIA-CHECK]   has_imports dict: {self.has_imports}")
            self._log(f"[MIXED-MEDIA-CHECK]   Result: {has_import}")
            self._log(f"[MIXED-MEDIA-CHECK] ========================================")
        
        return has_import
    
    def _log(self, message: str):
        """Debug logging helper"""
        if self.DEBUG_LOG:
            import sys
            from datetime import datetime
            import os
            
            full_message = f"ImportTracker: {message}"
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
                print(f"ImportTracker: Could not write to log file: {e}")


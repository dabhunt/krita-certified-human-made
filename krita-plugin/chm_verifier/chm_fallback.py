"""
Pure Python fallback implementation of CHM core functionality.
Used on macOS where native library loading is blocked by hardened runtime.

This provides the same interface as the Rust library but uses Python cryptography libraries.
"""

import hashlib
import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any


class CHMFallback:
    """Pure Python implementation of CHM core functionality"""
    
    def __init__(self):
        """Initialize the fallback implementation"""
        self.version = "0.1.0-python-fallback"
    
    def get_version(self) -> str:
        """Get library version"""
        return self.version
    
    def hello_from_rust(self) -> str:
        """Test function (named for compatibility)"""
        return "Hello from Python fallback! CHM library is working."


class CHMSession:
    """
    Pure Python implementation of CHM Session.
    Captures drawing events and generates verification proofs.
    
    Compatible with Rust CHMSession interface.
    """
    
    def __init__(self, document_id: Optional[str] = None):
        """
        Create a new session for a document.
        
        Args:
            document_id: Unique identifier for the document (optional)
        """
        self.id = str(uuid.uuid4())
        self.session_id = self.id  # Alias for compatibility
        self.document_id = document_id or "unknown"
        self.start_time = datetime.utcnow()
        self.events = []
        self.metadata = {
            "platform": "macOS",
            "implementation": "python-fallback"
        }
        self.finalized = False
        
        # FIX: Initialize layer count to 1 (default layer always exists)
        self._layer_count = 1
    
    def set_metadata(self, **kwargs):
        """
        Set session metadata.
        
        Args:
            **kwargs: Metadata key-value pairs
        """
        self.metadata.update(kwargs)
        
    def record_stroke(
        self,
        x: float,
        y: float,
        pressure: float,
        brush_name: Optional[str] = None,
        timestamp: Optional[float] = None
    ):
        """
        Record a brush stroke event.
        
        Args:
            x: X coordinate
            y: Y coordinate  
            pressure: Pressure value (0.0-1.0)
            brush_name: Name of the brush used (optional)
            timestamp: Event timestamp (seconds since epoch, auto-generated if None)
        """
        if self.finalized:
            raise RuntimeError("Cannot record events on finalized session")
        
        if timestamp is None:
            timestamp = datetime.utcnow().timestamp()
        
        event = {
            "type": "stroke",
            "x": x,
            "y": y,
            "pressure": pressure,
            "brush_name": brush_name,
            "timestamp": timestamp
        }
        self.events.append(event)
    
    def record_layer_created(self, layer_name: str, timestamp: float):
        """
        Record a layer creation event.
        
        Args:
            layer_name: Name of the created layer
            timestamp: Event timestamp
        """
        if self.finalized:
            raise RuntimeError("Cannot record events on finalized session")
        
        event = {
            "type": "layer_created",
            "layer_name": layer_name,
            "timestamp": timestamp
        }
        self.events.append(event)
    
    def record_import(
        self,
        file_path: str,
        import_type: str,
        timestamp: float
    ):
        """
        Record an image import event.
        
        Args:
            file_path: Path to imported file
            import_type: Type of import (reference, paste, etc.)
            timestamp: Event timestamp
        """
        if self.finalized:
            raise RuntimeError("Cannot record events on finalized session")
        
        event = {
            "type": "import",
            "file_path": file_path,
            "import_type": import_type,
            "timestamp": timestamp
        }
        self.events.append(event)
    
    def get_event_count(self) -> int:
        """Get number of recorded events"""
        return len(self.events)
    
    @property
    def event_count(self) -> int:
        """Get number of recorded events (property for compatibility)"""
        return len(self.events)
    
    def record_layer_added(
        self,
        layer_id: str,
        layer_type: str,
        timestamp: Optional[float] = None
    ):
        """
        Record a layer addition event.
        
        Args:
            layer_id: Unique identifier for the layer
            layer_type: Type of layer (paint, group, etc.)
            timestamp: Event timestamp
        """
        if self.finalized:
            raise RuntimeError("Cannot record events on finalized session")
        
        if timestamp is None:
            timestamp = datetime.utcnow().timestamp()
        
        event = {
            "type": "layer_added",
            "layer_id": layer_id,
            "layer_type": layer_type,
            "timestamp": timestamp
        }
        self.events.append(event)
        
        # Increment layer count
        self._layer_count += 1
    
    def get_session_id(self) -> str:
        """Get session ID"""
        return self.session_id
    
    def finalize(self, artwork_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Finalize the session and generate a proof summary.
        
        Args:
            artwork_path: Optional path to exported artwork for dual-hash computation
        
        Returns:
            Dictionary with session proof data
        """
        if self.finalized:
            raise RuntimeError("Session already finalized")
        
        self.finalized = True
        end_time = datetime.utcnow()
        duration = (end_time - self.start_time).total_seconds()
        
        # Count event types
        stroke_count = sum(1 for e in self.events if e.get("type") == "stroke")
        # Use tracked layer count (initialized to 1 for default layer, incremented on layer_added events)
        layer_count = self._layer_count
        import_count = sum(1 for e in self.events if e.get("type") == "import")
        
        # Generate event hash
        events_json = json.dumps(self.events, sort_keys=True)
        events_hash = hashlib.sha256(events_json.encode()).hexdigest()
        
        # File hash computation if artwork path provided
        file_hash = None
        
        if artwork_path:
            import os
            if os.path.exists(artwork_path):
                try:
                    # File hash (SHA-256 of exact bytes) - sufficient for duplicate detection
                    with open(artwork_path, 'rb') as f:
                        artwork_bytes = f.read()
                        file_hash = hashlib.sha256(artwork_bytes).hexdigest()
                        
                except Exception as e:
                    print(f"[CHM-FALLBACK] Warning: Failed to compute file hash: {e}")
        
        # Create proof summary
        proof = {
            "version": "1.0",
            "session_id": self.session_id,
            "document_id": self.document_id,
            "start_time": self.start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration_seconds": duration,
            "event_summary": {
                "total_events": len(self.events),
                "stroke_count": stroke_count,
                "layer_count": layer_count,
                "import_count": import_count
            },
            "events_hash": events_hash,
            "file_hash": file_hash if file_hash else "placeholder_no_artwork_provided",
            "classification": self._classify(),
            "metadata": self.metadata
        }
        
        return proof
    
    def _classify(self) -> str:
        """
        Classify the session based on events and metadata.
        
        Classification Logic (Dec 30, 2025):
        - HumanMade: Pure manual work, references ALLOWED (as long as not traced/visible)
        - MixedMedia: Imported images visible in final export (but not traced)
        - AI-Assisted: AI tools detected in metadata
        - Traced: High % of traced content (>33% edge correlation) - STICKY
        
        Returns:
            Classification string
        """
        # Priority 1: Check for AI tools in metadata
        ai_tools_used = self.metadata.get("ai_tools_used", False)
        if ai_tools_used:
            return "AI-Assisted"
        
        # Priority 2: Check for tracing (STICKY - once traced, always traced)
        tracing_detected = self.metadata.get("tracing_detected", False)
        if tracing_detected:
            return "Traced"
        
        # Priority 3: Check for visible imports in final export (MixedMedia)
        # Placeholder heuristic: if imports exist but very few strokes, likely MixedMedia
        has_imports = any(e.get("type") == "import" for e in self.events)
        has_strokes = any(e.get("type") == "stroke" for e in self.events)
        stroke_count = sum(1 for e in self.events if e.get("type") == "stroke")
        
        if has_imports and stroke_count < 10:
            return "MixedMedia"
        
        # Default: HumanMade (includes references as long as not traced/visible!)
        return "HumanMade"


# Module-level functions for compatibility with Rust library interface
_chm_instance = None


def get_version() -> str:
    """Get CHM library version"""
    global _chm_instance
    if _chm_instance is None:
        _chm_instance = CHMFallback()
    return _chm_instance.get_version()


def hello_from_rust() -> str:
    """Test function for library loading"""
    global _chm_instance
    if _chm_instance is None:
        _chm_instance = CHMFallback()
    return _chm_instance.hello_from_rust()


# Export classes and functions
# Also export Session for backwards compatibility
Session = CHMSession
__all__ = ['CHMSession', 'Session', 'get_version', 'hello_from_rust', 'CHMFallback']


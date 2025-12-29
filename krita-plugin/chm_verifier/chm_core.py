"""
CHM Core - Python Implementation

Pure Python implementation of CHM core functionality.
Uses standard Python libraries for cryptography and session management.

This is the primary implementation for MVP. Future versions may add
Rust optimization for performance-critical operations.
"""

import hashlib
import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any


class CHMProof:
    """
    Proof object wrapper for session verification data.
    Provides export_json() method for compatibility.
    """
    
    def __init__(self, proof_data: Dict[str, Any]):
        """
        Create a proof object from session data.
        
        Args:
            proof_data: Dictionary containing proof information
        """
        self.data = proof_data
        print(f"[FLOW-4a] 📝 CHMProof created with {len(proof_data)} keys")
        print(f"[FLOW-4a] Proof keys: {list(proof_data.keys())}")
        import sys
        sys.stdout.flush()
    
    def export_json(self) -> str:
        """
        Export proof as JSON string.
        
        Returns:
            JSON string representation of the proof
        """
        json_str = json.dumps(self.data, indent=2)
        print(f"[FLOW-4b] 📤 Proof exported as JSON ({len(json_str)} bytes)")
        import sys
        sys.stdout.flush()
        return json_str
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Get proof data as dictionary.
        
        Returns:
            Proof data dictionary
        """
        return self.data


class CHMFallback:
    """Pure Python implementation of CHM core functionality"""
    
    def __init__(self):
        """Initialize the CHM core"""
        self.version = "0.1.0"
    
    def get_version(self) -> str:
        """Get library version"""
        return self.version
    
    def hello_from_rust(self) -> str:
        """Test function (legacy name for compatibility)"""
        return "Hello from CHM library! Python implementation is working."


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
    
    def get_session_id(self) -> str:
        """Get session ID"""
        return self.session_id
    
    def finalize(self, artwork_path: Optional[str] = None) -> 'CHMProof':
        """
        Finalize the session and generate a proof summary.
        
        Args:
            artwork_path: Optional path to exported artwork for dual-hash computation
        
        Returns:
            CHMProof object with session verification data
        """
        if self.finalized:
            raise RuntimeError("Session already finalized")
        
        print(f"[FLOW-3a] 🔐 Finalizing session {self.session_id} with {len(self.events)} events")
        import sys
        import os
        sys.stdout.flush()
        
        self.finalized = True
        end_time = datetime.utcnow()
        duration = (end_time - self.start_time).total_seconds()
        
        # Count event types
        stroke_count = sum(1 for e in self.events if e.get("type") == "stroke")
        layer_count = sum(1 for e in self.events if e.get("type") == "layer_created")
        import_count = sum(1 for e in self.events if e.get("type") == "import")
        
        print(f"[FLOW-3b] 📊 Event summary: {stroke_count} strokes, {layer_count} layers, {import_count} imports")
        sys.stdout.flush()
        
        # Generate event hash
        events_json = json.dumps(self.events, sort_keys=True)
        events_hash = hashlib.sha256(events_json.encode()).hexdigest()
        
        print(f"[FLOW-3c] 🔑 Events hash: {events_hash[:16]}...")
        sys.stdout.flush()
        
        # Dual-hash computation if artwork path provided
        file_hash = None
        perceptual_hash = None
        
        if artwork_path and os.path.exists(artwork_path):
            print(f"[FLOW-3c-DUAL] 🖼️ Computing dual-hash for: {artwork_path}")
            sys.stdout.flush()
            
            try:
                # 1. File hash (SHA-256 of exact bytes)
                with open(artwork_path, 'rb') as f:
                    artwork_bytes = f.read()
                    file_hash = hashlib.sha256(artwork_bytes).hexdigest()
                    print(f"[FLOW-3c-DUAL] ✓ File hash (SHA-256): {file_hash[:16]}...")
                    sys.stdout.flush()
                
                # 2. Perceptual hash (survives re-encoding)
                try:
                    from PIL import Image
                    import imagehash
                    
                    img = Image.open(artwork_path)
                    # Use average hash (robust to compression/resizing)
                    phash = imagehash.average_hash(img, hash_size=16)  # 256-bit hash
                    perceptual_hash = str(phash)
                    print(f"[FLOW-3c-DUAL] ✓ Perceptual hash (aHash): {perceptual_hash[:16]}...")
                    sys.stdout.flush()
                except ImportError:
                    print(f"[FLOW-3c-DUAL] ⚠️ PIL/imagehash not available, skipping perceptual hash")
                    perceptual_hash = "unavailable_missing_dependencies"
                    sys.stdout.flush()
                except Exception as e:
                    print(f"[FLOW-3c-DUAL] ⚠️ Failed to compute perceptual hash: {e}")
                    perceptual_hash = f"error_{str(e)[:20]}"
                    sys.stdout.flush()
                    
            except Exception as e:
                print(f"[FLOW-3c-DUAL] ⚠️ Failed to compute file hash: {e}")
                sys.stdout.flush()
        else:
            print(f"[FLOW-3c-DUAL] ℹ️ No artwork path provided, using placeholder hashes")
            sys.stdout.flush()
        
        # Classify session
        classification = self._classify()
        confidence = 1.0 if classification == "HumanMade" else 0.5  # Simple confidence
        
        print(f"[FLOW-3d] 🏷️ Classification: {classification} (confidence: {confidence})")
        sys.stdout.flush()
        
        # Create proof summary
        proof_data = {
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
                "import_count": import_count,
                "session_duration_secs": int(duration)  # Add for UI display
            },
            "events_hash": events_hash,
            "file_hash": file_hash if file_hash else "placeholder_no_artwork_provided",
            "perceptual_hash": perceptual_hash if perceptual_hash else "placeholder_no_artwork_provided",
            "classification": classification,
            "confidence": confidence,
            "metadata": self.metadata
        }
        
        print(f"[FLOW-3e] ✅ Proof data created, wrapping in CHMProof object")
        sys.stdout.flush()
        
        return CHMProof(proof_data)
    
    def _classify(self) -> str:
        """
        Classify the session based on events.
        Simple classification for fallback implementation.
        
        Returns:
            Classification string
        """
        # Check for imports
        has_imports = any(e.get("type") == "import" for e in self.events)
        
        # Simple classification logic
        if has_imports:
            return "Referenced"  # Has reference images
        else:
            return "HumanMade"  # Pure human work


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


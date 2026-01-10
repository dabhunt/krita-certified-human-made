"""
CHM Core - Python Implementation

Pure Python implementation of CHM core functionality.
Uses standard Python libraries for cryptography and session management.

SECURITY (BUG-015 FIX):
- Server-side ED25519 signing (private key never exposed)
- Server-side GitHub timestamping (GitHub token never exposed)
- Public key embedded for verification (safe to distribute)
"""

import hashlib
import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any

# Import safe_flush utility for Windows compatibility
try:
    from .logging_util import safe_flush
except ImportError:
    # Fallback if logging_util not available
    import sys
    def safe_flush():
        if sys.stdout is not None:
            try:
                sys.stdout.flush()
            except (AttributeError, ValueError):
                pass

# =============================================================================
# ED25519 PUBLIC KEY (SAFE TO EMBED - USED FOR VERIFICATION ONLY)
# =============================================================================
# This public key verifies proofs signed by the server's private key.
# It's safe to distribute publicly - cannot be used to forge proofs.
ED25519_PUBLIC_KEY_PEM = """-----BEGIN PUBLIC KEY-----
MCowBQYDK2VwAyEAR9iDWLgtMcNYi0eWV9VKzgiKvXuVs1biEdwYxjnhIqo=
-----END PUBLIC KEY-----"""

# Global API client reference (set by plugin on startup)
_API_CLIENT = None


def set_api_client(api_client):
    """
    Set the global API client for server-side signing.
    
    SECURITY (BUG-015): Replaced set_signing_key() with set_api_client().
    Plugin no longer handles signing keys - all signing happens server-side.
    
    Args:
        api_client: CHMApiClient instance for server communication
    """
    global _API_CLIENT
    import sys
    
    _API_CLIENT = api_client
    
    if sys.stdout is not None:
        print(f"[API-CLIENT] ✓ API client registered for server-side signing")
    safe_flush()


def _compute_session_signature_via_server(proof_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Request server-side ED25519 signature + GitHub timestamp (COMBINED API CALL).
    
    SECURITY (BUG-015 FIX):
    - Private key stays on server (never exposed to plugin)
    - GitHub token stays on server (never exposed to plugin)
    - Returns ED25519 signature + GitHub gist URL
    - Users cannot forge proofs (no access to private key)
    
    Args:
        proof_data: Proof data dictionary
        
    Returns:
        dict: {
            'signature': str - ED25519 signature (base64),
            'signature_version': str - 'ed25519-v1',
            'github': dict or None - GitHub timestamp info
        } or None if API call failed
    """
    global _API_CLIENT
    
    print(f"[SIGNATURE-DEBUG] === Starting server-side signature request ===")
    print(f"[SIGNATURE-DEBUG] _API_CLIENT type: {type(_API_CLIENT)}")
    print(f"[SIGNATURE-DEBUG] _API_CLIENT is None: {_API_CLIENT is None}")
    safe_flush()
    
    if not _API_CLIENT:
        print("[SIGNATURE] ❌ CRITICAL: No API client set, cannot sign via server")
        print("[SIGNATURE] This means chm_core.set_api_client() was not called during plugin setup")
        import sys
        safe_flush()
        return None
    
    print(f"[SIGNATURE] ✓ API client available: {_API_CLIENT}")
    print(f"[SIGNATURE] Requesting server-side signing + timestamping...")
    safe_flush()
    
    # Call server API (handles both signing AND GitHub timestamp)
    try:
        print(f"[SIGNATURE-DEBUG] About to call _API_CLIENT.sign_and_timestamp()...")
        safe_flush()
        
        result = _API_CLIENT.sign_and_timestamp(proof_data)
        
        print(f"[SIGNATURE-DEBUG] API call completed, result type: {type(result)}")
        print(f"[SIGNATURE-DEBUG] Result keys: {list(result.keys()) if isinstance(result, dict) else 'NOT_A_DICT'}")
        safe_flush()
        
    except Exception as e:
        print(f"[SIGNATURE] ❌ EXCEPTION during API call: {e}")
        import traceback
        print(f"[SIGNATURE] Traceback:\n{traceback.format_exc()}")
        safe_flush()
        return None
    
    if result.get('error'):
        print(f"[SIGNATURE] ✗ Server signing failed: {result['error']}")
        safe_flush()
        return None
    
    if result.get('signature'):
        print(f"[SIGNATURE] ✓ Server signed proof: {result['signature'][:20]}...")
        print(f"[SIGNATURE]   Signature version: {result.get('signature_version', 'unknown')}")
        
        if result.get('github'):
            print(f"[SIGNATURE] ✓ GitHub timestamp: {result['github']['url']}")
        else:
            print(f"[SIGNATURE] ⚠️  No GitHub timestamp (non-fatal)")
        
        safe_flush()
        return result
    
    print(f"[SIGNATURE] ✗ No signature in server response")
    print(f"[SIGNATURE-DEBUG] Full result: {result}")
    safe_flush()
    return None


def _verify_session_signature(proof_data: Dict[str, Any]) -> bool:
    """
    Verify ED25519 signature of proof data using public key.
    
    SECURITY (BUG-015 FIX):
    - Uses ED25519 asymmetric verification
    - Public key embedded in code (safe - cannot forge)
    - Works with server-signed proofs
    - Pure Python (no Rust dependency)
    
    Args:
        proof_data: Proof data dictionary with 'signature' field
        
    Returns:
        True if signature is valid, False otherwise
    """
    # Check if proof has signature
    if "signature" not in proof_data:
        print("[VERIFY] ✗ Proof has no signature field")
        safe_flush()
        return False
    
    stored_signature = proof_data["signature"]
    signature_version = proof_data.get("signature_version", "v1")
    
    # Handle different signature versions
    if signature_version == "ed25519-v1":
        # New secure ED25519 signatures
        return _verify_ed25519_signature(proof_data, stored_signature)
    elif signature_version in ["v1", "hmac-v1"]:
        # Old HMAC signatures (DEPRECATED - insecure!)
        print("[VERIFY] ⚠️  WARNING: Proof uses deprecated HMAC signature (insecure)")
        print("[VERIFY] ⚠️  HMAC proofs can be forged - do not trust for authenticity")
        print("[VERIFY] ⚠️  Please regenerate proof with server-side ED25519 signing")
        safe_flush()
        # Return False - we don't support HMAC verification anymore (insecure)
        return False
    else:
        print(f"[VERIFY] ✗ Unknown signature version: {signature_version}")
        safe_flush()
        return False


def _verify_ed25519_signature(proof_data: Dict[str, Any], signature_b64: str) -> bool:
    """
    Verify ED25519 signature using embedded public key.
    
    Args:
        proof_data: Proof data dictionary
        signature_b64: Base64-encoded ED25519 signature
        
    Returns:
        bool: True if signature valid
    """
    try:
        # Import pure Python ED25519 verification
        from . import ed25519_pure
        
        # Prepare canonical message (same as server)
        canonical_data = {
            "version": proof_data.get("version"),
            "session_id": proof_data.get("session_id"),
            "events_hash": proof_data.get("events_hash"),
            "file_hash": proof_data.get("file_hash"),
            "classification": proof_data.get("classification"),
            "event_summary": {
                "total_events": proof_data.get("event_summary", {}).get("total_events"),
                "stroke_count": proof_data.get("event_summary", {}).get("stroke_count"),
                "layer_count": proof_data.get("event_summary", {}).get("layer_count"),
                "import_count": proof_data.get("event_summary", {}).get("import_count")
            },
            "metadata": {
                "ai_tools_used": proof_data.get("metadata", {}).get("ai_tools_used"),
                "ai_tools_list": proof_data.get("metadata", {}).get("ai_tools_list")
            },
            "signature_version": "ed25519-v1"
        }
        
        # Serialize to JSON (deterministic, same as server)
        message = json.dumps(canonical_data, sort_keys=True, separators=(',', ':')).encode('utf-8')
        
        print(f"[VERIFY] Verifying ED25519 signature...")
        print(f"[VERIFY]   Message size: {len(message)} bytes")
        print(f"[VERIFY]   Signature: {signature_b64[:20]}...")
        print(f"[VERIFY-DEBUG] First 100 chars: {message[:100]}")
        print(f"[VERIFY-DEBUG] Last 50 chars: {message[-50:]}")
        
        # Verify with public key (pure Python)
        is_valid = ed25519_pure.verify_pem(message, signature_b64, ED25519_PUBLIC_KEY_PEM)
        
        if is_valid:
            print(f"[VERIFY] ✅ ED25519 signature VALID - proof is authentic")
        else:
            print(f"[VERIFY] ❌ ED25519 signature INVALID - proof tampered or forged")
        
        safe_flush()
        return is_valid
        
    except Exception as e:
        print(f"[VERIFY] ✗ ED25519 verification error: {e}")
        import traceback
        print(f"[VERIFY] Traceback:\n{traceback.format_exc()}")
        safe_flush()
        return False


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
        safe_flush()
    
    def export_json(self) -> str:
        """
        Export proof as JSON string.
        
        Returns:
            JSON string representation of the proof
        """
        json_str = json.dumps(self.data, indent=2)
        print(f"[FLOW-4b] 📤 Proof exported as JSON ({len(json_str)} bytes)")
        import sys
        safe_flush()
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
    CHM Session - tracks drawing events and generates verification proofs.
    
    Captures all creative actions (strokes, layers, imports) and builds
    a timestamped proof of human-made artwork.
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
            "implementation": "python"
        }
        self.finalized = False
        
        # BUG#008 FIX: Track drawing time (time user is actively drawing, excludes AFK)
        self._drawing_time_secs = 0  # Accumulated drawing time in seconds
        
        # FIX: Initialize layer count to 1 (default layer always exists)
        self._layer_count = 1
    
    def set_metadata(self, **kwargs):
        """
        Set session metadata.
        
        Args:
            **kwargs: Metadata key-value pairs
        """
        self.metadata.update(kwargs)
    
    def get_metadata(self):
        """
        Get session metadata (compatibility with Rust API).
        
        Returns:
            dict: Session metadata
        """
        return self.metadata.copy()
        
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
    
    def record_undo_redo(self, action: str):
        """
        Record an undo/redo event (indicates human behavior).
        
        Args:
            action: Type of action ("undo" or "redo")
        """
        if self.finalized:
            raise RuntimeError("Cannot record events on finalized session")
        
        timestamp = datetime.utcnow().timestamp()
        
        event = {
            "type": "undo_redo",
            "action": action,
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
    
    @property
    def duration_secs(self) -> int:
        """Get session duration in seconds (compatibility with Rust API)"""
        duration = (datetime.utcnow() - self.start_time).total_seconds()
        return int(duration)
    
    @property
    def drawing_time_secs(self) -> int:
        """
        Get drawing time in seconds (time actively drawing, excludes AFK).
        BUG#008 FIX: Compatibility with Rust API.
        """
        return self._drawing_time_secs
    
    def add_drawing_time(self, seconds: int):
        """
        Add drawing time (called when user is actively drawing).
        BUG#008 FIX: Compatibility with Rust API.
        
        Args:
            seconds: Number of seconds to add to drawing time
        """
        self._drawing_time_secs += seconds
    
    def set_drawing_time(self, seconds: int):
        """
        Set drawing time (for session restoration).
        BUG#008 FIX: Compatibility with Rust API.
        
        Args:
            seconds: Drawing time in seconds
        """
        self._drawing_time_secs = seconds
    
    @property
    def is_finalized(self) -> bool:
        """Check if session is finalized (compatibility with Rust API)"""
        return self.finalized
    
    @property
    def public_key(self) -> str:
        """Get public key (returns placeholder for MVP)"""
        # Cryptographic signing will be added in future version
        return "mvp-placeholder-key"
    
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
    
    # NOTE: mark_as_traced() removed Jan 3, 2026 - tracing classification no longer used
    
    def mark_ai_assisted(self, tool_name: str = "Unknown"):
        """
        Mark session as AI-assisted.
        
        Args:
            tool_name: Name of AI tool used
        """
        if self.finalized:
            raise RuntimeError("Cannot mark finalized session as AI-assisted")
        
        self.metadata["ai_tools_used"] = True
        ai_tools = self.metadata.get("ai_tools_list", [])
        if tool_name not in ai_tools:
            ai_tools.append(tool_name)
        self.metadata["ai_tools_list"] = ai_tools
        print(f"[AI-ASSISTED] 🤖 Session marked as AI-Assisted (tool: {tool_name})")
    
    def finalize(self, artwork_path: Optional[str] = None, doc=None, doc_key: Optional[str] = None, import_tracker=None) -> 'CHMProof':
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
        safe_flush()
        
        self.finalized = True
        end_time = datetime.utcnow()
        duration = (end_time - self.start_time).total_seconds()
        
        # Count event types
        stroke_count = sum(1 for e in self.events if e.get("type") == "stroke")
        # Use tracked layer count (initialized to 1 for default layer, incremented on layer_added events)
        layer_count = self._layer_count
        import_count = sum(1 for e in self.events if e.get("type") == "import")
        # Only count undo operations (not redo) - stronger indicator of human creative process
        undo_count = sum(1 for e in self.events if e.get("type") == "undo_redo" and e.get("action") == "undo")
        
        print(f"[FLOW-3b] 📊 Event summary: {stroke_count} strokes, {layer_count} layers, {import_count} imports, {undo_count} undos")
        safe_flush()
        
        # Generate event hash
        events_json = json.dumps(self.events, sort_keys=True)
        events_hash = hashlib.sha256(events_json.encode()).hexdigest()
        
        print(f"[FLOW-3c] 🔑 Events hash: {events_hash[:16]}...")
        safe_flush()
        
        # File hash computation if artwork path provided
        file_hash = None
        
        if artwork_path and os.path.exists(artwork_path):
            print(f"[FLOW-3c-HASH] 🖼️ Computing file hash for: {artwork_path}")
            safe_flush()
            
            try:
                # File hash (SHA-256 of exact bytes) - sufficient for duplicate detection
                with open(artwork_path, 'rb') as f:
                    artwork_bytes = f.read()
                    file_hash = hashlib.sha256(artwork_bytes).hexdigest()
                    print(f"[FLOW-3c-HASH] ✓ File hash (SHA-256): {file_hash[:16]}...")
                    safe_flush()
                    
            except Exception as e:
                print(f"[FLOW-3c-HASH] ⚠️ Failed to compute file hash: {e}")
                safe_flush()
        else:
            print(f"[FLOW-3c-DUAL] ℹ️ No artwork path provided, using placeholder hashes")
            safe_flush()
        
        # BUG#005 FIX: Pass doc_key instead of doc_id
        # Classify session (pass import tracker for MixedMedia check)
        classification = self._classify(doc=doc, doc_key=doc_key, import_tracker=import_tracker)
        
        print(f"[FLOW-3d] 🏷️ Classification: {classification}")
        safe_flush()
        
        # Create proof summary
        proof_data = {
            "version": "1.0",
            "session_id": self.session_id,
            "document_id": self.document_id,
            "start_time": self.start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration_seconds": round(duration),
            "drawing_time_secs": int(self.drawing_time_secs),  # BUG#008 FIX: Include drawing time in proof
            "event_summary": {
                "total_events": len(self.events),
                "stroke_count": stroke_count,
                "layer_count": layer_count,
                "import_count": import_count,
                "undo_count": undo_count,
                "session_duration_secs": int(duration),  # Add for UI display
                "drawing_time_secs": int(self.drawing_time_secs)  # BUG#008 FIX: Also in event_summary for UI
            },
            "events_hash": events_hash,
            "file_hash": file_hash if file_hash else "placeholder_no_artwork_provided",
            "classification": classification,
            "import_count": import_count,  # Track as separate metric (not part of classification)
            "metadata": self.metadata
        }
        
        # TAMPER RESISTANCE: Server-side ED25519 signature + GitHub timestamp
        print(f"[FLOW-3f] 🔐 Requesting server-side ED25519 signature + GitHub timestamp...")
        safe_flush()
        
        # BUG-015 FIX: Use server-side signing (private key never exposed)
        # This also creates GitHub timestamp in same API call (DRY!)
        sign_result = _compute_session_signature_via_server(proof_data)
        
        if sign_result and sign_result.get('signature'):
            # Add signature to proof data
            proof_data["signature"] = sign_result['signature']
            proof_data["signature_version"] = sign_result.get('signature_version', 'ed25519-v1')
            print(f"[FLOW-3f] ✓ Server signed proof with ED25519")
            safe_flush()
            
            # GitHub timestamp included in server response (if successful)
            if sign_result.get('github'):
                github_timestamp = sign_result['github']
                print(f"[FLOW-3f] ✓ GitHub timestamp included: {github_timestamp.get('url')}")
                safe_flush()
                
                # Add timestamps section to proof (includes GitHub + local will be added later)
                proof_data["timestamps"] = {
                    "github": github_timestamp,
                    "chm_log": None  # Will be added by timestamp_service after return
                }
            else:
                print(f"[FLOW-3f] ⚠️  No GitHub timestamp (server-side error, non-fatal)")
                safe_flush()
                
        else:
            print(f"[FLOW-3f] ❌ Server signing failed!")
            print(f"[FLOW-3f] ❌ Cannot generate proof without signature")
            safe_flush()
            raise RuntimeError("Server-side signing failed - proof cannot be created without valid signature")
        
        print(f"[FLOW-3e] ✅ Proof data created (signed + timestamped), wrapping in CHMProof object")
        safe_flush()
        
        return CHMProof(proof_data)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize session to JSON-safe dictionary.
        
        Converts all properties to JSON-serializable types:
        - datetime objects -> ISO format strings
        - Ensures all values are JSON-safe primitives
        
        Returns:
            Dict with JSON-safe session data
        """
        return {
            'session_id': str(self.id),
            'event_count': int(self.event_count),
            'start_time': self.start_time.isoformat() + 'Z',  # ISO format with UTC marker
            'duration_secs': int(self.duration_secs),
            'drawing_time_secs': int(self.drawing_time_secs),  # BUG#008 FIX: Include drawing time
            'layer_count': int(self._layer_count),  # FIX: Include layer count
            'is_finalized': bool(self.is_finalized),
            'public_key': str(self.public_key),
            'metadata': self.get_metadata(),
            'events': self.events  # Include events for full session restoration
        }
    
    def create_snapshot(self) -> 'CHMSession':
        """
        Create a deep copy of this session for proof generation.
        
        This allows generating proofs (which require finalization)
        without destroying the active session that's still recording events.
        
        Returns:
            New CHMSession with same data but different identity
        """
        import copy
        
        snapshot = CHMSession(self.document_id)
        snapshot.id = self.id  # Keep same ID for continuity
        snapshot.session_id = self.session_id
        snapshot.start_time = self.start_time
        snapshot.events = copy.deepcopy(self.events)  # Deep copy of events
        snapshot.metadata = self.metadata.copy()
        snapshot.finalized = False  # Snapshot starts unfinalized
        snapshot._drawing_time_secs = self._drawing_time_secs  # BUG#008 FIX: Copy drawing time
        snapshot._layer_count = self._layer_count  # FIX: Copy layer count
        
        return snapshot
    
    def _classify(self, doc=None, doc_key: Optional[str] = None, import_tracker=None) -> str:
        """
        Classify the session based on events and metadata.
        
        Classification Logic (Updated Jan 3, 2026):
        - HumanMade: Pure manual work, reference imports ALLOWED
        - MixedMedia: Any non-reference image imports (STICKY - even if deleted)
        - AI-Assisted: AI tools detected in metadata
        
        Note: Tracing classification removed - was too complex and inaccurate.
        
        Args:
            doc: Krita document (optional, for future use)
            doc_key: Document key from session manager (optional, for MixedMedia detection)
            import_tracker: ImportTracker instance (optional, for MixedMedia detection)
        
        Returns:
            Classification string
        """
        print(f"[CLASSIFY-BFROS] ========================================")
        print(f"[CLASSIFY-BFROS] _classify() called")
        print(f"[CLASSIFY-BFROS]   doc_key: {doc_key}")
        print(f"[CLASSIFY-BFROS]   import_tracker: {import_tracker}")
        print(f"[CLASSIFY-BFROS]   has import_tracker: {import_tracker is not None}")
        print(f"[CLASSIFY-BFROS]   metadata: {self.metadata}")
        
        # Priority 1: Check for AI tools in metadata
        ai_tools_used = self.metadata.get("ai_tools_used", False)
        ai_tools_list = self.metadata.get("ai_tools_list", [])
        print(f"[CLASSIFY-BFROS]   ai_tools_used: {ai_tools_used}")
        print(f"[CLASSIFY-BFROS]   ai_tools_list: {ai_tools_list}")
        if ai_tools_used:
            print(f"[CLASSIFY-BFROS] Result: AI-Assisted")
            print(f"[CLASSIFY-BFROS] ========================================")
            return "AI-Assisted"
        
        # Priority 2: Check for image imports (STICKY - MixedMedia)
        # Any import registered = Mixed Media (persists even if deleted)
        if import_tracker and doc_key:
            print(f"[CLASSIFY-BFROS]   Checking import_tracker.has_mixed_media({doc_key})...")
            has_mixed = import_tracker.has_mixed_media(doc_key)
            print(f"[CLASSIFY-BFROS]   has_mixed_media result: {has_mixed}")
            if has_mixed:
                print(f"[CLASSIFY-BFROS] Result: MixedMedia")
                print(f"[CLASSIFY-BFROS] ========================================")
                return "MixedMedia"
        else:
            print(f"[CLASSIFY-BFROS]   Skipping import check (import_tracker={import_tracker}, doc_key={doc_key})")
        
        # Default: HumanMade
        # Reference imports are ALLOWED and don't affect this classification
        print(f"[CLASSIFY-BFROS] Result: HumanMade (default)")
        print(f"[CLASSIFY-BFROS] ========================================")
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


"""
C2PA Manifest Builder for CHM

Maps CHM SessionProof data to C2PA Content Credentials.
Implements privacy-preserving assertions (aggregate data only).

Architecture:
- Pure Python implementation (no Rust dependencies)
- Uses c2pa-python library (official CAI library)
- Fallback to custom PNG embedder if macOS signing issues occur
- Reads SessionProof JSON from existing Rust core
- No changes to Rust code required

Privacy Model:
- Aggregated data only (counts, durations, classification)
- No stroke coordinates, layer names, or absolute timestamps
- Optional detailed mode (opt-in for full provenance)
"""

import json
import os
from typing import Optional, Dict, List, Any
from datetime import datetime

# Global debug flag
DEBUG_LOG = True

class CHMtoC2PABuilder:
    """Build C2PA manifests from CHM SessionProof data"""
    
    def __init__(self, debug_log: bool = True):
        self.DEBUG_LOG = debug_log
        self.c2pa_available = False
        self.use_fallback_png = True  # Default to fallback (c2pa-python has macOS issues)
        
        # Try to import c2pa-python (likely to fail on macOS Krita)
        try:
            from c2pa import Builder
            self.Builder = Builder
            self.c2pa_available = True
            self.use_fallback_png = False
            if self.DEBUG_LOG:
                print("[C2PA] ✅ c2pa-python library available")
        except (ImportError, RuntimeError) as e:
            # Expected on macOS - c2pa-python requires native libs not compatible with Krita
            if self.DEBUG_LOG:
                print(f"[C2PA] ℹ️  c2pa-python not available (expected on macOS): {type(e).__name__}")
                print("[C2PA] → Using fallback PNG/JPEG embedder (works without native libs)")
            self.use_fallback_png = True
    
    def generate_manifest(
        self,
        session_proof_json: str,
        cert_path: Optional[str] = None,
        key_path: Optional[str] = None,
        privacy_mode: str = "lite"  # "lite" or "full"
    ) -> Optional[Dict[str, Any]]:
        """
        Generate C2PA manifest from CHM SessionProof.
        
        Args:
            session_proof_json: CHM proof from Rust (JSON string)
            cert_path: X.509 certificate (.pem) - optional for unsigned
            key_path: Private key (.pem) - optional for unsigned
            privacy_mode: "lite" (aggregated only) or "full" (detailed)
            
        Returns:
            Manifest dict, or None if generation fails
        """
        if self.DEBUG_LOG:
            print("[C2PA] Generating manifest from SessionProof...")
        
        try:
            # Parse SessionProof
            proof = json.loads(session_proof_json)
            
            if self.DEBUG_LOG:
                print(f"[C2PA] SessionProof keys: {list(proof.keys())}")
                print(f"[C2PA] Privacy mode: {privacy_mode}")
            
            # Build C2PA manifest structure
            manifest = self._build_manifest_structure(proof, privacy_mode)
            
            # Sign if credentials provided
            if cert_path and key_path:
                if self.DEBUG_LOG:
                    print("[C2PA] Signing manifest with provided certificate...")
                manifest = self._sign_manifest(manifest, cert_path, key_path)
            else:
                if self.DEBUG_LOG:
                    print("[C2PA] No certificate provided - manifest will be unsigned")
            
            if self.DEBUG_LOG:
                print(f"[C2PA] ✅ Manifest generated ({len(json.dumps(manifest))} bytes)")
            
            return manifest
            
        except Exception as e:
            if self.DEBUG_LOG:
                print(f"[C2PA] ❌ Error generating manifest: {e}")
                import traceback
                print(f"[C2PA] Traceback: {traceback.format_exc()}")
            return None
    
    def _build_manifest_structure(
        self, 
        proof: Dict[str, Any], 
        privacy_mode: str
    ) -> Dict[str, Any]:
        """
        Build C2PA manifest structure from CHM proof.
        
        Implements privacy-preserving mapping:
        - Lite mode: Aggregate counts only
        - Full mode: Detailed events (opt-in)
        """
        if self.DEBUG_LOG:
            print(f"[C2PA] Building manifest structure (mode: {privacy_mode})...")
        
        manifest = {
            "title": "Human-Made Artwork Provenance",
            "claim_generator": "CHM Krita Plugin v0.2.0",
            "assertions": []
        }
        
        # Add c2pa.actions assertion (edit history - aggregated)
        actions_assertion = self._create_actions_assertion(proof, privacy_mode)
        if actions_assertion:
            manifest["assertions"].append(actions_assertion)
        
        # Add c2pa.ai_generated assertion (AI detection)
        ai_assertion = self._create_ai_assertion(proof)
        if ai_assertion:
            manifest["assertions"].append(ai_assertion)
        
        # Add c2pa.ingredients assertion (reference images)
        ingredients_assertion = self._create_ingredients_assertion(proof)
        if ingredients_assertion:
            manifest["assertions"].append(ingredients_assertion)
        
        # Add CHM-specific metadata (non-standard, for compatibility)
        chm_metadata = self._create_chm_metadata(proof, privacy_mode)
        if chm_metadata:
            manifest["assertions"].append(chm_metadata)
        
        if self.DEBUG_LOG:
            print(f"[C2PA] Manifest structure built with {len(manifest['assertions'])} assertions")
        
        return manifest
    
    def _create_actions_assertion(
        self, 
        proof: Dict[str, Any], 
        privacy_mode: str
    ) -> Optional[Dict[str, Any]]:
        """
        Create c2pa.actions assertion (edit history).
        
        Privacy:
        - Lite: Aggregate counts and duration only
        - Full: Individual action types (no coordinates)
        """
        summary = proof.get('event_summary', {})
        
        if not summary:
            if self.DEBUG_LOG:
                print("[C2PA] ⚠️ No event_summary in proof, skipping actions assertion")
            return None
        
        # Basic actions (always included)
        actions = [
            {
                "action": "c2pa.created",
                "when": "session_start",  # Relative, not absolute timestamp
                "softwareAgent": f"Krita + CHM v0.2.0"
            }
        ]
        
        # Aggregated edit action
        stroke_count = summary.get('stroke_count', 0)
        layer_count = summary.get('layer_count', 0)
        duration_secs = summary.get('session_duration_secs', 0)
        
        classification = proof.get('classification', 'Unknown')
        digital_source_type = (
            "trainedAlgorithmicMedia" if classification in ["AIAssisted", "MixedMedia"]
            else "compositeCapture"
        )
        
        actions.append({
            "action": "c2pa.edited",
            "digitalSourceType": digital_source_type,
            "parameters": {
                "description": f"{stroke_count} strokes, {layer_count} layers, {duration_secs}s active time"
            }
        })
        
        # Full mode: Add action type breakdown (still no coordinates)
        if privacy_mode == "full":
            if self.DEBUG_LOG:
                print("[C2PA] Privacy mode=full: Adding detailed action breakdown")
            
            # Add counts by event type
            actions.append({
                "action": "c2pa.edited",
                "parameters": {
                    "stroke_count": stroke_count,
                    "layer_operations": summary.get('layer_operations_count', 0),
                    "imports": summary.get('imports_count', 0),
                    "undo_redo": summary.get('undo_redo_count', 0)
                }
            })
        
        return {
            "label": "c2pa.actions",
            "data": {
                "actions": actions
            }
        }
    
    def _create_ai_assertion(self, proof: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Create c2pa.ai_generated assertion (AI detection).
        
        Maps CHM classification to C2PA AI flag.
        """
        classification = proof.get('classification', 'Unknown')
        confidence = proof.get('confidence', 0.0)
        
        is_ai = classification in ["AIAssisted", "MixedMedia"]
        
        # Get AI plugins used (if available)
        summary = proof.get('event_summary', {})
        plugins_used = summary.get('plugins_used', [])
        
        return {
            "label": "c2pa.ai_generated",
            "data": {
                "isAIGenerated": is_ai,
                "tool": plugins_used if is_ai else [],
                "metadata": {
                    "chm_classification": classification,
                    "confidence": confidence
                }
            }
        }
    
    def _create_ingredients_assertion(
        self, 
        proof: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Create c2pa.ingredients assertion (reference images).
        
        Privacy: Only include hashes, not file paths or contents.
        
        Note: Current SessionProof only has imports_count, not individual hashes.
        This is a placeholder for future enhancement.
        """
        summary = proof.get('event_summary', {})
        imports_count = summary.get('imports_count', 0)
        
        if imports_count == 0:
            # No imports, skip assertion
            return None
        
        # Placeholder: Future versions should track import hashes in SessionProof
        return {
            "label": "c2pa.ingredients",
            "data": {
                "ingredients": [],
                "metadata": {
                    "chm_note": f"{imports_count} reference image(s) imported (hashes not tracked yet)"
                }
            }
        }
    
    def _create_chm_metadata(
        self, 
        proof: Dict[str, Any], 
        privacy_mode: str
    ) -> Dict[str, Any]:
        """
        Create CHM-specific metadata assertion (non-standard).
        
        This allows CHM to embed additional context not covered by C2PA spec.
        """
        metadata = {
            "session_id": proof.get('session_id', 'unknown'),
            "classification": proof.get('classification', 'Unknown'),
            "confidence": proof.get('confidence', 0.0),
            "privacy_mode": privacy_mode,
            "chm_version": "0.2.0"
        }
        
        # Include public key for verification
        if 'public_key' in proof:
            metadata['public_key'] = proof['public_key']
        
        return {
            "label": "chm.metadata",
            "data": metadata
        }
    
    def _sign_manifest(
        self, 
        manifest: Dict[str, Any], 
        cert_path: str, 
        key_path: str
    ) -> Dict[str, Any]:
        """
        Sign C2PA manifest with X.509 certificate.
        
        Note: This requires c2pa-python to be available.
        If not available, returns unsigned manifest.
        """
        if not self.c2pa_available:
            if self.DEBUG_LOG:
                print("[C2PA] ⚠️ c2pa-python not available, cannot sign manifest")
            return manifest
        
        try:
            # Read certificate and key
            with open(cert_path, 'rb') as f:
                cert_pem = f.read()
            with open(key_path, 'rb') as f:
                key_pem = f.read()
            
            # TODO: Implement actual signing with c2pa-python Builder
            # This requires deeper integration with c2pa-python API
            # For now, return unsigned manifest with note
            
            manifest['signing'] = {
                'certificate': cert_path,
                'status': 'unsigned (signing not yet implemented)'
            }
            
            if self.DEBUG_LOG:
                print("[C2PA] ⚠️ Manifest signing not yet implemented")
            
            return manifest
            
        except Exception as e:
            if self.DEBUG_LOG:
                print(f"[C2PA] ❌ Signing failed: {e}")
            return manifest
    
    def embed_in_image(
        self,
        image_path: str,
        manifest: Dict[str, Any],
        format: Optional[str] = None
    ) -> bool:
        """
        Embed C2PA manifest into image file.
        
        Supports:
        - PNG (via c2pa-python or fallback custom embedder)
        - JPEG (via c2pa-python)
        
        Args:
            image_path: Path to image file
            manifest: C2PA manifest dict
            format: Image format (auto-detected if None)
            
        Returns:
            True if embedding successful, False otherwise
        """
        # Auto-detect format
        if format is None:
            format = image_path.split('.')[-1].upper()
        
        if self.DEBUG_LOG:
            print(f"[C2PA] Embedding manifest in {format} image: {image_path}")
        
        try:
            if format == 'PNG':
                return self._embed_png(image_path, manifest)
            elif format in ['JPG', 'JPEG']:
                return self._embed_jpeg(image_path, manifest)
            else:
                if self.DEBUG_LOG:
                    print(f"[C2PA] ❌ Unsupported format: {format}")
                return False
                
        except Exception as e:
            if self.DEBUG_LOG:
                print(f"[C2PA] ❌ Embedding failed: {e}")
                import traceback
                print(f"[C2PA] Traceback: {traceback.format_exc()}")
            return False
    
    def _embed_png(self, image_path: str, manifest: Dict[str, Any]) -> bool:
        """Embed C2PA manifest in PNG file"""
        
        if self.c2pa_available and not self.use_fallback_png:
            # Use c2pa-python native embedding
            if self.DEBUG_LOG:
                print("[C2PA] Using c2pa-python for PNG embedding...")
            
            # TODO: Implement c2pa-python PNG embedding
            # This requires deeper integration with c2pa-python API
            
            if self.DEBUG_LOG:
                print("[C2PA] ⚠️ c2pa-python PNG embedding not yet implemented")
            return False
        else:
            # Use fallback custom PNG embedder
            if self.DEBUG_LOG:
                print("[C2PA] Using fallback custom PNG embedder...")
            
            from .png_c2pa_embedder import embed_c2pa_manifest_in_png
            return embed_c2pa_manifest_in_png(image_path, manifest)
    
    def _embed_jpeg(self, image_path: str, manifest: Dict[str, Any]) -> bool:
        """Embed C2PA manifest in JPEG file"""
        
        if self.c2pa_available and not self.use_fallback_png:
            # Use c2pa-python native embedding
            if self.DEBUG_LOG:
                print("[C2PA] Using c2pa-python for JPEG embedding...")
            
            # TODO: Implement c2pa-python JPEG embedding
            # This requires deeper integration with c2pa-python API
            
            if self.DEBUG_LOG:
                print("[C2PA] ⚠️ c2pa-python JPEG embedding not yet implemented")
            return False
        else:
            # Use fallback JPEG embedder
            if self.DEBUG_LOG:
                print("[C2PA] Using fallback JPEG embedder...")
            
            from .png_c2pa_embedder import embed_c2pa_manifest_in_jpeg
            return embed_c2pa_manifest_in_jpeg(image_path, manifest)


def run_privacy_audit(manifest: Dict[str, Any]) -> bool:
    """
    Audit C2PA manifest for privacy leaks.
    
    Checks for forbidden data:
    - Stroke coordinates
    - Layer names/IDs
    - Absolute timestamps
    - File paths
    - Individual event data
    
    Returns:
        True if audit passed (no leaks), False if leaks detected
    """
    if DEBUG_LOG:
        print("[C2PA-AUDIT] Running privacy audit on manifest...")
    
    manifest_str = json.dumps(manifest).lower()
    
    # Forbidden patterns that indicate privacy leaks
    forbidden = [
        'stroke_x', 'stroke_y', 'coordinate', 'position',  # Coordinates
        'pressure', 'tilt', 'rotation',  # Stylus data
        'individual_timestamp', 'event_timestamp',  # Individual event times
        'layer_name', 'layer_id', 'layer_uuid',  # Layer identifiers
        'file_path', 'directory', '/users/', '/home/',  # File paths
        '202', '2025-', '2024-',  # Absolute timestamps (year patterns)
    ]
    
    leaks = []
    for pattern in forbidden:
        if pattern in manifest_str:
            leaks.append(pattern)
    
    if leaks:
        if DEBUG_LOG:
            print(f"[C2PA-AUDIT] ❌ PRIVACY LEAK DETECTED: {leaks}")
        return False
    else:
        if DEBUG_LOG:
            print("[C2PA-AUDIT] ✅ Privacy audit passed - no leaks detected")
        return True


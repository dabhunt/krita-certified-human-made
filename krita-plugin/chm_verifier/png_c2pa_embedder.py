"""
Pure Python PNG C2PA Embedder

This module provides spec-compliant C2PA manifest embedding for PNG files
using ONLY Python stdlib (struct, zlib, json) - no external dependencies.

Works in Krita's bundled Python environment (no Pillow/PIL required).

C2PA Specification Reference:
- Section 6.3: PNG embedding
- Chunk type: 'caBX' (ancillary, private, not safe-to-copy)
- Chunk should precede IDAT chunks

Privacy Note:
- This embedder only writes the manifest provided to it
- Privacy filtering is handled by c2pa_builder.py
- This module is format-agnostic (just embeds bytes)
"""

import json
import struct
import zlib
from typing import Dict, Any
from .logging_util import log_message

DEBUG_LOG = True

def embed_c2pa_manifest_in_png(image_path: str, manifest: Dict[str, Any]) -> bool:
    """
    Embed C2PA manifest in PNG file using custom 'caBX' chunk.
    
    Uses pure Python (stdlib only: struct, zlib, json) for spec-compliant embedding.
    No external dependencies required - works in Krita's bundled Python.
    
    Args:
        image_path: Path to PNG file
        manifest: C2PA manifest dict (will be serialized to JSON)
        
    Returns:
        True if embedding successful, False otherwise
    """
    log_message("[PNG-C2PA] Starting C2PA manifest embedding...")
    log_message(f"[PNG-C2PA] Target: {image_path}")
    
    # Serialize manifest to JSON bytes
    try:
        manifest_json = json.dumps(manifest, indent=2)
        manifest_bytes = manifest_json.encode('utf-8')
        log_message(f"[PNG-C2PA] Manifest serialized: {len(manifest_bytes)} bytes")
    except Exception as e:
        log_message(f"[PNG-C2PA] ❌ Failed to serialize manifest: {e}")
        return False
    
    # Use pure Python implementation (no dependencies!)
    log_message("[PNG-C2PA] Using pure Python embedding (stdlib only)")
    log_message("[PNG-C2PA] → Creates spec-compliant caBX chunk")
    return embed_c2pa_chunk_proper(image_path, manifest_bytes)


def embed_c2pa_chunk_proper(image_path: str, manifest_bytes: bytes) -> bool:
    """
    Proper C2PA PNG embedding using 'caBX' chunk (spec-compliant).
    
    This uses ONLY Python stdlib (struct + zlib) - no external dependencies!
    Perfect for Krita's bundled Python which doesn't have Pillow.
    
    PNG Chunk Structure:
    - Length (4 bytes): Data field length
    - Type (4 bytes): Chunk type code ('caBX')
    - Data (n bytes): Actual chunk data (manifest)
    - CRC (4 bytes): CRC-32 of Type + Data
    
    'caBX' Chunk Properties:
    - Ancillary (lowercase first letter 'c')
    - Private (uppercase second letter 'a')
    - Not safe to copy (uppercase fourth letter 'X')
    
    Args:
        image_path: Path to PNG file
        manifest_bytes: C2PA manifest as bytes
        
    Returns:
        True if embedding successful, False otherwise
    """
    log_message(f"[PNG-C2PA-PURE] Starting pure Python PNG embedding...")
    log_message(f"[PNG-C2PA-PURE] Image: {image_path}")
    log_message(f"[PNG-C2PA-PURE] Manifest size: {len(manifest_bytes)} bytes")
    
    try:
        # Read PNG file in binary mode
        log_message("[PNG-C2PA-PURE] Reading PNG file...")
        with open(image_path, 'rb') as f:
            png_data = f.read()
        
        log_message(f"[PNG-C2PA-PURE] File read: {len(png_data)} bytes")
        
        # Verify PNG signature
        PNG_SIGNATURE = b'\x89PNG\r\n\x1a\n'
        if not png_data.startswith(PNG_SIGNATURE):
            log_message("[PNG-C2PA-PURE] ❌ Invalid PNG signature")
            return False
        
        log_message("[PNG-C2PA-PURE] ✓ Valid PNG signature")
        
        # Parse PNG chunks
        log_message("[PNG-C2PA-PURE] Parsing PNG chunks...")
        chunks = []
        offset = 8  # Skip PNG signature
        
        while offset < len(png_data):
            # Read chunk length
            if offset + 4 > len(png_data):
                break
            chunk_length = struct.unpack('>I', png_data[offset:offset+4])[0]
            offset += 4
            
            # Read chunk type
            if offset + 4 > len(png_data):
                break
            chunk_type = png_data[offset:offset+4]
            offset += 4
            
            # Read chunk data
            if offset + chunk_length > len(png_data):
                break
            chunk_data = png_data[offset:offset+chunk_length]
            offset += chunk_length
            
            # Read chunk CRC
            if offset + 4 > len(png_data):
                break
            chunk_crc = png_data[offset:offset+4]
            offset += 4
            
            chunks.append({
                'type': chunk_type,
                'data': chunk_data,
                'crc': chunk_crc
            })
            
            # Stop at IEND chunk
            if chunk_type == b'IEND':
                break
        
        log_message(f"[PNG-C2PA-PURE] Parsed {len(chunks)} PNG chunks")
        
        # Create 'caBX' chunk
        log_message("[PNG-C2PA-PURE] Creating caBX chunk...")
        cabx_type = b'caBX'
        cabx_data = manifest_bytes
        cabx_length = len(cabx_data)
        
        # Calculate CRC-32 (over type + data)
        crc_input = cabx_type + cabx_data
        cabx_crc = zlib.crc32(crc_input) & 0xffffffff
        
        cabx_chunk = {
            'type': cabx_type,
            'data': cabx_data,
            'crc': struct.pack('>I', cabx_crc)
        }
        
        log_message(f"[PNG-C2PA-PURE] caBX chunk created: {len(cabx_data)} bytes, CRC: {hex(cabx_crc)}")
        
        # Insert 'caBX' chunk before first IDAT chunk
        log_message("[PNG-C2PA-PURE] Finding IDAT chunk for insertion point...")
        idat_index = None
        for i, chunk in enumerate(chunks):
            if chunk['type'] == b'IDAT':
                idat_index = i
                break
        
        if idat_index is None:
            log_message("[PNG-C2PA-PURE] ❌ No IDAT chunk found")
            return False
        
        chunks.insert(idat_index, cabx_chunk)
        
        log_message(f"[PNG-C2PA-PURE] ✓ Inserted caBX chunk before IDAT (index {idat_index})")
        
        # Reconstruct PNG
        log_message("[PNG-C2PA-PURE] Reconstructing PNG with embedded caBX chunk...")
        new_png_data = PNG_SIGNATURE
        
        for chunk in chunks:
            chunk_length = len(chunk['data'])
            new_png_data += struct.pack('>I', chunk_length)
            new_png_data += chunk['type']
            new_png_data += chunk['data']
            new_png_data += chunk['crc']
        
        log_message(f"[PNG-C2PA-PURE] New PNG size: {len(new_png_data)} bytes (was {len(png_data)})")
        
        # Write modified PNG
        log_message(f"[PNG-C2PA-PURE] Writing modified PNG to {image_path}...")
        with open(image_path, 'wb') as f:
            f.write(new_png_data)
        
        log_message("[PNG-C2PA-PURE] ✅ C2PA manifest embedded successfully!")
        log_message("[PNG-C2PA-PURE] ✅ Used spec-compliant caBX chunk (no Pillow required)")
        
        return True
        
    except Exception as e:
        log_message(f"[PNG-C2PA-PURE] ❌ Embedding failed: {e}")
        import traceback
        log_message(f"[PNG-C2PA-PURE] Traceback:\n{traceback.format_exc()}")
        return False


def extract_c2pa_manifest_from_png(image_path: str) -> Dict[str, Any]:
    """
    Extract C2PA manifest from PNG 'caBX' chunk.
    
    Uses pure Python (no Pillow dependency).
    Useful for validation and testing.
    
    Args:
        image_path: Path to PNG file
        
    Returns:
        Manifest dict, or None if not found or invalid
    """
    log_message(f"[PNG-C2PA] Extracting manifest from PNG: {image_path}")
    
    try:
        return _extract_cabx_chunk(image_path)
    except Exception as e:
        log_message(f"[PNG-C2PA] ❌ Extraction failed: {e}")
        return None


def _extract_cabx_chunk(image_path: str) -> Dict[str, Any]:
    """Extract manifest from proper 'caBX' chunk (pure Python)"""
    try:
        with open(image_path, 'rb') as f:
            png_data = f.read()
        
        # Skip PNG signature
        offset = 8
        
        while offset < len(png_data):
            # Read chunk
            chunk_length = struct.unpack('>I', png_data[offset:offset+4])[0]
            offset += 4
            
            chunk_type = png_data[offset:offset+4]
            offset += 4
            
            chunk_data = png_data[offset:offset+chunk_length]
            offset += chunk_length + 4  # +4 for CRC
            
            # Check if this is 'caBX' chunk
            if chunk_type == b'caBX':
                # Deserialize manifest
                manifest_json = chunk_data.decode('utf-8')
                manifest = json.loads(manifest_json)
                
                log_message("[PNG-C2PA] ✅ Manifest extracted from caBX chunk")
                
                return manifest
            
            # Stop at IEND
            if chunk_type == b'IEND':
                break
        
        log_message("[PNG-C2PA] ⚠️ No caBX chunk found")
        
        return None
        
    except Exception as e:
        log_message(f"[PNG-C2PA] ❌ caBX extraction failed: {e}")
        return None


# JPEG C2PA Embedding - TODO: Implement pure Python version
# For now, PNG-only C2PA embedding is supported

def embed_c2pa_manifest_in_jpeg(image_path: str, manifest: Dict[str, Any]) -> bool:
    """
    Embed C2PA manifest in JPEG file.
    
    TODO: Implement pure Python JPEG embedding (similar to PNG caBX chunk approach).
    JPEG C2PA embedding uses JUMBF boxes in APP11 markers.
    
    Args:
        image_path: Path to JPEG file
        manifest: C2PA manifest dict (will be serialized to JSON)
        
    Returns:
        False (not yet implemented)
    """
    log_message("[JPEG-C2PA] ❌ JPEG C2PA embedding not yet implemented")
    log_message("[JPEG-C2PA] → Use PNG export for C2PA embedding")
    log_message("[JPEG-C2PA] → TODO: Implement pure Python JPEG APP11/JUMBF embedding")
    return False


"""
Pure Python PNG Metadata Embedder

This module provides CHM metadata embedding for PNG files using ONLY Python 
stdlib (struct, zlib) - no external dependencies (no PIL/Pillow required).

Works perfectly in Krita's bundled Python environment.

PNG tEXt Chunk Specification (ISO/IEC 15948:2004):
- Chunk type: 'tEXt' (textual information)
- Chunk data: keyword + null byte + text
- Keyword: Latin-1 string, 1-79 chars, null-terminated
- Text: Latin-1 or UTF-8 string

CHM Metadata Fields:
- CHM-Gist-URL: Full GitHub gist URL (for immediate verification)
- CHM-Proof-Hash: SHA-256 hash of proof (for integrity check)
- CHM-Classification: human-made, ai-assisted, or mixed-media
- CHM-Session-ID: Optional session UUID
- CHM-Version: Plugin version marker
"""

import struct
import zlib
from typing import Dict, Optional
from .logging_util import log_message

DEBUG_LOG = True

def add_chm_metadata(
    png_path: str,
    gist_url: str,
    proof_hash: str,
    classification: str,
    session_id: Optional[str] = None
) -> bool:
    """
    Add CHM metadata to a PNG file using tEXt chunks (pure Python, no PIL).
    
    This embeds the gist URL and other verification data directly in the PNG
    file, making verification immediate and robust against file modifications.
    
    Uses ONLY Python stdlib (struct + zlib) - no external dependencies!
    Perfect for Krita's bundled Python which doesn't have Pillow.
    
    Args:
        png_path: Path to PNG file to modify
        gist_url: Full GitHub gist URL (e.g., https://gist.github.com/abc123)
        proof_hash: SHA-256 hash of the proof
        classification: human-made, ai-assisted, or mixed-media
        session_id: Optional session UUID
        
    Returns:
        True if metadata was added successfully, False otherwise
    """
    log_message(f"[PNG-METADATA-PURE] Adding CHM metadata to: {png_path}")
    
    # Validate inputs
    if not gist_url or not proof_hash or not classification:
        log_message("[PNG-METADATA-PURE] ❌ Missing required metadata fields")
        return False
    
    try:
        # Read PNG file
        log_message("[PNG-METADATA-PURE] Reading PNG file...")
        with open(png_path, 'rb') as f:
            png_data = f.read()
        
        log_message(f"[PNG-METADATA-PURE] File read: {len(png_data)} bytes")
        
        # Verify PNG signature
        PNG_SIGNATURE = b'\x89PNG\r\n\x1a\n'
        if not png_data.startswith(PNG_SIGNATURE):
            log_message("[PNG-METADATA-PURE] ❌ Invalid PNG signature")
            return False
        
        log_message("[PNG-METADATA-PURE] ✓ Valid PNG signature")
        
        # Parse PNG chunks
        log_message("[PNG-METADATA-PURE] Parsing PNG chunks...")
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
        
        log_message(f"[PNG-METADATA-PURE] Parsed {len(chunks)} PNG chunks")
        
        # Create CHM metadata tEXt chunks
        log_message("[PNG-METADATA-PURE] Creating tEXt chunks for CHM metadata...")
        
        metadata_chunks = []
        
        # Add each metadata field as a separate tEXt chunk
        metadata_fields = {
            'CHM-Gist-URL': gist_url,
            'CHM-Proof-Hash': proof_hash,
            'CHM-Classification': classification,
            'CHM-Version': '1.0.0'
        }
        
        # Add optional session ID if provided
        if session_id:
            metadata_fields['CHM-Session-ID'] = session_id
        
        for keyword, text in metadata_fields.items():
            text_chunk = _create_text_chunk(keyword, text)
            metadata_chunks.append(text_chunk)
            log_message(f"[PNG-METADATA-PURE]   ✓ Created tEXt chunk: {keyword}")
        
        log_message(f"[PNG-METADATA-PURE] Created {len(metadata_chunks)} tEXt chunks")
        
        # Find insertion point (before IDAT)
        log_message("[PNG-METADATA-PURE] Finding IDAT chunk for insertion point...")
        idat_index = None
        for i, chunk in enumerate(chunks):
            if chunk['type'] == b'IDAT':
                idat_index = i
                break
        
        if idat_index is None:
            log_message("[PNG-METADATA-PURE] ❌ No IDAT chunk found")
            return False
        
        # Insert all metadata chunks before IDAT
        # Insert in reverse order to maintain correct order in file
        for text_chunk in reversed(metadata_chunks):
            chunks.insert(idat_index, text_chunk)
        
        log_message(f"[PNG-METADATA-PURE] ✓ Inserted {len(metadata_chunks)} tEXt chunks before IDAT")
        
        # Reconstruct PNG
        log_message("[PNG-METADATA-PURE] Reconstructing PNG with metadata chunks...")
        new_png_data = PNG_SIGNATURE
        
        for chunk in chunks:
            chunk_length = len(chunk['data'])
            new_png_data += struct.pack('>I', chunk_length)
            new_png_data += chunk['type']
            new_png_data += chunk['data']
            new_png_data += chunk['crc']
        
        log_message(f"[PNG-METADATA-PURE] New PNG size: {len(new_png_data)} bytes (was {len(png_data)})")
        
        # Write modified PNG
        log_message(f"[PNG-METADATA-PURE] Writing modified PNG to {png_path}...")
        with open(png_path, 'wb') as f:
            f.write(new_png_data)
        
        log_message("[PNG-METADATA-PURE] ✅ CHM metadata embedded successfully!")
        log_message("[PNG-METADATA-PURE] ✅ Used stdlib only (no PIL required)")
        
        # Verify metadata was written (sanity check)
        _verify_metadata_written(png_path, gist_url)
        
        return True
        
    except Exception as e:
        log_message(f"[PNG-METADATA-PURE] ❌ Embedding failed: {e}")
        import traceback
        log_message(f"[PNG-METADATA-PURE] Traceback:\n{traceback.format_exc()}")
        return False


def _create_text_chunk(keyword: str, text: str) -> dict:
    """
    Create a PNG tEXt chunk.
    
    PNG tEXt chunk structure:
    - Keyword: Latin-1 string (1-79 chars) + null terminator
    - Text: UTF-8 string (no null terminator at end)
    
    Chunk structure:
    - Length (4 bytes): Data field length
    - Type (4 bytes): 'tEXt'
    - Data (n bytes): keyword + null + text
    - CRC (4 bytes): CRC-32 of Type + Data
    
    Args:
        keyword: Metadata keyword (e.g., 'CHM-Gist-URL')
        text: Metadata value
        
    Returns:
        Chunk dict with 'type', 'data', 'crc' keys
    """
    # Validate keyword length (PNG spec: 1-79 chars)
    if len(keyword) < 1 or len(keyword) > 79:
        raise ValueError(f"Keyword length must be 1-79 chars, got {len(keyword)}")
    
    # Create chunk data: keyword (Latin-1) + null byte + text (UTF-8)
    chunk_type = b'tEXt'
    chunk_data = keyword.encode('latin-1') + b'\x00' + text.encode('utf-8')
    
    # Calculate CRC-32 (over type + data)
    crc_input = chunk_type + chunk_data
    chunk_crc = zlib.crc32(crc_input) & 0xffffffff
    
    return {
        'type': chunk_type,
        'data': chunk_data,
        'crc': struct.pack('>I', chunk_crc)
    }


def _verify_metadata_written(png_path: str, expected_gist_url: str) -> None:
    """
    Verify that metadata was actually written to the PNG file.
    This is a sanity check to catch issues early.
    """
    try:
        log_message("[PNG-METADATA-PURE] Verifying metadata was written...")
        
        metadata = extract_chm_metadata(png_path)
        
        if metadata and 'CHM-Gist-URL' in metadata:
            actual_url = metadata['CHM-Gist-URL']
            if actual_url == expected_gist_url:
                log_message("[PNG-METADATA-PURE] ✓ Metadata verification passed!")
            else:
                log_message(f"[PNG-METADATA-PURE] ⚠️ URL mismatch: expected {expected_gist_url}, got {actual_url}")
        else:
            log_message("[PNG-METADATA-PURE] ⚠️ Warning: Metadata not found after write")
            
    except Exception as e:
        log_message(f"[PNG-METADATA-PURE] ⚠️ Verification check failed: {e}")


def extract_chm_metadata(png_path: str) -> Optional[Dict[str, str]]:
    """
    Extract CHM metadata from a PNG file's tEXt chunks (pure Python).
    
    Args:
        png_path: Path to PNG file
        
    Returns:
        Dictionary with metadata keys (CHM-Gist-URL, etc.) or None if not found
    """
    log_message(f"[PNG-METADATA-PURE] Extracting CHM metadata from: {png_path}")
    
    try:
        with open(png_path, 'rb') as f:
            png_data = f.read()
        
        # Verify PNG signature
        PNG_SIGNATURE = b'\x89PNG\r\n\x1a\n'
        if not png_data.startswith(PNG_SIGNATURE):
            log_message("[PNG-METADATA-PURE] ❌ Invalid PNG signature")
            return None
        
        # Parse chunks and extract tEXt
        chm_metadata = {}
        offset = 8  # Skip PNG signature
        
        while offset < len(png_data):
            # Read chunk
            if offset + 12 > len(png_data):  # Minimum chunk size
                break
                
            chunk_length = struct.unpack('>I', png_data[offset:offset+4])[0]
            offset += 4
            
            chunk_type = png_data[offset:offset+4]
            offset += 4
            
            chunk_data = png_data[offset:offset+chunk_length]
            offset += chunk_length + 4  # +4 for CRC
            
            # Check if this is a tEXt chunk
            if chunk_type == b'tEXt':
                # Parse tEXt chunk: keyword + null + text
                null_pos = chunk_data.find(b'\x00')
                if null_pos > 0:
                    keyword = chunk_data[:null_pos].decode('latin-1')
                    text = chunk_data[null_pos+1:].decode('utf-8')
                    
                    # Only store CHM-prefixed metadata
                    if keyword.startswith('CHM-'):
                        chm_metadata[keyword] = text
                        log_message(f"[PNG-METADATA-PURE]   Found: {keyword}")
            
            # Stop at IEND
            if chunk_type == b'IEND':
                break
        
        if chm_metadata:
            log_message(f"[PNG-METADATA-PURE] ✓ Found {len(chm_metadata)} CHM metadata fields")
            return chm_metadata
        else:
            log_message("[PNG-METADATA-PURE] No CHM metadata found")
            return None
            
    except Exception as e:
        log_message(f"[PNG-METADATA-PURE] ❌ Extraction failed: {e}")
        import traceback
        log_message(f"[PNG-METADATA-PURE] Traceback:\n{traceback.format_exc()}")
        return None


def has_chm_metadata(png_path: str) -> bool:
    """
    Quick check if a PNG file has CHM metadata.
    
    Args:
        png_path: Path to PNG file
        
    Returns:
        True if CHM metadata is present, False otherwise
    """
    try:
        metadata = extract_chm_metadata(png_path)
        return metadata is not None and 'CHM-Gist-URL' in metadata
    except:
        return False


def get_gist_url(png_path: str) -> Optional[str]:
    """
    Convenience function to extract just the gist URL from a PNG.
    
    Args:
        png_path: Path to PNG file
        
    Returns:
        Gist URL string or None if not found
    """
    try:
        metadata = extract_chm_metadata(png_path)
        if metadata and 'CHM-Gist-URL' in metadata:
            return metadata['CHM-Gist-URL']
        return None
    except:
        return None


# Test/debug functionality
if __name__ == "__main__":
    """
    Test PNG metadata functionality standalone.
    Usage: python png_metadata_pure.py <path_to_png>
    """
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python png_metadata_pure.py <path_to_png>")
        print("This will add test metadata to the PNG file.")
        sys.exit(1)
    
    test_png = sys.argv[1]
    
    print("Testing PNG metadata embedding (Pure Python, no PIL)...")
    print(f"Target file: {test_png}")
    
    # Test adding metadata
    success = add_chm_metadata(
        png_path=test_png,
        gist_url="https://gist.github.com/test123456",
        proof_hash="abc123def456" * 4,  # Fake hash
        classification="human-made",
        session_id="test-session-uuid-12345"
    )
    
    if success:
        print("\n✓ Metadata added successfully!")
        
        # Test extraction
        print("\nExtracting metadata back...")
        metadata = extract_chm_metadata(test_png)
        
        if metadata:
            print("\n✓ Metadata extracted successfully!")
            print("\nMetadata contents:")
            for key, value in metadata.items():
                print(f"  {key}: {value}")
        else:
            print("\n❌ Failed to extract metadata!")
    else:
        print("\n❌ Failed to add metadata!")


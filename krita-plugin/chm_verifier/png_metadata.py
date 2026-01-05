"""
PNG Metadata Utility - Embed CHM verification data in PNG files

This module provides functions to embed and extract CHM metadata in PNG files
using standard tEXt chunks. This makes verification robust against file 
modifications (opening/re-saving) and eliminates GitHub indexing delays.

Metadata Fields:
- CHM-Gist-URL: Full GitHub gist URL (for immediate verification)
- CHM-Proof-Hash: SHA-256 hash of proof (for integrity check)
- CHM-Classification: human-made, ai-assisted, or mixed-media

Implementation uses bundled PIL (Pillow) from vendor/ directory.
"""

import os
import sys
from typing import Dict, Optional

# Debug logging flag
DEBUG_LOG = True


def _debug_log(message: str) -> None:
    """Print debug message if DEBUG_LOG is enabled"""
    if DEBUG_LOG:
        print(f"[PNG-METADATA] {message}")


def add_chm_metadata(
    png_path: str,
    gist_url: str,
    proof_hash: str,
    classification: str,
    session_id: Optional[str] = None
) -> bool:
    """
    Add CHM metadata to a PNG file using tEXt chunks.
    
    This embeds the gist URL and other verification data directly in the PNG
    file, making verification immediate and robust against file modifications.
    
    Args:
        png_path: Path to PNG file to modify
        gist_url: Full GitHub gist URL (e.g., https://gist.github.com/abc123)
        proof_hash: SHA-256 hash of the proof
        classification: human-made, ai-assisted, or mixed-media
        session_id: Optional session UUID
        
    Returns:
        True if metadata was added successfully, False otherwise
        
    Raises:
        FileNotFoundError: If PNG file doesn't exist
        ValueError: If file is not a valid PNG
    """
    _debug_log(f"Adding CHM metadata to: {png_path}")
    
    # Validate inputs
    if not os.path.exists(png_path):
        raise FileNotFoundError(f"PNG file not found: {png_path}")
    
    if not gist_url or not proof_hash or not classification:
        raise ValueError("gist_url, proof_hash, and classification are required")
    
    try:
        # Import PIL from vendor directory
        from PIL import Image
        from PIL.PngImagePlugin import PngInfo
        
        _debug_log(f"Opening PNG file: {png_path}")
        
        # Open the PNG file
        img = Image.open(png_path)
        
        # Verify it's actually a PNG
        if img.format != 'PNG':
            raise ValueError(f"File is not a PNG (format: {img.format})")
        
        # Create metadata structure
        metadata = PngInfo()
        
        # Add CHM metadata fields
        metadata.add_text("CHM-Gist-URL", gist_url)
        metadata.add_text("CHM-Proof-Hash", proof_hash)
        metadata.add_text("CHM-Classification", classification)
        
        # Optional fields
        if session_id:
            metadata.add_text("CHM-Session-ID", session_id)
        
        # Add plugin version marker
        metadata.add_text("CHM-Version", "1.0.0")
        
        _debug_log(f"Metadata prepared:")
        _debug_log(f"  - Gist URL: {gist_url}")
        _debug_log(f"  - Proof Hash: {proof_hash[:16]}...")
        _debug_log(f"  - Classification: {classification}")
        
        # Save PNG with embedded metadata
        # Note: This overwrites the original file
        img.save(png_path, "PNG", pnginfo=metadata)
        
        _debug_log(f"✓ CHM metadata successfully embedded in PNG")
        
        # Verify metadata was written (sanity check)
        _verify_metadata_written(png_path, gist_url)
        
        return True
        
    except ImportError as e:
        _debug_log(f"❌ Failed to import PIL: {e}")
        print(f"CHM: ERROR - PIL not available. Cannot embed metadata.")
        import traceback
        print(f"CHM: Import error traceback: {traceback.format_exc()}")
        return False
        
    except Exception as e:
        _debug_log(f"❌ Error adding metadata: {e}")
        print(f"CHM: ERROR - Failed to add metadata to PNG: {e}")
        import traceback
        print(f"CHM: Error traceback: {traceback.format_exc()}")
        return False


def _verify_metadata_written(png_path: str, expected_gist_url: str) -> None:
    """
    Verify that metadata was actually written to the PNG file.
    This is a sanity check to catch issues early.
    """
    try:
        from PIL import Image
        
        img = Image.open(png_path)
        
        # Check if metadata exists
        if hasattr(img, 'text') and 'CHM-Gist-URL' in img.text:
            actual_url = img.text['CHM-Gist-URL']
            if actual_url == expected_gist_url:
                _debug_log(f"✓ Metadata verification passed")
            else:
                _debug_log(f"⚠️ Metadata mismatch: expected {expected_gist_url}, got {actual_url}")
        else:
            _debug_log(f"⚠️ Warning: Metadata not found after write (may be a PIL issue)")
            
    except Exception as e:
        _debug_log(f"⚠️ Verification check failed: {e}")


def extract_chm_metadata(png_path: str) -> Optional[Dict[str, str]]:
    """
    Extract CHM metadata from a PNG file.
    
    Args:
        png_path: Path to PNG file
        
    Returns:
        Dictionary with metadata keys (CHM-Gist-URL, etc.) or None if not found
        
    Raises:
        FileNotFoundError: If PNG file doesn't exist
        ValueError: If file is not a valid PNG
    """
    _debug_log(f"Extracting CHM metadata from: {png_path}")
    
    if not os.path.exists(png_path):
        raise FileNotFoundError(f"PNG file not found: {png_path}")
    
    try:
        from PIL import Image
        
        img = Image.open(png_path)
        
        if img.format != 'PNG':
            raise ValueError(f"File is not a PNG (format: {img.format})")
        
        # Extract text chunks
        if not hasattr(img, 'text'):
            _debug_log(f"No text metadata found in PNG")
            return None
        
        # Filter CHM-specific metadata
        chm_metadata = {}
        for key, value in img.text.items():
            if key.startswith("CHM-"):
                chm_metadata[key] = value
                _debug_log(f"  Found: {key} = {value[:50]}...")
        
        if chm_metadata:
            _debug_log(f"✓ Found {len(chm_metadata)} CHM metadata fields")
            return chm_metadata
        else:
            _debug_log(f"No CHM metadata found")
            return None
            
    except ImportError as e:
        _debug_log(f"❌ Failed to import PIL: {e}")
        return None
        
    except Exception as e:
        _debug_log(f"❌ Error extracting metadata: {e}")
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
    Usage: python png_metadata.py <path_to_png>
    """
    if len(sys.argv) < 2:
        print("Usage: python png_metadata.py <path_to_png>")
        print("This will add test metadata to the PNG file.")
        sys.exit(1)
    
    test_png = sys.argv[1]
    
    print("Testing PNG metadata embedding...")
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


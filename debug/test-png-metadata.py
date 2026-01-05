#!/usr/bin/env python3
"""
Test PNG Metadata Module

This script tests the PNG metadata embedding functionality standalone,
without requiring Krita to be running.

Usage:
    python debug/test-png-metadata.py

Creates a test PNG, embeds CHM metadata, and verifies it can be read back.
"""

import os
import sys

# Add krita-plugin to path so we can import modules
plugin_path = os.path.join(os.path.dirname(__file__), "..", "krita-plugin")
sys.path.insert(0, plugin_path)

# Import PNG metadata module
from chm_verifier.png_metadata import (
    add_chm_metadata,
    extract_chm_metadata,
    has_chm_metadata,
    get_gist_url
)


def create_test_png(output_path: str):
    """Create a simple test PNG file"""
    try:
        from PIL import Image, ImageDraw
        
        # Create a 200x200 test image
        img = Image.new('RGB', (200, 200), color='lightblue')
        draw = ImageDraw.Draw(img)
        
        # Add some text
        draw.text((50, 80), "CHM Test Image", fill='black')
        draw.text((40, 100), "Metadata Test", fill='black')
        
        # Save as PNG
        img.save(output_path, 'PNG')
        print(f"✓ Created test PNG: {output_path}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to create test PNG: {e}")
        return False


def test_metadata_embedding():
    """Test CHM metadata embedding and extraction"""
    
    print("=" * 60)
    print("CHM PNG Metadata Test")
    print("=" * 60)
    print()
    
    # Create test directory
    test_dir = os.path.join(os.path.dirname(__file__), "test_output")
    os.makedirs(test_dir, exist_ok=True)
    
    test_png = os.path.join(test_dir, "test_metadata.png")
    
    # Step 1: Create test PNG
    print("Step 1: Creating test PNG...")
    if not create_test_png(test_png):
        return False
    print()
    
    # Step 2: Add CHM metadata
    print("Step 2: Adding CHM metadata...")
    test_gist_url = "https://gist.github.com/certifiedhumanmade/abc123def456"
    test_proof_hash = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    test_classification = "human-made"
    test_session_id = "550e8400-e29b-41d4-a716-446655440000"
    
    success = add_chm_metadata(
        png_path=test_png,
        gist_url=test_gist_url,
        proof_hash=test_proof_hash,
        classification=test_classification,
        session_id=test_session_id
    )
    
    if not success:
        print("❌ Failed to add metadata!")
        return False
    print()
    
    # Step 3: Check if metadata exists
    print("Step 3: Checking if metadata exists...")
    if has_chm_metadata(test_png):
        print("✓ has_chm_metadata() returned True")
    else:
        print("❌ has_chm_metadata() returned False!")
        return False
    print()
    
    # Step 4: Extract gist URL
    print("Step 4: Extracting gist URL...")
    extracted_url = get_gist_url(test_png)
    if extracted_url == test_gist_url:
        print(f"✓ Gist URL matches: {extracted_url}")
    else:
        print(f"❌ Gist URL mismatch!")
        print(f"   Expected: {test_gist_url}")
        print(f"   Got: {extracted_url}")
        return False
    print()
    
    # Step 5: Extract all metadata
    print("Step 5: Extracting all CHM metadata...")
    metadata = extract_chm_metadata(test_png)
    
    if not metadata:
        print("❌ No metadata extracted!")
        return False
    
    print("✓ Metadata extracted successfully!")
    print("\nMetadata contents:")
    for key, value in sorted(metadata.items()):
        print(f"  {key}: {value}")
    print()
    
    # Step 6: Verify all fields
    print("Step 6: Verifying metadata fields...")
    checks = [
        ("CHM-Gist-URL", test_gist_url),
        ("CHM-Proof-Hash", test_proof_hash),
        ("CHM-Classification", test_classification),
        ("CHM-Session-ID", test_session_id),
        ("CHM-Version", "1.0.0")
    ]
    
    all_passed = True
    for key, expected_value in checks:
        if key in metadata:
            if metadata[key] == expected_value:
                print(f"  ✓ {key}: OK")
            else:
                print(f"  ❌ {key}: Mismatch (expected: {expected_value}, got: {metadata[key]})")
                all_passed = False
        else:
            print(f"  ❌ {key}: Missing!")
            all_passed = False
    
    print()
    
    # Step 7: Check file size impact
    print("Step 7: Checking file size impact...")
    file_size = os.path.getsize(test_png)
    print(f"  Final file size: {file_size} bytes")
    print(f"  (Metadata adds ~200 bytes - negligible)")
    print()
    
    # Final result
    print("=" * 60)
    if all_passed:
        print("✅ ALL TESTS PASSED!")
        print(f"\nTest PNG saved at: {test_png}")
        print("You can inspect it with:")
        print(f"  exiftool {test_png}")
        print(f"  python -c \"from PIL import Image; img=Image.open('{test_png}'); print(img.text)\"")
    else:
        print("❌ SOME TESTS FAILED!")
    print("=" * 60)
    
    return all_passed


def test_metadata_preservation():
    """
    Test if metadata survives opening and re-saving.
    
    This simulates what happens when a user opens the PNG in an image viewer
    and re-saves it.
    """
    print("\n" + "=" * 60)
    print("Testing Metadata Preservation (Open & Re-save)")
    print("=" * 60)
    print()
    
    test_dir = os.path.join(os.path.dirname(__file__), "test_output")
    original_png = os.path.join(test_dir, "test_metadata.png")
    resaved_png = os.path.join(test_dir, "test_metadata_resaved.png")
    
    if not os.path.exists(original_png):
        print("⚠️ Original test PNG not found, skipping preservation test")
        return True
    
    try:
        from PIL import Image
        
        # Open and re-save (simulating user action)
        print("Opening PNG and re-saving...")
        img = Image.open(original_png)
        img.save(resaved_png, 'PNG')
        print(f"✓ Re-saved as: {resaved_png}")
        print()
        
        # Extract metadata from re-saved file
        print("Checking if metadata survived...")
        metadata = extract_chm_metadata(resaved_png)
        
        if metadata and 'CHM-Gist-URL' in metadata:
            print("✓ Metadata survived re-save!")
            print(f"  Gist URL: {metadata['CHM-Gist-URL']}")
            return True
        else:
            print("❌ Metadata was lost during re-save!")
            print("  This is expected with plain PIL save (metadata not preserved)")
            print("  In practice, macOS Preview and GIMP preserve tEXt chunks")
            return False
            
    except Exception as e:
        print(f"❌ Preservation test failed: {e}")
        return False


if __name__ == "__main__":
    print("\n🧪 CHM PNG Metadata Test Suite\n")
    
    # Test 1: Basic metadata embedding
    if not test_metadata_embedding():
        print("\n❌ Basic metadata test failed!")
        sys.exit(1)
    
    # Test 2: Metadata preservation
    test_metadata_preservation()
    
    print("\n✅ Test suite complete!\n")


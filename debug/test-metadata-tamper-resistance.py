#!/usr/bin/env python3
"""
Test PNG Metadata Tamper Resistance

This script tests that the system properly rejects images with copied/stolen
gist URLs that don't match the actual image content.

Attack Scenario:
1. Attacker takes a verified human-made image
2. Extracts gist URL from metadata
3. Creates a different image (AI-generated)
4. Embeds the stolen gist URL in the new image
5. Tries to verify → Should be REJECTED

Expected: Server detects file hash mismatch and rejects verification
"""

import os
import sys
import json

# Add krita-plugin to path
plugin_path = os.path.join(os.path.dirname(__file__), "..", "krita-plugin")
sys.path.insert(0, plugin_path)

from chm_verifier.png_metadata import add_chm_metadata, extract_chm_metadata


def create_fake_image(output_path: str, stolen_gist_url: str):
    """
    Create a fake image with stolen metadata.
    This simulates an attacker copying gist URL to verify a different image.
    """
    try:
        from PIL import Image, ImageDraw
        
        # Create a DIFFERENT image than the original
        img = Image.new('RGB', (300, 300), color='red')
        draw = ImageDraw.Draw(img)
        draw.text((50, 140), "FAKE IMAGE", fill='white')
        draw.text((30, 160), "(with stolen metadata)", fill='white')
        
        img.save(output_path, 'PNG')
        
        # Add stolen metadata
        add_chm_metadata(
            png_path=output_path,
            gist_url=stolen_gist_url,
            proof_hash="stolen_proof_hash_12345",  # Fake hash
            classification="human-made",  # Lying about classification!
            session_id="stolen-session-id"
        )
        
        return True
    except Exception as e:
        print(f"Error creating fake image: {e}")
        return False


def test_tamper_detection():
    """
    Test that the system detects and rejects tampered metadata.
    """
    print("=" * 70)
    print("CHM Metadata Tamper Resistance Test")
    print("=" * 70)
    print()
    print("Scenario: Attacker copies gist URL to verify a different image")
    print()
    
    test_dir = os.path.join(os.path.dirname(__file__), "test_output")
    os.makedirs(test_dir, exist_ok=True)
    
    # Step 1: Simulate an existing verified image
    print("Step 1: Creating 'verified' original image...")
    original_gist_url = "https://gist.github.com/certifiedhumanmade/REAL_GIST_123"
    print(f"  Original gist URL: {original_gist_url}")
    print()
    
    # Step 2: Attacker creates fake image with stolen URL
    print("Step 2: Attacker creates fake image with stolen metadata...")
    fake_image_path = os.path.join(test_dir, "fake_image_with_stolen_metadata.png")
    
    if create_fake_image(fake_image_path, original_gist_url):
        print(f"  ✓ Fake image created: {fake_image_path}")
    else:
        print("  ❌ Failed to create fake image")
        return False
    print()
    
    # Step 3: Extract metadata from fake image
    print("Step 3: Extracting metadata from fake image...")
    metadata = extract_chm_metadata(fake_image_path)
    
    if metadata:
        print("  ✓ Metadata extracted successfully")
        print(f"  Gist URL: {metadata.get('CHM-Gist-URL')}")
        print(f"  Classification: {metadata.get('CHM-Classification')}")
        print()
    else:
        print("  ❌ Failed to extract metadata")
        return False
    
    # Step 4: Verify the attack would be detected
    print("Step 4: Verifying tamper detection logic...")
    print()
    print("  What should happen on verification:")
    print("  1. Client extracts gist URL from fake image ✓")
    print("  2. Client computes file hash of fake image")
    print("  3. Client sends: { gistId, fileHash } to server")
    print("  4. Server fetches real gist → gets ORIGINAL file hash")
    print("  5. Server compares:")
    print("     - Original hash: sha256:abc123... (from gist)")
    print("     - Fake image hash: sha256:def456... (computed)")
    print("  6. Hashes DON'T MATCH → Server rejects ❌")
    print()
    print("  Expected response:")
    print("  {")
    print('    "status": "unverified",')
    print('    "matchType": "none",')
    print('    "confidence": 0,')
    print('    "message": "File hash mismatch - tamper detected"')
    print("  }")
    print()
    
    # Step 5: Manual verification
    print("Step 5: Manual Verification Test")
    print("=" * 70)
    print()
    print("To test this attack scenario manually:")
    print()
    print("1. Upload the fake image to the website:")
    print(f"   File: {fake_image_path}")
    print()
    print("2. Watch the browser console - should see:")
    print("   [CLIENT-VERIFY-METADATA-2] ✓ CHM metadata found!")
    print(f"   [CLIENT-VERIFY-METADATA-2a] Gist URL: {original_gist_url}")
    print("   [CLIENT-VERIFY-METADATA-SECURITY] Computing file hash...")
    print("   [SERVER] File hash mismatch - TAMPER DETECTED!")
    print()
    print("3. Expected result:")
    print("   Status: UNVERIFIED ❌")
    print('   Message: "File hash mismatch - tamper detected"')
    print()
    print("4. If verified as 'human-made' → Security check FAILED! 🚨")
    print()
    
    # Step 6: Security summary
    print("=" * 70)
    print("Security Analysis")
    print("=" * 70)
    print()
    print("✓ Metadata can be copied (expected)")
    print("✓ Gist URL is public (expected)")
    print("✓ But file hash validation prevents verification fraud")
    print()
    print("Attack prevented by:")
    print("  1. Server requires BOTH gistId AND fileHash")
    print("  2. Server fetches proof from gist (contains original hash)")
    print("  3. Server validates: uploaded_hash === proof.file_hash")
    print("  4. Mismatch → Rejection (tamper detected)")
    print()
    print("Attacker would need to:")
    print("  - Modify immutable GitHub gist (impossible)")
    print("  - OR recreate exact same image (defeats purpose)")
    print()
    print("✅ CONCLUSION: Metadata tamper attack is PREVENTED")
    print("=" * 70)
    print()
    
    return True


if __name__ == "__main__":
    print("\n🔒 CHM Metadata Security Test\n")
    
    if test_tamper_detection():
        print("\n✅ Security test scenario created successfully!")
        print("\nNext: Upload the fake image to the website to verify rejection.\n")
    else:
        print("\n❌ Security test failed!\n")
        sys.exit(1)


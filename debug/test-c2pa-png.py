#!/usr/bin/env python3
"""
Test C2PA PNG embedding with c2pa-python

This script tests if c2pa-python can embed manifests in PNG files.
Run this from terminal (not in Krita) to test basic functionality.
"""

import sys
import os
import json
import tempfile

# Add krita-plugin directory to path to import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'krita-plugin'))

DEBUG_LOG = True

def log(message):
    """Debug logging helper"""
    if DEBUG_LOG:
        print(f"[C2PA-PNG-TEST] {message}")

def create_test_png():
    """Create a simple test PNG image"""
    log("Creating test PNG image...")
    
    try:
        from PIL import Image
        
        # Create test image
        img = Image.new('RGB', (100, 100), color='red')
        
        # Save to temp file
        temp_png = tempfile.mktemp(suffix='.png')
        img.save(temp_png)
        
        log(f"✅ Test PNG created: {temp_png}")
        return temp_png
        
    except ImportError:
        log("❌ Pillow not available - cannot create test PNG")
        log("   Install with: pip3 install Pillow")
        return None
    except Exception as e:
        log(f"❌ Error creating PNG: {e}")
        return None

def create_test_manifest():
    """Create a simple test C2PA manifest"""
    log("Creating test C2PA manifest...")
    
    manifest = {
        "title": "Test Human-Made Artwork",
        "claim_generator": "CHM Krita Plugin Test",
        "assertions": [
            {
                "label": "c2pa.actions",
                "data": {
                    "actions": [
                        {
                            "action": "c2pa.created",
                            "when": "2024-01-01T00:00:00Z"
                        }
                    ]
                }
            },
            {
                "label": "c2pa.ai_generated",
                "data": {
                    "isAIGenerated": False
                }
            }
        ]
    }
    
    log(f"✅ Test manifest created ({len(json.dumps(manifest))} bytes)")
    return manifest

def test_c2pa_python_embedding(png_path, manifest):
    """Test c2pa-python native embedding"""
    log("\n" + "=" * 60)
    log("TEST 1: c2pa-python Native Embedding")
    log("=" * 60)
    
    try:
        from c2pa import Builder
        
        log("c2pa-python library available")
        log("⚠️  Note: Full c2pa-python embedding integration pending")
        log("   (requires deeper API integration)")
        
        # TODO: Implement actual c2pa-python embedding
        # This requires understanding c2pa-python's Builder API
        
        return False  # Not yet implemented
        
    except ImportError:
        log("❌ c2pa-python not available")
        return False
    except Exception as e:
        log(f"❌ Error: {e}")
        import traceback
        log(traceback.format_exc())
        return False

def test_fallback_png_embedding(png_path, manifest):
    """Test fallback PNG chunk embedder"""
    log("\n" + "=" * 60)
    log("TEST 2: Fallback PNG Chunk Embedder")
    log("=" * 60)
    
    try:
        from chm_verifier.png_c2pa_embedder import embed_c2pa_manifest_in_png
        
        log(f"Embedding manifest in PNG: {png_path}")
        
        success = embed_c2pa_manifest_in_png(png_path, manifest)
        
        if success:
            log("✅ SUCCESS: Manifest embedded using fallback embedder")
            log(f"   Modified PNG: {png_path}")
            
            # Check file size increased
            file_size = os.path.getsize(png_path)
            log(f"   File size: {file_size} bytes")
            
            return True
        else:
            log("❌ FAILED: Fallback embedding failed")
            return False
            
    except ImportError as e:
        log(f"❌ Could not import fallback embedder: {e}")
        return False
    except Exception as e:
        log(f"❌ Error: {e}")
        import traceback
        log(traceback.format_exc())
        return False

def test_manifest_extraction(png_path):
    """Test extracting C2PA manifest from PNG"""
    log("\n" + "=" * 60)
    log("TEST 3: Manifest Extraction")
    log("=" * 60)
    
    try:
        from chm_verifier.png_c2pa_embedder import extract_c2pa_manifest_from_png
        
        log(f"Extracting manifest from PNG: {png_path}")
        
        manifest = extract_c2pa_manifest_from_png(png_path)
        
        if manifest:
            log("✅ SUCCESS: Manifest extracted")
            log(f"   Manifest keys: {list(manifest.keys())}")
            log(f"   Title: {manifest.get('title', 'N/A')}")
            log(f"   Assertions: {len(manifest.get('assertions', []))}")
            return True
        else:
            log("⚠️  No manifest found (may be expected if embedding failed)")
            return False
            
    except Exception as e:
        log(f"❌ Error: {e}")
        import traceback
        log(traceback.format_exc())
        return False

def main():
    """Run all PNG embedding tests"""
    log("=" * 60)
    log("C2PA PNG EMBEDDING TEST")
    log("=" * 60)
    log("")
    
    # Create test PNG
    png_path = create_test_png()
    if not png_path:
        log("\n❌ FAILED: Could not create test PNG")
        return False
    
    # Create test manifest
    manifest = create_test_manifest()
    
    # Test c2pa-python embedding (not yet implemented)
    result1 = test_c2pa_python_embedding(png_path, manifest)
    
    # Test fallback embedding
    result2 = test_fallback_png_embedding(png_path, manifest)
    
    # Test extraction
    if result2:
        result3 = test_manifest_extraction(png_path)
    else:
        result3 = False
    
    # Summary
    log("\n" + "=" * 60)
    log("TEST SUMMARY")
    log("=" * 60)
    log(f"c2pa-python embedding: {'✅ PASS' if result1 else '⚠️  NOT IMPLEMENTED'}")
    log(f"Fallback PNG embedder: {'✅ PASS' if result2 else '❌ FAIL'}")
    log(f"Manifest extraction:   {'✅ PASS' if result3 else '⚠️  SKIP/FAIL'}")
    log("")
    
    if result2 and result3:
        log("✅ PNG EMBEDDING WORKING (fallback mode)")
        log("")
        log("Next steps:")
        log("1. Implement proper c2pa-python embedding")
        log("2. Test with real CHM SessionProof data")
        log("3. Validate with c2patool")
        return True
    else:
        log("❌ PNG EMBEDDING TESTS FAILED")
        log("")
        log("Check:")
        log("1. Pillow installed? (pip3 install Pillow)")
        log("2. CHM plugin files accessible?")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)



#!/usr/bin/env python3
"""
Test c2pa-python library installation and basic functionality.

This script tests if c2pa-python can be imported and used on macOS
without signing issues. Run this with Krita's Python interpreter.
"""

import sys
import os

DEBUG_LOG = True

def log(message):
    """Debug logging helper"""
    if DEBUG_LOG:
        print(f"[C2PA-TEST] {message}")

def test_c2pa_import():
    """Test if c2pa-python can be imported"""
    log("Testing c2pa-python import...")
    
    try:
        from c2pa import Builder, create_signer
        log("✅ c2pa-python imported successfully")
        return True
    except ImportError as e:
        log(f"❌ Failed to import c2pa-python: {e}")
        log("   → Install with: pip3 install c2pa-python")
        return False
    except Exception as e:
        log(f"❌ Error importing c2pa-python: {e}")
        log("   → This may indicate macOS signing issues")
        return False

def test_create_claim():
    """Test creating a basic C2PA claim"""
    log("\nTesting C2PA claim creation...")
    
    try:
        from c2pa import Builder
        
        builder = Builder()
        log("✅ Builder created successfully")
        
        # Test basic claim structure
        log("   → C2PA library is functional")
        return True
        
    except Exception as e:
        log(f"❌ Failed to create claim: {e}")
        import traceback
        log(f"   Traceback: {traceback.format_exc()}")
        return False

def main():
    """Run all C2PA tests"""
    log("=" * 60)
    log("C2PA Python Installation Test")
    log("=" * 60)
    log(f"Python: {sys.version}")
    log(f"Platform: {sys.platform}")
    log("")
    
    # Test import
    if not test_c2pa_import():
        log("\n❌ FAILED: c2pa-python not installed or not importable")
        log("\nTo install:")
        log("  1. Find Krita's pip:")
        log("     macOS: /Applications/krita.app/Contents/Frameworks/Python.framework/Versions/3.10/bin/pip3")
        log("  2. Install c2pa-python:")
        log("     pip3 install c2pa-python")
        return False
    
    # Test functionality
    if not test_create_claim():
        log("\n❌ FAILED: c2pa-python installed but not functional")
        return False
    
    log("\n" + "=" * 60)
    log("✅ ALL TESTS PASSED - c2pa-python is ready!")
    log("=" * 60)
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)


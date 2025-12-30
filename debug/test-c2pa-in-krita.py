"""
SAFE Test c2pa-python in Krita

Run this script in Krita's Scripting Console to verify c2pa-python works.
This version avoids operations that might crash Krita.
"""

print("=" * 60)
print("C2PA-PYTHON KRITA SAFE TEST")
print("=" * 60)
print()

# Test 1: Import c2pa (safe - just imports the module)
print("Test 1: Importing c2pa-python...")
try:
    import c2pa
    print("✅ SUCCESS: c2pa module imported")
    print(f"   c2pa module path: {c2pa.__file__}")
    print(f"   c2pa attributes: {[a for a in dir(c2pa) if not a.startswith('_')][:10]}")
except ImportError as e:
    print(f"❌ FAILED: Could not import c2pa")
    print(f"   Error: {e}")
    print()
    print("Troubleshooting:")
    print("1. Check if c2pa-python is installed to:")
    print("   /Users/david/Library/Python/3.10/lib/python/site-packages")
    print("2. Restart Krita")
    print()
    print("⚠️  TEST STOPPED - c2pa-python not available")
    # Don't use exit() in Krita console - it might close Krita!
else:
    print()
    
    # Test 2: Check if Builder is available (don't create it yet)
    print("Test 2: Checking c2pa.Builder availability...")
    try:
        from c2pa import Builder
        print("✅ SUCCESS: Builder class is available")
        print(f"   Builder type: {type(Builder)}")
    except ImportError as e:
        print(f"❌ FAILED: Could not import Builder")
        print(f"   Error: {e}")
    except Exception as e:
        print(f"⚠️  WARNING: Unexpected error")
        print(f"   Error: {e}")
    
    print()
    
    # Test 3: Check module contents (safe - no object creation)
    print("Test 3: Checking c2pa module contents...")
    try:
        import c2pa
        
        # List available functions/classes
        available = [item for item in dir(c2pa) if not item.startswith('_')]
        print(f"✅ c2pa module has {len(available)} public items")
        print(f"   Key items: {available[:15]}")
        
    except Exception as e:
        print(f"❌ Error: {e}")

print()
print("=" * 60)
print("SAFE TEST COMPLETE")
print("=" * 60)
print()
print("⚠️  NOTE: Full Builder testing skipped to avoid crashes")
print("If c2pa imported successfully, the library is available.")
print()
print("Next: Integrate C2PA into CHM export (doesn't require testing Builder in console)")
print("=" * 60)


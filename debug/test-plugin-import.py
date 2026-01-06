#!/usr/bin/env python3
"""
Test if CHM plugin can be imported without Krita
This helps debug import errors before trying in Krita
"""

import sys
import os

# Add plugin directory to path
plugin_dir = os.path.join(os.path.dirname(__file__), "..", "krita-plugin", "chm_verifier")
sys.path.insert(0, plugin_dir)

print("=" * 60)
print("CHM Plugin Import Test")
print("=" * 60)
print(f"Plugin directory: {plugin_dir}")
print()

# Test 1: Can we import the extension module?
print("Test 1: Importing chm_extension module...")
try:
    from chm_extension import CHMExtension
    print("✅ SUCCESS: chm_extension imported")
    print(f"   CHMExtension class: {CHMExtension}")
except Exception as e:
    print(f"❌ FAILED: {e}")
    import traceback
    traceback.print_exc()

print()

# Test 2: Can we import the Rust library?
print("Test 2: Importing CHM Rust library...")
lib_dir = os.path.join(plugin_dir, "lib")
if os.path.exists(lib_dir):
    sys.path.insert(0, lib_dir)
    print(f"   Lib directory: {lib_dir}")
    
    # Check if library file exists
    chm_so = os.path.join(lib_dir, "chm.so")
    if os.path.exists(chm_so):
        print(f"   ✅ chm.so exists ({os.path.getsize(chm_so)} bytes)")
        
        try:
            import chm
            print("   ✅ SUCCESS: chm module imported")
            print(f"   Version: {chm.get_version()}")
            print(f"   Test: {chm.hello_from_rust()}")
        except Exception as e:
            print(f"   ❌ FAILED: {e}")
            import traceback
            traceback.print_exc()
    else:
        print(f"   ❌ chm.so not found at: {chm_so}")
else:
    print(f"   ❌ Lib directory not found: {lib_dir}")

print()
print("=" * 60)
print("Import test complete")
print("=" * 60)



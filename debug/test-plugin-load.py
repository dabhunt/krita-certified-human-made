#!/usr/bin/env python3
"""
Test script to verify CHM plugin can be imported and loaded.
Run this from the command line to test plugin without Krita.
"""

import sys
import os

print("=" * 60)
print("CHM Plugin Load Test")
print("=" * 60)
print()

# Determine plugin path based on OS
if sys.platform == "darwin":
    plugin_base = os.path.expanduser("~/Library/Application Support/krita/pykrita")
elif sys.platform.startswith("linux"):
    plugin_base = os.path.expanduser("~/.local/share/krita/pykrita")
else:
    plugin_base = os.path.expanduser(r"%APPDATA%\krita\pykrita")

plugin_path = os.path.join(plugin_base, "chm_verifier")

print(f"Plugin path: {plugin_path}")
print(f"Exists: {os.path.exists(plugin_path)}")
print()

if not os.path.exists(plugin_path):
    print("ERROR: Plugin directory not found!")
    print(f"Expected: {plugin_path}")
    sys.exit(1)

# Add plugin to path
sys.path.insert(0, os.path.dirname(plugin_path))

# Test 1: Import __init__.py
print("Test 1: Checking __init__.py...")
print("-" * 40)
init_file = os.path.join(plugin_path, "__init__.py")
if os.path.exists(init_file):
    print(f"✓ __init__.py exists")
    print(f"  Size: {os.path.getsize(init_file)} bytes")
else:
    print("✗ __init__.py missing!")
    sys.exit(1)
print()

# Test 2: Check lib directory
print("Test 2: Checking Rust library...")
print("-" * 40)
lib_dir = os.path.join(plugin_path, "lib")
if os.path.exists(lib_dir):
    print(f"✓ lib directory exists")
    lib_files = os.listdir(lib_dir)
    print(f"  Contents: {lib_files}")
    
    # Check for chm.so
    lib_file = os.path.join(lib_dir, "chm.so")
    if os.path.exists(lib_file):
        print(f"✓ chm.so exists")
        print(f"  Size: {os.path.getsize(lib_file)} bytes")
        
        # Try to import
        sys.path.insert(0, lib_dir)
        try:
            import chm
            print(f"✓ Successfully imported chm library!")
            
            # Test basic functions
            try:
                version = chm.get_version()
                print(f"  Version: {version}")
            except Exception as e:
                print(f"  ⚠ Could not get version: {e}")
            
            try:
                msg = chm.hello_from_rust()
                print(f"  Test message: {msg}")
            except Exception as e:
                print(f"  ⚠ Could not call hello_from_rust: {e}")
                
        except ImportError as e:
            print(f"✗ Failed to import chm library: {e}")
            print()
            print("This is expected on macOS due to linking issues.")
            print("The library should still work when loaded by Krita.")
    else:
        print(f"✗ chm.so not found in lib directory")
else:
    print("✗ lib directory missing!")
print()

# Test 3: Check for required Python files
print("Test 3: Checking Python modules...")
print("-" * 40)
required_files = [
    "chm_extension.py",
    "chm_session_manager.py",
    "event_capture.py",
    "plugin_monitor.py",
    "verification_dialog.py"
]

for filename in required_files:
    filepath = os.path.join(plugin_path, filename)
    if os.path.exists(filepath):
        print(f"✓ {filename}")
    else:
        print(f"✗ {filename} MISSING")
print()

# Test 4: Check .desktop file
print("Test 4: Checking .desktop file...")
print("-" * 40)
desktop_file = os.path.join(plugin_base, "chm_verifier.desktop")
if os.path.exists(desktop_file):
    print(f"✓ chm_verifier.desktop exists")
    print(f"  Location: {desktop_file}")
    print()
    print("  Contents:")
    with open(desktop_file, 'r') as f:
        for line in f:
            print(f"    {line.rstrip()}")
else:
    print(f"✗ chm_verifier.desktop NOT FOUND")
    print(f"  Expected location: {desktop_file}")
    print(f"  NOTE: Must be in plugin root, NOT inside chm_verifier/")
print()

# Test 5: Check debug log
print("Test 5: Checking debug log...")
print("-" * 40)
log_file = os.path.expanduser("~/.local/share/chm/plugin_debug.log")
if os.path.exists(log_file):
    print(f"✓ Debug log exists: {log_file}")
    print()
    print("  Last 15 lines:")
    with open(log_file, 'r') as f:
        lines = f.readlines()
        for line in lines[-15:]:
            print(f"    {line.rstrip()}")
else:
    print(f"⚠ Debug log not found: {log_file}")
    print("  This means the plugin has never loaded in Krita")
print()

# Summary
print("=" * 60)
print("SUMMARY")
print("=" * 60)
print()
print("Next steps to verify plugin loads in Krita:")
print("  1. Close Krita completely")
print(f"  2. Delete debug log: rm -f '{log_file}'")
print("  3. Start Krita")
print(f"  4. Check log: cat '{log_file}'")
print()
print("Expected log entries if loading correctly:")
print("  - CHM: __init__.py starting to load")
print("  - CHM: Plugin registered successfully") 
print("  - CHM: CHMExtension.__init__() called")
print("  - CHM: setup() METHOD CALLED")
print()
print("If no log appears after starting Krita:")
print("  - Plugin is not enabled in Settings → Python Plugin Manager")
print("  - Or there's an import error preventing any code from running")
print()


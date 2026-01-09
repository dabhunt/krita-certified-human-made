#!/usr/bin/env python3
"""
Test Embedded Signing Key Functionality

This script tests that:
1. Signing key can be embedded during build
2. Plugin can load embedded key correctly
3. Embedded key matches the source key
4. Build process creates proper obfuscation

Usage:
    python3 debug/test-embedded-signing-key.py
"""

import os
import sys
import base64
import tempfile
import shutil

# Color codes for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
RESET = '\033[0m'

def print_success(msg):
    print(f"{GREEN}✓{RESET} {msg}")

def print_error(msg):
    print(f"{RED}✗{RESET} {msg}")

def print_info(msg):
    print(f"{YELLOW}ℹ{RESET} {msg}")


def test_signing_key_exists():
    """Test that developer has a signing key"""
    print("\n" + "="*70)
    print("TEST 1: Check Signing Key Exists")
    print("="*70)
    
    key_file = os.path.expanduser("~/.config/chm/signing_key.txt")
    
    if not os.path.exists(key_file):
        print_error(f"No signing key found at: {key_file}")
        print_info("Run: python3 scripts/generate-signing-key.py --auto-generate")
        return False
    
    print_success(f"Signing key found: {key_file}")
    
    # Read and validate key
    with open(key_file, 'r') as f:
        key = f.read().strip()
    
    try:
        decoded = base64.b64decode(key)
        print_success(f"Key is valid base64 ({len(decoded)} bytes)")
        print_info(f"Key fingerprint: {key[:8]}...{key[-8:]}")
        return True
    except Exception as e:
        print_error(f"Invalid key format: {e}")
        return False


def test_embedded_key_creation():
    """Test that embedded key can be created"""
    print("\n" + "="*70)
    print("TEST 2: Create Embedded Key File")
    print("="*70)
    
    key_file = os.path.expanduser("~/.config/chm/signing_key.txt")
    
    if not os.path.exists(key_file):
        print_error("Signing key not found (run TEST 1 first)")
        return False
    
    with open(key_file, 'r') as f:
        signing_key = f.read().strip()
    
    # Create temp embedded key file
    temp_dir = tempfile.mkdtemp()
    embedded_file = os.path.join(temp_dir, "signing_key_embedded.py")
    
    try:
        # Simulate build script logic
        with open(embedded_file, 'w') as f:
            f.write('# Auto-generated during build - DO NOT EDIT\n')
            f.write('def get_embedded_key():\n')
            f.write('    """Return the embedded signing key"""\n')
            f.write('    parts = [\n')
            
            # Split key into 20-char chunks
            for i in range(0, len(signing_key), 20):
                chunk = signing_key[i:i+20]
                f.write(f'        "{chunk}",\n')
            
            f.write('    ]\n')
            f.write('    return "".join(parts)\n')
        
        print_success(f"Created embedded key file: {embedded_file}")
        
        # Test that it can be imported and returns correct key
        sys.path.insert(0, temp_dir)
        import signing_key_embedded
        
        embedded_key = signing_key_embedded.get_embedded_key()
        
        if embedded_key == signing_key:
            print_success("Embedded key matches source key")
            print_info(f"Embedded key length: {len(embedded_key)} chars")
            return True
        else:
            print_error("Embedded key does NOT match source key")
            print_info(f"Source:   {signing_key[:20]}...")
            print_info(f"Embedded: {embedded_key[:20]}...")
            return False
            
    except Exception as e:
        print_error(f"Failed to create/test embedded key: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)
        if 'signing_key_embedded' in sys.modules:
            del sys.modules['signing_key_embedded']


def test_plugin_key_loading():
    """Test that plugin can load embedded key"""
    print("\n" + "="*70)
    print("TEST 3: Plugin Key Loading Logic")
    print("="*70)
    
    # Check if plugin file exists
    plugin_file = "krita-plugin/chm_verifier/chm_extension.py"
    
    if not os.path.exists(plugin_file):
        print_error(f"Plugin file not found: {plugin_file}")
        return False
    
    print_success(f"Plugin file found: {plugin_file}")
    
    # Check for embedded key import
    with open(plugin_file, 'r') as f:
        content = f.read()
    
    if 'from .signing_key_embedded import get_embedded_key' in content:
        print_success("Plugin imports embedded key module")
    else:
        print_error("Plugin does NOT import embedded key module")
        return False
    
    if 'Step 1: Checking embedded key (production)' in content:
        print_success("Plugin checks embedded key first (production mode)")
    else:
        print_error("Plugin does not prioritize embedded key")
        return False
    
    return True


def test_build_script():
    """Test that build script includes key embedding"""
    print("\n" + "="*70)
    print("TEST 4: Build Script Key Embedding")
    print("="*70)
    
    build_script = "scripts/package-release.sh"
    
    if not os.path.exists(build_script):
        print_error(f"Build script not found: {build_script}")
        return False
    
    print_success(f"Build script found: {build_script}")
    
    with open(build_script, 'r') as f:
        content = f.read()
    
    checks = [
        ("SIGNING_KEY_FILE=", "Defines signing key file path"),
        ("generate-signing-key.py --auto-generate", "Auto-generates key if missing"),
        ("signing_key_embedded.py", "Creates embedded key file"),
        ("get_embedded_key()", "Includes key retrieval function"),
    ]
    
    all_passed = True
    for check_str, description in checks:
        if check_str in content:
            print_success(description)
        else:
            print_error(f"Missing: {description}")
            all_passed = False
    
    return all_passed


def test_gitignore():
    """Test that embedded key is in .gitignore"""
    print("\n" + "="*70)
    print("TEST 5: Security - .gitignore Check")
    print("="*70)
    
    gitignore_file = ".gitignore"
    
    if not os.path.exists(gitignore_file):
        print_error(f".gitignore not found")
        return False
    
    with open(gitignore_file, 'r') as f:
        content = f.read()
    
    if 'signing_key_embedded.py' in content:
        print_success("Embedded key file is in .gitignore")
        print_info("This prevents accidental commits of the signing key")
        return True
    else:
        print_error("Embedded key file NOT in .gitignore")
        print_error("SECURITY RISK: Key could be committed to git!")
        return False


def main():
    """Run all tests"""
    print("="*70)
    print("EMBEDDED SIGNING KEY TEST SUITE")
    print("="*70)
    print()
    print("This suite tests the embedded signing key implementation")
    print("for production plugin distribution.")
    print()
    
    tests = [
        ("Signing Key Exists", test_signing_key_exists),
        ("Embedded Key Creation", test_embedded_key_creation),
        ("Plugin Key Loading", test_plugin_key_loading),
        ("Build Script", test_build_script),
        ("Security (.gitignore)", test_gitignore),
    ]
    
    results = []
    
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print_error(f"Test crashed: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    print()
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = f"{GREEN}PASS{RESET}" if result else f"{RED}FAIL{RESET}"
        print(f"  {status}  {name}")
    
    print()
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print()
        print(f"{GREEN}{'='*70}{RESET}")
        print(f"{GREEN}✓ ALL TESTS PASSED{RESET}")
        print(f"{GREEN}{'='*70}{RESET}")
        print()
        print("Next steps:")
        print("  1. Run: ./scripts/package-release.sh")
        print("  2. Verify embedded key is in ZIP but not in git")
        print("  3. Test on Windows production install")
        return 0
    else:
        print()
        print(f"{RED}{'='*70}{RESET}")
        print(f"{RED}✗ SOME TESTS FAILED{RESET}")
        print(f"{RED}{'='*70}{RESET}")
        print()
        print("Fix the failing tests before packaging release.")
        return 1


if __name__ == "__main__":
    sys.exit(main())


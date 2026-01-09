#!/usr/bin/env python3
"""
Generate Secret Signing Key for CHM Plugin

Creates a cryptographically secure random key for HMAC signing of session proofs.
This key must be kept secret and only stored on the developer's machine.

Usage:
    python3 generate-signing-key.py

Output:
    - Prints key to console (base64 encoded)
    - Optionally saves to ~/.config/chm/signing_key.txt
"""

import secrets
import base64
import os
import sys


def generate_signing_key(key_bytes=32):
    """
    Generate a cryptographically secure random key.
    
    Args:
        key_bytes: Key length in bytes (default: 32 = 256 bits)
        
    Returns:
        str: Base64-encoded key
    """
    # Generate random bytes using secrets module (cryptographically secure)
    random_bytes = secrets.token_bytes(key_bytes)
    
    # Encode as base64 for easy storage and handling
    key_b64 = base64.b64encode(random_bytes).decode('ascii')
    
    return key_b64


def save_key_to_config(key_b64, config_path=None):
    """
    Save key to config file.
    
    Args:
        key_b64: Base64-encoded key
        config_path: Optional custom path (default: ~/.config/chm/signing_key.txt)
        
    Returns:
        str: Path where key was saved
    """
    if config_path is None:
        # Default location
        config_dir = os.path.expanduser("~/.config/chm")
        config_path = os.path.join(config_dir, "signing_key.txt")
    
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    
    # Write key to file (restrictive permissions)
    with open(config_path, 'w') as f:
        f.write(key_b64)
    
    # Set file permissions to 0600 (owner read/write only)
    os.chmod(config_path, 0o600)
    
    return config_path


def main():
    """Main function"""
    # Check for auto-generate flag (used by build scripts)
    if "--auto-generate" in sys.argv:
        key_b64 = generate_signing_key(32)
        try:
            saved_path = save_key_to_config(key_b64)
            print(f"✓ Auto-generated signing key: {saved_path}")
            print(f"✓ Key fingerprint: {key_b64[:8]}...{key_b64[-8:]}")
            return
        except Exception as e:
            print(f"✗ Error auto-generating key: {e}")
            sys.exit(1)
    
    # Interactive mode
    print("=" * 70)
    print("CHM Plugin - Secret Signing Key Generator")
    print("=" * 70)
    print()
    
    # Generate key
    print("[1/3] Generating cryptographically secure random key (256 bits)...")
    key_b64 = generate_signing_key(32)  # 32 bytes = 256 bits
    print(f"      ✓ Key generated: {key_b64[:16]}...{key_b64[-16:]}")
    print(f"      ✓ Key length: {len(key_b64)} characters (base64 encoded)")
    print()
    
    # Show key
    print("[2/3] Your secret signing key:")
    print()
    print(f"      {key_b64}")
    print()
    print("      ⚠️  KEEP THIS KEY SECRET! Do not commit to git or share publicly.")
    print()
    
    # Ask to save
    response = input("[3/3] Save key to ~/.config/chm/signing_key.txt? [y/N]: ").strip().lower()
    
    if response in ['y', 'yes']:
        try:
            saved_path = save_key_to_config(key_b64)
            print(f"      ✓ Key saved to: {saved_path}")
            print(f"      ✓ File permissions: 0600 (owner read/write only)")
            print()
            print("NEXT STEPS:")
            print("  1. Verify key is loaded by plugin: check debug log for '[KEY-LOAD]'")
            print("  2. Test signature generation: export a proof and check for 'signature' field")
            print("  3. BACKUP THIS KEY in a secure location (password manager, etc.)")
            print("  4. DO NOT commit ~/.config/chm/ to git")
            print()
        except Exception as e:
            print(f"      ✗ Error saving key: {e}")
            print()
            print("MANUAL SETUP:")
            print(f"  1. Create directory: mkdir -p ~/.config/chm")
            print(f"  2. Save key: echo '{key_b64}' > ~/.config/chm/signing_key.txt")
            print(f"  3. Set permissions: chmod 600 ~/.config/chm/signing_key.txt")
            print()
            sys.exit(1)
    else:
        print("      Key not saved. You can save it manually:")
        print()
        print(f"      mkdir -p ~/.config/chm")
        print(f"      echo '{key_b64}' > ~/.config/chm/signing_key.txt")
        print(f"      chmod 600 ~/.config/chm/signing_key.txt")
        print()
    
    print("=" * 70)
    print("ALTERNATIVE: Set as environment variable")
    print("=" * 70)
    print()
    print(f"export CHM_SIGNING_KEY='{key_b64}'")
    print()
    print("Add to ~/.bashrc or ~/.zshrc for persistence")
    print()
    print("=" * 70)


if __name__ == "__main__":
    main()


#!/usr/bin/env python3
"""
Test API Client Server-Side Signing

Tests the sign_and_timestamp() method to diagnose BUG-016.
"""

import sys
import os

# Add plugin path
plugin_path = os.path.join(os.path.dirname(__file__), '..', 'krita-plugin', 'chm_verifier')
sys.path.insert(0, plugin_path)

from api_client import CHMApiClient
import json

print("=" * 60)
print("Testing CHM API Client - Server-Side Signing")
print("=" * 60)
print()

# Create API client with debug logging
print("Step 1: Creating API client...")
client = CHMApiClient(debug_log=True)
print(f"✓ API client created: {client}")
print(f"  API URL: {client.api_url}")
print(f"  Timeout: {client.timeout}s")
print()

# Create test proof data
print("Step 2: Creating test proof data...")
proof_data = {
    "version": "1.0",
    "session_id": "test-session-12345",
    "document_id": "test-doc",
    "classification": "HumanMade",
    "events_hash": "abc123def456",
    "file_hash": "file123hash456",
    "event_summary": {
        "total_events": 10,
        "stroke_count": 5,
        "layer_count": 2
    },
    "metadata": {
        "document_name": "test.kra"
    }
}
print("✓ Proof data created")
print(f"  Session ID: {proof_data['session_id']}")
print(f"  Classification: {proof_data['classification']}")
print()

# Test signing
print("Step 3: Requesting server-side signing + timestamp...")
print("-" * 60)
try:
    result = client.sign_and_timestamp(proof_data)
    
    print()
    print("-" * 60)
    print("Step 4: Analyzing result...")
    print()
    
    if result.get('error'):
        print(f"❌ ERROR: {result['error']}")
        print()
        print("This means the server API call failed.")
        print("Possible causes:")
        print("1. Server endpoint not deployed: /api/sign-and-timestamp")
        print("2. Server missing ED25519_PRIVATE_KEY in .env")
        print("3. Network error or server down")
        print("4. CORS/authentication error")
        sys.exit(1)
    
    if result.get('signature'):
        print(f"✅ SUCCESS: Server signed the proof!")
        print()
        print(f"Signature: {result['signature'][:40]}...")
        print(f"Signature version: {result.get('signature_version')}")
        
        if result.get('github'):
            print(f"GitHub timestamp: {result['github']['url']}")
            print(f"GitHub created_at: {result['github']['created_at']}")
        else:
            print("⚠️  No GitHub timestamp (non-fatal)")
        
        print()
        print("=" * 60)
        print("TEST PASSED: API client working correctly!")
        print("=" * 60)
        sys.exit(0)
    else:
        print("❌ ERROR: No signature in response")
        print()
        print(f"Full response: {json.dumps(result, indent=2)}")
        sys.exit(1)
        
except Exception as e:
    print()
    print(f"❌ EXCEPTION: {e}")
    import traceback
    print()
    print("Traceback:")
    print(traceback.format_exc())
    sys.exit(1)


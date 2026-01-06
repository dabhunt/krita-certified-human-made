#!/usr/bin/env python3
"""
C2PA Privacy Audit Script

Tests C2PA manifest generation to ensure no privacy leaks.
Validates that only aggregate data is included (no coordinates, layer names, etc.)
"""

import sys
import os
import json

# Add krita-plugin directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'krita-plugin'))

from chm_verifier.c2pa_builder import CHMtoC2PABuilder, run_privacy_audit

DEBUG_LOG = True

def create_test_session_proof():
    """Create a realistic test SessionProof with potentially sensitive data"""
    return {
        "session_id": "test-session-12345",
        "classification": "HumanMade",
        "confidence": 0.95,
        "event_summary": {
            "stroke_count": 1247,
            "layer_count": 8,
            "layer_operations_count": 45,
            "imports_count": 2,
            "undo_redo_count": 23,
            "plugins_used": [],
            "session_duration_secs": 3600
        },
        "public_key": "ed25519:AABBCCDD...",
        "start_time": "2025-12-30T10:00:00Z"
    }

def test_privacy_lite_mode():
    """Test that LITE mode doesn't leak sensitive data"""
    print("=" * 60)
    print("TEST 1: Privacy Audit - LITE MODE")
    print("=" * 60)
    print()
    
    builder = CHMtoC2PABuilder(debug_log=DEBUG_LOG)
    proof = create_test_session_proof()
    
    # Generate manifest in LITE mode (privacy-preserving)
    manifest = builder.generate_manifest(
        session_proof_json=json.dumps(proof),
        privacy_mode="lite"
    )
    
    if not manifest:
        print("❌ FAILED: Could not generate manifest")
        return False
    
    print(f"Manifest generated ({len(json.dumps(manifest))} bytes)")
    print()
    
    # Run privacy audit
    audit_passed = run_privacy_audit(manifest)
    
    if audit_passed:
        print("\n✅ LITE MODE: Privacy audit PASSED")
        print("   No sensitive data leaked")
        return True
    else:
        print("\n❌ LITE MODE: Privacy audit FAILED")
        print("   Sensitive data detected in manifest!")
        return False

def test_privacy_full_mode():
    """Test that FULL mode includes more data but still no coordinates/layer names"""
    print("\n" + "=" * 60)
    print("TEST 2: Privacy Audit - FULL MODE")
    print("=" * 60)
    print()
    
    builder = CHMtoC2PABuilder(debug_log=DEBUG_LOG)
    proof = create_test_session_proof()
    
    # Generate manifest in FULL mode (detailed provenance)
    manifest = builder.generate_manifest(
        session_proof_json=json.dumps(proof),
        privacy_mode="full"
    )
    
    if not manifest:
        print("❌ FAILED: Could not generate manifest")
        return False
    
    print(f"Manifest generated ({len(json.dumps(manifest))} bytes)")
    print()
    
    # Run privacy audit (should still pass - no coordinates/layer names even in full mode)
    audit_passed = run_privacy_audit(manifest)
    
    if audit_passed:
        print("\n✅ FULL MODE: Privacy audit PASSED")
        print("   Even in full mode, critical privacy data is protected")
        return True
    else:
        print("\n❌ FULL MODE: Privacy audit FAILED")
        print("   Sensitive data detected in manifest!")
        return False

def test_manifest_contents():
    """Inspect what's actually in the manifest"""
    print("\n" + "=" * 60)
    print("TEST 3: Manifest Contents Inspection")
    print("=" * 60)
    print()
    
    builder = CHMtoC2PABuilder(debug_log=False)  # Disable debug for cleaner output
    proof = create_test_session_proof()
    
    manifest_lite = builder.generate_manifest(
        session_proof_json=json.dumps(proof),
        privacy_mode="lite"
    )
    
    manifest_full = builder.generate_manifest(
        session_proof_json=json.dumps(proof),
        privacy_mode="full"
    )
    
    print("LITE MODE Manifest Structure:")
    print(json.dumps(manifest_lite, indent=2))
    print()
    
    print("\nFULL MODE Manifest Structure:")
    print(json.dumps(manifest_full, indent=2))
    print()
    
    # Compare sizes
    lite_size = len(json.dumps(manifest_lite))
    full_size = len(json.dumps(manifest_full))
    
    print(f"Size comparison:")
    print(f"  LITE: {lite_size} bytes")
    print(f"  FULL: {full_size} bytes")
    print(f"  Difference: +{full_size - lite_size} bytes ({((full_size / lite_size - 1) * 100):.1f}% larger)")
    print()
    
    return True

def main():
    """Run all privacy audit tests"""
    print("=" * 60)
    print("C2PA PRIVACY AUDIT")
    print("=" * 60)
    print()
    
    results = []
    
    # Test 1: LITE mode privacy
    results.append(("LITE Mode Privacy", test_privacy_lite_mode()))
    
    # Test 2: FULL mode privacy
    results.append(("FULL Mode Privacy", test_privacy_full_mode()))
    
    # Test 3: Manifest contents
    results.append(("Manifest Inspection", test_manifest_contents()))
    
    # Summary
    print("\n" + "=" * 60)
    print("AUDIT SUMMARY")
    print("=" * 60)
    
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{test_name}: {status}")
    
    all_passed = all(result[1] for result in results)
    
    print()
    if all_passed:
        print("✅ ALL PRIVACY AUDITS PASSED")
        print()
        print("C2PA manifests are privacy-preserving:")
        print("  ✓ No stroke coordinates")
        print("  ✓ No layer names/IDs")
        print("  ✓ No absolute timestamps")
        print("  ✓ No file paths")
        print("  ✓ Only aggregate counts and durations")
        return True
    else:
        print("❌ SOME PRIVACY AUDITS FAILED")
        print()
        print("Review manifest generation code for privacy leaks!")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)



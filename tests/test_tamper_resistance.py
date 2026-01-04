#!/usr/bin/env python3
"""
Tamper Resistance Automated Test Suite

Tests the HMAC signature-based tamper resistance system.
Covers all scenarios from tamper-resistance-testing-guide.md

Run with: python3 tests/test_tamper_resistance.py
"""

import json
import os
import sys
import tempfile
import shutil
import unittest
from pathlib import Path
from typing import Dict, Any, Optional

# Add plugin directory to path
PLUGIN_DIR = Path(__file__).parent.parent / "krita-plugin" / "chm_verifier"
sys.path.insert(0, str(PLUGIN_DIR))

from chm_core import (
    CHMSession,
    set_signing_key,
    _compute_session_signature,
    _verify_session_signature,
    CHMProof
)


class TamperResistanceTestSuite(unittest.TestCase):
    """
    Comprehensive test suite for tamper resistance functionality.
    """
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment once for all tests"""
        print("\n" + "=" * 70)
        print("CHM Plugin - Tamper Resistance Test Suite")
        print("=" * 70)
        
        # Generate a test signing key
        import secrets
        import base64
        cls.test_key_bytes = secrets.token_bytes(32)
        cls.test_key_b64 = base64.b64encode(cls.test_key_bytes).decode('ascii')
        
        print(f"\n[SETUP] Generated test signing key: {cls.test_key_b64[:16]}...{cls.test_key_b64[-16:]}")
        
        # Set the signing key globally
        set_signing_key(cls.test_key_b64)
        print("[SETUP] ✓ Signing key set in chm_core module")
        
        # Create temp directory for test artifacts
        cls.temp_dir = tempfile.mkdtemp(prefix="chm_test_")
        print(f"[SETUP] ✓ Test artifacts directory: {cls.temp_dir}")
        print()
    
    @classmethod
    def tearDownClass(cls):
        """Clean up test environment"""
        print("\n" + "=" * 70)
        print("[CLEANUP] Removing test artifacts...")
        shutil.rmtree(cls.temp_dir, ignore_errors=True)
        print(f"[CLEANUP] ✓ Removed {cls.temp_dir}")
        print("=" * 70 + "\n")
    
    def _create_test_session(self, with_events: bool = True) -> CHMSession:
        """
        Create a test session with sample events.
        
        Args:
            with_events: Whether to add sample events
            
        Returns:
            CHMSession instance
        """
        session = CHMSession(document_id="test_doc_001")
        
        if with_events:
            # Add sample strokes
            session.record_stroke(100.0, 200.0, 0.8, "test_brush", 1234567890.0)
            session.record_stroke(150.0, 250.0, 0.9, "test_brush", 1234567891.0)
            session.record_stroke(200.0, 300.0, 0.7, "test_brush", 1234567892.0)
            
            # Add layer event
            session.record_layer_added("layer_001", "paint", 1234567893.0)
            
            # Add drawing time
            session.add_drawing_time(120)  # 2 minutes
        
        return session
    
    def _generate_test_proof(self, session: Optional[CHMSession] = None) -> Dict[str, Any]:
        """
        Generate a test proof from a session.
        
        Args:
            session: Optional session to use (creates new if None)
            
        Returns:
            Proof data dictionary
        """
        if session is None:
            session = self._create_test_session()
        
        proof = session.finalize()
        return proof.to_dict()
    
    # ========================================================================
    # Test 1: Signing Key Management
    # ========================================================================
    
    def test_01_signing_key_loaded(self):
        """Test that signing key is loaded and accessible"""
        print("\n[TEST-01] Verifying signing key is loaded...")
        
        # The key was set in setUpClass
        # Verify by attempting to generate a signature
        proof_data = self._generate_test_proof()
        
        self.assertIn("signature", proof_data, "Proof should have signature field")
        self.assertIn("signature_version", proof_data, "Proof should have signature_version field")
        self.assertEqual(proof_data["signature_version"], "v1", "Signature version should be v1")
        self.assertIsInstance(proof_data["signature"], str, "Signature should be a string")
        self.assertEqual(len(proof_data["signature"]), 64, "HMAC-SHA256 signature should be 64 hex chars")
        
        print(f"[TEST-01] ✓ Signature present: {proof_data['signature'][:16]}...{proof_data['signature'][-16:]}")
        print("[TEST-01] ✅ PASSED")
    
    def test_02_missing_signing_key_behavior(self):
        """Test that missing signing key is handled gracefully"""
        print("\n[TEST-02] Testing behavior without signing key...")
        
        # Import fresh module to clear global state
        import importlib
        import chm_core
        
        # Save original key
        original_key = chm_core._SIGNING_KEY
        
        try:
            # Clear signing key
            chm_core._SIGNING_KEY = None
            
            # Create session and finalize
            session = self._create_test_session()
            proof = session.finalize()
            proof_data = proof.to_dict()
            
            # Should not have signature if key is missing
            # (Our implementation adds signature=None if key is missing)
            if "signature" in proof_data:
                self.assertIsNone(proof_data["signature"], 
                                "Signature should be None when key is missing")
            
            print("[TEST-02] ✓ Proof generated without signature when key missing")
            print("[TEST-02] ✅ PASSED")
            
        finally:
            # Restore original key
            chm_core._SIGNING_KEY = original_key
    
    # ========================================================================
    # Test 3: Valid Proof Generation
    # ========================================================================
    
    def test_03_valid_proof_generation(self):
        """Test that exported proofs include valid HMAC signatures"""
        print("\n[TEST-03] Testing valid proof generation...")
        
        session = self._create_test_session()
        proof_data = self._generate_test_proof(session)
        
        # Verify proof structure
        self.assertIn("version", proof_data)
        self.assertIn("session_id", proof_data)
        self.assertIn("classification", proof_data)
        self.assertIn("events_hash", proof_data)
        self.assertIn("event_summary", proof_data)
        self.assertIn("signature", proof_data)
        self.assertIn("signature_version", proof_data)
        
        # Verify event summary
        self.assertEqual(proof_data["event_summary"]["stroke_count"], 3)
        self.assertEqual(proof_data["event_summary"]["layer_count"], 2)  # 1 default + 1 added
        
        print(f"[TEST-03] ✓ Proof structure valid")
        print(f"[TEST-03] ✓ Classification: {proof_data['classification']}")
        print(f"[TEST-03] ✓ Events hash: {proof_data['events_hash'][:16]}...")
        print(f"[TEST-03] ✓ Signature: {proof_data['signature'][:16]}...")
        print("[TEST-03] ✅ PASSED")
    
    # ========================================================================
    # Test 4: Signature Verification - Valid Proof
    # ========================================================================
    
    def test_04_signature_verification_valid(self):
        """Test that untampered proofs pass verification"""
        print("\n[TEST-04] Testing signature verification (valid proof)...")
        
        proof_data = self._generate_test_proof()
        
        # Verify signature
        is_valid = _verify_session_signature(proof_data)
        
        self.assertTrue(is_valid, "Valid proof should pass signature verification")
        
        print("[TEST-04] ✓ Signature verification passed")
        print("[TEST-04] ✅ PASSED")
    
    # ========================================================================
    # Test 5: Tampering Detection - Modified Classification
    # ========================================================================
    
    def test_05_tampering_classification(self):
        """Test that modified classification breaks signature"""
        print("\n[TEST-05] Testing tampering detection (classification)...")
        
        proof_data = self._generate_test_proof()
        original_classification = proof_data["classification"]
        
        # Verify original is valid
        self.assertTrue(_verify_session_signature(proof_data), 
                       "Original proof should be valid")
        
        # Tamper with classification
        proof_data["classification"] = "AI-Assisted" if original_classification != "AI-Assisted" else "HumanMade"
        
        # Verify signature is now invalid
        is_valid = _verify_session_signature(proof_data)
        
        self.assertFalse(is_valid, "Modified classification should break signature")
        
        print(f"[TEST-05] ✓ Original: {original_classification}")
        print(f"[TEST-05] ✓ Tampered: {proof_data['classification']}")
        print("[TEST-05] ✓ Tampering detected successfully")
        print("[TEST-05] ✅ PASSED")
    
    # ========================================================================
    # Test 6: Tampering Detection - Modified Event Counts
    # ========================================================================
    
    def test_06_tampering_event_counts(self):
        """Test that modified event counts break signature"""
        print("\n[TEST-06] Testing tampering detection (event counts)...")
        
        proof_data = self._generate_test_proof()
        original_stroke_count = proof_data["event_summary"]["stroke_count"]
        
        # Verify original is valid
        self.assertTrue(_verify_session_signature(proof_data), 
                       "Original proof should be valid")
        
        # Tamper with stroke count
        proof_data["event_summary"]["stroke_count"] = 9999
        
        # Verify signature is now invalid
        is_valid = _verify_session_signature(proof_data)
        
        self.assertFalse(is_valid, "Modified stroke count should break signature")
        
        print(f"[TEST-06] ✓ Original stroke count: {original_stroke_count}")
        print(f"[TEST-06] ✓ Tampered stroke count: {proof_data['event_summary']['stroke_count']}")
        print("[TEST-06] ✓ Tampering detected successfully")
        print("[TEST-06] ✅ PASSED")
    
    # ========================================================================
    # Test 7: Tampering Detection - Modified Events Hash
    # ========================================================================
    
    def test_07_tampering_events_hash(self):
        """Test that modified events hash breaks signature"""
        print("\n[TEST-07] Testing tampering detection (events hash)...")
        
        proof_data = self._generate_test_proof()
        original_hash = proof_data["events_hash"]
        
        # Verify original is valid
        self.assertTrue(_verify_session_signature(proof_data), 
                       "Original proof should be valid")
        
        # Tamper with events hash
        proof_data["events_hash"] = "fake_hash_1234567890abcdef"
        
        # Verify signature is now invalid
        is_valid = _verify_session_signature(proof_data)
        
        self.assertFalse(is_valid, "Modified events hash should break signature")
        
        print(f"[TEST-07] ✓ Original events_hash: {original_hash[:32]}...")
        print(f"[TEST-07] ✓ Tampered events_hash: {proof_data['events_hash']}")
        print("[TEST-07] ✓ Tampering detected successfully")
        print("[TEST-07] ✅ PASSED")
    
    # ========================================================================
    # Test 8: Tampering Detection - Modified Signature
    # ========================================================================
    
    def test_08_tampering_signature(self):
        """Test that modified signature is detected"""
        print("\n[TEST-08] Testing tampering detection (signature itself)...")
        
        proof_data = self._generate_test_proof()
        original_signature = proof_data["signature"]
        
        # Verify original is valid
        self.assertTrue(_verify_session_signature(proof_data), 
                       "Original proof should be valid")
        
        # Tamper with signature
        proof_data["signature"] = "0" * 64  # Fake signature
        
        # Verify signature is now invalid
        is_valid = _verify_session_signature(proof_data)
        
        self.assertFalse(is_valid, "Modified signature should be detected")
        
        print(f"[TEST-08] ✓ Original signature: {original_signature[:16]}...")
        print(f"[TEST-08] ✓ Tampered signature: {proof_data['signature'][:16]}...")
        print("[TEST-08] ✓ Tampering detected successfully")
        print("[TEST-08] ✅ PASSED")
    
    # ========================================================================
    # Test 9: Tampering Detection - Modified Layer Count
    # ========================================================================
    
    def test_09_tampering_layer_count(self):
        """Test that modified layer count breaks signature"""
        print("\n[TEST-09] Testing tampering detection (layer count)...")
        
        proof_data = self._generate_test_proof()
        original_layer_count = proof_data["event_summary"]["layer_count"]
        
        # Verify original is valid
        self.assertTrue(_verify_session_signature(proof_data), 
                       "Original proof should be valid")
        
        # Tamper with layer count
        proof_data["event_summary"]["layer_count"] = 9999
        
        # Verify signature is now invalid
        is_valid = _verify_session_signature(proof_data)
        
        self.assertFalse(is_valid, "Modified layer count should break signature")
        
        print(f"[TEST-09] ✓ Original layer count: {original_layer_count}")
        print(f"[TEST-09] ✓ Tampered layer count: {proof_data['event_summary']['layer_count']}")
        print("[TEST-09] ✓ Tampering detected successfully")
        print("[TEST-09] ✅ PASSED")
    
    # ========================================================================
    # Test 10: Tampering Detection - Modified Import Count
    # ========================================================================
    
    def test_10_tampering_import_count(self):
        """Test that modified import count breaks signature"""
        print("\n[TEST-10] Testing tampering detection (import count)...")
        
        proof_data = self._generate_test_proof()
        original_import_count = proof_data["event_summary"]["import_count"]
        
        # Verify original is valid
        self.assertTrue(_verify_session_signature(proof_data), 
                       "Original proof should be valid")
        
        # Tamper with import count
        proof_data["event_summary"]["import_count"] = 9999
        
        # Verify signature is now invalid
        is_valid = _verify_session_signature(proof_data)
        
        self.assertFalse(is_valid, "Modified import count should break signature")
        
        print(f"[TEST-10] ✓ Original import count: {original_import_count}")
        print(f"[TEST-10] ✓ Tampered import count: {proof_data['event_summary']['import_count']}")
        print("[TEST-10] ✓ Tampering detected successfully")
        print("[TEST-10] ✅ PASSED")
    
    # ========================================================================
    # Test 11: Tampering Detection - Modified AI Tools Metadata
    # ========================================================================
    
    def test_11_tampering_ai_tools(self):
        """Test that modified AI tools metadata breaks signature"""
        print("\n[TEST-11] Testing tampering detection (AI tools metadata)...")
        
        proof_data = self._generate_test_proof()
        original_ai_used = proof_data["metadata"].get("ai_tools_used", False)
        
        # Verify original is valid
        self.assertTrue(_verify_session_signature(proof_data), 
                       "Original proof should be valid")
        
        # Tamper with AI tools metadata
        proof_data["metadata"]["ai_tools_used"] = not original_ai_used
        proof_data["metadata"]["ai_tools_list"] = ["FakeAI"]
        
        # Verify signature is now invalid
        is_valid = _verify_session_signature(proof_data)
        
        self.assertFalse(is_valid, "Modified AI tools metadata should break signature")
        
        print(f"[TEST-11] ✓ Original ai_tools_used: {original_ai_used}")
        print(f"[TEST-11] ✓ Tampered ai_tools_used: {proof_data['metadata']['ai_tools_used']}")
        print("[TEST-11] ✓ Tampering detected successfully")
        print("[TEST-11] ✅ PASSED")
    
    # ========================================================================
    # Test 12: Signature Determinism
    # ========================================================================
    
    def test_12_signature_determinism(self):
        """Test that same proof data produces same signature"""
        print("\n[TEST-12] Testing signature determinism...")
        
        # Create identical sessions
        session1 = self._create_test_session()
        session2 = self._create_test_session()
        
        # Generate proofs
        proof1 = session1.finalize()
        proof2 = session2.finalize()
        
        proof1_data = proof1.to_dict()
        proof2_data = proof2.to_dict()
        
        # Make session IDs and timestamps identical for comparison
        proof2_data["session_id"] = proof1_data["session_id"]
        proof2_data["start_time"] = proof1_data["start_time"]
        proof2_data["end_time"] = proof1_data["end_time"]
        proof2_data["duration_seconds"] = proof1_data["duration_seconds"]
        proof2_data["events_hash"] = proof1_data["events_hash"]
        proof2_data["file_hash"] = proof1_data["file_hash"]
        
        # Recompute signature for proof2 with identical data
        sig1 = _compute_session_signature(proof1_data, "v1")
        sig2 = _compute_session_signature(proof2_data, "v1")
        
        self.assertEqual(sig1, sig2, "Identical proof data should produce identical signatures")
        
        print(f"[TEST-12] ✓ Signature 1: {sig1[:16]}...{sig1[-16:]}")
        print(f"[TEST-12] ✓ Signature 2: {sig2[:16]}...{sig2[-16:]}")
        print("[TEST-12] ✓ Signatures are deterministic")
        print("[TEST-12] ✅ PASSED")
    
    # ========================================================================
    # Test 13: Non-Critical Fields (Should NOT Break Signature)
    # ========================================================================
    
    def test_13_non_critical_fields(self):
        """Test that modifying non-critical fields does NOT break signature"""
        print("\n[TEST-13] Testing non-critical fields (timestamps)...")
        
        proof_data = self._generate_test_proof()
        
        # Verify original is valid
        self.assertTrue(_verify_session_signature(proof_data), 
                       "Original proof should be valid")
        
        # Modify non-critical fields (timestamps, duration, document_id)
        original_start_time = proof_data["start_time"]
        proof_data["start_time"] = "2025-01-01T00:00:00Z"
        proof_data["end_time"] = "2025-01-01T01:00:00Z"
        proof_data["duration_seconds"] = 3600
        proof_data["document_id"] = "different_doc_id"
        
        # Verify signature is STILL valid (these fields not signed)
        is_valid = _verify_session_signature(proof_data)
        
        self.assertTrue(is_valid, "Non-critical fields should not break signature")
        
        print(f"[TEST-13] ✓ Original start_time: {original_start_time}")
        print(f"[TEST-13] ✓ Modified start_time: {proof_data['start_time']}")
        print("[TEST-13] ✓ Signature still valid (timestamps not signed)")
        print("[TEST-13] ✅ PASSED")
    
    # ========================================================================
    # Test 14: Multiple Tamper Attempts
    # ========================================================================
    
    def test_14_multiple_tampering(self):
        """Test detection of multiple simultaneous tampering attempts"""
        print("\n[TEST-14] Testing multiple simultaneous tampering attempts...")
        
        proof_data = self._generate_test_proof()
        
        # Verify original is valid
        self.assertTrue(_verify_session_signature(proof_data), 
                       "Original proof should be valid")
        
        # Tamper with multiple critical fields at once
        proof_data["classification"] = "AI-Assisted"
        proof_data["event_summary"]["stroke_count"] = 9999
        proof_data["events_hash"] = "fake_hash"
        
        # Verify signature is now invalid
        is_valid = _verify_session_signature(proof_data)
        
        self.assertFalse(is_valid, "Multiple tampering should be detected")
        
        print("[TEST-14] ✓ Modified: classification, stroke_count, events_hash")
        print("[TEST-14] ✓ Tampering detected successfully")
        print("[TEST-14] ✅ PASSED")
    
    # ========================================================================
    # Test 15: Proof JSON Serialization/Deserialization
    # ========================================================================
    
    def test_15_proof_serialization(self):
        """Test that proof can be serialized to JSON and deserialized"""
        print("\n[TEST-15] Testing proof JSON serialization/deserialization...")
        
        # Generate proof
        proof = self._generate_test_proof()
        
        # Serialize to JSON
        proof_json = json.dumps(proof, indent=2)
        
        # Deserialize from JSON
        proof_loaded = json.loads(proof_json)
        
        # Verify signature is still valid after round-trip
        is_valid = _verify_session_signature(proof_loaded)
        
        self.assertTrue(is_valid, "Proof should be valid after JSON round-trip")
        
        print(f"[TEST-15] ✓ Serialized proof: {len(proof_json)} bytes")
        print(f"[TEST-15] ✓ Deserialized and verified successfully")
        print("[TEST-15] ✅ PASSED")
    
    # ========================================================================
    # Test 16: File-Based Proof Verification
    # ========================================================================
    
    def test_16_file_based_verification(self):
        """Test verifying proof loaded from file"""
        print("\n[TEST-16] Testing file-based proof verification...")
        
        # Generate proof
        proof_data = self._generate_test_proof()
        
        # Save to file
        proof_file = Path(self.temp_dir) / "test_proof.json"
        with open(proof_file, 'w') as f:
            json.dump(proof_data, f, indent=2)
        
        print(f"[TEST-16] ✓ Saved proof to: {proof_file}")
        
        # Load from file
        with open(proof_file, 'r') as f:
            loaded_proof = json.load(f)
        
        # Verify signature
        is_valid = _verify_session_signature(loaded_proof)
        
        self.assertTrue(is_valid, "Proof loaded from file should be valid")
        
        print("[TEST-16] ✓ Loaded and verified proof from file")
        print("[TEST-16] ✅ PASSED")
    
    # ========================================================================
    # Test 17: AI-Assisted Classification Signature
    # ========================================================================
    
    def test_17_ai_assisted_classification(self):
        """Test signature with AI-Assisted classification"""
        print("\n[TEST-17] Testing AI-Assisted classification signature...")
        
        session = self._create_test_session()
        
        # Mark as AI-assisted
        session.mark_ai_assisted("TestAI")
        
        # Generate proof
        proof_data = self._generate_test_proof(session)
        
        # Verify classification
        self.assertEqual(proof_data["classification"], "AI-Assisted")
        self.assertTrue(proof_data["metadata"]["ai_tools_used"])
        self.assertIn("TestAI", proof_data["metadata"]["ai_tools_list"])
        
        # Verify signature
        is_valid = _verify_session_signature(proof_data)
        self.assertTrue(is_valid, "AI-Assisted proof should have valid signature")
        
        print(f"[TEST-17] ✓ Classification: {proof_data['classification']}")
        print(f"[TEST-17] ✓ AI tools: {proof_data['metadata']['ai_tools_list']}")
        print(f"[TEST-17] ✓ Signature valid")
        print("[TEST-17] ✅ PASSED")
    
    # ========================================================================
    # Test 18: Empty Session Signature
    # ========================================================================
    
    def test_18_empty_session(self):
        """Test signature generation for empty session (no events)"""
        print("\n[TEST-18] Testing empty session signature...")
        
        # Create session without events
        session = self._create_test_session(with_events=False)
        
        # Generate proof
        proof_data = self._generate_test_proof(session)
        
        # Verify event counts
        self.assertEqual(proof_data["event_summary"]["stroke_count"], 0)
        self.assertEqual(proof_data["event_summary"]["total_events"], 0)
        
        # Verify signature is still present and valid
        self.assertIn("signature", proof_data)
        is_valid = _verify_session_signature(proof_data)
        self.assertTrue(is_valid, "Empty session should have valid signature")
        
        print(f"[TEST-18] ✓ Empty session (0 events)")
        print(f"[TEST-18] ✓ Signature: {proof_data['signature'][:16]}...")
        print(f"[TEST-18] ✓ Signature valid")
        print("[TEST-18] ✅ PASSED")
    
    # ========================================================================
    # Test 19: Signature Version Handling
    # ========================================================================
    
    def test_19_signature_version(self):
        """Test signature version field"""
        print("\n[TEST-19] Testing signature version handling...")
        
        proof_data = self._generate_test_proof()
        
        # Verify version field
        self.assertIn("signature_version", proof_data)
        self.assertEqual(proof_data["signature_version"], "v1")
        
        # Compute signature with explicit version
        sig_v1 = _compute_session_signature(proof_data, "v1")
        self.assertEqual(sig_v1, proof_data["signature"])
        
        print(f"[TEST-19] ✓ Signature version: {proof_data['signature_version']}")
        print(f"[TEST-19] ✓ Version included in signature computation")
        print("[TEST-19] ✅ PASSED")
    
    # ========================================================================
    # Test 20: Stress Test - Large Proof
    # ========================================================================
    
    def test_20_large_proof_signature(self):
        """Test signature generation for large proof with many events"""
        print("\n[TEST-20] Testing large proof signature...")
        
        session = CHMSession(document_id="large_test")
        
        # Add many events
        for i in range(1000):
            session.record_stroke(float(i), float(i * 2), 0.5, "test_brush")
        
        for i in range(50):
            session.record_layer_added(f"layer_{i}", "paint")
        
        session.add_drawing_time(3600)  # 1 hour
        
        # Generate proof
        proof_data = self._generate_test_proof(session)
        
        # Verify signature
        self.assertIn("signature", proof_data)
        is_valid = _verify_session_signature(proof_data)
        self.assertTrue(is_valid, "Large proof should have valid signature")
        
        print(f"[TEST-20] ✓ Large proof: {proof_data['event_summary']['total_events']} events")
        print(f"[TEST-20] ✓ Signature: {proof_data['signature'][:16]}...")
        print(f"[TEST-20] ✓ Signature valid")
        print("[TEST-20] ✅ PASSED")


def run_test_suite():
    """
    Run the complete test suite and generate report.
    """
    # Create test suite
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TamperResistanceTestSuite)
    
    # Run tests with verbose output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    print(f"Tests run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print("=" * 70)
    
    # Return exit code
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(run_test_suite())


#!/usr/bin/env python3
"""
Test GitHub Gist Timestamp Service (Pure Python stdlib only)

This script tests the GitHub Gist timestamping functionality using only
Python standard library (no external dependencies).
"""

import sys
import os

# Add parent directory to path to import from krita-plugin
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'krita-plugin'))

from chm_verifier.timestamp_service import TripleTimestampService
import hashlib
from datetime import datetime

def generate_test_hash():
    """Generate a test proof hash"""
    test_data = f"CHM_TEST_PROOF_{datetime.utcnow().isoformat()}"
    return hashlib.sha256(test_data.encode()).hexdigest()

def main():
    print("=" * 60)
    print("GitHub Gist Timestamp Test (Pure Python stdlib)")
    print("=" * 60)
    print()
    
    # Check for GitHub token
    github_token = os.environ.get('CHM_GITHUB_TOKEN')
    if github_token:
        print(f"✓ GitHub token found (length: {len(github_token)})")
        print("  Mode: Authenticated (higher rate limits)")
    else:
        print("ℹ️  No GitHub token found")
        print("  Mode: Anonymous (lower rate limits)")
        print()
        print("To use authenticated mode:")
        print("  export CHM_GITHUB_TOKEN='your_token_here'")
        print()
    
    # Initialize timestamp service
    config = {
        'github_token': github_token,
        'enable_github': True,
        'enable_wayback': False,
        'enable_chm_log': True
    }
    
    print("Initializing timestamp service...")
    service = TripleTimestampService(config=config, debug_log=True)
    print()
    
    # Generate test proof hash
    proof_hash = generate_test_hash()
    print(f"Test proof hash: {proof_hash}")
    print()
    
    # Create test proof context
    proof_dict = {
        'session_id': 'test-session-123',
        'classification': 'HumanMade',
        'file_hash': hashlib.sha256(b'test_file_data').hexdigest()
    }
    
    # Submit to timestamp services
    print("Submitting to timestamp services...")
    print("-" * 60)
    
    try:
        results = service.submit_proof_hash(proof_hash, proof_dict)
        
        print()
        print("=" * 60)
        print("RESULTS")
        print("=" * 60)
        print()
        
        print(f"Success count: {results['success_count']}/2 services")
        print()
        
        if results['github']:
            print("✓ GitHub Gist:")
            print(f"  URL: {results['github']['url']}")
            print(f"  Timestamp: {results['github']['timestamp']}")
            print(f"  Commit SHA: {results['github'].get('commit_sha', 'N/A')}")
        else:
            print("✗ GitHub Gist: Failed")
            if results['errors']:
                for error in results['errors']:
                    if 'GitHub' in error:
                        print(f"  Error: {error}")
        
        print()
        
        if results['chm_log']:
            print("✓ CHM Log:")
            print(f"  Index: {results['chm_log']['log_index']}")
            print(f"  Timestamp: {results['chm_log']['timestamp']}")
        else:
            print("✗ CHM Log: Failed")
        
        print()
        print("=" * 60)
        
        if results['success_count'] >= 1:
            print("✓ Test PASSED - At least one timestamp service succeeded")
        else:
            print("✗ Test FAILED - No timestamp services succeeded")
            
    except Exception as e:
        print()
        print("=" * 60)
        print("ERROR")
        print("=" * 60)
        print(f"Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == '__main__':
    sys.exit(main())


"""
CHM API Client

Handles communication with CHM backend API for:
1. Server-side ED25519 signing (private key never leaves server)
2. GitHub Gist timestamping (GitHub token never leaves server)
3. Proof submission/storage

SECURITY (BUG-015 FIX):
- Plugin NO LONGER handles signing keys or GitHub tokens
- All secrets managed server-side
- Single API call: /api/sign-and-timestamp
"""

import json
import os
from datetime import datetime
import hashlib


class CHMApiClient:
    """Client for CHM backend API (signing + timestamping + storage)"""
    
    def __init__(self, config=None, debug_log=False):
        """
        Initialize API client.
        
        Args:
            config: dict with optional settings:
                - api_url: Backend API URL (default: https://certified-human-made.org)
                - timeout: Request timeout in seconds (default: 30)
            debug_log: bool - enable debug logging
        """
        self.config = config or {}
        self.debug_log = debug_log
        
        # API configuration
        self.api_url = self.config.get('api_url', 'https://certified-human-made.org')
        self.timeout = self.config.get('timeout', 30)
        
        # File paths for local storage (duplicate detection, etc.)
        self.data_dir = os.path.expanduser("~/.local/share/chm")
        os.makedirs(self.data_dir, exist_ok=True)
        
        self.proofs_file = os.path.join(self.data_dir, "submitted_proofs.jsonl")
        self.duplicates_index = os.path.join(self.data_dir, "file_hash_index.json")
        
        self._log(f"[API-INIT] API Client initialized")
        self._log(f"[API-INIT] API URL: {self.api_url}")
        self._log(f"[API-INIT] Timeout: {self.timeout}s")
    
    def sign_and_timestamp(self, proof_data):
        """
        Sign proof and create GitHub timestamp via server API.
        
        SECURITY (BUG-015 FIX):
        - Server holds ED25519 private key (never exposed)
        - Server holds GitHub token (never exposed)
        - Returns signature + gist URL to plugin
        
        Args:
            proof_data: dict - Proof data to sign
        
        Returns:
            dict: {
                'signature': str - ED25519 signature (base64),
                'signature_version': str - 'ed25519-v1',
                'github': dict or None - GitHub gist info,
                'error': str - Error message if failed
            }
        """
        self._log(f"[API-SIGN] === Requesting server-side signing + timestamping ===")
        self._log(f"[API-SIGN] Session ID: {proof_data.get('session_id', 'unknown')[:16]}...")
        self._log(f"[API-SIGN] Classification: {proof_data.get('classification')}")
        
        try:
            # Use stdlib urllib (Krita doesn't have requests library)
            import urllib.request
            import urllib.error
            import ssl
            
            # Prepare request
            url = f"{self.api_url}/api/sign-and-timestamp"
            
            request_data = {
                'proof_data': proof_data
            }
            
            data_bytes = json.dumps(request_data).encode('utf-8')
            
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'CHM-Krita-Plugin/1.0'
            }
            
            req = urllib.request.Request(url, data=data_bytes, headers=headers, method='POST')
            
            self._log(f"[API-SIGN] POSTing to {url}...")
            self._log(f"[API-SIGN] Payload size: {len(data_bytes)} bytes")
            self._log(f"[API-SIGN] Timeout: {self.timeout}s")
            
            # Create SSL context
            ssl_context = ssl.create_default_context()
            
            # Make request
            try:
                with urllib.request.urlopen(req, timeout=self.timeout, context=ssl_context) as response:
                    response_data = response.read().decode('utf-8')
                    result = json.loads(response_data)
                    
                    self._log(f"[API-SIGN] ✓ Server response received")
                    self._log(f"[API-SIGN] ✓ Signature: {result.get('signature', 'MISSING')[:20]}...")
                    self._log(f"[API-SIGN] ✓ Signature version: {result.get('signature_version')}")
                    
                    if result.get('github'):
                        self._log(f"[API-SIGN] ✓ GitHub timestamp: {result['github']['url']}")
                    else:
                        self._log(f"[API-SIGN] ⚠️  No GitHub timestamp (non-fatal)")
                    
                    return result
                    
            except urllib.error.HTTPError as e:
                error_body = e.read().decode('utf-8') if e.fp else 'No error body'
                self._log(f"[API-SIGN] ✗ HTTP Error {e.code}: {error_body}")
                
                # Parse error message
                try:
                    error_data = json.loads(error_body)
                    error_message = error_data.get('message', error_body)
                except:
                    error_message = error_body
                
                return {
                    'error': f"Server error ({e.code}): {error_message}"
                }
                
            except urllib.error.URLError as e:
                self._log(f"[API-SIGN] ✗ Network Error: {e.reason}")
                return {
                    'error': f"Network error: {e.reason}. Check internet connection."
                }
                
            except Exception as e:
                self._log(f"[API-SIGN] ✗ Unexpected error: {e}")
                import traceback
                self._log(f"[API-SIGN] Traceback:\n{traceback.format_exc()}")
                return {
                    'error': f"Signing failed: {str(e)}"
                }
                
        except Exception as e:
            self._log(f"[API-SIGN] ✗ Fatal error: {e}")
            import traceback
            self._log(f"[API-SIGN] Traceback:\n{traceback.format_exc()}")
            return {
                'error': f"Fatal error: {str(e)}"
            }
    
    def submit_proof(self, proof_dict):
        """
        Submit proof to CHM backend/database.
        
        MVP: Logs to local file
        Phase 2: POST to https://api.chm.org/v1/proofs/submit
        
        Args:
            proof_dict: dict - Complete proof data
        
        Returns:
            dict: {
                'status': 'success' or 'error',
                'proof_id': str - session_id,
                'message': str,
                'timestamp': str - ISO format
            }
        """
        try:
            self._log(f"[API] Submitting proof: {proof_dict.get('session_id', 'unknown')}")
            
            # Add submission timestamp
            submission_record = {
                **proof_dict,
                'submitted_at': datetime.utcnow().isoformat() + 'Z',
                'submission_mode': self.mode
            }
            
            if self.mode == 'file_mock':
                return self._submit_to_file(submission_record)
            else:
                # Future: HTTP POST to backend
                return self._submit_to_http(submission_record)
                
        except Exception as e:
            self._log(f"[API] ✗ Submission failed: {e}")
            return {
                'status': 'error',
                'proof_id': proof_dict.get('session_id', 'unknown'),
                'message': f"Submission failed: {e}",
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            }
    
    def _submit_to_file(self, proof_record):
        """
        MVP: Save proof to local JSONL file (one proof per line).
        
        Args:
            proof_record: dict - proof with submission timestamp
        
        Returns:
            dict: success response
        """
        try:
            # Append to JSONL file (newline-delimited JSON)
            with open(self.proofs_file, 'a') as f:
                f.write(json.dumps(proof_record) + '\n')
            
            # Update file hash index for duplicate detection
            self._update_hash_index(proof_record)
            
            self._log(f"[API] ✓ Proof logged to: {self.proofs_file}")
            
            return {
                'status': 'success',
                'proof_id': proof_record['session_id'],
                'message': 'Proof logged locally (MVP - no backend yet)',
                'timestamp': proof_record['submitted_at'],
                'local_file': self.proofs_file
            }
            
        except Exception as e:
            raise Exception(f"File write failed: {e}")
    
    def _submit_to_http(self, proof_record):
        """
        Phase 2: POST proof to backend API.
        
        Args:
            proof_record: dict - proof with submission timestamp
        
        Returns:
            dict: API response
        """
        # TODO: Implement in Phase 2
        # import requests
        # url = self.config.get('api_url', 'https://api.chm.org') + '/v1/proofs/submit'
        # response = requests.post(url, json=proof_record, timeout=30)
        # return response.json()
        
        raise NotImplementedError("HTTP submission not implemented yet (Phase 2)")
    
    def check_duplicate(self, file_hash):
        """
        Check if artwork with this file hash already has a proof.
        
        Args:
            file_hash: str - SHA-256 hash of artwork file
        
        Returns:
            dict or None: Existing proof record if found, None otherwise
        """
        try:
            if not os.path.exists(self.duplicates_index):
                return None
            
            with open(self.duplicates_index, 'r') as f:
                index = json.load(f)
            
            existing = index.get(file_hash)
            
            if existing:
                self._log(f"[API] ⚠️  Duplicate detected: {file_hash[:16]}...")
                return existing
            else:
                self._log(f"[API] ✓ No duplicate found for: {file_hash[:16]}...")
                return None
                
        except Exception as e:
            self._log(f"[API] Duplicate check failed: {e}")
            return None
    
    def _update_hash_index(self, proof_record):
        """
        Update file hash index with new proof.
        
        Args:
            proof_record: dict - proof data
        """
        try:
            # Load existing index
            if os.path.exists(self.duplicates_index):
                with open(self.duplicates_index, 'r') as f:
                    index = json.load(f)
            else:
                index = {}
            
            # Add entry for file_hash
            file_hash = proof_record.get('file_hash')
            if file_hash:
                index[file_hash] = {
                    'session_id': proof_record['session_id'],
                    'classification': proof_record.get('classification', 'Unknown'),
                    'submitted_at': proof_record['submitted_at'],
                    'perceptual_hash': proof_record.get('perceptual_hash')
                }
            
            # Save updated index
            with open(self.duplicates_index, 'w') as f:
                json.dump(index, f, indent=2)
            
            self._log(f"[API] Index updated: {len(index)} proofs tracked")
            
        except Exception as e:
            self._log(f"[API] Index update failed: {e}")
    
    def get_stats(self):
        """
        Get statistics about submitted proofs.
        
        Returns:
            dict: {
                'total_proofs': int,
                'unique_artworks': int (by file hash),
                'classifications': dict (counts per classification)
            }
        """
        try:
            stats = {
                'total_proofs': 0,
                'unique_artworks': 0,
                'classifications': {}
            }
            
            # Count total proofs
            if os.path.exists(self.proofs_file):
                with open(self.proofs_file, 'r') as f:
                    stats['total_proofs'] = sum(1 for _ in f)
            
            # Count unique artworks and classifications
            if os.path.exists(self.duplicates_index):
                with open(self.duplicates_index, 'r') as f:
                    index = json.load(f)
                    stats['unique_artworks'] = len(index)
                    
                    for entry in index.values():
                        cls = entry.get('classification', 'Unknown')
                        stats['classifications'][cls] = stats['classifications'].get(cls, 0) + 1
            
            return stats
            
        except Exception as e:
            self._log(f"[API] Stats failed: {e}")
            return {'error': str(e)}
    
    def _log(self, message):
        """Print debug log if enabled"""
        if self.debug_log:
            print(message)


if __name__ == "__main__":
    # Test API client
    print("Testing CHM API Client...")
    
    client = CHMApiClient(debug_log=True)
    
    # Test proof submission
    test_proof = {
        'session_id': 'test_session_123',
        'file_hash': 'abc123' * 10,  # 60 chars
        'perceptual_hash': 'def456789abcdef0',
        'classification': 'HumanMade',
        'event_summary': {
            'stroke_count': 42,
            'duration_seconds': 300
        }
    }
    
    result = client.submit_proof(test_proof)
    print(f"\nSubmission result: {json.dumps(result, indent=2)}")
    
    # Test duplicate detection
    duplicate = client.check_duplicate(test_proof['file_hash'])
    print(f"\nDuplicate check: {duplicate}")
    
    # Test stats
    stats = client.get_stats()
    print(f"\nStats: {json.dumps(stats, indent=2)}")


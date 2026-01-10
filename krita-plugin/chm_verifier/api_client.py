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
        self._log(f"[API-SIGN] ========================================")
        self._log(f"[API-SIGN] STARTING SERVER SIGNING REQUEST")
        self._log(f"[API-SIGN] ========================================")
        self._log(f"[API-SIGN] Session ID: {proof_data.get('session_id', 'unknown')[:16]}...")
        self._log(f"[API-SIGN] Classification: {proof_data.get('classification')}")
        self._log(f"[API-SIGN] API URL configured: {self.api_url}")
        
        try:
            self._log(f"[API-SIGN] [BFROS-1] Importing urllib modules...")
            # Use stdlib urllib (Krita doesn't have requests library)
            import urllib.request
            import urllib.error
            import ssl
            self._log(f"[API-SIGN] [BFROS-1] ✓ urllib modules imported")
            
            # Prepare request
            url = f"{self.api_url}/api/sign-and-timestamp"
            self._log(f"[API-SIGN] [BFROS-2] Target URL: {url}")
            
            request_data = {
                'proof_data': proof_data
            }
            
            self._log(f"[API-SIGN] [BFROS-3] Encoding request data...")
            data_bytes = json.dumps(request_data).encode('utf-8')
            self._log(f"[API-SIGN] [BFROS-3] ✓ Payload size: {len(data_bytes)} bytes")
            
            headers = {
                'Content-Type': 'application/json',
                'User-Agent': 'CHM-Krita-Plugin/1.0'
            }
            self._log(f"[API-SIGN] [BFROS-4] Headers: {headers}")
            
            self._log(f"[API-SIGN] [BFROS-5] Creating urllib Request object...")
            req = urllib.request.Request(url, data=data_bytes, headers=headers, method='POST')
            self._log(f"[API-SIGN] [BFROS-5] ✓ Request object created")
            
            self._log(f"[API-SIGN] [BFROS-6] Creating SSL context...")
            
            # Multi-strategy SSL context creation (handles Krita's bundled Python)
            ssl_context = None
            ssl_strategy_used = None
            
            # Try certifi first (best cross-platform solution)
            try:
                import certifi
                certifi_path = certifi.where()
                if os.path.isfile(certifi_path):
                    self._log(f"[API-SIGN] [BFROS-6a] Trying certifi package...")
                    ssl_context = ssl.create_default_context(cafile=certifi_path)
                    ssl_strategy_used = "certifi"
                    self._log(f"[API-SIGN] [BFROS-6a] ✓ Using certifi: {certifi_path}")
            except ImportError:
                self._log(f"[API-SIGN] [BFROS-6a] certifi not available")
            except Exception as e:
                self._log(f"[API-SIGN] [BFROS-6a] certifi failed: {e}")
            
            # Fallback: Try default system context
            if not ssl_context:
                try:
                    self._log(f"[API-SIGN] [BFROS-6b] Trying system default SSL context...")
                    ssl_context = ssl.create_default_context()
                    ssl_strategy_used = "system_default"
                    self._log(f"[API-SIGN] [BFROS-6b] ✓ Using system default context")
                except Exception as e:
                    self._log(f"[API-SIGN] [BFROS-6b] System default failed: {e}")
            
            # Last resort: Unverified context (INSECURE but functional)
            # Only for development/testing - logs warning
            if not ssl_context:
                self._log(f"[API-SIGN] [BFROS-6c] ⚠️  FALLBACK: Creating unverified SSL context")
                self._log(f"[API-SIGN] [BFROS-6c] ⚠️  This disables certificate verification!")
                self._log(f"[API-SIGN] [BFROS-6c] ⚠️  Use only for development/testing")
                ssl_context = ssl._create_unverified_context()
                ssl_strategy_used = "unverified"
            
            self._log(f"[API-SIGN] [BFROS-6] ✓ SSL context created using: {ssl_strategy_used}")
            
            self._log(f"[API-SIGN] [BFROS-7] === MAKING HTTP REQUEST ===")
            self._log(f"[API-SIGN] [BFROS-7] URL: {url}")
            self._log(f"[API-SIGN] [BFROS-7] Timeout: {self.timeout}s")
            self._log(f"[API-SIGN] [BFROS-7] About to call urllib.request.urlopen()...")
            
            # Make request
            try:
                with urllib.request.urlopen(req, timeout=self.timeout, context=ssl_context) as response:
                    self._log(f"[API-SIGN] [BFROS-8] ✓ Got response from server!")
                    self._log(f"[API-SIGN] [BFROS-8] HTTP Status: {response.status}")
                    
                    response_data = response.read().decode('utf-8')
                    self._log(f"[API-SIGN] [BFROS-9] ✓ Response body read ({len(response_data)} bytes)")
                    
                    result = json.loads(response_data)
                    self._log(f"[API-SIGN] [BFROS-10] ✓ JSON parsed successfully")
                    
                    self._log(f"[API-SIGN] ✓ Server response received")
                    self._log(f"[API-SIGN] ✓ Signature: {result.get('signature', 'MISSING')[:20]}...")
                    self._log(f"[API-SIGN] ✓ Signature version: {result.get('signature_version')}")
                    
                    if result.get('github'):
                        self._log(f"[API-SIGN] ✓ GitHub timestamp: {result['github']['url']}")
                    else:
                        self._log(f"[API-SIGN] ⚠️  No GitHub timestamp (non-fatal)")
                    
                    self._log(f"[API-SIGN] ========================================")
                    self._log(f"[API-SIGN] REQUEST COMPLETED SUCCESSFULLY")
                    self._log(f"[API-SIGN] ========================================")
                    return result
                    
            except urllib.error.HTTPError as e:
                self._log(f"[API-SIGN] [BFROS-ERROR] ❌ HTTP Error!")
                self._log(f"[API-SIGN] [BFROS-ERROR] Status code: {e.code}")
                self._log(f"[API-SIGN] [BFROS-ERROR] Reason: {e.reason}")
                
                error_body = e.read().decode('utf-8') if e.fp else 'No error body'
                self._log(f"[API-SIGN] [BFROS-ERROR] Error body: {error_body}")
                
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
                self._log(f"[API-SIGN] [BFROS-ERROR] ❌ URL/Network Error!")
                self._log(f"[API-SIGN] [BFROS-ERROR] Error type: {type(e.reason).__name__}")
                self._log(f"[API-SIGN] [BFROS-ERROR] Error reason: {e.reason}")
                self._log(f"[API-SIGN] [BFROS-ERROR] This usually means:")
                self._log(f"[API-SIGN] [BFROS-ERROR]   - DNS resolution failed")
                self._log(f"[API-SIGN] [BFROS-ERROR]   - Server unreachable")
                self._log(f"[API-SIGN] [BFROS-ERROR]   - Connection timeout")
                self._log(f"[API-SIGN] [BFROS-ERROR]   - SSL/TLS handshake failed")
                
                return {
                    'error': f"Network error: {e.reason}. Check internet connection and API URL."
                }
                
            except Exception as e:
                self._log(f"[API-SIGN] [BFROS-ERROR] ❌ Unexpected exception during request!")
                self._log(f"[API-SIGN] [BFROS-ERROR] Exception type: {type(e).__name__}")
                self._log(f"[API-SIGN] [BFROS-ERROR] Exception message: {str(e)}")
                import traceback
                self._log(f"[API-SIGN] [BFROS-ERROR] Traceback:\n{traceback.format_exc()}")
                return {
                    'error': f"Signing failed: {str(e)}"
                }
                
        except Exception as e:
            self._log(f"[API-SIGN] [BFROS-ERROR] ❌ Fatal error in sign_and_timestamp()!")
            self._log(f"[API-SIGN] [BFROS-ERROR] Exception type: {type(e).__name__}")
            self._log(f"[API-SIGN] [BFROS-ERROR] Exception message: {str(e)}")
            import traceback
            self._log(f"[API-SIGN] [BFROS-ERROR] Traceback:\n{traceback.format_exc()}")
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
        """Log debug message to file if enabled"""
        if self.debug_log:
            # Import debug_log from __init__.py to write to file
            try:
                from . import debug_log
                debug_log(message)
            except ImportError:
                # Fallback to print if debug_log not available
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


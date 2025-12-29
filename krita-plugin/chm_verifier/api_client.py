"""
CHM API Client

Handles submission of proofs to CHM backend/database.
MVP: File-based mock (logs to local file)
Phase 2: Replace with actual HTTP POST to backend API
"""

import json
import os
from datetime import datetime
import hashlib


class CHMApiClient:
    """Client for submitting proofs to CHM backend"""
    
    def __init__(self, config=None, debug_log=False):
        """
        Initialize API client.
        
        Args:
            config: dict with optional settings:
                - api_url: Backend API URL (default: mock file-based)
                - timeout: Request timeout in seconds (default: 30)
            debug_log: bool - enable debug logging
        """
        self.config = config or {}
        self.debug_log = debug_log
        
        # MVP: Use file-based mock
        self.mode = self.config.get('mode', 'file_mock')
        
        # File paths for MVP
        self.data_dir = os.path.expanduser("~/.local/share/chm")
        os.makedirs(self.data_dir, exist_ok=True)
        
        self.proofs_file = os.path.join(self.data_dir, "submitted_proofs.jsonl")
        self.duplicates_index = os.path.join(self.data_dir, "file_hash_index.json")
        
        self._log(f"API Client initialized (mode={self.mode})")
    
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
                    'confidence': proof_record.get('confidence', 0.0),
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
        'confidence': 0.95,
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


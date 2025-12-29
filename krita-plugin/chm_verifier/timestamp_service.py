"""
Triple Timestamp Service

Submits proof hashes to three independent timestamp sources:
1. GitHub Gist (public, immutable git history)
2. Internet Archive Wayback Machine (permanent archival) - DEFERRED TO PHASE 2
3. CHM Public Log (self-hosted transparency log)

MVP: GitHub Gist + CHM Log (local file)
Phase 2: Add Wayback Machine (requires hosted URL)
"""

import json
import os
import hashlib
import hmac
from datetime import datetime


class TripleTimestampService:
    """Service for timestamping proof hashes via three independent sources"""
    
    def __init__(self, config=None, debug_log=False):
        """
        Initialize timestamp service.
        
        Args:
            config: dict with optional settings:
                - github_token: GitHub personal access token (optional, for higher rate limits)
                - enable_github: bool (default True)
                - enable_wayback: bool (default False for MVP)
                - enable_chm_log: bool (default True)
            debug_log: bool - enable debug logging
        """
        self.config = config or {}
        self.debug_log = debug_log
        
        self.github_token = self.config.get('github_token')
        self.enable_github = self.config.get('enable_github', True)
        self.enable_wayback = self.config.get('enable_wayback', False)  # Phase 2
        self.enable_chm_log = self.config.get('enable_chm_log', True)
        
        # CHM Log setup (MVP: local file)
        self.data_dir = os.path.expanduser("~/.local/share/chm")
        os.makedirs(self.data_dir, exist_ok=True)
        self.log_file = os.path.join(self.data_dir, "public_timestamp_log.jsonl")
        
        # Secret key for log signatures (MVP: simple HMAC)
        self.log_secret = self._get_or_create_secret()
        
        self._log(f"Timestamp Service initialized (GitHub={self.enable_github}, "
                  f"Wayback={self.enable_wayback}, CHM Log={self.enable_chm_log})")
    
    def submit_proof_hash(self, proof_hash, proof_dict=None):
        """
        Submit proof hash to all enabled timestamp services.
        
        Args:
            proof_hash: str - SHA-256 hash of proof JSON
            proof_dict: dict - optional proof data for context
        
        Returns:
            dict: {
                'github': {...} or None,
                'wayback': {...} or None,
                'chm_log': {...} or None,
                'success_count': int,
                'errors': list
            }
        """
        results = {
            'github': None,
            'wayback': None,
            'chm_log': None,
            'success_count': 0,
            'errors': []
        }
        
        self._log(f"[TIMESTAMP] Submitting proof hash: {proof_hash[:16]}...")
        
        # GitHub Gist submission
        if self.enable_github:
            try:
                results['github'] = self._submit_to_github(proof_hash, proof_dict)
                results['success_count'] += 1
                self._log(f"[TIMESTAMP] ✓ GitHub Gist: {results['github']['url']}")
            except Exception as e:
                error_msg = f"GitHub submission failed: {e}"
                results['errors'].append(error_msg)
                self._log(f"[TIMESTAMP] ✗ {error_msg}")
        
        # Wayback Machine submission (Phase 2)
        if self.enable_wayback:
            try:
                results['wayback'] = self._submit_to_wayback(proof_hash, proof_dict)
                results['success_count'] += 1
                self._log(f"[TIMESTAMP] ✓ Wayback: {results['wayback']['url']}")
            except Exception as e:
                error_msg = f"Wayback submission failed: {e}"
                results['errors'].append(error_msg)
                self._log(f"[TIMESTAMP] ✗ {error_msg}")
        
        # CHM Public Log submission
        if self.enable_chm_log:
            try:
                results['chm_log'] = self._submit_to_chm_log(proof_hash, proof_dict)
                results['success_count'] += 1
                self._log(f"[TIMESTAMP] ✓ CHM Log: index={results['chm_log']['log_index']}")
            except Exception as e:
                error_msg = f"CHM Log submission failed: {e}"
                results['errors'].append(error_msg)
                self._log(f"[TIMESTAMP] ✗ {error_msg}")
        
        self._log(f"[TIMESTAMP] Timestamp submission complete: {results['success_count']}/3 succeeded")
        
        return results
    
    def _submit_to_github(self, proof_hash, proof_dict=None):
        """
        Submit proof hash to GitHub Gist.
        
        Creates a public gist with the proof hash. Git commit timestamp
        provides immutable proof-of-existence.
        
        Args:
            proof_hash: str - hash to timestamp
            proof_dict: dict - optional proof context
        
        Returns:
            dict: {
                'url': str - gist URL,
                'commit_sha': str - first commit SHA,
                'timestamp': str - ISO timestamp,
                'verified': bool
            }
        """
        try:
            import requests
        except ImportError:
            raise Exception("requests library not available (needed for GitHub API)")
        
        # Prepare gist content
        gist_content = {
            "proof_hash": proof_hash,
            "timestamp": datetime.utcnow().isoformat() + 'Z',
            "version": "1.0",
            "service": "CHM - Certified Human-Made"
        }
        
        # Add context if provided (classification, session ID, etc.)
        if proof_dict:
            gist_content['context'] = {
                'session_id': proof_dict.get('session_id'),
                'classification': proof_dict.get('classification'),
                'file_hash': proof_dict.get('file_hash', '')[:16] + '...'  # Truncated
            }
        
        # GitHub Gist API request
        url = "https://api.github.com/gists"
        headers = {
            'Accept': 'application/vnd.github.v3+json'
        }
        
        if self.github_token:
            headers['Authorization'] = f'token {self.github_token}'
        
        gist_data = {
            "description": f"CHM Proof Timestamp: {proof_hash[:16]}...",
            "public": True,
            "files": {
                "chm_proof_timestamp.json": {
                    "content": json.dumps(gist_content, indent=2)
                }
            }
        }
        
        self._log(f"[GITHUB] POSTing to {url}...")
        response = requests.post(url, json=gist_data, headers=headers, timeout=10)
        response.raise_for_status()
        
        result = response.json()
        
        return {
            'url': result['html_url'],
            'commit_sha': result['history'][0]['version'] if result.get('history') else None,
            'timestamp': result.get('created_at', gist_content['timestamp']),
            'verified': True
        }
    
    def _submit_to_wayback(self, proof_hash, proof_dict=None):
        """
        Submit proof hash to Internet Archive Wayback Machine.
        
        PHASE 2: Requires hosted URL (need chm.org to host proof hashes).
        MVP: Not implemented yet.
        
        Args:
            proof_hash: str - hash to timestamp
            proof_dict: dict - optional proof context
        
        Returns:
            dict: Wayback snapshot info
        """
        raise NotImplementedError(
            "Wayback Machine submission requires hosted URL (deferred to Phase 2). "
            "Alternative: Use GitHub Gist URL as Wayback input."
        )
    
    def _submit_to_chm_log(self, proof_hash, proof_dict=None):
        """
        Submit proof hash to CHM Public Transparency Log.
        
        MVP: Append-only local file (JSONL format)
        Phase 2: POST to log.chm.org
        
        Args:
            proof_hash: str - hash to timestamp
            proof_dict: dict - optional proof context
        
        Returns:
            dict: {
                'url': str - log entry URL (file:// for MVP),
                'log_index': int - entry number,
                'timestamp': str - ISO timestamp,
                'signature': str - HMAC signature,
                'verified': bool
            }
        """
        # Get next index
        log_index = self._get_next_log_index()
        
        # Create log entry
        timestamp = datetime.utcnow().isoformat() + 'Z'
        entry = {
            'index': log_index,
            'proof_hash': proof_hash,
            'timestamp': timestamp,
        }
        
        # Add context if provided
        if proof_dict:
            entry['context'] = {
                'session_id': proof_dict.get('session_id'),
                'classification': proof_dict.get('classification')
            }
        
        # Sign entry (MVP: HMAC with secret key)
        entry['signature'] = self._sign_entry(entry)
        
        # Append to log file
        with open(self.log_file, 'a') as f:
            f.write(json.dumps(entry) + '\n')
        
        return {
            'url': f"file://{self.log_file}#index={log_index}",
            'log_index': log_index,
            'timestamp': timestamp,
            'signature': entry['signature'],
            'verified': True
        }
    
    def _get_next_log_index(self):
        """Get next available log index"""
        if not os.path.exists(self.log_file):
            return 1
        
        with open(self.log_file, 'r') as f:
            count = sum(1 for _ in f)
        
        return count + 1
    
    def _sign_entry(self, entry):
        """
        Sign log entry with HMAC-SHA256.
        
        Args:
            entry: dict - log entry (without signature)
        
        Returns:
            str: hex-encoded HMAC signature
        """
        # Create canonical representation
        canonical = json.dumps({
            'index': entry['index'],
            'proof_hash': entry['proof_hash'],
            'timestamp': entry['timestamp']
        }, sort_keys=True)
        
        # Compute HMAC
        signature = hmac.new(
            self.log_secret.encode(),
            canonical.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return signature
    
    def _get_or_create_secret(self):
        """Get or create secret key for log signatures"""
        secret_file = os.path.join(self.data_dir, '.log_secret')
        
        if os.path.exists(secret_file):
            with open(secret_file, 'r') as f:
                return f.read().strip()
        
        # Generate new secret
        import secrets
        secret = secrets.token_hex(32)
        
        with open(secret_file, 'w') as f:
            f.write(secret)
        
        # Set restrictive permissions
        os.chmod(secret_file, 0o600)
        
        return secret
    
    def verify_timestamps(self, timestamps):
        """
        Verify that timestamps are still accessible.
        
        Args:
            timestamps: dict - timestamp results from submit_proof_hash()
        
        Returns:
            dict: {
                'github': bool,
                'wayback': bool,
                'chm_log': bool,
                'all_verified': bool
            }
        """
        verification = {
            'github': False,
            'wayback': False,
            'chm_log': False
        }
        
        # Verify GitHub Gist
        if timestamps.get('github'):
            try:
                import requests
                response = requests.head(timestamps['github']['url'], timeout=5)
                verification['github'] = response.status_code == 200
            except:
                verification['github'] = False
        
        # Verify Wayback snapshot
        if timestamps.get('wayback'):
            try:
                import requests
                response = requests.head(timestamps['wayback']['url'], timeout=5)
                verification['wayback'] = response.status_code == 200
            except:
                verification['wayback'] = False
        
        # Verify CHM Log entry
        if timestamps.get('chm_log'):
            # MVP: Just check file exists
            verification['chm_log'] = os.path.exists(self.log_file)
        
        verification['all_verified'] = all([
            verification['github'] if timestamps.get('github') else True,
            verification['wayback'] if timestamps.get('wayback') else True,
            verification['chm_log'] if timestamps.get('chm_log') else True
        ])
        
        return verification
    
    def _log(self, message):
        """Print debug log if enabled"""
        if self.debug_log:
            print(message)


if __name__ == "__main__":
    # Test timestamp service
    print("Testing Triple Timestamp Service...")
    
    service = TripleTimestampService(debug_log=True)
    
    # Test proof hash
    test_proof = {
        'session_id': 'test_session_456',
        'classification': 'HumanMade',
        'file_hash': 'abc123' * 10
    }
    
    proof_hash = hashlib.sha256(json.dumps(test_proof).encode()).hexdigest()
    print(f"\nProof hash: {proof_hash[:32]}...")
    
    # Submit timestamps
    results = service.submit_proof_hash(proof_hash, test_proof)
    print(f"\nTimestamp results:")
    print(json.dumps(results, indent=2))
    
    # Verify timestamps
    verification = service.verify_timestamps(results)
    print(f"\nVerification: {verification}")


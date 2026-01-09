"""
Immutable Timestamp Service

Submits proof hashes to create verifiable, tamper-proof timestamps:
1. GitHub Gist (primary) - Public, third-party verified, immutable Git commit history
2. CHM Local Log (secondary) - HMAC-SHA256 signed append-only local log

GitHub Gist provides true non-repudiation (not user-controlled).
Local log provides integrity verification and offline access.

Future: Internet Archive Wayback Machine integration may be added (requires hosted URL).
"""

import json
import os
import hashlib
import hmac
from datetime import datetime


class TripleTimestampService:
    """
    Service for timestamping proof hashes via GitHub Gist (primary) and local CHM log (secondary).
    
    Note: Class name kept as 'TripleTimestampService' for backwards compatibility,
    but currently implements dual timestamp system (GitHub Gist + local log).
    """
    
    def __init__(self, config=None, debug_log=False, logger_func=None):
        """
        Initialize timestamp service.
        
        Args:
            config: dict with optional settings:
                - github_token: GitHub personal access token (optional, for higher rate limits)
                - enable_github: bool (default True)
                - enable_wayback: bool (default False for MVP)
                - enable_chm_log: bool (default True)
            debug_log: bool - enable debug logging
            logger_func: callable - custom logging function (optional, defaults to print)
        """
        self.config = config or {}
        self.debug_log = debug_log
        self.logger_func = logger_func  # Custom logger (e.g., CHM's _debug_log)
        
        self._log("[TIMESTAMP-INIT] === Initializing Timestamp Service ===")
        self._log(f"[TIMESTAMP-INIT] Config received: {self.config}")
        self._log(f"[TIMESTAMP-INIT] Debug logging: {self.debug_log}")
        
        self.github_token = self.config.get('github_token')
        self.enable_github = self.config.get('enable_github', True)
        self.enable_wayback = self.config.get('enable_wayback', False)  # Phase 2
        self.enable_chm_log = self.config.get('enable_chm_log', True)
        
        self._log(f"[TIMESTAMP-INIT] github_token present: {bool(self.github_token)}")
        if self.github_token:
            self._log(f"[TIMESTAMP-INIT] github_token length: {len(self.github_token)}")
        self._log(f"[TIMESTAMP-INIT] enable_github: {self.enable_github}")
        self._log(f"[TIMESTAMP-INIT] enable_wayback: {self.enable_wayback}")
        self._log(f"[TIMESTAMP-INIT] enable_chm_log: {self.enable_chm_log}")
        
        # CHM Log setup (MVP: local file)
        self.data_dir = os.path.expanduser("~/.local/share/chm")
        os.makedirs(self.data_dir, exist_ok=True)
        self.log_file = os.path.join(self.data_dir, "public_timestamp_log.jsonl")
        
        # Secret key for log signatures (MVP: simple HMAC)
        self.log_secret = self._get_or_create_secret()
        
        self._log(f"[TIMESTAMP-INIT] Timestamp Service initialized (GitHub={self.enable_github}, "
                  f"Wayback={self.enable_wayback}, CHM Log={self.enable_chm_log})")
        self._log("[TIMESTAMP-INIT] === Initialization complete ===")

    
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
        self._log(f"[TIMESTAMP] enable_github flag: {self.enable_github}")
        self._log(f"[TIMESTAMP] enable_wayback flag: {self.enable_wayback}")
        self._log(f"[TIMESTAMP] enable_chm_log flag: {self.enable_chm_log}")
        
        # GitHub Gist submission
        if self.enable_github:
            self._log(f"[TIMESTAMP-DEBUG] GitHub enabled, attempting submission...")
            self._log(f"[TIMESTAMP-DEBUG] Token available: {'yes' if self.github_token else 'no'}")
            if self.github_token:
                self._log(f"[TIMESTAMP-DEBUG] Token length: {len(self.github_token)}")
            try:
                self._log(f"[TIMESTAMP-DEBUG] Calling _submit_to_github()...")
                results['github'] = self._submit_to_github(proof_hash, proof_dict)
                self._log(f"[TIMESTAMP-DEBUG] _submit_to_github() returned: {type(results['github'])}")
                self._log(f"[TIMESTAMP-DEBUG] GitHub result: {results['github']}")
                results['success_count'] += 1
                self._log(f"[TIMESTAMP] ✓ GitHub Gist: {results['github']['url']}")
            except Exception as e:
                error_msg = f"GitHub submission failed: {str(e)}"
                results['errors'].append(error_msg)
                self._log(f"[TIMESTAMP] ✗ {error_msg}")
                self._log(f"[TIMESTAMP-DEBUG] Error type: {type(e).__name__}")
                self._log(f"[TIMESTAMP-DEBUG] Error str: {str(e)}")
                # Add full traceback for debugging
                import traceback
                self._log(f"[TIMESTAMP-DEBUG] GitHub error traceback:\n{traceback.format_exc()}")
        else:
            self._log(f"[TIMESTAMP] GitHub submission SKIPPED (enable_github={self.enable_github})")
        
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
        
        self._log(f"[TIMESTAMP] Timestamp submission complete: {results['success_count']}/2 succeeded")
        
        return results
    
    def _submit_to_github(self, proof_hash, proof_dict=None):
        """
        Submit proof hash to GitHub Gist.
        
        Creates a public gist with the proof hash. Git commit timestamp
        provides immutable proof-of-existence.
        
        Uses stdlib urllib (no external dependencies like requests).
        
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
        self._log("[GITHUB-SUBMIT] === Starting GitHub Gist submission ===")
        
        # Use stdlib urllib instead of requests (Krita doesn't have requests)
        try:
            self._log("[GITHUB-SUBMIT] Importing urllib modules...")
            import urllib.request
            import urllib.error
            import ssl
            self._log("[GITHUB-SUBMIT] ✓ urllib modules imported")
        except Exception as e:
            self._log(f"[GITHUB-SUBMIT] ✗ Failed to import urllib: {e}")
            raise
        
        # Create SSL context (for cross-platform certificate handling)
        try:
            self._log("[GITHUB-SUBMIT] Creating SSL context...")
            
            # DIAGNOSTIC: Check for certifi package (Python SSL cert bundle)
            certifi_available = False
            certifi_path = None
            try:
                import certifi
                certifi_available = True
                certifi_path = certifi.where()
                self._log(f"[SSL-DIAG] certifi package available: {certifi_path}")
            except ImportError:
                self._log("[SSL-DIAG] certifi package NOT available")
            
            # DIAGNOSTIC: Check system SSL paths
            import os
            import platform
            system_info = platform.system()
            self._log(f"[SSL-DIAG] Operating system: {system_info}")
            
            system_cert_paths = [
                '/etc/ssl/cert.pem',  # macOS
                '/etc/ssl/certs/ca-certificates.crt',  # Linux
                '/etc/pki/tls/certs/ca-bundle.crt',  # RedHat/CentOS
            ]
            
            # Windows certificate paths (system cert store)
            if system_info == 'Windows':
                self._log("[SSL-DIAG] Windows detected - will use system cert store")
            
            self._log("[SSL-DIAG] Checking system certificate paths:")
            for cert_path in system_cert_paths:
                exists = os.path.isfile(cert_path)
                self._log(f"[SSL-DIAG]   {cert_path}: {'EXISTS' if exists else 'NOT FOUND'}")
            
            # Try multiple SSL context creation strategies
            ssl_context = None
            ssl_strategy_used = None
            
            # Strategy 1: Use certifi if available (best for Windows)
            if certifi_available and certifi_path and os.path.isfile(certifi_path):
                self._log("[SSL-STRATEGY-1] Trying certifi package...")
                try:
                    ssl_context = ssl.create_default_context(cafile=certifi_path)
                    ssl_strategy_used = "certifi"
                    self._log("[SSL-STRATEGY-1] ✓ SSL context created with certifi")
                except Exception as e:
                    self._log(f"[SSL-STRATEGY-1] ✗ certifi failed: {e}")
            
            # Strategy 2: Use default context (system certs) - works on macOS/Linux
            if not ssl_context:
                self._log("[SSL-STRATEGY-2] Trying default system context...")
                try:
                    ssl_context = ssl.create_default_context()
                    ssl_strategy_used = "system_default"
                    self._log("[SSL-STRATEGY-2] ✓ SSL context created with system certs")
                except Exception as e:
                    self._log(f"[SSL-STRATEGY-2] ✗ Default context failed: {e}")
            
            # Strategy 3: Windows-specific - load system certs manually
            if not ssl_context and system_info == 'Windows':
                self._log("[SSL-STRATEGY-3] Trying Windows cert store import...")
                try:
                    ssl_context = ssl.create_default_context()
                    # On Windows, Python should automatically use the system cert store
                    # But we'll explicitly set minimum TLS version for compatibility
                    ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2
                    ssl_strategy_used = "windows_certstore"
                    self._log("[SSL-STRATEGY-3] ✓ SSL context with Windows cert store")
                except Exception as e:
                    self._log(f"[SSL-STRATEGY-3] ✗ Windows cert store failed: {e}")
            
            # Strategy 4: Unverified context (FALLBACK - less secure but functional)
            if not ssl_context:
                self._log("[SSL-STRATEGY-4] ⚠️  FALLBACK: Using unverified SSL context")
                self._log("[SSL-STRATEGY-4] ⚠️  This disables certificate verification")
                self._log("[SSL-STRATEGY-4] ⚠️  Connection is encrypted but not authenticated")
                ssl_context = ssl._create_unverified_context()
                ssl_strategy_used = "unverified"
                self._log("[SSL-STRATEGY-4] ✓ Unverified SSL context created")
            
            self._log(f"[GITHUB-SUBMIT] ✓ SSL context created successfully (strategy: {ssl_strategy_used})")
            
        except Exception as e:
            self._log(f"[GITHUB-SUBMIT] ✗ Failed to create SSL context: {e}")
            raise
        
        # Prepare gist content with comprehensive proof details
        gist_content = {
            "proof_hash": proof_hash,
            "timestamp": datetime.utcnow().isoformat() + 'Z',
            "version": "1.0",
            "service": "CHM - Certified Human-Made"
        }
        
        # Add comprehensive proof details if provided
        if proof_dict:
            event_summary = proof_dict.get('event_summary', {})
            
            # Prepare metadata without sensitive info (os_info removed for privacy)
            metadata = proof_dict.get('metadata', {}).copy()
            metadata.pop('os_info', None)  # Remove OS info from public gist
            
            # Extract AI tools info
            # Determine AI tools status: 'None', 'Disabled', or 'Yes'
            ai_tools_used = metadata.get('ai_tools_used', False)
            ai_plugins_detected = metadata.get('ai_plugins_detected', False)
            
            if ai_tools_used:
                ai_tools_status = 'Yes'
            elif ai_plugins_detected:
                ai_tools_status = 'Disabled'
            else:
                ai_tools_status = 'None'
            
            gist_content['proof_details'] = {
                # Classification
                'classification': proof_dict.get('classification', 'Unknown'),
                
                # Session info
                'session_id': proof_dict.get('session_id'),
                'document_id': proof_dict.get('document_id'),
                
                # Timing
                'start_time': proof_dict.get('start_time'),
                'end_time': proof_dict.get('end_time'),
                'session_seconds': proof_dict.get('duration_seconds', 0),  # Renamed from duration_seconds
                'drawing_time': event_summary.get('drawing_time_secs', 0),  # Added drawing_time
                
                # Event statistics
                'total_events': event_summary.get('total_events', 0),
                'stroke_count': event_summary.get('stroke_count', 0),
                'layer_count': event_summary.get('layer_count', 0),
                'import_count': event_summary.get('import_count', 0),
                
                # AI tools status: 'None', 'Disabled', or 'Yes'
                'ai_tools': ai_tools_status,
                
                # Hashes (full, not truncated)
                'file_hash': proof_dict.get('file_hash', 'N/A'),
                'events_hash': proof_dict.get('events_hash', 'N/A'),
                
                # Metadata (without sensitive info)
                'metadata': metadata
            }
        
        # GitHub Gist API request
        url = "https://api.github.com/gists"
        headers = {
            'Accept': 'application/vnd.github.v3+json',
            'Content-Type': 'application/json',
            'User-Agent': 'CHM-Krita-Plugin/1.0'
        }
        
        if self.github_token:
            headers['Authorization'] = f'token {self.github_token}'
        
        # Create descriptive gist title with key details
        if proof_dict:
            classification = proof_dict.get('classification', 'Unknown')
            duration = proof_dict.get('duration_seconds', 0)
            stroke_count = proof_dict.get('event_summary', {}).get('stroke_count', 0)
            description = f"CHM Proof: {classification} - {duration}s, {stroke_count} strokes - Hash: {proof_hash[:16]}..."
        else:
            description = f"CHM Proof Timestamp: {proof_hash[:16]}..."
        
        gist_data = {
            "description": description,
            "public": True,
            "files": {
                "chm_proof_timestamp.json": {
                    "content": json.dumps(gist_content, indent=2)
                }
            }
        }
        
        # Convert to bytes for urllib
        data_bytes = json.dumps(gist_data).encode('utf-8')
        
        # Create request
        req = urllib.request.Request(url, data=data_bytes, headers=headers, method='POST')
        
        self._log(f"[GITHUB] POSTing to {url}...")
        self._log(f"[GITHUB] Using token: {'yes' if self.github_token else 'no (anonymous)'}")
        
        try:
            with urllib.request.urlopen(req, timeout=10, context=ssl_context) as response:
                response_data = response.read().decode('utf-8')
                result = json.loads(response_data)
                
                self._log(f"[GITHUB] ✓ Gist created: {result.get('html_url', 'unknown')}")
                
                # BUG#009 DEBUG: Log what hash was stored in the gist
                if proof_dict:
                    stored_hash = gist_content.get('proof_details', {}).get('file_hash', 'MISSING')
                    self._log(f"[GITHUB-DEBUG] File hash stored in gist: {stored_hash[:40] if stored_hash != 'MISSING' else 'MISSING'}...")
                    self._log(f"[GITHUB-DEBUG] Classification: {gist_content.get('proof_details', {}).get('classification', 'MISSING')}")
                    self._log(f"[GITHUB-DEBUG] Session ID: {gist_content.get('proof_details', {}).get('session_id', 'MISSING')}")
                
                return {
                    'url': result['html_url'],
                    'commit_sha': result['history'][0]['version'] if result.get('history') else None,
                    'timestamp': result.get('created_at', gist_content['timestamp']),
                    'verified': True
                }
        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8') if e.fp else 'No error body'
            self._log(f"[GITHUB] HTTP Error {e.code}: {error_body}")
            # More descriptive error messages
            if e.code == 401:
                raise Exception(f"GitHub authentication failed (code {e.code}). Check API token.")
            elif e.code == 403:
                raise Exception(f"GitHub rate limit or permissions issue (code {e.code})")
            elif e.code == 404:
                raise Exception(f"GitHub API endpoint not found (code {e.code})")
            else:
                raise Exception(f"GitHub API HTTP error {e.code}: {error_body[:100]}")
        except urllib.error.URLError as e:
            self._log(f"[GITHUB] URL Error: {e.reason}")
            # More descriptive error for common SSL/network issues
            error_str = str(e.reason)
            if 'certificate' in error_str.lower() or 'ssl' in error_str.lower():
                raise Exception(f"SSL certificate error: {error_str}. Try installing certifi package.")
            elif 'timed out' in error_str.lower() or 'timeout' in error_str.lower():
                raise Exception(f"Network timeout connecting to GitHub: {error_str}")
            else:
                raise Exception(f"GitHub connection failed: {error_str}")
        except ssl.SSLError as e:
            self._log(f"[GITHUB] SSL Error: {e}")
            raise Exception(f"SSL/TLS error: {str(e)}. Certificate validation may have failed.")
        except Exception as e:
            self._log(f"[GITHUB] Unexpected error: {e}")
            self._log(f"[GITHUB] Error type: {type(e).__name__}")
            import traceback
            self._log(f"[GITHUB] Traceback:\n{traceback.format_exc()}")
            raise Exception(f"{type(e).__name__}: {str(e)}")
    
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
        
        Uses stdlib urllib (no external dependencies).
        
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
        import urllib.request
        import urllib.error
        import ssl
        
        # Create SSL context
        ssl_context = ssl.create_default_context()
        
        verification = {
            'github': False,
            'wayback': False,
            'chm_log': False
        }
        
        # Verify GitHub Gist
        if timestamps.get('github'):
            try:
                req = urllib.request.Request(
                    timestamps['github']['url'],
                    method='HEAD'
                )
                with urllib.request.urlopen(req, timeout=5, context=ssl_context) as response:
                    verification['github'] = (response.status == 200)
            except:
                verification['github'] = False
        
        # Verify Wayback snapshot
        if timestamps.get('wayback'):
            try:
                req = urllib.request.Request(
                    timestamps['wayback']['url'],
                    method='HEAD'
                )
                with urllib.request.urlopen(req, timeout=5, context=ssl_context) as response:
                    verification['wayback'] = (response.status == 200)
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
            if self.logger_func:
                # Use custom logger (e.g., CHM's _debug_log that writes to file)
                self.logger_func(message)
            else:
                # Fallback to print
                print(message)


if __name__ == "__main__":
    # Test timestamp service
    print("Testing Timestamp Service (GitHub Gist + Local Log)...")
    
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


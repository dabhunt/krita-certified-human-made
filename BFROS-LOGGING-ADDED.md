# ✅ BFROS Logging Added - Ready for Diagnosis

**Date:** 2026-01-10  
**Commit:** 1976c7d  
**Status:** Ready for testing

---

## 🔍 What Was Fixed

### Problem Identified

The plugin was trying to use production backend but **no logs were appearing** because:

1. **`log_config_on_startup()`** used `print()` which doesn't write to Krita's log file
2. **`api_client._log()`** used `print()` which doesn't write to file
3. **No step-by-step logging** in the API request flow

Result: Impossible to diagnose WHERE the request was failing!

### Solution Implemented

Added **comprehensive BFROS (Binary Search for Root of Source) logging** at every step:

#### 1. Configuration Logging (Fixed)

**Before:**
```python
def log_config_on_startup():
    print("[CONFIG] ...") # ← Never appears in log file!
```

**After:**
```python
def log_config_on_startup(logger_func=None):
    log = logger_func if logger_func else print
    log("[CONFIG] Environment: production")
    log("[CONFIG] API_URL: https://certified-human-made.org")
    # ... etc
```

Now logs will appear in `plugin_debug.log`!

#### 2. API Client Logging (Fixed)

**Before:**
```python
def _log(self, message):
    if self.debug_log:
        print(message)  # ← Never appears in log file!
```

**After:**
```python
def _log(self, message):
    if self.debug_log:
        from . import debug_log
        debug_log(message)  # ← Writes to file!
```

#### 3. BFROS Checkpoints Added

Added 10 checkpoints in the request flow:

```
[BFROS-1] Importing urllib modules
[BFROS-2] Target URL created
[BFROS-3] Encoding request data
[BFROS-4] Headers prepared
[BFROS-5] Request object created
[BFROS-6] SSL context created
[BFROS-7] === MAKING HTTP REQUEST ===
[BFROS-8] Got response from server
[BFROS-9] Response body read
[BFROS-10] JSON parsed
```

Plus detailed error logging:
```
[BFROS-ERROR] Error type, reason, diagnostic hints
```

---

## 🧪 How to Test

### 1. Restart Krita

```bash
# Kill Krita if running
pkill -9 Krita

# Start fresh
open -a Krita
```

### 2. Create Simple Drawing

1. New document
2. Draw a few strokes
3. File → Export

### 3. Try Export with CHM Proof

Click "Export with CHM Proof"

### 4. Check Logs

```bash
tail -100 ~/.local/share/chm/plugin_debug.log
```

---

## 📋 What You Should See in Logs

### On Plugin Startup

```
[CONFIG] ================================
[CONFIG] CHM Plugin Environment Config
[CONFIG] ================================
[CONFIG] Environment: production
[CONFIG] IS_PRODUCTION: True
[CONFIG] IS_DEVELOPMENT: False
[CONFIG] API_URL: https://certified-human-made.org
[CONFIG] API_URL source: DEFAULT_API_URL (from CHM_ENV=production)
[CONFIG] CHM_ENV source: Default (production)
[CONFIG] ================================
```

### On Export Attempt

```
[API-SIGN] ========================================
[API-SIGN] STARTING SERVER SIGNING REQUEST
[API-SIGN] ========================================
[API-SIGN] Session ID: 96e0b331...
[API-SIGN] Classification: HumanMade
[API-SIGN] API URL configured: https://certified-human-made.org
[API-SIGN] [BFROS-1] Importing urllib modules...
[API-SIGN] [BFROS-1] ✓ urllib modules imported
[API-SIGN] [BFROS-2] Target URL: https://certified-human-made.org/api/sign-and-timestamp
[API-SIGN] [BFROS-3] Encoding request data...
[API-SIGN] [BFROS-3] ✓ Payload size: 1234 bytes
[API-SIGN] [BFROS-4] Headers: {'Content-Type': 'application/json', 'User-Agent': 'CHM-Krita-Plugin/1.0'}
[API-SIGN] [BFROS-5] Creating urllib Request object...
[API-SIGN] [BFROS-5] ✓ Request object created
[API-SIGN] [BFROS-6] Creating SSL context...
[API-SIGN] [BFROS-6] ✓ SSL context created
[API-SIGN] [BFROS-7] === MAKING HTTP REQUEST ===
[API-SIGN] [BFROS-7] URL: https://certified-human-made.org/api/sign-and-timestamp
[API-SIGN] [BFROS-7] Timeout: 30s
[API-SIGN] [BFROS-7] About to call urllib.request.urlopen()...
```

**Then one of:**

#### Success Case:
```
[API-SIGN] [BFROS-8] ✓ Got response from server!
[API-SIGN] [BFROS-8] HTTP Status: 200
[API-SIGN] [BFROS-9] ✓ Response body read (XYZ bytes)
[API-SIGN] [BFROS-10] ✓ JSON parsed successfully
[API-SIGN] ✓ Server response received
[API-SIGN] ✓ Signature: abc123...
[API-SIGN] ✓ GitHub timestamp: https://gist.github.com/...
```

#### DNS/Network Failure Case:
```
[API-SIGN] [BFROS-ERROR] ❌ URL/Network Error!
[API-SIGN] [BFROS-ERROR] Error type: gaierror
[API-SIGN] [BFROS-ERROR] Error reason: [Errno 8] nodename nor servname provided, or not known
[API-SIGN] [BFROS-ERROR] This usually means:
[API-SIGN] [BFROS-ERROR]   - DNS resolution failed
[API-SIGN] [BFROS-ERROR]   - Server unreachable
[API-SIGN] [BFROS-ERROR]   - Connection timeout
[API-SIGN] [BFROS-ERROR]   - SSL/TLS handshake failed
```

#### HTTP Error Case:
```
[API-SIGN] [BFROS-ERROR] ❌ HTTP Error!
[API-SIGN] [BFROS-ERROR] Status code: 404
[API-SIGN] [BFROS-ERROR] Reason: Not Found
[API-SIGN] [BFROS-ERROR] Error body: {"message": "Endpoint not found"}
```

---

## 🔍 Diagnosing the Issue

### If Logs Stop at BFROS-7

**Problem:** Request never sent or connection failed immediately

**Possible causes:**
- DNS resolution failed (`certified-human-made.org` doesn't resolve)
- Network connectivity issue
- Firewall blocking outbound HTTPS

**Next steps:**
```bash
# Test DNS
nslookup certified-human-made.org

# Test connectivity
curl -v https://certified-human-made.org

# Test API endpoint
curl -X POST https://certified-human-made.org/api/sign-and-timestamp \
  -H "Content-Type: application/json" \
  -d '{"proof_data": {}}'
```

### If Logs Show URLError

**Problem:** Network-level failure

**Common reasons:**
1. Domain doesn't resolve (DNS issue)
2. Server not running
3. Wrong URL
4. SSL certificate issue

**Solutions:**
- Verify `certified-human-made.org` points to Replit
- Use Replit URL directly: `./debug/test-prod-backend.sh https://your-repl.replit.app`

### If Logs Show HTTPError

**Problem:** Server received request but returned error

**Common codes:**
- `404` - Endpoint not found (wrong URL path)
- `500` - Server error
- `502/503` - Server down or restarting

**Solutions:**
- Check Replit server is running
- Check server logs on Replit
- Verify endpoint exists: `/api/sign-and-timestamp`

---

## 📞 Share Logs for Diagnosis

After testing, share these logs:

```bash
# Get configuration
grep "\[CONFIG\]" ~/.local/share/chm/plugin_debug.log | tail -20

# Get API attempt
grep "\[API-SIGN\]" ~/.local/share/chm/plugin_debug.log | tail -50

# Get BFROS checkpoints
grep "BFROS" ~/.local/share/chm/plugin_debug.log | tail -30

# Or get everything from last export
tail -200 ~/.local/share/chm/plugin_debug.log | grep -A 5 "EXPORT WITH CHM PROOF"
```

---

## 🎯 Expected Outcome

After restarting Krita and testing export, logs should show **EXACTLY WHERE** the request fails:

- **BFROS-1 to BFROS-6**: Setup (should all succeed)
- **BFROS-7**: Making request (critical checkpoint)
- **BFROS-8+**: Response received (if successful)
- **BFROS-ERROR**: Failure details (if unsuccessful)

With this logging, we can pinpoint:
1. Is it DNS?
2. Is it network connectivity?
3. Is it server error?
4. Is it SSL?
5. Is it wrong URL?

---

## ✅ Summary

**What was added:**
1. ✅ Configuration logging to file (was going to stdout)
2. ✅ API client logging to file (was going to stdout)
3. ✅ 10 BFROS checkpoints in request flow
4. ✅ Detailed error diagnostics with hints

**What to do:**
1. Restart Krita
2. Test export
3. Check logs: `tail -100 ~/.local/share/chm/plugin_debug.log`
4. Share log output showing BFROS checkpoints

**Files changed:**
- `krita-plugin/chm_verifier/config.py` - Fixed logging function
- `krita-plugin/chm_verifier/chm_extension.py` - Pass logger to config
- `krita-plugin/chm_verifier/api_client.py` - Comprehensive BFROS logging

**Commit:** `1976c7d`

---

Now we'll be able to see **exactly** where the request is failing! 🔍


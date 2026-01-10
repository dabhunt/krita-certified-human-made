# ✅ Environment Configuration System - Ready for Testing!

**Date:** 2026-01-10  
**Status:** Complete and tested  
**Committed:** Yes (commit 1371b31)

---

## 🎉 What's New

You now have a **seamless way to test your Krita plugin** against different backend environments without creating release builds!

### The Problem (Solved!)

- ❌ Production releases were failing because plugin defaulted to `localhost:5000`
- ❌ Hard to test dev plugin against production backend
- ❌ No validation that releases used correct configuration
- ❌ Difficult to diagnose configuration issues

### The Solution

- ✅ Plugin now defaults to production (safe for releases)
- ✅ Easy testing against any backend (one command!)
- ✅ Automatic validation in release packaging
- ✅ Comprehensive diagnostic tools

---

## 🚀 Quick Start - Test Right Now!

### Test Your Dev Plugin Against Production

```bash
cd /Users/david/Documents/GitHub/krita-certified-human-made
./debug/test-prod-backend.sh
```

**That's it!** The script will:
1. Configure plugin for production backend
2. Build the plugin
3. Update your Krita installation
4. Tell you what to test

Then just:
1. Restart Krita
2. Create a simple drawing
3. File → Export with CHM Proof
4. Check the logs:
   ```bash
   tail -50 ~/.local/share/chm/plugin_debug.log | grep -E "\[CONFIG\]|\[API-"
   ```

You should see:
```
[CONFIG] Environment: production
[CONFIG] API_URL: https://certified-human-made.org
[API-SIGN] POSTing to https://certified-human-made.org/api/sign-and-timestamp...
[API-SIGN] ✓ Server response received
[API-SIGN] ✓ Signature: ...
[API-SIGN] ✓ GitHub timestamp: https://gist.github.com/...
```

**Success!** Your dev plugin is talking to production backend! 🎉

---

## 📋 All Available Commands

### Check Current Configuration

```bash
./debug/show-current-config.sh
```

Shows:
- Environment variables
- Config file defaults
- Resolved configuration
- Connectivity test
- Recommendations

### Test Against Different Backends

```bash
# Test against production (certified-human-made.org)
./debug/test-prod-backend.sh

# Test against Replit
./debug/test-prod-backend.sh https://your-repl-name.replit.app

# Test against local server
./debug/test-local-backend.sh

# Test against custom URL
./debug/test-local-backend.sh http://192.168.1.100:5000
```

### Manual Environment Switching

```bash
# Switch to production
./debug/set-environment.sh production

# Switch to development
./debug/set-environment.sh development

# Use custom production URL
./debug/set-environment.sh production https://your-repl.replit.app

# Then rebuild
./build-for-krita.sh && ./dev-update-plugin.sh
```

### View Logs

```bash
# Recent logs
tail -50 ~/.local/share/chm/plugin_debug.log

# Watch in real-time
tail -f ~/.local/share/chm/plugin_debug.log

# Just configuration
grep "\[CONFIG\]" ~/.local/share/chm/plugin_debug.log

# Just API calls
grep "\[API-" ~/.local/share/chm/plugin_debug.log
```

---

## 🧪 Recommended Testing Flow

### 1. Verify Current Configuration

```bash
./debug/show-current-config.sh
```

Should show:
```
Environment: production
API URL: https://certified-human-made.org
✅ Server is reachable
```

### 2. Test Against Production

```bash
./debug/test-prod-backend.sh
# Restart Krita
# Test export
# Check logs
```

### 3. Test Against Local (If Backend Running)

```bash
# In another terminal, start backend
cd /Users/david/Documents/GitHub/certified-human-made
npm run dev

# In this terminal
./debug/test-local-backend.sh
# Restart Krita
# Test export
# Check logs
```

### 4. Create Release Build

```bash
# Ensure production defaults
./debug/set-environment.sh production

# Build and package (with automatic validation)
./build-for-krita.sh
./scripts/package-release.sh
```

The package script will **automatically validate** that:
- ✅ Default environment is `production`
- ✅ Production URL is NOT `localhost`
- ✅ Configuration is release-ready

If validation fails, it will tell you exactly what to fix!

---

## 📚 Documentation

### Quick Reference (One Page)

```bash
cat docs/QUICK-ENVIRONMENT-REFERENCE.md
```

Or just remember these commands:
- `./debug/show-current-config.sh` - Check config
- `./debug/test-prod-backend.sh` - Test production
- `./debug/test-local-backend.sh` - Test local

### Complete Guides

| Document | Purpose |
|----------|---------|
| `docs/QUICK-ENVIRONMENT-REFERENCE.md` | One-page cheat sheet |
| `docs/ENVIRONMENT-CONFIGURATION.md` | Complete guide with all scenarios |
| `docs/TESTING-ENVIRONMENT-SETUP.md` | Step-by-step testing procedures |
| `docs/ENVIRONMENT-SETUP-SUMMARY.md` | Implementation details and changes |
| `THIS FILE` | Quick start and overview |

---

## 🔍 What Changed?

### Configuration System

**Before:**
```python
# config.py (OLD)
IS_PRODUCTION = os.environ.get('CHM_ENV', '').lower() == 'production'
IS_DEVELOPMENT = not IS_PRODUCTION  # Defaulted to True - WRONG!
DEFAULT_API_URL = 'http://localhost:5000'  # Wrong for releases!
```

**After:**
```python
# config.py (NEW)
CHM_ENV = os.environ.get('CHM_ENV', 'production').lower()  # Defaults to production!
IS_PRODUCTION = CHM_ENV == 'production'
IS_DEVELOPMENT = CHM_ENV == 'development'
DEFAULT_API_URL = 'https://certified-human-made.org'  # Correct for releases!
```

### New Files

```
debug/
├── set-environment.sh           ← Universal environment switcher
├── show-current-config.sh       ← Configuration diagnostic
├── test-prod-backend.sh         ← Quick production test
└── test-local-backend.sh        ← Quick local test

docs/
├── ENVIRONMENT-CONFIGURATION.md         ← Complete guide
├── QUICK-ENVIRONMENT-REFERENCE.md       ← One-page reference
├── TESTING-ENVIRONMENT-SETUP.md         ← Testing scenarios
└── ENVIRONMENT-SETUP-SUMMARY.md         ← Implementation details
```

### Modified Files

- `krita-plugin/chm_verifier/config.py` - Production defaults + logging
- `krita-plugin/chm_verifier/chm_extension.py` - Startup diagnostics
- `scripts/package-release.sh` - Configuration validation

---

## 🎯 Key Features

### 1. Production-Safe Defaults

Release builds now **default to production** automatically. No environment variables needed!

### 2. Easy Environment Switching

Test against any backend with one command:
```bash
./debug/test-prod-backend.sh <OPTIONAL_URL>
```

### 3. Automatic Validation

The package script **validates configuration** before creating release:
```bash
./scripts/package-release.sh
# Automatically checks:
# ✅ Default environment is 'production'
# ✅ Production URL is NOT 'localhost'
```

### 4. Startup Diagnostics

Plugin now logs configuration on startup:
```
[CONFIG] ================================
[CONFIG] CHM Plugin Environment Config
[CONFIG] ================================
[CONFIG] Environment: production
[CONFIG] API_URL: https://certified-human-made.org
[CONFIG] API_URL source: DEFAULT_API_URL
[CONFIG] CHM_ENV source: Default (production)
[CONFIG] ================================
```

**No more guessing what configuration the plugin is using!**

### 5. Diagnostic Tools

Check configuration anytime:
```bash
./debug/show-current-config.sh
```

Includes:
- Environment variables
- Config file settings
- Resolved values
- Connectivity test
- Recommendations

---

## 🐛 Troubleshooting

### Issue: Wrong URL in logs

**Solution:**
```bash
./debug/set-environment.sh production
./build-for-krita.sh && ./dev-update-plugin.sh
# Restart Krita
```

### Issue: Can't reach server

**Check:**
```bash
./debug/show-current-config.sh
# Will test connectivity and show recommendations
```

### Issue: Release validation fails

**Fix:**
```bash
./debug/set-environment.sh production
# Then try packaging again
./scripts/package-release.sh
```

---

## 💡 Pro Tips

### Daily Development Workflow

```bash
# Once at start of day
./debug/test-local-backend.sh

# Then just code and test
# No need to rebuild unless you change Rust code
```

### Before Creating Release

```bash
# 1. Test against production
./debug/test-prod-backend.sh

# 2. Ensure production defaults
./debug/set-environment.sh production

# 3. Create release (automatic validation)
./build-for-krita.sh
./scripts/package-release.sh
```

### Debugging Production Issues

```bash
# Test dev plugin against production
./debug/test-prod-backend.sh

# Watch logs
tail -f ~/.local/share/chm/plugin_debug.log

# Test export in Krita
# Logs appear in real-time!
```

---

## 📞 Next Steps

### 1. Test It Right Now!

```bash
./debug/test-prod-backend.sh
# Restart Krita
# Test export
# Check logs: tail -50 ~/.local/share/chm/plugin_debug.log
```

### 2. Verify Configuration

```bash
./debug/show-current-config.sh
```

Should show:
- ✅ Environment: production
- ✅ API URL: https://certified-human-made.org
- ✅ Server is reachable

### 3. Create a Test Release

```bash
./debug/set-environment.sh production
./build-for-krita.sh
./scripts/package-release.sh
```

Should complete without errors and create:
```
releases/chm_verifier-v1.0.0.zip
```

### 4. Test the Release ZIP

```bash
# Extract to temp location
mkdir -p /tmp/chm-release-test
cd /tmp/chm-release-test
unzip ~/Documents/GitHub/krita-certified-human-made/releases/chm_verifier-v*.zip

# Check config in ZIP
grep "CHM_ENV\|DEFAULT_API_URL" chm_verifier/config.py

# Should show:
# CHM_ENV = os.environ.get('CHM_ENV', 'production').lower()
# DEFAULT_API_URL = 'https://certified-human-made.org'
```

---

## ✅ Success Criteria

After testing, you should see:

### In Configuration Diagnostic
```bash
./debug/show-current-config.sh
```
- ✅ Environment: production
- ✅ API URL: https://certified-human-made.org
- ✅ Server is reachable

### In Plugin Logs
```bash
grep "\[CONFIG\]" ~/.local/share/chm/plugin_debug.log
```
- ✅ Environment: production
- ✅ API_URL: https://certified-human-made.org
- ✅ API_URL source: DEFAULT_API_URL

### In Export Test
```bash
grep "\[API-SIGN\]" ~/.local/share/chm/plugin_debug.log
```
- ✅ POSTing to https://certified-human-made.org/api/sign-and-timestamp
- ✅ Server response received
- ✅ Signature: (base64)...
- ✅ GitHub timestamp: https://gist.github.com/...

---

## 🎉 Summary

**You now have:**

1. ✅ **Production-safe defaults** - Releases work out-of-the-box
2. ✅ **Easy testing** - One command to test any backend
3. ✅ **Automatic validation** - Catches config errors before release
4. ✅ **Diagnostic tools** - Debug issues quickly
5. ✅ **Complete documentation** - All scenarios covered

**Ready to test!** Start with:
```bash
./debug/test-prod-backend.sh
```

Then restart Krita and try an export! 🎨

---

**Questions?** Check the documentation:
- Quick commands: `docs/QUICK-ENVIRONMENT-REFERENCE.md`
- Complete guide: `docs/ENVIRONMENT-CONFIGURATION.md`
- Testing procedures: `docs/TESTING-ENVIRONMENT-SETUP.md`

**Happy testing!** 🚀


# ✅ Development Environment Setup Complete!

## What Changed

The CHM Krita plugin now has **smart environment detection**:

| Mode | API URL | When to Use |
|------|---------|-------------|
| **Development** (DEFAULT) | `http://localhost:5000` | Local testing with backend server |
| **Production** | `https://certified-human-made.org` | Testing with live server |

## Quick Commands

```bash
# Check current mode
./debug/set-environment.sh status

# Switch to development (default, uses localhost:5000)
./debug/set-environment.sh dev
./build-for-krita.sh && ./dev-update-plugin.sh

# Switch to production (uses certified-human-made.org)
./debug/set-environment.sh production
./build-for-krita.sh && ./dev-update-plugin.sh
```

## Current Status

✅ **Plugin is in DEVELOPMENT mode** (uses `localhost:5000`)

To use the plugin:

### 1. Start Local Backend Server

```bash
cd /Users/david/Documents/GitHub/certified-human-made
bun run dev
```

Wait for:
```
[express] serving on 0.0.0.0:5000
```

### 2. Restart Krita

If Krita is running:
```bash
killall krita
```

Then open Krita normally.

### 3. Test Export

1. Open/create a document in Krita
2. Make some strokes
3. Tools → Scripts → CHM: Export with Proof
4. Should connect to local backend on `localhost:5000`

### 4. Verify It's Working

Check logs:
```bash
tail -50 ~/.local/share/chm/plugin_debug.log
```

Should show:
```
[API-CLIENT] ✓ Environment: development
[API-CLIENT] ✓ API URL: http://localhost:5000
[API-SIGN] Making HTTP POST to: http://localhost:5000/api/sign-and-timestamp
```

## Testing With Production Server

When you want to test with the live production backend:

```bash
cd /Users/david/Documents/GitHub/krita-certified-human-made

# Switch to production mode
./debug/set-environment.sh production

# Rebuild and install
./build-for-krita.sh && ./dev-update-plugin.sh
```

Restart Krita. Plugin will now use `https://certified-human-made.org`

## Environment Variable Overrides

For advanced use cases:

```bash
# Force production mode via environment variable
export CHM_ENV=production
/Applications/Krita.app/Contents/MacOS/krita

# Or use custom URL
export CHM_API_URL=https://my-staging-server.com
/Applications/Krita.app/Contents/MacOS/krita
```

## Files Changed

### New Files
- `debug/set-environment.sh` - Simple dev/production switcher
- `debug/find-replit-url.md` - How to find Replit URL (now less relevant)
- `docs/DEV-VS-PRODUCTION-CONFIG.md` - Complete documentation

### Modified Files
- `krita-plugin/chm_verifier/config.py` - Auto-detection logic added
- `krita-plugin/chm_verifier/chm_extension.py` - Logs environment on startup

## What Was the Problem?

Previously, the plugin was hardcoded to use `certified-human-made.org`, which:
- ❌ Required DNS to be working
- ❌ Couldn't test with local backend
- ❌ Needed manual config file changes

Now it:
- ✅ Defaults to localhost for development
- ✅ Easy switching with simple commands
- ✅ Works offline with local backend
- ✅ Production mode for release testing

## Next Steps

**For Development:**
1. Keep it in dev mode (default)
2. Start local backend: `cd ../certified-human-made && bun run dev`
3. Test plugin in Krita
4. All API calls go to `localhost:5000`

**Before Release:**
1. Switch to production: `./debug/set-environment.sh production`
2. Test thoroughly with live server
3. Verify all features work
4. Include in release build

## Troubleshooting

### "Connection refused" Error

**You're in dev mode but backend isn't running:**
```bash
cd /Users/david/Documents/GitHub/certified-human-made
bun run dev
```

**Want to use production instead:**
```bash
cd /Users/david/Documents/GitHub/krita-certified-human-made
./debug/set-environment.sh production
./build-for-krita.sh && ./dev-update-plugin.sh
```

### "Server signing failed"

**Check which URL is configured:**
```bash
./debug/set-environment.sh status
```

**Check logs to see what's happening:**
```bash
tail -50 ~/.local/share/chm/plugin_debug.log | grep -E "API-CLIENT|API-SIGN"
```

### Wrong Environment After Switch

1. **Rebuild:** `./build-for-krita.sh && ./dev-update-plugin.sh`
2. **Restart Krita:** `killall krita` then reopen
3. **Verify:** Check logs for `[API-CLIENT] ✓ Environment: development` or `production`

## Documentation

- **Quick Reference:** This file
- **Complete Guide:** `docs/DEV-VS-PRODUCTION-CONFIG.md`
- **Bug Analysis:** `docs/bugs/BUG-016-server-signing-api-failure.md`
- **Quick Fix:** `QUICK-FIX-API-URL.md`

## Summary

🎉 **Development workflow is now simple:**

1. Plugin defaults to `localhost:5000` (development mode)
2. Start local backend: `bun run dev`
3. Test in Krita
4. Switch to production when needed: `./debug/set-environment.sh production`

No more DNS issues, no more manual URL configuration, just works! ✨


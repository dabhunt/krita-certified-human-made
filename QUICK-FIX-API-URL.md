# 🚀 Quick Fix: Plugin Can't Reach Server

## Problem

Export fails with: `[EXPORT] ❌ Server signing failed: Server-side signing failed`

## Root Cause

DNS for `certified-human-made.org` points to wrong server (not your Replit)

## Quick Fix (5 minutes)

### Step 1: Find Your Replit URL

1. Go to https://replit.com
2. Open your "certified-human-made" project
3. Look at the Webview URL (top right of screen)
4. Copy the URL - it looks like:
   - `https://certified-human-made-dabhunt.replit.app` OR
   - `https://9b9241a8-xxxxx.replit.dev` OR
   - Similar format

### Step 2: Configure Plugin

```bash
cd /Users/david/Documents/GitHub/krita-certified-human-made

# Set development API URL (replace with YOUR actual Replit URL!)
./debug/set-dev-api-url.sh https://YOUR-ACTUAL-URL.replit.app

# Build and update plugin
./build-for-krita.sh && ./dev-update-plugin.sh
```

### Step 3: Test

1. **Quit Krita completely** (Command+Q)
2. **Start Krita** 
3. **Open a document** with some work
4. **Try export:** Tools → Scripts → CHM: Export with Proof
5. **Check logs if it fails:**
   ```bash
   tail -50 ~/.local/share/chm/plugin_debug.log
   ```

## Expected Log Output (Success)

```
[API-CLIENT] ✓ API client set (URL: https://your-url.replit.app)
[API-INIT] API URL: https://your-url.replit.app
[API-SIGN] Making HTTP POST to: https://your-url.replit.app/api/sign-and-timestamp
[API-SIGN] ✓ Server response received (200)
[EXPORT] ✅ Export successful!
```

## If Still Failing

**Check server is running on Replit:**
- Go to your Replit project
- Should see "Webview" with your app running
- Test by visiting the URL in browser - should see the CHM website

**Share debug logs:**
```bash
tail -100 ~/.local/share/chm/plugin_debug.log > ~/Desktop/plugin-debug.txt
```

Send me `plugin-debug.txt` from your Desktop.

## Permanent Fix (Later)

Once you fix DNS configuration:

```bash
# Reset to production URL
./debug/set-dev-api-url.sh production
./build-for-krita.sh && ./dev-update-plugin.sh
```

---

## Troubleshooting

### "Permission denied" running script

```bash
chmod +x ./debug/set-dev-api-url.sh
```

### Krita won't quit

```bash
killall krita
```

### Plugin not updating

```bash
# Force remove and reinstall
rm -rf ~/.local/share/krita/pykrita/chm_verifier
./dev-update-plugin.sh
```

---

**Full docs:** `docs/bugs/BUG-016-server-signing-api-failure.md`


# How to Find Your Replit URL

## Method 1: Replit Dashboard (Easiest)

1. **Go to https://replit.com**

2. **Find your project:**
   - Look for "certified-human-made" in your projects list
   - Click to open it

3. **Look at the Webview:**
   - Top right corner of the screen
   - Click the "Open in new tab" icon (⧉)
   - **The URL that opens is your Replit URL!**
   
   Examples of what it might look like:
   - `https://certified-human-made-dabhunt.replit.app`
   - `https://9b9241a8-5d19-4e9a-b8fd-xxxxx.replit.dev`
   - `https://certified-human-made.dabhunt.repl.co`

4. **Copy that entire URL** (including https://)

## Method 2: From Replit Console

If your Repl is running, the console shows:
```
11:22:52 PM [express] serving on 0.0.0.0:5000
```

The external URL is shown in the "Webview" tab or by clicking the URL icon in top right.

## Method 3: Check .replit File

Your project might have the URL in deployment config, but this is less reliable.

## What to Do With the URL

Once you have it:

```bash
cd /Users/david/Documents/GitHub/krita-certified-human-made

# Paste YOUR actual URL here:
./debug/set-dev-api-url.sh https://YOUR-URL-HERE.replit.app

# Build and update:
./build-for-krita.sh && ./dev-update-plugin.sh
```

## Common Mistakes

❌ **Don't use:** `localhost:5000` (only works on Replit server itself)  
❌ **Don't use:** `0.0.0.0:5000` (internal address)  
❌ **Don't forget:** The `https://` at the start  
❌ **Don't add:** Extra slashes or paths at the end

✅ **Correct format:** `https://something.replit.app` or `.replit.dev`

## Test Your URL

Open the URL in your browser. You should see:

**✅ Success - You'll see:**
- The Certified Human Made website
- Home page with verification tools
- Professional looking design

**❌ Wrong - If you see:**
- "Page not found" → Wrong URL or app not running
- Directory listing → Wrong server
- Error page → App crashed, check Replit console

## If App Not Running

In Replit:
1. Click the big **Run** button at top
2. Wait for console to show: `[express] serving on 0.0.0.0:5000`
3. Then grab the Webview URL

## Still Can't Find It?

Check your Replit dashboard for the project name and share it. The URL format is usually:
```
https://[PROJECT-NAME]-[USERNAME].replit.app
```

For example:
- Project name: `certified-human-made`
- Username: `dabhunt`
- Likely URL: `https://certified-human-made-dabhunt.replit.app`

But the exact format can vary, so always check the Webview!


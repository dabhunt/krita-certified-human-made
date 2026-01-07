# How to Create the v1.0.0 GitHub Release

Follow these steps to create the GitHub release for v1.0.0:

## Step 1: Navigate to GitHub Releases

1. Go to your repository on GitHub: https://github.com/dabhunt/krita-certified-human-made
2. Click on **"Releases"** in the right sidebar (or go to `/releases`)
3. Click the **"Draft a new release"** button

## Step 2: Fill in Release Details

**Tag version**: 
- Select `v1.0.0` from the dropdown (already pushed)

**Release title**: 
```
Certified Human-Made v1.0.0 - Production Release
```

**Description**:
- Copy the entire contents from `GITHUB-RELEASE-BODY.md`
- Or write your own based on the release notes

## Step 3: Upload Release Assets

Click "Attach binaries by dropping them here or selecting them" and upload:

1. **`releases/chm_verifier-v1.0.0.zip`** (109 MB)
   - This is the main plugin distribution file
   - Users will download this to install the plugin

## Step 4: Set Release Options

- ✅ Check **"Set as the latest release"**
- ✅ Check **"Create a discussion for this release"** (optional but recommended)
- ❌ Do NOT check "Set as a pre-release"

## Step 5: Publish

Click **"Publish release"**

---

## What Happens Next

Once published, users can:
1. Download `chm_verifier-v1.0.0.zip` from the Releases page
2. Install it in Krita via Tools → Scripts → Import Python Plugin from File...
3. Start using CHM to verify their artwork!

---

## Quick Copy-Paste

### Release Title
```
Certified Human-Made v1.0.0 - Production Release
```

### Tag
```
v1.0.0
```

### Target
```
main
```

---

## Files Ready for Upload

Location: `releases/chm_verifier-v1.0.0.zip` (109 MB)

---

## Alternative: Using GitHub CLI (if installed)

If you install GitHub CLI (`gh`), you can create the release from command line:

```bash
cd /Users/david/Documents/GitHub/krita-certified-human-made

gh release create v1.0.0 \
  releases/chm_verifier-v1.0.0.zip \
  --title "Certified Human-Made v1.0.0 - Production Release" \
  --notes-file GITHUB-RELEASE-BODY.md \
  --latest
```

To install GitHub CLI:
```bash
brew install gh
gh auth login
```

---

## Verification

After publishing, verify:
1. Release appears on the repository homepage
2. ZIP file is downloadable
3. Tag v1.0.0 is linked correctly
4. Release notes display properly
5. "Latest release" badge shows v1.0.0

---

Good luck with the release! 🚀


# CHM Plugin - Testing Quick Start

## 🆕 New Feature: PNG Metadata Verification

**What's New:** Exported PNGs now have verification data embedded in metadata, enabling **instant verification (<1 second)** instead of waiting for GitHub indexing (10-60 minutes).

**See:** [Testing PNG Metadata Guide](/docs/testing-png-metadata.md) for comprehensive testing instructions.

**Quick Check:**
```bash
# After exporting test.png with latest plugin:
exiftool test.png | grep CHM-Gist-URL
# Should show: CHM-Gist-URL : https://gist.github.com/...
```

---

## ⚡ Quick Test (5 minutes)

### 1. Restart Krita
```bash
# Close Krita if running, then reopen
```

### 2. Check Plugin Loaded
Look for these logs in Krita console:
```
CHM: Plugin registered successfully
[CHM] ✓ PIL (Pillow) available
[CHM] ✓ imagehash available
[CHM] ✓ Perceptual hashing ENABLED
```

### 3. Draw & Export
1. Create new 500x500 document
2. Draw 10-15 brush strokes
3. **Tools → Scripts → CHM: Export with Proof**
4. Save as `test.png`

### 4. Verify Success Dialog
Should show:
```
✅ Image exported with CHM proof!

Classification: HumanMade
Timestamps: ✓ Timestamped (2/2 services)
Database: ✓ Submitted

GitHub Gist: https://gist.github.com/...
```

### 5. Check Files Created
```bash
ls -lh test*
# Should show:
# test.png (your artwork)
# test_proof.json (proof data)
```

### 6. Verify Proof JSON
```bash
cat test_proof.json | python3 -m json.tool | grep -E "(file_hash|perceptual_hash|classification|success_count)"
```

**Expected**:
- `"file_hash": "sha256:abc123..."` (64 chars)
- `"perceptual_hash": "def456789abcdef0"` (16 chars, NOT "unavailable")
- `"classification": "HumanMade"`
- `"success_count": 2`

### 7. Verify GitHub Gist
- Copy URL from success dialog
- Open in browser
- Verify it contains your proof hash

---

## ✅ Success Criteria

Phase 1 is working if:
- ✅ Plugin loads without errors
- ✅ Export creates 2 files (image + proof JSON)
- ✅ perceptual_hash is 16-char hex (NOT "unavailable")
- ✅ GitHub Gist URL is accessible
- ✅ success_count = 2

---

## 🐛 If Something Goes Wrong

### Issue: perceptual_hash = "unavailable_missing_dependencies"
```bash
# Re-check dependencies
cd /Users/david/Documents/GitHub/krita-certified-human-made
ls -la krita-plugin/chm_verifier/vendor/

# Should show: PIL/, imagehash/, numpy/, scipy/, PyWavelets/
# If missing, rebuild: ./build-for-krita.sh && ./dev-update-plugin.sh
```

### Issue: GitHub Gist fails
- Check network connection
- Look in logs: `~/.local/share/chm/plugin_debug.log`
- CHM Log should still succeed (local file)

### Issue: No files created
- Check logs: `tail -f ~/.local/share/chm/plugin_debug.log`
- Look for `[EXPORT]` messages
- Verify session was created (draw at least 5 strokes first)

---

## 📚 Full Test Guide

For comprehensive testing (all 5 scenarios):
→ See `docs/end-to-end-mvp-test-guide.md`

---

## 🎯 Next Steps

After confirming quick test passes:
1. Test duplicate detection (export same artwork twice)
2. Check database files:
   ```bash
   cat ~/.local/share/chm/submitted_proofs.jsonl | tail -1 | python3 -m json.tool
   cat ~/.local/share/chm/file_hash_index.json | python3 -m json.tool
   ```
3. Test AI plugin detection (if you have AI plugins installed)

---

**Phase 1 Status**: ✅ COMPLETE  
**Ready for**: User Testing  
**Documentation**: `docs/phase1-completion-summary.md`


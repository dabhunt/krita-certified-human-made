# CHM Verifier Plugin - Installation Guide

## Quick Start (Development)

### Step 1: Build the Rust Library

From the project root directory:

```bash
cd /Users/david/Documents/GitHub/krita-certified-human-made
cargo build --release
```

### Step 2: Copy the Compiled Library

On macOS, copy the compiled library to the plugin's lib directory:

```bash
# Create lib directory if it doesn't exist
mkdir -p krita-plugin/chm_verifier/lib

# Copy the compiled library (macOS)
cp target/release/libchm.dylib krita-plugin/chm_verifier/lib/chm.so
```

**Note**: Even though macOS produces `.dylib`, we rename it to `.so` for Python import compatibility.

### Step 3: Install the Plugin in Krita

**Option A: Symlink (Recommended for Development)**

This allows you to edit files without reinstalling:

```bash
# macOS plugin directory
KRITA_PLUGIN_DIR="$HOME/Library/Application Support/krita/pykrita"

# Create pykrita directory if it doesn't exist
mkdir -p "$KRITA_PLUGIN_DIR"

# Create symlink to your plugin
ln -s "/Users/david/Documents/GitHub/krita-certified-human-made/krita-plugin/chm_verifier" "$KRITA_PLUGIN_DIR/chm_verifier"
```

**Option B: Copy (Alternative)**

```bash
# macOS plugin directory
KRITA_PLUGIN_DIR="$HOME/Library/Application Support/krita/pykrita"

# Create pykrita directory if it doesn't exist
mkdir -p "$KRITA_PLUGIN_DIR"

# Copy the entire plugin directory
cp -r krita-plugin/chm_verifier "$KRITA_PLUGIN_DIR/"
```

### Step 4: Enable the Plugin in Krita

1. **Open Krita**
2. Go to **Settings** → **Configure Krita** (or **Krita** → **Preferences** on macOS)
3. Select **Python Plugin Manager** from the left sidebar
4. Find **"Certified Human-Made Verifier"** in the list
5. Check the box to enable it
6. Click **OK**
7. **Restart Krita** (required for plugins to load)

### Step 5: Verify Installation

After restarting Krita:

1. Open the **Scripter** (Tools → Scripts → Scripter)
2. Check the console output for CHM plugin messages:
   - Look for: `"CHM Verifier: Setup called"`
   - Look for: `"CHM Verifier: Loaded CHM library version X.X.X"`
   - Look for: `"CHM Verifier: Event capture started"`

If you see these messages, the plugin is working! ✅

## Troubleshooting

### Plugin Not Appearing in Plugin Manager

**Issue**: CHM Verifier doesn't appear in the Python Plugin Manager list.

**Solutions**:
1. Verify the `.desktop` file exists:
   ```bash
   ls -l "$HOME/Library/Application Support/krita/pykrita/chm_verifier/chm_verifier.desktop"
   ```

2. Check the `.desktop` file format (must be valid):
   ```bash
   cat "$HOME/Library/Application Support/krita/pykrita/chm_verifier/chm_verifier.desktop"
   ```

3. Ensure `__init__.py` exists:
   ```bash
   ls -l "$HOME/Library/Application Support/krita/pykrita/chm_verifier/__init__.py"
   ```

### CHM Library Not Found

**Issue**: Error message: `"CHM library not available: No module named 'chm'"`

**Solutions**:
1. Verify the compiled library exists:
   ```bash
   ls -l krita-plugin/chm_verifier/lib/chm.so
   ```

2. Rebuild the Rust library:
   ```bash
   cargo clean
   cargo build --release
   cp target/release/libchm.dylib krita-plugin/chm_verifier/lib/chm.so
   ```

3. Check file permissions:
   ```bash
   chmod 644 krita-plugin/chm_verifier/lib/chm.so
   ```

### Import Errors or Crashes

**Issue**: Krita crashes on startup or shows Python import errors.

**Possible Causes**:
1. **Python version mismatch**: Krita uses its bundled Python. The compiled library must match.
2. **Missing dependencies**: PyO3 linking issues on macOS (expected in development).

**Solutions**:
1. Check Krita's Python version:
   - Open Krita Scripter
   - Run: `import sys; print(sys.version)`
   
2. For macOS linking issues (expected):
   - These will be resolved in Phase 3 packaging
   - For now, compilation success is sufficient
   - The plugin structure can be tested without the Rust library

3. Test without Rust library (temporary):
   - Comment out the `import chm` in `chm_extension.py`
   - Test basic plugin loading

### Debug Mode

To see detailed debug logs:

1. Open Krita
2. Go to **Tools** → **Scripts** → **Scripter**
3. Keep the Scripter console open while using Krita
4. All debug messages (prefixed with "CHM Verifier:") will appear here

You can also check Krita's log file:
```bash
# macOS log location
tail -f "$HOME/Library/Application Support/krita/krita.log"
```

## Development Workflow

### Making Changes

1. **Edit Python files** in `/Users/david/Documents/GitHub/krita-certified-human-made/krita-plugin/chm_verifier/`
2. **Restart Krita** to reload the plugin
3. **Check Scripter console** for errors or debug messages

### Rebuilding Rust Library

If you modify Rust code:

```bash
# From project root
cargo build --release
cp target/release/libchm.dylib krita-plugin/chm_verifier/lib/chm.so

# If using symlink, changes are automatic
# If using copy method, recopy the plugin:
cp -r krita-plugin/chm_verifier "$HOME/Library/Application Support/krita/pykrita/"
```

Then restart Krita.

### Uninstalling

```bash
# Remove plugin directory
rm -rf "$HOME/Library/Application Support/krita/pykrita/chm_verifier"

# Or if using symlink:
rm "$HOME/Library/Application Support/krita/pykrita/chm_verifier"
```

Then restart Krita.

## Platform-Specific Paths

### macOS
- **Plugin Directory**: `~/Library/Application Support/krita/pykrita/`
- **Config Directory**: `~/Library/Application Support/krita/`
- **Log File**: `~/Library/Application Support/krita/krita.log`

### Linux
- **Plugin Directory**: `~/.local/share/krita/pykrita/`
- **Config Directory**: `~/.config/krita/`
- **Log File**: `~/.local/share/krita/krita.log`

### Windows
- **Plugin Directory**: `%APPDATA%\krita\pykrita\`
- **Config Directory**: `%APPDATA%\krita\`
- **Log File**: `%APPDATA%\krita\krita.log`

## Next Steps

Once installed and verified:

1. Create a new document in Krita
2. Draw some strokes
3. Check Scripter console for event capture messages
4. Verify sessions are being created and events recorded

## Need Help?

- Check the Scripter console for error messages
- Review `docs/krita-api-research.md` for known limitations
- Check `docs/phase0-completion-report.md` for troubleshooting tips


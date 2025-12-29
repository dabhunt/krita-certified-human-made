# Quick Start - Load CHM Plugin in Krita

## Option 1: Automated Installation (Recommended)

From the project root directory:

```bash
./install-plugin.sh
```

This script will:
1. Build the Rust library
2. Copy it to the plugin directory
3. Install the plugin to Krita (symlink or copy)
4. Show you the next steps

## Option 2: Manual Installation

### Build & Copy Library

```bash
# From project root
cargo build --release
mkdir -p krita-plugin/chm_verifier/lib
cp target/release/libchm.dylib krita-plugin/chm_verifier/lib/chm.so
```

### Install to Krita (Symlink - Recommended)

```bash
mkdir -p "$HOME/Library/Application Support/krita/pykrita"
ln -s "$(pwd)/krita-plugin/chm_verifier" "$HOME/Library/Application Support/krita/pykrita/chm_verifier"
# CRITICAL: .desktop file must be in pykrita root, not inside plugin folder!
cp krita-plugin/chm_verifier.desktop "$HOME/Library/Application Support/krita/pykrita/chm_verifier.desktop"
```

### Enable in Krita

1. Open **Krita**
2. **Settings** → **Configure Krita** → **Python Plugin Manager**
3. Check **"Certified Human-Made"**
4. Click **OK**
5. **Restart Krita**

### Verify It's Working

1. Open **Tools** → **Scripts** → **Scripter**
2. Look for these messages in console:
   ```
   CHM: Setup called
   CHM: Loaded CHM library version 0.1.0
   CHM: Event capture started
   ```

## Troubleshooting

**Plugin not in list?**
- Check the symlink exists: `ls -l "$HOME/Library/Application Support/krita/pykrita/chm_verifier"`
- **CRITICAL:** Verify `.desktop` file exists **in pykrita root** (not inside plugin folder!):
  ```bash
  ls -l "$HOME/Library/Application Support/krita/pykrita/chm_verifier.desktop"
  ```

**"CHM library not available" error?**
- Rebuild: `cargo build --release`
- Recopy: `cp target/release/libchm.dylib krita-plugin/chm_verifier/lib/chm.so`
- Restart Krita

**No debug messages?**
- Check Scripter console is open
- Verify plugin is enabled in Plugin Manager
- Try restarting Krita again

## Full Documentation

See `INSTALLATION.md` for complete troubleshooting guide.


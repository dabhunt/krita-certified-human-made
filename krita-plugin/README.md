# Certified Human-Made (CHM) - Krita Plugin

**Prove your digital art is human-made, not AI-generated.**

## Why This Matters

In a world where AI can generate photorealistic art in seconds, **human creativity needs authentication**. Artists spend years developing their skills, and this plugin helps them prove it.

## What It Does

This Krita plugin:
- ✅ Captures your creative process as you work
- ✅ Generates cryptographic proof of human authorship
- ✅ Detects AI assistance and mixed media
- ✅ Protects your privacy (data never leaves your computer unencrypted)
- ✅ Provides a **Docker panel** for quick access to export and session stats

## Classification System

The plugin assigns one of these labels:

1. **Human-Made**: Purely human work (no AI plugins, no imported images visible in final export)
2. **Mixed Media**: Non-reference images imported (may be visible in final export)
3. **AI-Assisted**: AI plugins detected and enabled

### Important: Reference Images

Reference images used for study (anatomy, pose, color inspiration, etc.) that remain hidden in your final artwork maintain the **Human-Made** classification. The system detects and classifies as **Mixed Media** only when non-reference images are imported and may be visible in the final export.

## Using the Plugin

### CHM Docker Panel

After installation, the CHM Docker panel provides quick access to all features:

1. **Open the Docker**: Settings → Dockers → CHM Proof Exporter
2. **View live stats**: Strokes, layers, time, classification (updates every 5 seconds)
3. **Export with one click**: Click "Export with Proof" button
4. **View session details**: Click "View Current Session" button
5. **Expand details**: Click collapsible sections for advanced stats, AI detection, and session info

The Docker can be positioned anywhere in your workspace (default: right side).

### Menu Actions

Alternative access via menu:
- **Tools → CHM: Export with Proof** - Export your artwork with cryptographic proof
- **Tools → CHM: View Current Session** - See detailed session statistics

## Installation

See [INSTALLATION.md](INSTALLATION.md) for detailed setup instructions.

## Building the Library

From the repository root directory:

```bash
cargo build --release
```

Then copy the compiled library to this directory:

**Linux**:
```bash
cp target/release/libchm.so krita-plugin/chm_verifier/lib/chm.so
```

**macOS**:
```bash
cp target/release/libchm.dylib krita-plugin/chm_verifier/lib/chm.so
```

**Windows**:
```bash
copy target\release\chm.pyd krita-plugin\chm_verifier\lib\chm.pyd
```

## Documentation

- **[Manual.html](chm_verifier/Manual.html)**: Full user guide
- **[INSTALLATION.md](INSTALLATION.md)**: Setup instructions
- **[QUICKSTART.md](QUICKSTART.md)**: Quick start guide

## License

GPL-3.0 (same as Krita) - see [LICENSE](../LICENSE)


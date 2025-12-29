# Certified Human-Made (CHM) - Krita Plugin

**Prove your digital art is human-made, not AI-generated.**

## Why This Matters

In a world where AI can generate photorealistic art in seconds, **human creativity needs authentication**. Artists spend years developing their skills, and this plugin helps them prove it.

## What It Does

This Krita plugin:
- ✅ Captures your creative process as you work
- ✅ Generates cryptographic proof of human authorship
- ✅ Detects AI assistance, tracing, and mixed media
- ✅ Protects your privacy (data never leaves your computer unencrypted)

## Classification System

The plugin assigns one of these labels (highest to lowest verification level):

1. **Human-Made**: Purely human work (highest verification level)
2. **Traced**: Direct tracing over references (>33% edge correlation)
3. **Mixed Media**: Imported images visible in final export
4. **AI-Assisted**: AI plugins detected (lowest verification level)

### Important: References Are OK!

Using reference images is a **normal and professional** part of the artistic process. References only affect your classification if:
- You directly trace over them (>33% edge correlation), OR
- They remain visible in the final exported artwork

Hidden references used for anatomy study, pose reference, color inspiration, etc. are allowed and maintain the **Human-Made** label. The system transparently tracks reference usage in detailed metadata while keeping your top-level classification as Human-Made.

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


# Certified Human-Made (CHM) - Krita Plugin

**Prove your digital art is human-made, not AI-generated.**

A privacy-first verification system for Krita that captures your creative process and generates cryptographic proof of human authorship — **no blockchain, no crypto, no complexity**.

[![License: GPL-3.0](https://img.shields.io/badge/License-GPL%203.0-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Rust](https://img.shields.io/badge/rust-1.92+-orange.svg)](https://www.rust-lang.org)
[![Krita](https://img.shields.io/badge/krita-5.2+-purple.svg)](https://krita.org)

---

## 🎯 What is CHM?

### Why This Matters

In a world where AI can generate photorealistic art in seconds, **human creativity needs authentication**. Artists spend years developing their skills, and this system helps them prove it.

**How do you prove you actually drew something?**

CHM is a **complete verification ecosystem** for digital art:

**🎨 Krita Plugin** (This Repository):
- ✅ **Captures** your drawing process (strokes, layers, timing)
- ✅ **Analyzes** for AI assistance vs. pure human creation
- ✅ **Generates** tamper-proof certificates with immutable timestamps
- ✅ **Protects** your privacy (only hashes uploaded, never your artwork)

**🌐 Web Verification Tool** ([certified-human-made.org](https://certified-human-made.org)):
- ✅ **Public verification** for anyone to check artwork authenticity
- ✅ **Works with re-encoded images** (Twitter JPEG compression, Instagram, etc.)
- ✅ **Displays proof details** (classification, timestamps, creation stats)
- ✅ **C2PA compatible** (Content Authenticity Initiative standards)

**The Complete Flow**:
```
You Create → Plugin Certifies → GitHub Timestamps → Anyone Can Verify
```

### What You Get

**Immutable Proof of Authorship**:
- ✅ **GitHub Timestamp**: Permanent, public record (cannot be altered or backdated)
- ✅ **Web Verification**: Anyone can verify your work at [certified-human-made.org](https://certified-human-made.org)
- ✅ **C2PA Compatible**: Works alongside Content Authenticity Initiative standards
- ✅ **Embedded in Image**: Proof data stored in PNG metadata (no separate files needed)

**Example Proof Details**:
```json
{
  "classification": "HumanMade",
  "stroke_count": 1247,
  "session_seconds": 13420,
  "drawing_time": 8400,
  "layer_count": 5,
  "ai_tools": "None",
  "timestamp": "2026-01-06T18:50:30Z",
  "github_gist": "https://gist.github.com/..."
}
```

**Your Privacy**: Individual strokes, layer data, and artwork pixels **never leave your computer**. Only cryptographic hashes are uploaded for verification.

---

## 🚀 Quick Start

### System Requirements

**Krita Version**: 5.2.0 or newer  
**Operating Systems**: Windows, Linux, macOS  
**Internet**: Required for timestamp generation  

### Installation

#### Step 1: Download the Plugin

Download the latest release ZIP file from [GitHub Releases](https://github.com/dabhunt/krita-certified-human-made/releases). (NOT source code, the other .zip)

Remember where you save the ZIP file — you'll need it in the next step.

#### Step 2: Install in Krita

1. **Open Krita**
2. Go to **Tools** → **Scripts** → **Import Python Plugin from File...**
3. Select the **ZIP file** you downloaded
4. When prompted to enable the plugin, click **Yes**

⚠️ **Note**: This will replace any previous installation of the CHM plugin.

#### Step 3: Restart Krita

**Krita must be restarted** for the plugin to load properly.

#### Step 4: Verify Installation

After restarting Krita:

1. Go to **Settings** → **Configure Krita** (or **Krita** → **Preferences** on macOS)
2. Select **Python Plugin Manager** from the left sidebar
3. Find **"Certified Human-Made"** in the list and ensure it's checked ✅
4. Click **OK**

#### Step 5: Open Docker
Open CHM Docker in Settings → Dockers → CHM Proof Exporter

### Getting Started

1. **Create or Open** a document in Krita
2. **Start Drawing** → CHM automatically tracks your creative process
3. **Generate Proof** → Go to **Tools** → **Scripts** → **CHM Verifier** → **Generate Proof**
4. **Get Immutable Timestamp** → Your proof is automatically registered on GitHub (public, verifiable)
5. **Share Your Work** → Post your artwork anywhere — proof is linked to the image

### Where Proofs Are Stored

**Embedded in Image**: Proof data is automatically embedded in your exported PNG file metadata — no separate files to manage!

**GitHub Gist**: Immutable public record viewable at the GitHub URL shown after generation

**Your Exported Artwork**: Simply share your PNG file — the proof travels with it

### Verify Any Image

**Anyone can verify artwork** at [certified-human-made.org](https://certified-human-made.org):

1. **Upload Image** → Drag and drop any artwork
2. **Instant Verification** → Checks against CHM and C2PA authenticity standards
3. **View Proof** → See creation details, timestamps, and classification
4. **Share Results** → Link to verification results page

**Works with re-encoded images!** Even if someone downloads your art from Twitter (compressed to JPEG), the verification system can still confirm it's your certified work using perceptual hashing.

---

## 🔒 Privacy First

### What Gets Uploaded (Public Timestamps)

- ✅ SHA-256 hash of encrypted session (irreversible)
- ✅ SHA-256 hash of exported artwork file
- ✅ Classification ("HumanMade", "Referenced", "MixedMedia", "AIAssisted")
- ✅ Aggregated counts (stroke count, layers, session duration)

### What NEVER Gets Uploaded

- ❌ Your artwork (pixels)
- ❌ Individual brush strokes (coordinates, pressure, timing)
- ❌ Layer names or pixel data
- ❌ Reference images
- ❌ Any identifiable creative process data

**How It Works**: All session data encrypted locally (AES-256-GCM). Only a cryptographic hash is timestamped publicly. Even we cannot decrypt your creative process.

**Read More**: [Privacy & Data Flow](docs/privacy-model.md)

---

## 🔧 Troubleshooting

### Plugin Not Appearing in Plugin Manager

**Issue**: CHM doesn't show up in the Python Plugin Manager list.

**Solutions**:
1. Ensure you installed via **Tools → Scripts → Import Python Plugin from File...**
2. Check that you selected the **ZIP file** (not an extracted folder)
3. Restart Krita after installation
4. See the [detailed installation guide](krita-plugin/INSTALLATION.md) for manual installation steps

### Plugin Won't Enable / Greyed Out

**Issue**: The checkbox next to "Certified Human-Made" is greyed out or won't stay checked.

**Solutions**:
1. Check the Scripter console (**Tools → Scripts → Scripter**) for error messages
2. Verify Krita version is 5.2.0 or newer: **Help → About Krita**
3. Try reinstalling: Tools → Scripts → Import Python Plugin from File...
4. On macOS: See [macOS-specific fixes](debug/fix-plugin-greyed-out.sh)

### No Console Messages / Plugin Not Working

**Issue**: Plugin appears enabled but doesn't show any messages or functionality.

**Solutions**:
1. **Restart Krita** after enabling the plugin
2. Create a **new document** (some plugins require an active document)
3. Open the **Scripter console** to see debug output: **Tools → Scripts → Scripter**
4. Try generating a proof after drawing some strokes to confirm functionality

### Network/Timestamp Issues

**Issue**: Error generating proofs or "Network error" messages.

**Solutions**:
1. Ensure you have an **active internet connection**
2. Check that GitHub is accessible (plugin uses GitHub Gist for timestamps)
3. Try again in a few moments (temporary network issues)
4. The plugin will still capture session data locally — timestamps can be added later

### Need More Help?

- **Installation Guide**: [krita-plugin/INSTALLATION.md](krita-plugin/INSTALLATION.md) — Detailed troubleshooting steps
- **Testing Scripts**: See `debug/` folder for diagnostic tools
- **Report Issues**: [GitHub Issues](https://github.com/armstrongl/krita-certified-human-made/issues)
- **Discussions**: [GitHub Discussions](https://github.com/armstrongl/krita-certified-human-made/discussions)

⚠️ **Note**: Please do not seek help on official Krita channels — they are not responsible for third-party plugins. Use our GitHub instead!

---

## 🌐 Web Verification Tool

### Verify Artwork at certified-human-made.org

The CHM ecosystem includes a **free public verification tool** where anyone can check if an image has been certified as human-made:

**Upload → Verify → Share**

#### Features

**Dual-Hash Verification**:
- **Exact Match**: Original file verification (file_hash matches)
- **Perceptual Match**: Works with re-encoded images (e.g., Twitter/Instagram compression)

**What You Can See**:
- ✅ Classification (HumanMade, MixedMedia, AIAssisted)
- ✅ Creation details (stroke count, session duration, drawing time, layers)
- ✅ Triple timestamps (GitHub, Internet Archive, CHM Log)
- ✅ AI tools detection (None, or which AI plugins were detected)
- ✅ Platform and metadata (canvas size, Krita version)

**How It Works**:
1. **Artist creates** artwork in Krita with CHM plugin
2. **Plugin generates proof** and registers cryptographic hash on GitHub
3. **Anyone uploads image** to certified-human-made.org
4. **System matches** the image (even if re-compressed) to the registered proof
5. **Results displayed** with full transparency about creation process

**Privacy Protected**: The verification system only stores cryptographic hashes. Your actual artwork, brush strokes, and creative process data remain on your computer.

**Try It**: [certified-human-made.org](https://certified-human-made.org)

---

## 🎨 How It Works

### 1. Capture Drawing Process (Local)

```
Brush Strokes → Layer Operations → Imports → Plugin Usage
                         ↓
              Encrypted Session File
         (~/.local/share/chm/sessions/)
```

### 2. Analyze Locally

- **AI Plugin Detection**: Scans for AI tools (Krita AI Diffusion, etc.)
- **Import Analysis**: Tracks imported images and their usage
- **Pattern Analysis**: Human vs. AI workflow patterns

**Classification Levels**:
1. `HumanMade`: Purely human work (no AI plugins, no imported images visible)
2. `MixedMedia`: Non-reference images imported (may be visible in final export)
3. `AIAssisted`: AI plugins detected and enabled

### 3. Generate Proof & Timestamp

```
Encrypted Session → Dual Hashes → Immutable Timestamps → Web Database
                   ├─ File Hash (SHA-256)         ↓
                   └─ Perceptual Hash (pHash)     ↓
                                           GitHub Gist (public)
                                           Internet Archive
                                           CHM Local Log
```

**Dual-Hash System**:
- **File Hash**: Exact file verification (proves unmodified original)
- **Perceptual Hash**: Visual content verification (survives JPEG compression, format changes)

**Why This Matters**: Your artwork shared on Twitter/Instagram gets compressed to JPEG. The perceptual hash ensures verification still works even when the file is re-encoded!

**Triple Timestamping** (Not Blockchain):
- ✅ **GitHub Gist**: Immutable Git commit history (legally recognized)
- ✅ **Internet Archive**: Wayback Machine snapshot (third-party verification)
- ✅ **CHM Public Log**: Append-only HMAC-signed log (offline verification)

**Why Not Blockchain?**
- ✅ **Zero cost**: No fees, no crypto needed
- ✅ **Publicly auditable**: Anyone can verify timestamps
- ✅ **Environmentally friendly**: No proof-of-work mining
- ✅ **Legally recognized**: Git commits are court-admissible

### 4. Public Verification (certified-human-made.org)

```
Anyone uploads image → Compute hashes → Database lookup
                           ↓
                    ┌──────┴──────┐
              Exact Match    Perceptual Match
                   ↓              ↓
           "Original File"  "Visual Match - Re-encoded"
                   ↓              ↓
              Display Proof Details
           (classification, strokes, session time, drawing time, AI tools, timestamps)
```

**Result**: Anyone can verify your artwork is human-made, even years later!

---

## 📖 Documentation

### Krita Plugin

- **[Architecture](krita-plugin/ARCHITECTURE.md)**: System design & data flow
- **[Installation Guide](krita-plugin/INSTALLATION.md)**: Detailed setup instructions
- **[Security Audit](docs/README-SECURITY-AUDIT.md)**: Comprehensive security review
- **[Security Quick Reference](docs/SECURITY-QUICK-REFERENCE.md)**: Security features overview
- **[Production Readiness](docs/PRODUCTION-READINESS.md)**: Release preparation status
- **[Tamper Resistance Testing](docs/tamper-resistance-testing-guide.md)**: Manual testing guide
- **[Automated Test Suite](tests/README-TAMPER-TESTS.md)**: Automated security tests

### Web Verification Tool

- **[Web App Integration Guide](../certified-human-made/Readme-webapp.txt)**: API specification for verification
- **[Dual-Hash Strategy](../certified-human-made/Readme-webapp.txt#dual-hash-verification-strategy)**: How re-encoded image verification works
- **[Verification Logic](../certified-human-made/Readme-webapp.txt#verification-logic)**: Step-by-step implementation
- **Try It Live**: [certified-human-made.org](https://certified-human-made.org)

---

## 🛠️ Development

### Building from Source

**For Users**: See the [Installation](#installation) section above — you don't need to build from source!

**For Developers**:

#### Requirements
- **Rust** 1.70+ ([install](https://rustup.rs))
- **Python** 3.9+ (Krita's bundled version)
- **Krita** 5.2+
- **Git**

#### Build & Install

```bash
# Clone repository
git clone https://github.com/armstrongl/krita-certified-human-made.git
cd krita-certified-human-made

# Build Rust core and install plugin (one command)
./install-plugin.sh
```

The install script will:
1. Build the Rust library with correct settings for Krita
2. Copy/symlink the plugin to your Krita plugin directory
3. Handle platform-specific configuration (macOS code signing, etc.)

#### Manual Build Steps

If you prefer manual control:

```bash
# Build Rust library
cargo build --release

# Copy compiled library to plugin
# macOS:
cp target/release/libchm.dylib krita-plugin/chm_verifier/lib/chm.so

# Linux:
cp target/release/libchm.so krita-plugin/chm_verifier/lib/chm.so

# Windows:
copy target\release\chm.pyd krita-plugin\chm_verifier\lib\chm.pyd

# Install to Krita plugin directory (see platform paths below)
# Then restart Krita
```

**Platform-Specific Plugin Directories**:
- **macOS**: `~/Library/Application Support/krita/pykrita/`
- **Linux**: `~/.local/share/krita/pykrita/`
- **Windows**: `%APPDATA%\krita\pykrita\`

See [krita-plugin/INSTALLATION.md](krita-plugin/INSTALLATION.md) for detailed development setup instructions.

**Run Tests**:
```bash
# Rust tests
cargo test

# Timestamp tests (requires network)
cargo test --ignored

# Python bindings test
./tests/test_python_bindings.sh

# Tamper resistance tests (automated security tests)
./tests/run-tamper-tests.sh

# Run with coverage
./tests/ci-tamper-tests.sh --coverage
```

### Project Structure

```
krita-certified-human-made/
├── src/                    # Rust core library
│   ├── lib.rs             # Module exports
│   ├── session.rs         # Session management
│   ├── events.rs          # Event types
│   ├── proof.rs           # Proof generation
│   ├── analysis.rs        # Classification engine
│   ├── crypto.rs          # Encryption & signatures
│   ├── error.rs           # Error handling
│   └── python_bindings.rs # PyO3 Python API
├── krita-plugin/          # Python Krita plugin
│   └── chm_verifier/      # Main plugin
├── tests/                 # Rust + integration tests
├── docs/                  # Documentation
└── Cargo.toml            # Rust dependencies
```

---

## 🤝 Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Areas Needing Help

- **Testing**: Beta test on different OS/Krita versions
- **Documentation**: Improve user guides, add translations
- **AI Plugin Detection**: Maintain registry of AI plugins
- **Import Detection**: Improve image analysis algorithms
- **UI/UX**: Polish PyQt5 dialogs

---

## 📜 License

GPL-3.0 (same as Krita) - see [LICENSE](LICENSE)

This ensures compatibility with Krita's licensing and potential future integration.

---

## 🙏 Acknowledgments

- **Krita Team**: Amazing open-source painting software
- **GitHub**: Free git hosting & immutable timestamp infrastructure
- **Art Community**: Feedback on privacy & usability

---

## 📬 Contact

- **Issues**: [GitHub Issues](https://github.com/armstrongl/krita-certified-human-made/issues)
- **Discussions**: [GitHub Discussions](https://github.com/armstrongl/krita-certified-human-made/discussions)

---

**Made with ❤️ for artists fighting AI art misrepresentation**

*Your creativity deserves proof.*

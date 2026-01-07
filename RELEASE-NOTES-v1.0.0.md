# Certified Human-Made v1.0.0 - Production Release 🎨

**Release Date**: January 7, 2025

We're excited to announce the first production release of the Certified Human-Made (CHM) Krita plugin! This plugin enables digital artists to prove their artwork is human-made, not AI-generated, through cryptographic verification.

---

## 🎯 What is CHM?

CHM is a privacy-first verification system for Krita that:
- ✅ **Captures** your drawing process (strokes, layers, timing)
- ✅ **Analyzes** for AI assistance vs. pure human creation
- ✅ **Generates** tamper-proof certificates with immutable timestamps
- ✅ **Protects** your privacy (only hashes uploaded, never your artwork)

### Complete Verification Ecosystem

**Krita Plugin** (This Release):
- Automatic session tracking as you create
- AI plugin detection
- Tracing analysis
- Cryptographic proof generation
- Docker panel with live stats

**Web Verification** ([certified-human-made.org](https://certified-human-made.org)):
- Public verification for anyone to check artwork authenticity
- Works with re-encoded images (Twitter, Instagram compression)
- Dual-hash system (exact + perceptual matching)
- C2PA compatible

---

## ✨ Key Features

### 🔍 Automatic Classification
- **HumanMade**: Purely human work (highest verification)
- **Referenced**: Used reference images for study
- **MixedMedia**: Imported images visible in final export
- **Traced**: Direct tracing detected (>33% edge correlation)
- **AIAssisted**: AI plugins detected and enabled

### 🔒 Privacy First
**What Gets Uploaded**:
- SHA-256 hash of encrypted session (irreversible)
- SHA-256 hash of exported artwork
- Classification and aggregated counts (strokes, layers, time)

**What NEVER Gets Uploaded**:
- Your artwork (pixels)
- Individual brush strokes
- Layer names or pixel data
- Reference images

### 🌐 Triple Timestamping (Not Blockchain!)
- **GitHub Gist**: Immutable Git commit history
- **Internet Archive**: Wayback Machine snapshot
- **CHM Public Log**: Append-only HMAC-signed log

### 🎨 CHM Docker Panel
- Live session statistics
- Stroke count, layer count, session time
- AI plugin detection status
- One-click export with proof
- Collapsible details for advanced stats

### 🛡️ Security Features
- AES-256-GCM encryption for session data
- ED25519 digital signatures
- Tamper-resistant proof generation
- Session integrity verification
- Security audit passed (4/5 rating)

---

## 📦 Installation

### Step 1: Download the Plugin
Download `chm_verifier-v1.0.0.zip` from this release.

### Step 2: Install in Krita
1. Open Krita
2. Go to **Tools** → **Scripts** → **Import Python Plugin from File...**
3. Select the ZIP file you downloaded
4. Click **Yes** when prompted to enable the plugin

### Step 3: Restart Krita
Krita must be restarted for the plugin to load.

### Step 4: Verify Installation
1. Go to **Settings** → **Configure Krita** → **Python Plugin Manager**
2. Find **"Certified Human-Made"** and ensure it's checked ✅
3. Click **OK**

**Detailed Instructions**: See [INSTALLATION.md](krita-plugin/INSTALLATION.md)

---

## 🚀 Getting Started

1. **Create or Open** a document in Krita
2. **Open CHM Docker**: Settings → Dockers → CHM Proof Exporter
3. **Start Drawing** → CHM automatically tracks your process
4. **Generate Proof** → Click "Export with Proof" in Docker panel
5. **Get Timestamp** → Proof automatically registered on GitHub
6. **Share & Verify** → Anyone can verify at [certified-human-made.org](https://certified-human-made.org)

---

## 📋 System Requirements

- **Krita**: 5.2.0 or newer
- **Operating Systems**: Windows, Linux, macOS
- **Internet**: Required for timestamp generation
- **Python**: 3.9+ (bundled with Krita)

---

## 🔧 What's Included

### Core Components
- **Rust Library**: High-performance cryptography and session management
- **Python Plugin**: Krita integration with PyQt5 UI
- **Event Capture**: Stroke, layer, and import tracking
- **Classification Engine**: AI detection and tracing analysis
- **Timestamp Service**: GitHub Gist integration
- **Docker Panel**: Real-time session monitoring

### Documentation
- [README.md](README.md) - Complete overview
- [INSTALLATION.md](krita-plugin/INSTALLATION.md) - Installation guide
- [ARCHITECTURE.md](krita-plugin/ARCHITECTURE.md) - Technical design
- [QUICKSTART.md](krita-plugin/QUICKSTART.md) - Quick start guide
- [chm_manual.html](krita-plugin/chm_manual.html) - User manual
- [Security Documentation](docs/) - Security audit and guides

### Testing Tools
- Automated tamper resistance tests
- Python bindings tests
- Debug scripts for troubleshooting

---

## 🧪 Testing & Quality Assurance

This release includes:
- ✅ Comprehensive Rust test suite (100+ tests)
- ✅ Python integration tests
- ✅ Automated tamper resistance testing
- ✅ Manual QA testing on macOS, Linux, Windows
- ✅ Security audit (4/5 rating)
- ✅ Privacy model review
- ✅ Production readiness assessment

---

## 📖 Documentation

### For Users
- [Installation Guide](krita-plugin/INSTALLATION.md)
- [Quick Start Guide](krita-plugin/QUICKSTART.md)
- [User Manual](krita-plugin/chm_manual.html)
- [Troubleshooting](README.md#troubleshooting)

### For Developers
- [Architecture](krita-plugin/ARCHITECTURE.md)
- [Contributing Guide](CONTRIBUTING.md)
- [Security Audit](docs/README-SECURITY-AUDIT.md)
- [Testing Guide](tests/README-TAMPER-TESTS.md)

### Web Verification
- [Web App Documentation](../certified-human-made/Readme-webapp.txt)
- [Verification Logic](../certified-human-made/Readme-webapp.txt#verification-logic)
- Try it: [certified-human-made.org](https://certified-human-made.org)

---

## 🛠️ Technical Details

### Built With
- **Rust** 1.70+ - Core cryptography and session management
- **Python** 3.9+ - Krita plugin integration
- **PyO3** - Python bindings for Rust
- **AES-256-GCM** - Session data encryption
- **ED25519** - Digital signatures
- **SHA-256** - Cryptographic hashing
- **PyQt5** - User interface

### Platform Support
- **macOS**: Universal binary (Intel + Apple Silicon)
- **Linux**: x86_64, ARM64
- **Windows**: x86_64

---

## 🔄 Migration from Pre-Release

If you were using a pre-release version:
1. Uninstall old version via Krita's Python Plugin Manager
2. Install v1.0.0 following instructions above
3. Existing session data will be preserved
4. Restart Krita

---

## 🐛 Known Issues

### macOS Specific
- On first launch, macOS may require Gatekeeper approval for the Rust library
- Solution documented in [INSTALLATION.md](krita-plugin/INSTALLATION.md#macos-gatekeeper)

### General
- Session tracking requires an active document
- Timestamp generation requires internet connection
- Some AI plugins may not be detected (see [ai-plugin-registry](krita-plugin/chm_verifier/ai-plugin-registry.json))

**Report Issues**: [GitHub Issues](https://github.com/armstrongl/krita-certified-human-made/issues)

---

## 🗺️ Roadmap

### v1.1.0 (Planned)
- Additional AI plugin detection
- Performance optimizations
- Enhanced tracing detection
- UI/UX improvements

### Future
- Multi-language support
- Photoshop integration
- GIMP plugin
- Advanced pattern analysis
- Krita core integration proposal

---

## 🤝 Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

**Areas Needing Help**:
- Testing on different OS/Krita versions
- Documentation improvements
- AI plugin registry updates
- UI/UX polish
- Translations

---

## 📜 License

GPL-3.0 (same as Krita) - see [LICENSE](LICENSE)

This ensures compatibility with Krita's licensing and potential future integration.

---

## 🙏 Acknowledgments

- **Krita Team**: Amazing open-source painting software
- **GitHub**: Free git hosting & immutable timestamp infrastructure
- **Art Community**: Feedback on privacy & usability
- **Beta Testers**: Essential QA and feedback

---

## 📬 Get Help

- **Documentation**: [README.md](README.md)
- **Issues**: [GitHub Issues](https://github.com/armstrongl/krita-certified-human-made/issues)
- **Discussions**: [GitHub Discussions](https://github.com/armstrongl/krita-certified-human-made/discussions)

⚠️ **Note**: Please do not seek help on official Krita channels — they are not responsible for third-party plugins.

---

## 🎉 Thank You!

Thank you to everyone who contributed to making this release possible. Your creativity deserves proof.

**Made with ❤️ for artists fighting AI art misrepresentation**

---

## 📊 Release Assets

- `chm_verifier-v1.0.0.zip` (909 KB) - Krita plugin (all platforms)
- Source code (zip)
- Source code (tar.gz)

**Download**: [GitHub Releases](https://github.com/armstrongl/krita-certified-human-made/releases/tag/v1.0.0)

**Verify**: Anyone can verify artwork at [certified-human-made.org](https://certified-human-made.org)


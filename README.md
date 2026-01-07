# Certified Human-Made (CHM) - Krita Plugin

**Prove your digital art is human-made, not AI-generated.**

A privacy-first verification system for Krita that captures your creative process and generates cryptographic proof of human authorship — **no blockchain, no crypto, no complexity**.

[![License: GPL-3.0](https://img.shields.io/badge/License-GPL%203.0-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Rust](https://img.shields.io/badge/rust-1.92+-orange.svg)](https://www.rust-lang.org)
[![Krita](https://img.shields.io/badge/krita-5.2+-purple.svg)](https://krita.org)

---

## 🎯 What is CHM?

### Why This Matters

In a world where AI can generate photorealistic art in seconds, **human creativity needs authentication**. Artists spend years developing their skills, and this plugin helps them prove it.

**How do you prove you actually drew something?**

CHM is a Krita plugin that:
- ✅ **Captures** your drawing process (strokes, layers, timing)
- ✅ **Analyzes** for AI assistance vs. pure human creation
- ✅ **Generates** tamper-proof certificates with immutable GitHub timestamps
- ✅ **Protects** your privacy (only hashes uploaded, never your artwork)

### What You Get

**Proof Certificate** (shareable):
```json
{
  "classification": "HumanMade",
  "confidence": 0.95,
  "stroke_count": 1247,
  "session_duration": "3h 42m",
  "references_used": true,
  "timestamps": {
    "github": "2025-12-28T10:30:45Z",
    "chm_log": 12345
  }
}
```

**Your Privacy**: Individual strokes, layer data, and artwork pixels **never leave your computer**.

---

## 🚀 Quick Start

### Installation

**Requirements**:
- Krita 5.2+ (macOS, Windows, or Linux)
- Internet connection (for timestamps)

**Install via Krita Resources** (Coming Soon):
1. Open Krita → Settings → Manage Resources
2. Search for "Certified Human-Made"
3. Click Install

**Manual Install** (Current):
1. Download latest release from [Releases](https://github.com/armstrongl/krita-certified-human-made/releases)
2. Extract to Krita plugin directory:
   - **macOS**: `~/Library/Application Support/krita/pykrita/`
   - **Windows**: `%APPDATA%/krita/pykrita/`
   - **Linux**: `~/.local/share/krita/pykrita/`
3. Restart Krita
4. Enable plugin: Settings → Configure Krita → Python Plugin Manager

### Usage

1. **Start Drawing** → CHM automatically tracks your session
2. **Finish Artwork** → Tools → CHM → Generate Proof
3. **Get Certificate** → Timestamped proof saved to `~/.local/share/chm/proofs/`
4. **Share Proof** → Post on social media, include in portfolio

---

## 🔒 Privacy First

### What Gets Uploaded (Public Timestamps)

- ✅ SHA-256 hash of encrypted session (irreversible)
- ✅ Classification ("PureHumanMade", "Referenced", etc.)
- ✅ Aggregated counts (1247 strokes, 5 layers, 3h 42m)
- ✅ Confidence score (0.95)

### What NEVER Gets Uploaded

- ❌ Your artwork (pixels)
- ❌ Individual brush strokes (coordinates, pressure, timing)
- ❌ Layer names or pixel data
- ❌ Reference images
- ❌ Any identifiable creative process data

**How It Works**: All session data encrypted locally (AES-256-GCM). Only a cryptographic hash is timestamped publicly. Even we cannot decrypt your creative process.

**Read More**: [Privacy & Data Flow](docs/privacy-model.md)

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
- **Tracing Analysis**: Compares imports vs. final artwork (edge correlation)
- **Pattern Analysis**: Human vs. AI workflow patterns

**Classification** (Highest to Lowest Verification Level):
1. `HumanMade`: Purely human work (references allowed if not traced/visible)
2. `Traced`: Direct tracing detected (>33% edge correlation)
3. `MixedMedia`: Imported images visible in final export
4. `AIAssisted`: AI plugins detected and enabled (lowest verification level)

**Note**: Using reference images is normal and professional! References only affect classification if you directly trace over them (>33% edge correlation) or leave them visible in the final export. Hidden references used for anatomy/pose study maintain the `HumanMade` label.

### 3. Generate Proof & Timestamp

```
Encrypted Session → SHA-256 Hash → Immutable Timestamp
                                    ├─ GitHub Gist (public, third-party)
                                    └─ CHM Local Log (HMAC-signed)
```

**Why GitHub Gist?** (Not Blockchain)
- ✅ **Immutable**: Git's cryptographic commit history provides proof-of-existence
- ✅ **Third-party verified**: Not controlled by user or CHM
- ✅ **Legally recognized**: Git commits are court-admissible
- ✅ **Zero cost**: No fees, unlimited public gists
- ✅ **Publicly auditable**: Anyone can verify the timestamp
- ✅ **No blockchain needed**: No crypto stigma, environmentally friendly

**Local CHM Log**: HMAC-signed append-only log provides supplementary verification for offline access

---

## 📖 Documentation

- **[Architecture](krita-plugin/ARCHITECTURE.md)**: System design & data flow
- **[Security Audit](docs/README-SECURITY-AUDIT.md)**: Comprehensive security review
- **[Security Quick Reference](docs/SECURITY-QUICK-REFERENCE.md)**: Security features overview
- **[Production Readiness](docs/PRODUCTION-READINESS.md)**: Release preparation status
- **[Tamper Resistance Testing](docs/tamper-resistance-testing-guide.md)**: Manual testing guide
- **[Automated Test Suite](tests/README-TAMPER-TESTS.md)**: Automated security tests

---

## 🛠️ Development

### Building from Source

**Requirements**:
- Rust 1.70+ ([install](https://rustup.rs))
- Python 3.9+
- Krita 5.2+

**Build**:
```bash
# Clone repository
git clone https://github.com/armstrongl/krita-certified-human-made.git
cd krita-certified-human-made

# Build Rust core
cargo build --release

# Copy plugin to Krita
cp -r krita-plugin/chm_verifier ~/Library/Application\ Support/krita/pykrita/

# Restart Krita
```

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
- **Tracing Detection**: Improve image comparison algorithms
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
- **Krita Artists**: [Forum Thread](https://krita-artists.org) (coming soon)

---

## 🗺️ Roadmap

### v1.0.0-rc1 (Current - Production Ready ✅)
- [x] Event capture implementation complete
- [x] Session management with encryption
- [x] Proof generation with ED25519 signatures
- [x] GitHub Gist immutable timestamping
- [x] AI plugin detection system
- [x] Import tracking and classification
- [x] Security audit passed (4/5 rating)
- [x] Comprehensive test suite

### v0.2.0-alpha (Phase 1 - In Progress)
- [ ] Event capture implementation
- [ ] Session management
- [ ] Proof generation
- [ ] Basic UI

### v0.3.0-beta (Phase 2)
- [ ] Classification engine
- [ ] AI plugin detection
- [ ] Tracing analysis
- [ ] Comprehensive testing

### v1.0.0 (Phase 3)
- [ ] Public release
- [ ] Krita Resources submission
- [ ] Community feedback integration
- [ ] Security audit

### Future
- [ ] Multi-language support
- [ ] Advanced pattern analysis
- [ ] Krita core integration proposal

---

**Made with ❤️ for artists fighting AI art misrepresentation**

*Your creativity deserves proof.*

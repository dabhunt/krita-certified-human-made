# CHM Krita Plugin - Architecture Documentation

## Table of Contents

1. [Overview](#overview)
2. [System Architecture](#system-architecture)
3. [Core Components](#core-components)
4. [Data Flow](#data-flow)
5. [Module Reference](#module-reference)
6. [Extension Points](#extension-points)
7. [Security Architecture](#security-architecture)

---

## Overview

The CHM Krita plugin is a Python-based extension that captures artistic workflow events and generates cryptographic proofs of human authorship. It operates entirely locally within Krita, with minimal network access (only for timestamping).

### Key Design Principles

1. **Privacy-First**: Artwork pixels and raw event data never leave the user's computer unencrypted
2. **Transparent**: Users see exactly what classification their work receives and why
3. **Non-Intrusive**: Captures events passively without interrupting the creative process
4. **Tamper-Resistant**: Uses cryptographic signatures to prevent proof forgery
5. **Modular**: Clean separation between capture, analysis, and proof generation

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Krita Application                         │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                    CHM Plugin (Python)                     │  │
│  │                                                             │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌─────────────────┐  │  │
│  │  │Event Capture │  │ Session Mgmt │  │ Classification  │  │  │
│  │  │              │→ │              │→ │   Analysis      │  │  │
│  │  │- Strokes     │  │- Storage     │  │- AI Detection   │  │  │
│  │  │- Layers      │  │- Encryption  │  │- Import Track   │  │  │
│  │  │- Imports     │  │- Persistence │  │                 │  │  │
│  │  └──────────────┘  └──────────────┘  └─────────────────┘  │  │
│  │                           ↓                                 │  │
│  │  ┌────────────────────────────────────────────────────┐    │  │
│  │  │           Proof Generation & Signing               │    │  │
│  │  │  - Aggregate metadata                              │    │  │
│  │  │  - ED25519 signatures (Rust or Python fallback)    │    │  │
│  │  │  - AES-256-GCM encryption                          │    │  │
│  │  └────────────────────────────────────────────────────┘    │  │
│  │                           ↓                                 │  │
│  │  ┌────────────────────────────────────────────────────┐    │  │
│  │  │        Triple Timestamp (Network Access)           │    │  │
│  │  │  - GitHub Gist API                                 │    │  │
│  │  │  - Internet Archive                                │    │  │
│  │  │  - CHM Public Log                                  │    │  │
│  │  └────────────────────────────────────────────────────┘    │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                             ↓
                    ~/.local/share/chm/
                    ├── sessions/     (encrypted)
                    ├── proofs/       (signed JSON)
                    └── logs/         (debug output)
```

---

## Core Components

### 1. Event Capture (`event_capture.py`)

**Responsibility**: Passively monitor and record user actions in Krita.

**Key Features**:
- Stroke detection via document polling (500ms intervals)
- Layer change detection (new layers, imports)
- Import detection (drag-drop, paste, file import)
- Undo/redo tracking
- AFK (away-from-keyboard) detection

**Technical Details**:
- Uses Qt event filters and Krita API signals
- Polls `document.modified()` for stroke detection (primary method)
- Thumbnail hashing to detect actual pixel changes (not just flag changes)
- Delayed import detection for paste operations (waits 3 seconds for pixels to load)

### 2. Session Management (`chm_session_manager.py`)

**Responsibility**: Manage artwork sessions from creation to proof generation.

**Key Features**:
- Session lifecycle (create, resume, finalize)
- Event aggregation and storage
- Metadata management
- Session migration (unsaved → saved documents)

**Data Structures**:
```python
Session {
    id: UUID,
    events: [Event],
    metadata: {
        canvas_size, krita_version, os_info,
        ai_tools_used, ai_plugins_detected, ...
    },
    drawing_time_secs: int,
    duration_secs: int,
    classification: "HumanMade" | "AIAssisted" | "MixedMedia"
}
```

### 3. Session Storage (`session_storage.py`)

**Responsibility**: Persist sessions to disk with encryption.

**Key Features**:
- AES-256-GCM encryption (optional)
- UUID-based keys for unsaved documents
- Filepath-based keys for saved documents
- Session migration on file save

**Storage Location**: `~/.local/share/chm/sessions/`

### 4. Plugin Monitor (`plugin_monitor.py`)

**Responsibility**: Detect AI plugins and tools in Krita.

**Key Features**:
- Scans Krita plugin directories
- Maintains AI plugin registry (JSON database)
- Distinguishes enabled vs. installed plugins

**Detection Methods**:
- File system scanning
- Krita plugin API queries

### 5. Import Tracker (`import_tracker.py`)

**Responsibility**: Track imported images and references.

**Key Features**:
- Detects drag-drop imports
- Detects paste operations
- Detects file → import operations
- Tracks import metadata (size, type, timestamp)

**Classification Logic**:
- Import detected → "MixedMedia" classification (sticky)

### 6. Proof Generation (`chm_core.py`, `c2pa_builder.py`)

**Responsibility**: Generate signed, timestamped proofs.

**Key Features**:
- Aggregates session events into summary
- Classifies artwork (HumanMade, AIAssisted, MixedMedia)
- Generates ED25519 signatures
- Creates C2PA-compatible metadata (optional)

**Output Format**:
```json
{
  "version": "1.0",
  "classification": "HumanMade",
  "confidence": 0.95,
  "session_summary": {
    "stroke_count": 1247,
    "layer_count": 12,
    "session_duration_secs": 13320,
    "drawing_time_secs": 8940
  },
  "signatures": {
    "session_hash": "sha256:...",
    "ed25519_signature": "..."
  },
  "timestamps": {
    "github": "2026-01-06T10:30:45Z",
    "archive": "2026-01-06T10:30:47Z"
  }
}
```

### 7. Timestamp Service (`timestamp_service.py`)

**Responsibility**: Create immutable, third-party timestamps.

**Services Used**:
1. **GitHub Gist** - Creates public gist with proof hash
2. **Internet Archive** - Submits to Wayback Machine
3. **CHM Public Log** - (Optional) Public blockchain-free log

**Why Not Blockchain?**: 
- Zero cost vs. gas fees
- No crypto stigma in art community
- Legally recognized timestamps
- More environmentally friendly

---

## Data Flow

### Typical Workflow

```
1. User Opens Krita Document
   ↓
2. CHM Plugin Initializes
   ↓ 
3. Try Resume Existing Session (if file previously opened)
   OR Create New Session
   ↓
4. User Draws (Events Captured Passively)
   - Strokes detected via polling (500ms)
   - Layers tracked via Krita signals
   - Imports detected on layer creation
   ↓
5. Session Persisted to Disk (on save, close, or periodic)
   ~/.local/share/chm/sessions/{session_id}.json (encrypted)
   ↓
6. User Clicks "Generate Proof" (Tools → CHM → Generate Proof)
   ↓
7. Classification Analysis
   - Check for AI plugins → "AIAssisted"
   - Check for imports → "MixedMedia"  
   - Default → "HumanMade"
   ↓
8. Proof Generation
   - Aggregate events into summary
   - Sign with ED25519 (Rust or Python fallback)
   - Encrypt full session data
   ↓
9. Triple Timestamp (Network Access)
   - Upload proof hash to GitHub Gist
   - Submit to Internet Archive
   - Log to CHM public log
   ↓
10. Save Proof Certificate
    ~/.local/share/chm/proofs/{artwork_name}_proof.json
    ↓
11. User Shares Proof
    - Post on social media
    - Include in portfolio
    - Verify at certifiedhumanmade.org
```

---

## Module Reference

### Core Modules

| Module | Lines | Purpose | Key Classes/Functions |
|--------|-------|---------|----------------------|
| `event_capture.py` | ~1900 | Event monitoring | `EventCapture`, `UndoRedoHandler` |
| `chm_session_manager.py` | ~488 | Session lifecycle | `CHMSessionManager`, `CHMSession` |
| `chm_extension.py` | ~1107 | Krita integration | `CHMExtension` (main entry point) |
| `chm_core.py` | ~715 | Proof generation | `generate_proof()`, `classify_session()` |
| `session_storage.py` | ~304 | Persistence | `SessionStorage` |
| `plugin_monitor.py` | ~245 | AI detection | `PluginMonitor` |
| `import_tracker.py` | ~133 | Import tracking | `ImportTracker` |

### Supporting Modules

| Module | Purpose |
|--------|---------|
| `config.py` | Centralized configuration |
| `logging_util.py` | Logging utilities |
| `c2pa_builder.py` | C2PA metadata format |
| `timestamp_service.py` | Triple timestamp API |
| `api_client.py` | HTTP client for timestamps |
| `png_metadata.py` | PNG metadata embedding |
| `ed25519_pure.py` | Pure Python ED25519 (fallback) |

### UI Modules

| Module | Purpose |
|--------|---------|
| `verification_dialog.py` | Proof verification UI |
| `session_info_dialog.py` | Session details UI |
| `export_confirmation_dialog.py` | Proof export UI |
| `path_preferences.py` | Settings UI |

---

## Extension Points

### Adding New Event Types

1. Add event type to `events.py` (if using Rust) or `CHMSession` class
2. Add capture logic in `event_capture.py`
3. Update aggregation in `chm_core.py` for classification

Example:
```python
# In event_capture.py
def on_new_event_type(self, data):
    session = self.session_manager.get_session(doc)
    session.record_custom_event("event_type", data)
```

### Adding New AI Plugins

Update `ai-plugin-registry.json`:
```json
{
  "name": "new-ai-plugin",
  "display_name": "New AI Plugin",
  "ai_type": "AI_GENERATION",
  "detection_paths": [
    "~/.local/share/krita/pykrita/new-ai-plugin/"
  ],
  "added_date": "2026-01-06"
}
```

### Adding New Classification Rules

Modify `classify_session()` in `chm_core.py`:
```python
def classify_session(session, ai_plugins, has_imports):
    # Priority 1: AI detection
    if ai_plugins:
        return "AIAssisted"
    
    # Priority 2: Import detection  
    if has_imports:
        return "MixedMedia"
    
    # Priority 3: NEW RULE HERE
    if custom_condition:
        return "CustomClassification"
    
    # Default: Pure human-made
    return "HumanMade"
```

---

## Security Architecture

### Cryptographic Stack

```
Component          Algorithm       Key Size    Purpose
─────────────────  ─────────────  ─────────  ─────────────────────
Signatures         ED25519         256-bit    Proof authenticity
Encryption         AES-256-GCM     256-bit    Session data privacy
Hashing            SHA-256         256-bit    Content integrity
Random Numbers     ChaCha20        -          Secure key generation
```

### Threat Model

**Protected Against**:
- ✅ Proof tampering (signatures detect any changes)
- ✅ Proof forgery (requires private signing key)
- ✅ Session replay (dual-hash binds proof to specific artwork)
- ✅ Metadata injection (code signing prevents plugin modification)

**Not Protected Against** (Out of Scope):
- ❌ User intentionally hiding AI usage (trust model)
- ❌ Social engineering (non-technical attack)
- ❌ Zero-day vulnerabilities in dependencies

### Privacy Guarantees

**What Stays Local** (Never Uploaded):
- Individual brush strokes (coordinates, pressure, timing)
- Layer pixel data
- Reference images
- Artwork pixels

**What Gets Timestamped** (Public):
- SHA-256 hash of encrypted session
- Classification ("HumanMade", "AIAssisted", etc.)
- Aggregated counts (1247 strokes, 12 layers, 3h 42m)
- Confidence score

---

## Development Guidelines

### Code Style

- **Python**: Follow PEP 8, use type hints
- **Max File Size**: 600 lines (modularize if larger)
- **Max Function Size**: 50 lines (split if larger)
- **Logging**: Use `logging_util` module, not print()
- **Configuration**: Use `config.py`, not hardcoded values

### Testing

- Unit tests for core logic
- Integration tests for Krita API interaction
- Security tests for crypto operations
- Manual testing checklist for UI

### Documentation

- Docstrings for all public functions
- Inline comments for complex logic
- Update this ARCHITECTURE.md when adding major features

---

## Debugging

### Enable Debug Mode

```bash
export CHM_DEBUG=true
krita
```

Logs written to: `~/.local/share/chm/logs/plugin_debug.log`

### Common Issues

**Plugin Not Loading**:
- Check `~/.local/share/chm/logs/plugin_debug.log`
- Verify Python version (3.9+)
- Check Krita plugin manager (Settings → Python Plugin Manager)

**Events Not Captured**:
- Enable debug mode
- Check for errors in log file
- Verify session was created (`session_manager.get_session()`)

**Proof Generation Fails**:
- Check network connectivity (for timestamps)
- Verify Rust crypto library loaded (or Python fallback)
- Check session has events (`session.event_count > 0`)

---

## Version History

- **v1.0.0-rc1** (2026-01-06): Production readiness refactor
- **v0.3.0-alpha**: Classification engine complete
- **v0.2.0-alpha**: Event capture implementation
- **v0.1.0-alpha**: Initial proof-of-concept

---

## Future Enhancements

### Planned Features

- [ ] Multi-language support
- [ ] Advanced pattern analysis (AI vs. human workflow detection)
- [ ] Krita core integration (upstream contribution)
- [ ] Real-time feedback during creation
- [ ] Proof verification API

### Research Areas

- Machine learning for human vs. AI workflow patterns
- Federated proof network (decentralized without blockchain)
- Integration with other digital art tools (Photoshop, Procreate)

---

**For More Information**:
- [Contributing Guide](../CONTRIBUTING.md)
- [Security Audit](../docs/README-SECURITY-AUDIT.md)
- [Installation Guide](INSTALLATION.md)
- [User Manual](chm_verifier/Manual.html)


# Contributing to Certified Human-Made

Thank you for your interest in contributing to CHM! This document provides guidelines for contributing.

## Code of Conduct

Be respectful, inclusive, and constructive. We're building tools for artists, and we value creativity and collaboration.

## How to Contribute

### Reporting Bugs

1. Check [existing issues](https://github.com/armstrongl/krita-certified-human-made/issues) first
2. Use the bug report template
3. Include:
   - Krita version
   - OS version
   - Steps to reproduce
   - Expected vs. actual behavior
   - Logs from `~/.local/share/chm/logs/`

### Suggesting Features

1. Check [discussions](https://github.com/armstrongl/krita-certified-human-made/discussions) first
2. Open a discussion (not an issue) to propose the feature
3. Explain the use case and why it's valuable
4. Be open to feedback

### Contributing Code

#### Setup Development Environment

```bash
# Fork the repository on GitHub
git clone https://github.com/YOUR_USERNAME/krita-certified-human-made.git
cd krita-certified-human-made

# Install dependencies
cargo build
cargo test

# Copy plugin to Krita for testing
cp -r krita-plugin/chm_verifier ~/Library/Application\ Support/krita/pykrita/
```

#### Coding Standards

**Rust**:
- Follow [Rust API Guidelines](https://rust-lang.github.io/api-guidelines/)
- Run `cargo fmt` before committing
- Run `cargo clippy` and fix warnings
- Add tests for new functionality
- Document public APIs with `///` comments

**Python**:
- Follow [PEP 8](https://pep8.org/)
- Use type hints where applicable
- Add docstrings for functions/classes
- Keep functions under 50 lines

**General**:
- Keep files under 400 lines (modularize if larger)
- Write meaningful commit messages
- One feature/fix per pull request

#### Pull Request Process

1. **Create a branch**: `git checkout -b feature/your-feature-name`
2. **Make changes**: Follow coding standards
3. **Test**: Run all tests (`cargo test`, manual Krita testing)
4. **Commit**: Use conventional commits format:
   ```
   feat: Add tracing detection algorithm
   fix: Correct session encryption key storage
   docs: Update privacy model documentation
   test: Add unit tests for proof generation
   ```
5. **Push**: `git push origin feature/your-feature-name`
6. **Open PR**: Use the pull request template
7. **Address feedback**: Respond to review comments
8. **Merge**: Once approved, we'll merge your PR

#### Testing

**Before submitting PR**:
- [ ] Rust tests pass: `cargo test`
- [ ] Python bindings work: `./tests/test_python_bindings.sh`
- [ ] Plugin loads in Krita without errors
- [ ] Manual testing of affected functionality
- [ ] No new linter warnings

### Contributing Documentation

Documentation improvements are highly valued!

- Fix typos, improve clarity
- Add examples and diagrams
- Translate to other languages (future)
- Update outdated information

### Maintaining AI Plugin Registry

Help us keep the AI plugin detection accurate:

1. Find a new AI plugin for Krita
2. Add to `ai-plugin-registry.json`:
   ```json
   {
     "name": "plugin-name",
     "type": "AI_GENERATION",
     "detection_paths": [
       "~/.local/share/krita/pykrita/plugin-name/"
     ],
     "added_date": "2025-12-28"
   }
   ```
3. Submit PR with the update

## Development Workflow

### Branch Strategy

- `main`: Stable releases only
- `develop`: Integration branch for features
- `feature/*`: Individual features
- `fix/*`: Bug fixes
- `docs/*`: Documentation updates

### Release Process

1. All features merged to `develop`
2. Testing on `develop`
3. Version bump in `Cargo.toml`
4. Merge `develop` → `main`
5. Tag release: `git tag v0.2.0`
6. Build binaries via GitHub Actions
7. Publish to GitHub Releases

## Getting Help

- **Questions**: [GitHub Discussions](https://github.com/armstrongl/krita-certified-human-made/discussions)
- **Chat**: (coming soon - Discord/Matrix?)
- **Krita Community**: [Krita Artists Forum](https://krita-artists.org)

## Recognition

Contributors will be:
- Listed in [CONTRIBUTORS.md](CONTRIBUTORS.md)
- Mentioned in release notes
- Credited in documentation (if applicable)

Thank you for helping make digital art verification accessible to all artists! 🎨


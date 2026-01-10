# Release Quick Start 🚀

## One-Time Setup

```bash
# 1. Install GitHub CLI
brew install gh

# 2. Authenticate
gh auth login
```

## Create a Release

### Patch Release (Bug Fixes)
```bash
./release.sh --patch
```
Example: 1.0.0 → 1.0.1

### Minor Release (New Features)
```bash
./release.sh --minor
```
Example: 1.0.0 → 1.1.0

### Major Release (Breaking Changes)
```bash
./release.sh --major
```
Example: 1.0.0 → 2.0.0

## That's It!

The script automatically:
- ✅ Updates version numbers
- ✅ Runs tests
- ✅ Builds the plugin
- ✅ Creates ZIP package
- ✅ Commits changes
- ✅ Creates git tag
- ✅ Pushes to GitHub
- ✅ Creates GitHub release
- ✅ Uploads ZIP file

**Full documentation**: See [docs/RELEASE-PROCESS.md](docs/RELEASE-PROCESS.md)

## Verify Release

After completion, visit:
```
https://github.com/dabhunt/krita-certified-human-made/releases
```

Download and test the ZIP file to ensure it works!


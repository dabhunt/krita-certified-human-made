# v1.0.0 Release Checklist ✅

## Completed Steps

- [x] Updated version to 1.0.0 in `Cargo.toml`
- [x] Updated version to 1.0.0 in `krita-plugin/chm_verifier.desktop`
- [x] Created git tag `v1.0.0`
- [x] Pushed tag to GitHub
- [x] Built Rust library for release
- [x] Created plugin distribution ZIP: `releases/chm_verifier-v1.0.0.zip` (109 MB)
- [x] Created comprehensive release notes: `RELEASE-NOTES-v1.0.0.md`
- [x] Created GitHub release body: `GITHUB-RELEASE-BODY.md`
- [x] Created release instructions: `CREATE-GITHUB-RELEASE.md`
- [x] Added `releases/` to `.gitignore` (files too large for git)
- [x] Pushed all changes to main

## Next Steps (Manual - GitHub Web UI)

### 1. Navigate to GitHub Releases
Go to: https://github.com/dabhunt/krita-certified-human-made/releases

### 2. Create New Release
- Click **"Draft a new release"**
- Select tag: **v1.0.0**
- Title: **Certified Human-Made v1.0.0 - Production Release**
- Description: Copy from `GITHUB-RELEASE-BODY.md`

### 3. Upload Assets
Upload this file:
- **Location**: `/Users/david/Documents/GitHub/krita-certified-human-made/releases/chm_verifier-v1.0.0.zip`
- **Size**: 109 MB
- **Description**: Krita plugin distribution (all platforms)

### 4. Publish Settings
- ✅ Set as the latest release
- ✅ Create a discussion for this release (optional)
- ❌ Do NOT mark as pre-release

### 5. Publish!
Click **"Publish release"**

## Release Assets Summary

### Main Distribution
- **File**: `chm_verifier-v1.0.0.zip`
- **Size**: 109 MB
- **Location**: `/Users/david/Documents/GitHub/krita-certified-human-made/releases/`
- **Contents**: 
  - Complete Krita plugin
  - Compiled Rust library (macOS)
  - All Python files
  - User manual (HTML)
  - Desktop file

### Documentation
- **README.md**: Complete overview with installation instructions
- **INSTALLATION.md**: Detailed installation guide
- **QUICKSTART.md**: Quick start guide
- **chm_manual.html**: User manual
- **ARCHITECTURE.md**: Technical architecture
- **CONTRIBUTING.md**: Contribution guidelines

### Release Materials
- **RELEASE-NOTES-v1.0.0.md**: Comprehensive release notes (this is also suitable for a blog post)
- **GITHUB-RELEASE-BODY.md**: Shorter release description for GitHub
- **CREATE-GITHUB-RELEASE.md**: Instructions for creating the release

## Verification After Publishing

After creating the release on GitHub, verify:

- [ ] Release appears on repository homepage
- [ ] Tag v1.0.0 is correctly linked
- [ ] ZIP file (109 MB) is downloadable
- [ ] Release notes display properly with formatting
- [ ] "Latest release" badge shows v1.0.0
- [ ] Source code archives are auto-generated (zip and tar.gz)

## Post-Release Tasks (Optional)

- [ ] Announce on Krita Artists Forum
- [ ] Tweet/social media announcement
- [ ] Update certified-human-made.org homepage with release info
- [ ] Submit to Krita Resources (if applicable)
- [ ] Create blog post using RELEASE-NOTES-v1.0.0.md
- [ ] Update project roadmap

## Installation Test

After publishing, test the installation process:

1. Download ZIP from GitHub releases
2. Install in Krita via Tools → Scripts → Import Python Plugin
3. Restart Krita
4. Enable in Python Plugin Manager
5. Verify functionality (create artwork, generate proof)

## Links

- **Repository**: https://github.com/dabhunt/krita-certified-human-made
- **Releases**: https://github.com/dabhunt/krita-certified-human-made/releases
- **Web Verification**: https://certified-human-made.org
- **Tag**: https://github.com/dabhunt/krita-certified-human-made/releases/tag/v1.0.0

## Notes

- The ZIP file is **not** in git (too large - 109 MB exceeds GitHub's 100 MB limit)
- The ZIP file will be uploaded directly to GitHub releases as an asset
- GitHub automatically generates source code archives (zip/tar.gz) from the v1.0.0 tag
- Plugin supports macOS, Linux, and Windows (platform-specific libraries included)

## Success Criteria

Release is successful when:
1. Users can download the ZIP from GitHub releases
2. Installation works via Krita's import feature
3. Plugin loads without errors
4. Core functionality works (session tracking, proof generation, verification)
5. Documentation is clear and accessible

---

**Status**: Ready for GitHub release creation! 🚀

Follow the instructions in `CREATE-GITHUB-RELEASE.md` to complete the release process.


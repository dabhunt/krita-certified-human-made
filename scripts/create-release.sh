#!/bin/bash
# Automated GitHub Release Creator for CHM Plugin
# Handles: version bump, build, package, commit, tag, and GitHub release creation

set -e

echo "🚀 CHM Automated Release Creator"
echo "================================="
echo ""

# Parse command line arguments
SKIP_BUILD=false
SKIP_TESTS=false
RELEASE_TYPE=""
CUSTOM_VERSION=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-build)
            SKIP_BUILD=true
            shift
            ;;
        --skip-tests)
            SKIP_TESTS=true
            shift
            ;;
        --patch|--minor|--major)
            RELEASE_TYPE="${1#--}"
            shift
            ;;
        --version)
            CUSTOM_VERSION="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --patch         Bump patch version (1.0.0 → 1.0.1)"
            echo "  --minor         Bump minor version (1.0.0 → 1.1.0)"
            echo "  --major         Bump major version (1.0.0 → 2.0.0)"
            echo "  --version X.Y.Z Set specific version"
            echo "  --skip-build    Skip build step (use existing binary)"
            echo "  --skip-tests    Skip test suite"
            echo "  --help          Show this help"
            echo ""
            echo "Example:"
            echo "  $0 --minor              # Create minor version release"
            echo "  $0 --version 1.2.3      # Create specific version"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Check if gh CLI is installed
if ! command -v gh &> /dev/null; then
    echo "❌ GitHub CLI (gh) is not installed!"
    echo ""
    echo "Install with:"
    echo "  macOS:   brew install gh"
    echo "  Linux:   See https://github.com/cli/cli/blob/trunk/docs/install_linux.md"
    echo "  Windows: See https://github.com/cli/cli/releases"
    echo ""
    echo "After installing, authenticate with: gh auth login"
    exit 1
fi

# Check if authenticated
if ! gh auth status &> /dev/null; then
    echo "❌ Not authenticated with GitHub!"
    echo ""
    echo "Run: gh auth login"
    exit 1
fi

echo "✅ GitHub CLI installed and authenticated"
echo ""

# Check and load Rust environment
echo "Checking Rust environment..."
echo "-----------------------------"

if ! command -v cargo &> /dev/null; then
    echo "⚠️  Cargo not found in PATH, attempting to load Rust environment..."
    if [ -f "$HOME/.cargo/env" ]; then
        source "$HOME/.cargo/env"
        if command -v cargo &> /dev/null; then
            echo "✅ Rust environment loaded successfully"
        else
            echo "❌ Failed to load Rust environment!"
            exit 1
        fi
    else
        echo "❌ Rust not installed!"
        echo ""
        echo "Install Rust from: https://rustup.rs/"
        echo ""
        echo "After installation, restart your terminal or run:"
        echo "  source \$HOME/.cargo/env"
        exit 1
    fi
else
    echo "✅ Rust/Cargo found: $(cargo --version)"
fi
echo ""

# Step 1: Determine new version
echo "Step 1: Determining version..."
echo "------------------------------"

CURRENT_VERSION=$(grep '^version = ' Cargo.toml | head -1 | cut -d'"' -f2)
echo "Current version: $CURRENT_VERSION"

if [ -n "$CUSTOM_VERSION" ]; then
    NEW_VERSION="$CUSTOM_VERSION"
    echo "Using custom version: $NEW_VERSION"
elif [ -n "$RELEASE_TYPE" ]; then
    # Parse current version
    IFS='.' read -r MAJOR MINOR PATCH <<< "$CURRENT_VERSION"
    
    case $RELEASE_TYPE in
        patch)
            NEW_VERSION="${MAJOR}.${MINOR}.$((PATCH + 1))"
            ;;
        minor)
            NEW_VERSION="${MAJOR}.$((MINOR + 1)).0"
            ;;
        major)
            NEW_VERSION="$((MAJOR + 1)).0.0"
            ;;
    esac
    echo "Bumping $RELEASE_TYPE version: $CURRENT_VERSION → $NEW_VERSION"
else
    echo ""
    echo "No version specified. Options:"
    echo "  --patch : $CURRENT_VERSION → $(echo $CURRENT_VERSION | awk -F. '{print $1"."$2"."$3+1}')"
    echo "  --minor : $CURRENT_VERSION → $(echo $CURRENT_VERSION | awk -F. '{print $1"."$2+1".0"}')"
    echo "  --major : $CURRENT_VERSION → $(echo $CURRENT_VERSION | awk -F. '{print $1+1".0.0"}')"
    echo "  --version X.Y.Z : Set specific version"
    echo ""
    exit 1
fi

echo ""

# Step 2: Check for uncommitted changes
echo "Step 2: Checking git status..."
echo "-------------------------------"

if ! git diff-index --quiet HEAD --; then
    echo "⚠️  You have uncommitted changes:"
    git status --short
    echo ""
    read -p "Commit these changes first? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        read -p "Enter commit message: " COMMIT_MSG
        git add -A
        git commit -m "$COMMIT_MSG"
        echo "✅ Changes committed"
    else
        echo "Please commit or stash changes before creating a release"
        exit 1
    fi
fi

echo "✅ Working directory clean"
echo ""

# Step 3: Update version numbers
echo "Step 3: Updating version numbers..."
echo "------------------------------------"

# Update Cargo.toml
sed -i.bak "s/^version = \".*\"/version = \"$NEW_VERSION\"/" Cargo.toml && rm Cargo.toml.bak
echo "✅ Updated Cargo.toml"

# Update plugin desktop file
DESKTOP_FILE="krita-plugin/chm_verifier.desktop"
if [ -f "$DESKTOP_FILE" ]; then
    sed -i.bak "s/^X-Version-Plugin=.*/X-Version-Plugin=$NEW_VERSION/" "$DESKTOP_FILE" && rm "${DESKTOP_FILE}.bak"
    echo "✅ Updated $DESKTOP_FILE"
fi

echo ""

# Step 4: Run tests (optional)
if [ "$SKIP_TESTS" = false ]; then
    echo "Step 4: Running tests..."
    echo "------------------------"
    
    if cargo test --quiet; then
        echo "✅ All tests passed"
    else
        echo "❌ Tests failed!"
        echo ""
        echo "Fix tests or use --skip-tests to bypass (not recommended)"
        exit 1
    fi
    echo ""
else
    echo "Step 4: Skipping tests (--skip-tests flag)"
    echo ""
fi

# Step 5: Build plugin
if [ "$SKIP_BUILD" = false ]; then
    echo "Step 5: Building plugin..."
    echo "--------------------------"
    
    if ./build-for-krita.sh; then
        echo "✅ Build successful"
    else
        echo "❌ Build failed!"
        exit 1
    fi
    echo ""
else
    echo "Step 5: Skipping build (--skip-build flag)"
    echo ""
fi

# Step 6: Package release
echo "Step 6: Packaging release..."
echo "----------------------------"

OUTPUT_FILE="releases/chm_verifier-v${NEW_VERSION}.zip"

# Remove existing ZIP if present
if [ -f "$OUTPUT_FILE" ]; then
    rm "$OUTPUT_FILE"
fi

# Create releases directory
mkdir -p releases

# Create ZIP (excluding vendor folder and other unnecessary files)
cd krita-plugin
zip -r "../$OUTPUT_FILE" \
    chm_verifier/ \
    chm_verifier.desktop \
    chm_manual.html \
    -x "*.pyc" \
    -x "*__pycache__*" \
    -x "*.DS_Store" \
    -x "*/.git/*" \
    -x "*/vendor/*" \
    -q

cd ..

ZIP_SIZE=$(ls -lh "$OUTPUT_FILE" | awk '{print $5}')
echo "✅ Package created: $OUTPUT_FILE ($ZIP_SIZE)"
echo ""

# Step 7: Commit version changes
echo "Step 7: Committing version bump..."
echo "-----------------------------------"

git add Cargo.toml Cargo.lock "$DESKTOP_FILE"
git commit -m "Bump version to $NEW_VERSION"
echo "✅ Version bump committed"
echo ""

# Step 8: Create and push git tag
echo "Step 8: Creating git tag..."
echo "---------------------------"

TAG_NAME="v${NEW_VERSION}"

# Check if tag already exists
if git rev-parse "$TAG_NAME" >/dev/null 2>&1; then
    echo "⚠️  Tag $TAG_NAME already exists"
    read -p "Delete and recreate? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        git tag -d "$TAG_NAME"
        git push origin ":refs/tags/$TAG_NAME" 2>/dev/null || true
    else
        echo "Aborted"
        exit 1
    fi
fi

# Create annotated tag
git tag -a "$TAG_NAME" -m "Release v${NEW_VERSION}

- Production-ready Krita plugin
- Privacy-first human-made art verification
- AI detection and classification
- Cryptographic proof generation
- Triple timestamping system"

echo "✅ Tag created: $TAG_NAME"
echo ""

# Step 9: Push to GitHub
echo "Step 9: Pushing to GitHub..."
echo "----------------------------"

git push origin main
git push origin "$TAG_NAME"

echo "✅ Pushed to GitHub"
echo ""

# Step 10: Generate release notes
echo "Step 10: Generating release notes..."
echo "-------------------------------------"

RELEASE_NOTES_FILE="releases/release-notes-v${NEW_VERSION}.md"

cat > "$RELEASE_NOTES_FILE" <<EOF
# Certified Human-Made v${NEW_VERSION}

**Prove your digital art is human-made, not AI-generated.**

## Installation

1. Download \`chm_verifier-v${NEW_VERSION}.zip\` below
2. Open Krita → Tools → Scripts → Import Python Plugin from File...
3. Select the downloaded ZIP file
4. Restart Krita
5. Enable plugin in Settings → Python Plugin Manager

## What's Included

- Complete Krita plugin (all platforms)
- Automatic session tracking
- AI plugin detection
- Cryptographic proof generation
- Privacy-first design (only hashes uploaded)
- Web verification at [certified-human-made.org](https://certified-human-made.org)

## System Requirements

- **Krita**: 5.2.0 or newer
- **OS**: Windows, Linux, macOS
- **Internet**: Required for timestamp generation

## Documentation

- [Installation Guide](https://github.com/dabhunt/krita-certified-human-made/blob/main/krita-plugin/INSTALLATION.md)
- [User Manual](https://github.com/dabhunt/krita-certified-human-made/blob/main/krita-plugin/chm_manual.html)
- [Quick Start](https://github.com/dabhunt/krita-certified-human-made/blob/main/krita-plugin/QUICKSTART.md)

## Changes in This Release

See commit history for detailed changes.

---

**License**: GPL-3.0  
**Made with ❤️ for artists fighting AI art misrepresentation**
EOF

echo "✅ Release notes created: $RELEASE_NOTES_FILE"
echo ""

# Step 11: Create GitHub release
echo "Step 11: Creating GitHub release..."
echo "------------------------------------"

echo "Creating release on GitHub..."

if gh release create "$TAG_NAME" \
    "$OUTPUT_FILE" \
    --title "Certified Human-Made v${NEW_VERSION}" \
    --notes-file "$RELEASE_NOTES_FILE" \
    --latest; then
    
    echo ""
    echo "======================================"
    echo "✅ Release Created Successfully!"
    echo "======================================"
    echo ""
    echo "Version: $NEW_VERSION"
    echo "Tag: $TAG_NAME"
    echo "Package: $OUTPUT_FILE ($ZIP_SIZE)"
    echo ""
    echo "View release:"
    echo "https://github.com/dabhunt/krita-certified-human-made/releases/tag/$TAG_NAME"
    echo ""
else
    echo ""
    echo "❌ Failed to create GitHub release"
    echo ""
    echo "The tag and commit were pushed successfully."
    echo "You can manually create the release at:"
    echo "https://github.com/dabhunt/krita-certified-human-made/releases/new?tag=$TAG_NAME"
    echo ""
    echo "Upload: $OUTPUT_FILE"
    exit 1
fi

# Step 12: Cleanup
echo "Step 12: Cleanup..."
echo "-------------------"

# Keep the ZIP file but could optionally clean other temp files
echo "✅ Release artifacts saved in releases/"
echo ""

echo "======================================"
echo "🎉 Release Complete!"
echo "======================================"
echo ""
echo "Next steps:"
echo "1. Test the release: Download and install from GitHub"
echo "2. Announce on social media"
echo "3. Update certified-human-made.org if needed"
echo ""


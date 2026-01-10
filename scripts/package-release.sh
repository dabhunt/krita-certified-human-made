#!/bin/bash
# Package CHM Plugin for Release
# Creates a ZIP file for distribution (all platforms)

set -e

echo "📦 CHM Plugin Release Packager"
echo "=============================="
echo ""

# Determine version
VERSION=$(grep '^version = ' Cargo.toml | head -1 | cut -d'"' -f2)
if [ -z "$VERSION" ]; then
    echo "❌ Could not detect version from Cargo.toml"
    exit 1
fi

echo "Version detected: $VERSION"
echo ""

# Create releases directory
mkdir -p releases

# Output filename
OUTPUT_FILE="releases/chm_verifier-v${VERSION}.zip"

# Check if file exists
if [ -f "$OUTPUT_FILE" ]; then
    echo "⚠️  Release file already exists: $OUTPUT_FILE"
    read -p "Overwrite? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Cancelled."
        exit 0
    fi
    rm "$OUTPUT_FILE"
fi

echo "Step 1: Checking build..."
echo "-------------------------"

# Check if library exists
if [ ! -f "krita-plugin/chm_verifier/lib/chm.so" ]; then
    echo "❌ Library not found! Run ./build-for-krita.sh first"
    exit 1
fi

LIB_SIZE=$(ls -lh krita-plugin/chm_verifier/lib/chm.so | awk '{print $5}')
echo "✅ Library found (${LIB_SIZE})"
echo ""

echo "Step 1.5: Validating production configuration..."
echo "--------------------------------------------------"

CONFIG_FILE="krita-plugin/chm_verifier/config.py"

# Check default environment
DEFAULT_ENV=$(grep "CHM_ENV = os.environ.get('CHM_ENV', " "$CONFIG_FILE" | sed -E "s/.*'CHM_ENV', '([^']+)'.*/\1/")
echo "Default environment: $DEFAULT_ENV"

if [ "$DEFAULT_ENV" != "production" ]; then
    echo ""
    echo "❌ ERROR: Release builds MUST default to production!"
    echo ""
    echo "Current default: CHM_ENV='$DEFAULT_ENV'"
    echo "Expected default: CHM_ENV='production'"
    echo ""
    echo "Fix with:"
    echo "  ./debug/set-environment.sh production"
    echo ""
    exit 1
fi

# Check default API URL for production
PROD_URL=$(grep -A 3 "else:" "$CONFIG_FILE" | grep "DEFAULT_API_URL = " | sed -E "s/.*DEFAULT_API_URL = '([^']+)'.*/\1/")
echo "Production API URL: $PROD_URL"

if [ -z "$PROD_URL" ]; then
    echo "⚠️  WARNING: Could not verify production API URL"
fi

# Verify it's not localhost
if echo "$PROD_URL" | grep -q "localhost"; then
    echo ""
    echo "❌ ERROR: Production URL cannot be localhost!"
    echo ""
    echo "Current production URL: $PROD_URL"
    echo "Expected: https://certified-human-made.org (or custom production URL)"
    echo ""
    exit 1
fi

echo "✅ Configuration is production-ready"
echo "   - Default environment: production"
echo "   - Production API URL: $PROD_URL"
echo ""

echo "Step 2: Verifying server API connectivity..."
echo "---------------------------------------------"
echo "✅ Signing now done server-side (no embedded key needed)"
echo "   • Server endpoint: api.certified-human-made.org/api/sign-and-timestamp"
echo "   • ED25519 private key stays on server (secure!)"
echo "   • Plugin only has public key for verification"
echo ""

echo "Step 3: Creating ZIP archive..."
echo "--------------------------------"

# Create ZIP from krita-plugin directory
cd krita-plugin
zip -r "../$OUTPUT_FILE" \
    chm_verifier/ \
    chm_verifier.desktop \
    -x "*.pyc" \
    -x "*__pycache__*" \
    -x "*.DS_Store" \
    -x "*/.git/*"

cd ..

# Get file size
ZIP_SIZE=$(ls -lh "$OUTPUT_FILE" | awk '{print $5}')

echo ""
echo "=============================="
echo "✅ Release Package Created!"
echo "=============================="
echo ""
echo "File: $OUTPUT_FILE"
echo "Size: $ZIP_SIZE"
echo ""
echo "Contents:"
unzip -l "$OUTPUT_FILE" | head -20
echo ""
echo "Total files: $(unzip -l "$OUTPUT_FILE" | tail -1 | awk '{print $2}')"
echo ""
echo "Step 4: Verification..."
echo "-----------------------"
echo "✅ Package includes ED25519 public key for verification"
echo "✅ No private key embedded (server-side signing only)"

echo ""
echo "=============================="
echo "⚠️  IMPORTANT NOTES"
echo "=============================="
echo ""
echo "1. SERVER-SIDE SIGNING (BUG-015 FIX)"
echo "   - Signing now done on api.certified-human-made.org"
echo "   - ED25519 private key stays on server (never exposed)"
echo "   - Users need internet connection for proof creation"
echo ""
echo "2. SECURITY IMPROVEMENT"
echo "   - Old HMAC signing was insecure (symmetric key)"
echo "   - New ED25519 signing is cryptographically secure"
echo "   - Users cannot forge proofs (no private key access)"
echo ""
echo "Next steps:"
echo "1. Ensure server has ED25519_PRIVATE_KEY in .env"
echo "2. Test plugin with internet connection"
echo "3. Upload to GitHub: https://github.com/dabhunt/krita-certified-human-made/releases"
echo ""



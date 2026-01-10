#!/bin/bash
#
# Quick Test: Dev Plugin Against Production Backend
#
# This script configures and builds the plugin to test against the production
# backend (or a Replit URL) without creating a full release build.
#

set -e

PROD_URL="${1:-https://certified-human-made.org}"

echo "🧪 Testing Dev Plugin Against Production Backend"
echo "================================================="
echo ""
echo "Target Backend: $PROD_URL"
echo ""

# Check if we're in the right directory
if [ ! -f "build-for-krita.sh" ]; then
    echo "❌ Error: Must run from krita-certified-human-made directory"
    exit 1
fi

echo "Step 1: Configure for production backend..."
./debug/set-environment.sh production "$PROD_URL"
echo ""

echo "Step 2: Build plugin..."
./build-for-krita.sh
echo ""

echo "Step 3: Update plugin..."
./dev-update-plugin.sh
echo ""

echo "✅ Plugin ready for testing!"
echo ""
echo "🎨 Next steps:"
echo "1. Restart Krita (if running)"
echo "2. Create a simple drawing"
echo "3. File → Export with CHM Proof"
echo "4. Check logs: tail -f ~/.local/share/chm/plugin_debug.log"
echo ""
echo "Expected log output:"
echo "  [CONFIG] Environment: production"
echo "  [CONFIG] API_URL: $PROD_URL"
echo "  [API-SIGN] POSTing to $PROD_URL/api/sign-and-timestamp..."
echo ""
echo "💡 To switch back to local development:"
echo "   ./debug/set-environment.sh development"
echo "   ./build-for-krita.sh && ./dev-update-plugin.sh"
echo ""


#!/bin/bash
#
# Quick Test: Dev Plugin Against Local Backend
#
# This script configures and builds the plugin to test against a local
# development server.
#

set -e

LOCAL_URL="${1:-http://localhost:5000}"

echo "🧪 Testing Dev Plugin Against Local Backend"
echo "============================================"
echo ""
echo "Target Backend: $LOCAL_URL"
echo ""

# Check if we're in the right directory
if [ ! -f "build-for-krita.sh" ]; then
    echo "❌ Error: Must run from krita-certified-human-made directory"
    exit 1
fi

echo "Step 1: Check if local server is running..."
if command -v curl &> /dev/null; then
    if curl -s -o /dev/null -w "%{http_code}" --connect-timeout 2 "$LOCAL_URL" | grep -q "200\|404"; then
        echo "✅ Server is running at $LOCAL_URL"
    else
        echo "❌ Server is NOT running at $LOCAL_URL"
        echo ""
        echo "Start the backend server first:"
        echo "  cd /Users/david/Documents/GitHub/certified-human-made"
        echo "  npm run dev"
        echo ""
        read -p "Continue anyway? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
fi
echo ""

echo "Step 2: Configure for local backend..."
./debug/set-environment.sh development "$LOCAL_URL"
echo ""

echo "Step 3: Build plugin..."
./build-for-krita.sh
echo ""

echo "Step 4: Update plugin..."
./dev-update-plugin.sh
echo ""

echo "✅ Plugin ready for testing!"
echo ""
echo "🎨 Next steps:"
echo "1. Make sure backend server is running:"
echo "   cd /Users/david/Documents/GitHub/certified-human-made"
echo "   npm run dev"
echo ""
echo "2. Restart Krita (if running)"
echo "3. Create a simple drawing"
echo "4. File → Export with CHM Proof"
echo "5. Check logs: tail -f ~/.local/share/chm/plugin_debug.log"
echo ""
echo "Expected log output:"
echo "  [CONFIG] Environment: development"
echo "  [CONFIG] API_URL: $LOCAL_URL"
echo "  [API-SIGN] POSTing to $LOCAL_URL/api/sign-and-timestamp..."
echo ""
echo "💡 To switch to production:"
echo "   ./debug/set-environment.sh production"
echo "   ./build-for-krita.sh && ./dev-update-plugin.sh"
echo ""


#!/bin/bash
#
# Set CHM Plugin to Use Development API URL
#
# This script configures the Krita plugin to use your Replit development URL
# instead of the production certified-human-made.org domain.
#
# Usage:
#   ./debug/set-dev-api-url.sh https://your-repl-name.replit.app
#   ./debug/set-dev-api-url.sh production  # Reset to production URL
#

set -e

API_URL="$1"

if [ -z "$API_URL" ]; then
    echo "❌ Error: Please provide API URL or 'production'"
    echo ""
    echo "Usage:"
    echo "  $0 <API_URL>          # Set custom API URL"
    echo "  $0 production         # Reset to production URL"
    echo ""
    echo "Examples:"
    echo "  $0 https://certified-human-made-dabhunt.replit.app"
    echo "  $0 https://9b9241a8-xyz.replit.dev"
    echo "  $0 production"
    exit 1
fi

CONFIG_FILE="krita-plugin/chm_verifier/config.py"

# Check if config file exists
if [ ! -f "$CONFIG_FILE" ]; then
    echo "❌ Error: Config file not found: $CONFIG_FILE"
    echo "Run this script from the krita-certified-human-made directory"
    exit 1
fi

# Handle "production" keyword
if [ "$API_URL" = "production" ]; then
    API_URL="https://certified-human-made.org"
    echo "🔧 Resetting to production URL..."
else
    echo "🔧 Setting development API URL..."
fi

# Update config.py
echo "📝 Updating $CONFIG_FILE..."

# Use sed to update the API_URL line
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS sed syntax
    sed -i '' "s|^API_URL = .*|API_URL = os.environ.get('CHM_API_URL', '$API_URL')|" "$CONFIG_FILE"
else
    # Linux sed syntax
    sed -i "s|^API_URL = .*|API_URL = os.environ.get('CHM_API_URL', '$API_URL')|" "$CONFIG_FILE"
fi

echo "✅ Config updated!"
echo ""
echo "Current setting:"
grep "^API_URL = " "$CONFIG_FILE"
echo ""
echo "🔄 Next steps:"
echo "1. Run: ./build-for-krita.sh && ./dev-update-plugin.sh"
echo "2. Restart Krita"
echo "3. Try exporting with CHM proof"
echo ""
echo "💡 Tip: You can override this in Krita by setting environment variable:"
echo "   export CHM_API_URL='https://your-custom-url.com'"


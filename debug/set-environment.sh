#!/bin/bash
#
# CHM Plugin Environment Switcher
#
# Easily switch between development and production backend configurations.
# This script helps you test the plugin against different backend environments.
#
# Usage:
#   ./debug/set-environment.sh production              # Use production backend
#   ./debug/set-environment.sh development             # Use local backend
#   ./debug/set-environment.sh production <CUSTOM_URL> # Use custom production URL
#   ./debug/set-environment.sh development <CUSTOM_URL># Use custom dev URL
#

set -e

ENV_MODE="$1"
CUSTOM_URL="$2"

if [ -z "$ENV_MODE" ]; then
    echo "❌ Error: Environment mode required"
    echo ""
    echo "Usage:"
    echo "  $0 production              # Use production backend (certified-human-made.org)"
    echo "  $0 development             # Use local backend (localhost:5000)"
    echo "  $0 production <URL>        # Use custom production URL"
    echo "  $0 development <URL>       # Use custom dev URL"
    echo ""
    echo "Examples:"
    echo "  $0 production              # Standard production"
    echo "  $0 development             # Local development"
    echo "  $0 production https://your-repl.replit.app"
    exit 1
fi

CONFIG_FILE="krita-plugin/chm_verifier/config.py"

# Check if config file exists
if [ ! -f "$CONFIG_FILE" ]; then
    echo "❌ Error: Config file not found: $CONFIG_FILE"
    echo "Run this script from the krita-certified-human-made directory"
    exit 1
fi

echo "🔧 CHM Plugin Environment Switcher"
echo "=================================="
echo ""

case "$ENV_MODE" in
    production)
        if [ -n "$CUSTOM_URL" ]; then
            NEW_DEFAULT_URL="$CUSTOM_URL"
            echo "Setting PRODUCTION mode with CUSTOM URL..."
            echo "  Environment: production"
            echo "  API URL: $CUSTOM_URL"
        else
            NEW_DEFAULT_URL="https://certified-human-made.org"
            echo "Setting PRODUCTION mode..."
            echo "  Environment: production"
            echo "  API URL: https://certified-human-made.org"
        fi
        NEW_ENV="production"
        ;;
        
    development)
        if [ -n "$CUSTOM_URL" ]; then
            NEW_DEFAULT_URL="$CUSTOM_URL"
            echo "Setting DEVELOPMENT mode with CUSTOM URL..."
            echo "  Environment: development"
            echo "  API URL: $CUSTOM_URL"
        else
            NEW_DEFAULT_URL="http://localhost:5000"
            echo "Setting DEVELOPMENT mode..."
            echo "  Environment: development"
            echo "  API URL: http://localhost:5000"
        fi
        NEW_ENV="development"
        ;;
        
    *)
        echo "❌ Error: Invalid environment mode: $ENV_MODE"
        echo "Must be 'production' or 'development'"
        exit 1
        ;;
esac

echo ""
echo "📝 Updating config.py..."

# Create backup
cp "$CONFIG_FILE" "$CONFIG_FILE.backup"

# Update CHM_ENV default
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS sed syntax
    sed -i '' "s|^CHM_ENV = os.environ.get('CHM_ENV', '.*').lower()|CHM_ENV = os.environ.get('CHM_ENV', '$NEW_ENV').lower()|" "$CONFIG_FILE"
else
    # Linux sed syntax
    sed -i "s|^CHM_ENV = os.environ.get('CHM_ENV', '.*').lower()|CHM_ENV = os.environ.get('CHM_ENV', '$NEW_ENV').lower()|" "$CONFIG_FILE"
fi

# Update the if/else block for DEFAULT_API_URL based on environment
if [ "$NEW_ENV" = "development" ]; then
    # Set development URL
    if [[ "$OSTYPE" == "darwin"* ]]; then
        sed -i '' "s|^    DEFAULT_API_URL = 'http://localhost:5000'|    DEFAULT_API_URL = '$NEW_DEFAULT_URL'|" "$CONFIG_FILE"
    else
        sed -i "s|^    DEFAULT_API_URL = 'http://localhost:5000'|    DEFAULT_API_URL = '$NEW_DEFAULT_URL'|" "$CONFIG_FILE"
    fi
else
    # Set production URL
    if [[ "$OSTYPE" == "darwin"* ]]; then
        sed -i '' "s|^    DEFAULT_API_URL = 'https://certified-human-made.org'|    DEFAULT_API_URL = '$NEW_DEFAULT_URL'|" "$CONFIG_FILE"
    else
        sed -i "s|^    DEFAULT_API_URL = 'https://certified-human-made.org'|    DEFAULT_API_URL = '$NEW_DEFAULT_URL'|" "$CONFIG_FILE"
    fi
fi

echo "✅ Config updated!"
echo ""
echo "Current configuration in config.py:"
echo "-----------------------------------"
grep "^CHM_ENV = " "$CONFIG_FILE" || true
grep "^    DEFAULT_API_URL = " "$CONFIG_FILE" || true
echo ""
echo "🔄 Next steps:"
echo "1. Build plugin: ./build-for-krita.sh"
echo "2. Update plugin: ./dev-update-plugin.sh"
echo "3. Restart Krita"
echo "4. Test export"
echo ""
echo "💡 To override at runtime, set environment variable before launching Krita:"
echo "   export CHM_API_URL='https://your-custom-url.com'"
echo "   /Applications/Krita.app/Contents/MacOS/krita"
echo ""
echo "📋 Backup saved to: $CONFIG_FILE.backup"
echo "   To restore: cp $CONFIG_FILE.backup $CONFIG_FILE"
echo ""

#!/bin/bash
#
# Set CHM Plugin Environment (Dev vs Production)
#
# This configures whether the plugin uses localhost:5000 (dev) or
# certified-human-made.org (production) for the backend API.
#
# Usage:
#   ./debug/set-environment.sh dev         # Use localhost:5000
#   ./debug/set-environment.sh production  # Use certified-human-made.org
#   ./debug/set-environment.sh status      # Show current setting
#

set -e

MODE="$1"
CONFIG_FILE="krita-plugin/chm_verifier/config.py"

# Check if config file exists
if [ ! -f "$CONFIG_FILE" ]; then
    echo "❌ Error: Config file not found: $CONFIG_FILE"
    echo "Run this script from the krita-certified-human-made directory"
    exit 1
fi

# Show current status
show_status() {
    echo ""
    echo "📊 Current Configuration:"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    # Check what's in the config
    if grep -q "IS_PRODUCTION = os.environ.get('CHM_ENV', '').lower() == 'production'" "$CONFIG_FILE"; then
        echo "Environment: 🔧 DEVELOPMENT (default)"
        echo "API URL: http://localhost:5000"
        echo ""
        echo "💡 Plugin will connect to local backend server"
    elif grep -q "IS_DEVELOPMENT = os.environ.get('CHM_ENV', '').lower() != 'production'" "$CONFIG_FILE"; then
        echo "Environment: 🚀 PRODUCTION"
        echo "API URL: https://certified-human-made.org"
        echo ""
        echo "💡 Plugin will connect to production server"
    else
        echo "⚠️  Unknown configuration"
    fi
    
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
}

# Handle commands
case "$MODE" in
    dev|development)
        echo "🔧 Setting DEVELOPMENT mode..."
        echo ""
        
        # Set IS_PRODUCTION = False (development is default)
        if [[ "$OSTYPE" == "darwin"* ]]; then
            # macOS
            sed -i '' "s|^IS_PRODUCTION = .*|IS_PRODUCTION = os.environ.get('CHM_ENV', '').lower() == 'production'|" "$CONFIG_FILE"
            sed -i '' "s|^IS_DEVELOPMENT = .*|IS_DEVELOPMENT = not IS_PRODUCTION  # Default to development mode|" "$CONFIG_FILE"
        else
            # Linux
            sed -i "s|^IS_PRODUCTION = .*|IS_PRODUCTION = os.environ.get('CHM_ENV', '').lower() == 'production'|" "$CONFIG_FILE"
            sed -i "s|^IS_DEVELOPMENT = .*|IS_DEVELOPMENT = not IS_PRODUCTION  # Default to development mode|" "$CONFIG_FILE"
        fi
        
        echo "✅ Development mode enabled!"
        show_status
        echo "🔄 Next steps:"
        echo "1. Run: ./build-for-krita.sh && ./dev-update-plugin.sh"
        echo "2. Start local backend: cd ../certified-human-made && bun run dev"
        echo "3. Restart Krita"
        echo "4. Plugin will use http://localhost:5000"
        ;;
    
    prod|production)
        echo "🚀 Setting PRODUCTION mode..."
        echo ""
        
        # Set IS_PRODUCTION = True
        if [[ "$OSTYPE" == "darwin"* ]]; then
            # macOS
            sed -i '' "s|^IS_PRODUCTION = .*|IS_PRODUCTION = True  # Production mode|" "$CONFIG_FILE"
            sed -i '' "s|^IS_DEVELOPMENT = .*|IS_DEVELOPMENT = False|" "$CONFIG_FILE"
        else
            # Linux
            sed -i "s|^IS_PRODUCTION = .*|IS_PRODUCTION = True  # Production mode|" "$CONFIG_FILE"
            sed -i "s|^IS_DEVELOPMENT = .*|IS_DEVELOPMENT = False|" "$CONFIG_FILE"
        fi
        
        echo "✅ Production mode enabled!"
        show_status
        echo "🔄 Next steps:"
        echo "1. Run: ./build-for-krita.sh && ./dev-update-plugin.sh"
        echo "2. Restart Krita"
        echo "3. Plugin will use https://certified-human-made.org"
        ;;
    
    status|check)
        show_status
        ;;
    
    *)
        echo "❌ Error: Invalid mode"
        echo ""
        echo "Usage:"
        echo "  $0 dev          # Set to development mode (localhost:5000)"
        echo "  $0 production   # Set to production mode (certified-human-made.org)"
        echo "  $0 status       # Show current configuration"
        echo ""
        echo "Examples:"
        echo "  $0 dev          # For local development"
        echo "  $0 production   # For testing with production server"
        echo "  $0 status       # Check current setting"
        exit 1
        ;;
esac


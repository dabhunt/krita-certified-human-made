#!/bin/bash
#
# CHM Plugin Configuration Diagnostic
#
# Shows current plugin configuration including environment variables,
# config file settings, and resolved API URL.
#

set -e

echo "🔍 CHM Plugin Configuration Diagnostic"
echo "======================================="
echo ""

CONFIG_FILE="krita-plugin/chm_verifier/config.py"

# Check if config file exists
if [ ! -f "$CONFIG_FILE" ]; then
    echo "❌ Error: Config file not found: $CONFIG_FILE"
    echo "Run this script from the krita-certified-human-made directory"
    exit 1
fi

echo "📁 Config File: $CONFIG_FILE"
echo ""

echo "1️⃣  ENVIRONMENT VARIABLES"
echo "-------------------------"
if [ -n "$CHM_ENV" ]; then
    echo "CHM_ENV = '$CHM_ENV' ✓"
else
    echo "CHM_ENV = (not set - will use config.py default)"
fi

if [ -n "$CHM_API_URL" ]; then
    echo "CHM_API_URL = '$CHM_API_URL' ✓"
else
    echo "CHM_API_URL = (not set - will use config.py default)"
fi
echo ""

echo "2️⃣  CONFIG FILE DEFAULTS"
echo "------------------------"
echo "Default environment:"
grep "^CHM_ENV = os.environ.get" "$CONFIG_FILE" | head -1 || echo "(not found)"
echo ""
echo "URL for development:"
grep "DEFAULT_API_URL = 'http://localhost:5000'" "$CONFIG_FILE" || echo "(not set to localhost)"
echo ""
echo "URL for production:"
grep "DEFAULT_API_URL = 'https://certified-human-made.org'" "$CONFIG_FILE" || grep "DEFAULT_API_URL = 'https://" "$CONFIG_FILE" || echo "(not found)"
echo ""

echo "3️⃣  RESOLVED CONFIGURATION"
echo "---------------------------"

# Simulate the Python logic to determine actual values
if [ -n "$CHM_ENV" ]; then
    RESOLVED_ENV="$CHM_ENV"
else
    # Extract default from config.py
    RESOLVED_ENV=$(grep "^CHM_ENV = os.environ.get" "$CONFIG_FILE" | sed -E "s/.*'CHM_ENV', '([^']+)'.*/\1/")
fi

echo "Environment: $RESOLVED_ENV"

if [ -n "$CHM_API_URL" ]; then
    RESOLVED_URL="$CHM_API_URL"
else
    # Extract URL based on environment
    if [ "$RESOLVED_ENV" = "development" ]; then
        RESOLVED_URL=$(grep "DEFAULT_API_URL = 'http" "$CONFIG_FILE" | sed -E "s/.*DEFAULT_API_URL = '([^']+)'.*/\1/" | head -1)
    else
        RESOLVED_URL=$(grep "DEFAULT_API_URL = 'https" "$CONFIG_FILE" | sed -E "s/.*DEFAULT_API_URL = '([^']+)'.*/\1/" | head -1)
    fi
fi

echo "API URL: $RESOLVED_URL"
echo ""

echo "4️⃣  CONNECTIVITY TEST"
echo "---------------------"
echo "Testing connection to: $RESOLVED_URL"

if command -v curl &> /dev/null; then
    # Test with curl
    if curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 "$RESOLVED_URL" | grep -q "200\|301\|302\|404"; then
        echo "✅ Server is reachable"
    else
        echo "❌ Server is NOT reachable (timeout or connection refused)"
        echo "   This could mean:"
        echo "   - Server is not running"
        echo "   - URL is incorrect"
        echo "   - Network/firewall issue"
    fi
else
    echo "⚠️  curl not available - skipping connectivity test"
fi
echo ""

echo "5️⃣  RECOMMENDATIONS"
echo "-------------------"

if [ "$RESOLVED_ENV" = "development" ] && [ "$RESOLVED_URL" != "http://localhost:5000" ]; then
    echo "⚠️  Custom development URL detected: $RESOLVED_URL"
    echo "   Make sure your local server is running on this URL"
fi

if [ "$RESOLVED_ENV" = "production" ] && [ "$RESOLVED_URL" = "http://localhost:5000" ]; then
    echo "❌ PROBLEM: Production mode but using localhost URL!"
    echo "   This will fail unless you have a local server running"
    echo "   Fix: ./debug/set-environment.sh production"
fi

if [ "$RESOLVED_ENV" = "development" ] && [ "$RESOLVED_URL" = "https://certified-human-made.org" ]; then
    echo "⚠️  Development mode but using production URL"
    echo "   This is OK for testing dev plugin against production backend"
fi

echo ""
echo "📚 QUICK COMMANDS"
echo "-----------------"
echo "Switch to production:   ./debug/set-environment.sh production"
echo "Switch to development:  ./debug/set-environment.sh development"
echo "Use Replit URL:         ./debug/set-environment.sh production https://your-repl.replit.app"
echo "Build and update:       ./build-for-krita.sh && ./dev-update-plugin.sh"
echo "View plugin logs:       tail -50 ~/.local/share/chm/plugin_debug.log"
echo ""


#!/bin/bash

# Quick Development Update Script for macOS
# Use this during development to quickly update the plugin after code changes
# Much faster than full install-plugin.sh

set -e

echo "🔄 CHM Quick Plugin Update (macOS)"
echo "=================================="
echo ""

PLUGIN_DIR="$HOME/Library/Application Support/krita/pykrita"
SOURCE_DIR="$(pwd)/krita-plugin/chm_verifier"

# Check if we're in the right directory
if [ ! -d "krita-plugin/chm_verifier" ]; then
    echo "❌ Error: Must run from krita-certified-human-made directory"
    exit 1
fi

# Check if Krita is running
if pgrep -x "krita" > /dev/null; then
    echo "⚠️  WARNING: Krita is currently running"
    echo "   You must restart Krita for changes to take effect"
    echo ""
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo "Updating Python files..."
# Only copy Python files (faster than copying everything)
cp "$SOURCE_DIR"/*.py "$PLUGIN_DIR/chm_verifier/" 2>/dev/null || true
cp "$SOURCE_DIR/chm_verifier.desktop" "$PLUGIN_DIR/" 2>/dev/null || true

echo "✅ Python files updated"
echo ""

# Check if Rust library needs updating
SOURCE_LIB="$SOURCE_DIR/lib/chm.so"
DEST_LIB="$PLUGIN_DIR/chm_verifier/lib/chm.so"

if [ -f "$SOURCE_LIB" ]; then
    # Compare modification times
    if [ "$SOURCE_LIB" -nt "$DEST_LIB" ]; then
        echo "Rust library changed, updating..."
        mkdir -p "$PLUGIN_DIR/chm_verifier/lib"
        cp "$SOURCE_LIB" "$DEST_LIB"
        
        # Ensure unsigned for macOS
        codesign --remove-signature "$DEST_LIB" 2>/dev/null || true
        echo "✅ Rust library updated and unsigned"
    else
        echo "ℹ️  Rust library unchanged (skipping)"
    fi
else
    echo "⚠️  No Rust library found in source (run build-for-krita.sh first)"
fi

echo ""
echo "=================================="
echo "✅ Update Complete!"
echo "=================================="
echo ""
echo "Next steps:"
echo "  1. Restart Krita (if running)"
echo "  2. Check debug log:"
echo "     tail -f ~/.local/share/chm/plugin_debug.log"
echo ""


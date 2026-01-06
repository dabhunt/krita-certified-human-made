#!/bin/bash

# Quick fix for macOS code signature issue
# This removes the code signature from the CHM library to allow Krita to load it

echo "🔧 CHM macOS Code Signature Fix"
echo "================================"
echo ""

PLUGIN_LIB="$HOME/Library/Application Support/krita/pykrita/chm_verifier/lib/chm.so"

if [ ! -f "$PLUGIN_LIB" ]; then
    echo "❌ Library not found at: $PLUGIN_LIB"
    echo ""
    echo "Make sure you've run ./install-plugin.sh first"
    exit 1
fi

echo "Current signature status:"
codesign -dv "$PLUGIN_LIB" 2>&1 | head -5

echo ""
echo "Removing code signature..."
codesign --remove-signature "$PLUGIN_LIB"

echo ""
echo "New signature status:"
codesign -dv "$PLUGIN_LIB" 2>&1 || echo "✅ No signature (this is correct)"

echo ""
echo "================================"
echo "✅ Fix Applied!"
echo "================================"
echo ""
echo "Next steps:"
echo "  1. Delete debug log: rm -f ~/.local/share/chm/plugin_debug.log"
echo "  2. Restart Krita"
echo "  3. Check log: cat ~/.local/share/chm/plugin_debug.log"
echo ""
echo "You should now see the plugin load successfully!"
echo ""



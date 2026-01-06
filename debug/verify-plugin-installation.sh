#!/bin/bash

# CHM Plugin Installation Verification Script
# This script checks all aspects of the plugin installation

echo "=========================================="
echo "CHM Plugin Installation Verification"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Detect OS
OS_TYPE=$(uname -s)
echo "OS: $OS_TYPE"
echo ""

# Set plugin paths based on OS
if [[ "$OS_TYPE" == "Darwin" ]]; then
    PLUGIN_DIR="$HOME/Library/Application Support/krita/pykrita"
    KRITA_RC="$HOME/Library/Preferences/kritarc"
elif [[ "$OS_TYPE" == "Linux" ]]; then
    PLUGIN_DIR="$HOME/.local/share/krita/pykrita"
    KRITA_RC="$HOME/.config/kritarc"
else
    echo "${RED}✗ Unsupported OS: $OS_TYPE${NC}"
    exit 1
fi

echo "Expected plugin directory: $PLUGIN_DIR"
echo ""

# Check 1: Plugin directory exists
echo "Check 1: Plugin Directory"
echo "-------------------------"
if [ -d "$PLUGIN_DIR" ]; then
    echo "${GREEN}✓ Plugin directory exists${NC}"
else
    echo "${RED}✗ Plugin directory does not exist: $PLUGIN_DIR${NC}"
    echo "  Run: mkdir -p \"$PLUGIN_DIR\""
    exit 1
fi
echo ""

# Check 2: CHM plugin files exist
echo "Check 2: CHM Plugin Files"
echo "-------------------------"
PLUGIN_PATH="$PLUGIN_DIR/chm_verifier"
if [ -d "$PLUGIN_PATH" ]; then
    echo "${GREEN}✓ chm_verifier directory exists${NC}"
else
    echo "${RED}✗ chm_verifier directory not found${NC}"
    echo "  Expected: $PLUGIN_PATH"
    exit 1
fi

# Check required files
REQUIRED_FILES=(
    "__init__.py"
    "chm_extension.py"
    "chm_session_manager.py"
    "event_capture.py"
    "lib/chm.so"
)

for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$PLUGIN_PATH/$file" ]; then
        echo "${GREEN}✓ $file exists${NC}"
    else
        echo "${RED}✗ $file missing${NC}"
    fi
done
echo ""

# Check 3: Desktop file
echo "Check 3: Desktop Entry File"
echo "----------------------------"
DESKTOP_FILE="$PLUGIN_DIR/chm_verifier.desktop"
if [ -f "$DESKTOP_FILE" ]; then
    echo "${GREEN}✓ chm_verifier.desktop exists${NC}"
    echo "  Location: $DESKTOP_FILE"
else
    echo "${RED}✗ chm_verifier.desktop not found${NC}"
    echo "  Expected: $DESKTOP_FILE"
    echo "  NOTE: File should be in plugin ROOT, not inside chm_verifier/"
fi
echo ""

# Check 4: Rust library
echo "Check 4: Rust Library"
echo "---------------------"
RUST_LIB="$PLUGIN_PATH/lib/chm.so"
if [ -f "$RUST_LIB" ]; then
    echo "${GREEN}✓ Rust library exists${NC}"
    
    # Check if it's a real file or symlink
    if [ -L "$RUST_LIB" ]; then
        echo "  ${YELLOW}⚠ File is a symlink${NC}"
        LINK_TARGET=$(readlink "$RUST_LIB")
        echo "  Links to: $LINK_TARGET"
        if [ -f "$LINK_TARGET" ]; then
            echo "  ${GREEN}✓ Target file exists${NC}"
        else
            echo "  ${RED}✗ Target file missing (broken symlink)${NC}"
        fi
    fi
    
    # Check file size
    FILE_SIZE=$(stat -f%z "$RUST_LIB" 2>/dev/null || stat -c%s "$RUST_LIB" 2>/dev/null)
    echo "  File size: $FILE_SIZE bytes"
    if [ "$FILE_SIZE" -lt 1000 ]; then
        echo "  ${YELLOW}⚠ File seems too small${NC}"
    fi
    
    # Check permissions
    PERMS=$(stat -f%Lp "$RUST_LIB" 2>/dev/null || stat -c%a "$RUST_LIB" 2>/dev/null)
    echo "  Permissions: $PERMS"
    
    # Try to list symbols (macOS)
    if command -v nm &> /dev/null; then
        echo ""
        echo "  Library symbols (first 5):"
        nm -g "$RUST_LIB" 2>&1 | head -5 | sed 's/^/    /'
    fi
else
    echo "${RED}✗ Rust library not found${NC}"
    echo "  Expected: $RUST_LIB"
    echo ""
    echo "  To build and copy:"
    echo "    cd $(dirname $(dirname $PLUGIN_DIR))/krita-certified-human-made"
    echo "    cargo build --release"
    echo "    cp target/release/libchm.dylib \"$RUST_LIB\""
fi
echo ""

# Check 5: Krita configuration
echo "Check 5: Krita Configuration"
echo "-----------------------------"
if [ -f "$KRITA_RC" ]; then
    echo "${GREEN}✓ kritarc exists${NC}"
    
    # Check if plugin is enabled
    if grep -q "chm_verifier" "$KRITA_RC"; then
        echo "${GREEN}✓ chm_verifier found in configuration${NC}"
        echo ""
        echo "  Plugin configuration:"
        grep "chm_verifier" "$KRITA_RC" | sed 's/^/    /'
    else
        echo "${YELLOW}⚠ chm_verifier not found in kritarc${NC}"
        echo "  This is OK if plugin not enabled yet"
    fi
else
    echo "${YELLOW}⚠ kritarc not found${NC}"
    echo "  This is normal if Krita hasn't been run yet"
fi
echo ""

# Check 6: Debug log
echo "Check 6: Plugin Debug Log"
echo "-------------------------"
LOG_FILE="$HOME/.local/share/chm/plugin_debug.log"
if [ -f "$LOG_FILE" ]; then
    echo "${GREEN}✓ Debug log exists${NC}"
    echo "  Location: $LOG_FILE"
    echo ""
    echo "  Last 10 log entries:"
    tail -10 "$LOG_FILE" | sed 's/^/    /'
else
    echo "${YELLOW}⚠ Debug log not found${NC}"
    echo "  Expected: $LOG_FILE"
    echo "  This means the plugin has not loaded yet"
fi
echo ""

# Summary
echo "=========================================="
echo "SUMMARY & NEXT STEPS"
echo "=========================================="
echo ""
echo "To verify plugin is loading:"
echo "  1. Close Krita completely"
echo "  2. Delete old log: rm -f \"$LOG_FILE\""
echo "  3. Open Krita"
echo "  4. Check log: cat \"$LOG_FILE\""
echo ""
echo "Expected log entries:"
echo "  - CHM: __init__.py starting to load"
echo "  - CHM: Plugin registered successfully"
echo "  - CHM: CHMExtension.__init__() called"
echo "  - CHM: setup() METHOD CALLED"
echo ""
echo "If log is empty or missing:"
echo "  - Plugin did not load at all"
echo "  - Check Settings → Configure Krita → Python Plugin Manager"
echo "  - Enable 'Certified Human-Made' and restart Krita"
echo ""



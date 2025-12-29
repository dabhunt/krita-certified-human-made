#!/bin/bash
# Fix CHM Plugin Greyed Out Issue
# This script clears Python cache and verifies installation

echo "🔧 CHM Plugin Fix Script"
echo "======================="
echo ""

# Step 1: Clear Python cache
echo "Step 1: Clearing Python cache..."
CACHE_DIR="$HOME/Library/Application Support/krita/pykrita/chm_verifier/__pycache__"
if [ -d "$CACHE_DIR" ]; then
    rm -rf "$CACHE_DIR"
    echo "✓ Cleared cache: $CACHE_DIR"
else
    echo "ℹ  No cache to clear"
fi

echo ""

# Step 2: Verify symlink
echo "Step 2: Verifying symlink..."
SYMLINK="$HOME/Library/Application Support/krita/pykrita/chm_verifier"
if [ -L "$SYMLINK" ]; then
    TARGET=$(readlink "$SYMLINK")
    echo "✓ Symlink exists"
    echo "  Points to: $TARGET"
    
    if [ -d "$TARGET" ]; then
        echo "✓ Target directory exists"
    else
        echo "✗ ERROR: Target directory does not exist!"
        echo "  You may need to reinstall: ./install-plugin.sh"
        exit 1
    fi
else
    echo "✗ ERROR: Symlink does not exist!"
    echo "  Run: ./install-plugin.sh"
    exit 1
fi

echo ""

# Step 3: Verify .desktop file
echo "Step 3: Verifying .desktop file..."
DESKTOP_FILE="$HOME/Library/Application Support/krita/pykrita/chm_verifier.desktop"
if [ -f "$DESKTOP_FILE" ]; then
    echo "✓ Desktop file exists"
    
    # Check X-KDE-Library value
    LIBRARY=$(grep "X-KDE-Library=" "$DESKTOP_FILE" | cut -d'=' -f2)
    echo "  X-KDE-Library: $LIBRARY"
    
    if [ "$LIBRARY" = "chm_verifier" ]; then
        echo "✓ Library name is correct"
    else
        echo "✗ WARNING: Library name should be 'chm_verifier', found '$LIBRARY'"
    fi
else
    echo "✗ ERROR: Desktop file not found!"
    echo "  Run: cp krita-plugin/chm_verifier.desktop \"$HOME/Library/Application Support/krita/pykrita/\""
    exit 1
fi

echo ""

# Step 4: Verify Rust library
echo "Step 4: Verifying Rust library..."
RUST_LIB="$HOME/Library/Application Support/krita/pykrita/chm_verifier/lib/chm.so"
if [ -f "$RUST_LIB" ]; then
    SIZE=$(ls -lh "$RUST_LIB" | awk '{print $5}')
    echo "✓ Rust library exists (${SIZE})"
    
    # Try to import it
    python3 -c "
import sys
sys.path.insert(0, '$HOME/Library/Application Support/krita/pykrita/chm_verifier/lib')
try:
    import chm
    print('✓ Library imports successfully')
    print('  Version:', chm.get_version())
except Exception as e:
    print('✗ ERROR: Cannot import library')
    print('  Error:', e)
    exit(1)
" || exit 1
else
    echo "✗ ERROR: Rust library not found!"
    echo "  Run: ./build-for-krita.sh"
    exit 1
fi

echo ""

# Step 5: Test Python imports
echo "Step 5: Testing Python module imports..."
python3 << 'EOF'
import sys
sys.path.insert(0, '/Users/david/Library/Application Support/krita/pykrita/chm_verifier')
sys.path.insert(0, '/Users/david/Library/Application Support/krita/pykrita/chm_verifier/lib')

errors = []

# Test chm library
try:
    import chm
    print('✓ chm library imports')
except Exception as e:
    errors.append(f'chm: {e}')
    print(f'✗ chm library: {e}')

# Test chm_session_manager
try:
    import chm_session_manager
    print('✓ chm_session_manager imports')
except Exception as e:
    errors.append(f'chm_session_manager: {e}')
    print(f'✗ chm_session_manager: {e}')

# Test event_capture
try:
    import event_capture
    print('✓ event_capture imports')
except Exception as e:
    errors.append(f'event_capture: {e}')
    print(f'✗ event_capture: {e}')

# Test plugin_monitor
try:
    import plugin_monitor
    print('✓ plugin_monitor imports')
except Exception as e:
    errors.append(f'plugin_monitor: {e}')
    print(f'✗ plugin_monitor: {e}')

# Test verification_dialog
try:
    import verification_dialog
    print('✓ verification_dialog imports')
except Exception as e:
    errors.append(f'verification_dialog: {e}')
    print(f'✗ verification_dialog: {e}')

if errors:
    print('\n⚠️  Some modules have import issues:')
    for error in errors:
        print(f'   - {error}')
    print('\nNote: Some imports may fail outside Krita (e.g., krita module)')
    print('This is normal - test inside Krita Scripter console')

EOF

echo ""

# Step 6: Summary
echo "======================="
echo "✅ Diagnostics Complete"
echo "======================="
echo ""
echo "Next steps:"
echo "1. Quit Krita completely (Cmd+Q)"
echo "2. Restart Krita"
echo "3. Go to Settings → Configure Krita → Python Plugin Manager"
echo "4. Check if 'Certified Human-Made Verifier' is enabled"
echo "5. Open Tools → Scripts → Scripter to see debug output"
echo ""
echo "If plugin is still greyed out, check Scripter console for error messages."
echo ""


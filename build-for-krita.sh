#!/bin/bash
# Build CHM library specifically for Krita's bundled Python
# Handles macOS PyO3 linking issues

set -e

echo "🔧 Building CHM Library for Krita"
echo "=================================="
echo ""

# Step 1: Detect Krita's Python version
KRITA_PYTHON_PATH="/Applications/Krita.app/Contents/Frameworks/Python.framework/Versions/Current"

if [ ! -d "$KRITA_PYTHON_PATH" ]; then
    echo "❌ Krita not found at /Applications/Krita.app"
    echo "   Please install Krita or update KRITA_PYTHON_PATH in this script"
    exit 1
fi

# Get Python version
PYTHON_VERSION=$("$KRITA_PYTHON_PATH/bin/python3" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "📱 Detected Krita's Python: $PYTHON_VERSION"
echo ""

# Step 2: Set PyO3 environment variables for Krita's Python
echo "Step 1: Configuring PyO3 for Krita's Python..."
echo "-----------------------------------------------"

export PYO3_PYTHON="$KRITA_PYTHON_PATH/bin/python3"
export PYTHON_SYS_EXECUTABLE="$KRITA_PYTHON_PATH/bin/python3"

# Get Python config
PYTHON_LDFLAGS=$("$KRITA_PYTHON_PATH/bin/python3-config" --ldflags 2>/dev/null || echo "")

if [ -z "$PYTHON_LDFLAGS" ]; then
    echo "⚠️  python3-config not found, using manual configuration..."
    
    # Manual configuration for Krita's bundled Python
    export RUSTFLAGS="-C link-args=-Wl,-rpath,$KRITA_PYTHON_PATH/lib -C link-args=-L$KRITA_PYTHON_PATH/lib"
else
    echo "✅ Using python3-config from Krita"
fi

echo "   PYO3_PYTHON: $PYO3_PYTHON"
echo ""

# Step 3: Clean previous builds
echo "Step 2: Cleaning previous builds..."
echo "------------------------------------"
cargo clean
echo "✅ Clean complete"
echo ""

# Step 4: Build the library
echo "Step 3: Building Rust library..."
echo "---------------------------------"
echo "   This may take a few minutes on first build..."
echo ""

if cargo build --release; then
    echo ""
    echo "✅ Build successful!"
else
    echo ""
    echo "❌ Build failed!"
    echo ""
    echo "Debugging information:"
    echo "----------------------"
    echo "Python executable: $PYO3_PYTHON"
    echo "Python version: $PYTHON_VERSION"
    echo "RUSTFLAGS: $RUSTFLAGS"
    echo ""
    echo "Common fixes:"
    echo "1. Ensure Krita is installed at /Applications/Krita.app"
    echo "2. Try: conda deactivate (if in conda environment)"
    echo "3. Check docs/phase0-completion-report.md for known issues"
    exit 1
fi

echo ""
echo "Step 4: Copying library to plugin..."
echo "-------------------------------------"

# Create lib directory
mkdir -p krita-plugin/chm_verifier/lib

# Copy the compiled library
cp target/release/libchm.dylib krita-plugin/chm_verifier/lib/chm.so

echo "✅ Library copied to: krita-plugin/chm_verifier/lib/chm.so"
echo ""

# Verify the library
echo "Step 5: Verifying library..."
echo "----------------------------"

if [ -f "krita-plugin/chm_verifier/lib/chm.so" ]; then
    FILE_SIZE=$(ls -lh krita-plugin/chm_verifier/lib/chm.so | awk '{print $5}')
    echo "✅ Library file exists (Size: $FILE_SIZE)"
    
    # Check dependencies
    echo ""
    echo "Library dependencies:"
    otool -L krita-plugin/chm_verifier/lib/chm.so | grep -i python || echo "   (No Python framework dependency - this is OK for cdylib)"
else
    echo "❌ Library file not found!"
    exit 1
fi

echo ""
echo "================================"
echo "✅ Build Complete!"
echo "================================"
echo ""
echo "Next steps:"
echo "1. Run: ./install-plugin.sh (to install to Krita)"
echo "   OR manually symlink:"
echo "   ln -s \"\$(pwd)/krita-plugin/chm_verifier\" \"\$HOME/Library/Application Support/krita/pykrita/chm_verifier\""
echo ""
echo "2. Open Krita → Settings → Python Plugin Manager"
echo "3. Enable 'Certified Human-Made Verifier'"
echo "4. Restart Krita"
echo ""


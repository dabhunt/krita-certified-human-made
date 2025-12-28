#!/bin/bash
# Build CHM library specifically for Krita's bundled Python
# Handles macOS PyO3 linking issues

set -e

echo "🔧 Building CHM Library for Krita"
echo "=================================="
echo ""

# Load Rust environment if not already loaded
if ! command -v cargo &> /dev/null; then
    echo "Loading Rust environment..."
    if [ -f "$HOME/.cargo/env" ]; then
        source "$HOME/.cargo/env"
        echo "✅ Rust environment loaded"
    else
        echo "❌ Rust not found! Please install Rust: https://rustup.rs/"
        exit 1
    fi
    echo ""
fi

# Step 1: Detect Krita's Python version
KRITA_PYTHON_PATH="/Applications/krita.app/Contents/Frameworks/Python.framework/Versions/3.10"

if [ ! -d "$KRITA_PYTHON_PATH" ]; then
    echo "❌ Krita not found at /Applications/krita.app"
    echo "   Please install Krita or update KRITA_PYTHON_PATH in this script"
    exit 1
fi

PYTHON_VERSION="3.10"
echo "📱 Detected Krita's Python: $PYTHON_VERSION"
echo "   Location: $KRITA_PYTHON_PATH"
echo ""

# Step 2: Set PyO3 environment variables for Krita's Python
echo "Step 1: Configuring PyO3 for Krita's Python..."
echo "-----------------------------------------------"

# PyO3 can build without executing Python if we provide these variables
export PYO3_CROSS_LIB_DIR="$KRITA_PYTHON_PATH/lib"
export PYO3_CROSS_PYTHON_VERSION="$PYTHON_VERSION"

# Tell PyO3 we're cross-compiling (even though we're not, this skips Python execution)
export PYO3_CROSS="1"

# macOS Python extension modules use -undefined dynamic_lookup
# This allows the symbols to be resolved at runtime when Python loads the module
# This is the standard way PyO3 extension modules work on macOS
export RUSTFLAGS="-C link-arg=-undefined -C link-arg=dynamic_lookup"

echo "   PYO3_CROSS_LIB_DIR: $PYO3_CROSS_LIB_DIR"
echo "   PYO3_CROSS_PYTHON_VERSION: $PYO3_CROSS_PYTHON_VERSION"
echo "   Using macOS extension module linking (dynamic_lookup)"
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
    echo "Python lib dir: $PYO3_CROSS_LIB_DIR"
    echo "Python version: $PYO3_CROSS_PYTHON_VERSION"
    echo "RUSTFLAGS: $RUSTFLAGS"
    echo ""
    echo "Common fixes:"
    echo "1. Ensure Krita is installed at /Applications/krita.app"
    echo "2. Try: conda deactivate (if in conda environment)"
    echo "3. Check docs/macos-build-guide.md for troubleshooting"
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


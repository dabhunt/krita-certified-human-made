#!/bin/bash
# CHM Verifier Plugin Installation Script
# Builds Rust library and installs plugin to Krita

set -e  # Exit on error

echo "🔧 CHM Verifier Plugin Installer"
echo "================================"
echo ""

# Detect OS
if [[ "$OSTYPE" == "darwin"* ]]; then
    PLUGIN_DIR="$HOME/Library/Application Support/krita/pykrita"
    LIB_EXT="dylib"
    echo "📱 Detected: macOS"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    PLUGIN_DIR="$HOME/.local/share/krita/pykrita"
    LIB_EXT="so"
    echo "🐧 Detected: Linux"
elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
    PLUGIN_DIR="$APPDATA/krita/pykrita"
    LIB_EXT="pyd"
    echo "🪟 Detected: Windows"
else
    echo "❌ Unsupported OS: $OSTYPE"
    exit 1
fi

echo ""

# Step 1: Build Rust library
echo "Step 1: Building Rust library..."
echo "--------------------------------"

# Use specialized build script for macOS (handles PyO3 linking)
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "Using macOS-specific build script (handles Krita's Python)..."
    ./build-for-krita.sh
    
    if [ $? -ne 0 ]; then
        echo "❌ Build failed!"
        exit 1
    fi
    
    echo "✅ Build complete (library already copied to plugin)"
    
else
    # Linux/Windows: standard build
    cargo build --release
    
    if [ $? -ne 0 ]; then
        echo "❌ Cargo build failed!"
        exit 1
    fi
    
    echo "✅ Rust library built successfully"
    echo ""
    
    # Create lib directory
    echo "Step 2: Preparing plugin library directory..."
    mkdir -p krita-plugin/chm_verifier/lib
    
    # Copy compiled library
    echo "Step 3: Copying compiled library..."
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        cp target/release/libchm.so krita-plugin/chm_verifier/lib/chm.so
    else
        cp target/release/chm.pyd krita-plugin/chm_verifier/lib/chm.pyd
    fi
    
    echo "✅ Library copied to plugin directory"
fi

echo ""

# Step 4: Install to Krita
echo "Step 4: Installing plugin to Krita..."
echo "--------------------------------------"

# Create Krita plugin directory if it doesn't exist
mkdir -p "$PLUGIN_DIR"

# Ask user for installation method
echo ""
echo "Choose installation method:"
echo "  1) Symlink (recommended for development - changes auto-update)"
echo "  2) Copy (standalone installation)"
echo ""
read -p "Enter choice (1 or 2): " choice

if [ "$choice" = "1" ]; then
    # Symlink method
    if [ -L "$PLUGIN_DIR/chm_verifier" ]; then
        echo "⚠️  Symlink already exists, removing old one..."
        rm "$PLUGIN_DIR/chm_verifier"
    elif [ -d "$PLUGIN_DIR/chm_verifier" ]; then
        echo "⚠️  Directory already exists, removing old installation..."
        rm -rf "$PLUGIN_DIR/chm_verifier"
    fi
    
    # Get absolute path to avoid issues
    PLUGIN_SOURCE="$(cd "$(pwd)/krita-plugin/chm_verifier" && pwd)"
    
    # Create symlink using absolute path
    ln -s "$PLUGIN_SOURCE" "$PLUGIN_DIR/chm_verifier"
    
    # Copy .desktop file (must be in pykrita root, not inside plugin folder)
    cp krita-plugin/chm_verifier.desktop "$PLUGIN_DIR/chm_verifier.desktop"
    
    echo "✅ Plugin symlinked to: $PLUGIN_DIR/chm_verifier"
    echo "   Source: $PLUGIN_SOURCE"
    echo "   (Changes to plugin files will auto-update)"
else
    # Copy method
    if [ -d "$PLUGIN_DIR/chm_verifier" ]; then
        echo "⚠️  Removing old installation..."
        rm -rf "$PLUGIN_DIR/chm_verifier"
    fi
    
    cp -r krita-plugin/chm_verifier "$PLUGIN_DIR/"
    
    # Copy .desktop file (must be in pykrita root, not inside plugin folder)
    cp krita-plugin/chm_verifier.desktop "$PLUGIN_DIR/chm_verifier.desktop"
    
    echo "✅ Plugin copied to: $PLUGIN_DIR/chm_verifier"
fi

echo ""
echo "================================"
echo "✅ Installation Complete!"
echo "================================"
echo ""
echo "Next steps:"
echo "1. Open Krita"
echo "2. Go to Settings → Configure Krita → Python Plugin Manager"
echo "3. Enable 'Certified Human-Made Verifier'"
echo "4. Click OK and restart Krita"
echo "5. Check Tools → Scripts → Scripter console for debug messages"
echo ""
echo "Look for these messages in Scripter console:"
echo "  - 'CHM Verifier: Setup called'"
echo "  - 'CHM Verifier: Loaded CHM library version X.X.X'"
echo "  - 'CHM Verifier: Event capture started'"
echo ""
echo "📖 For troubleshooting, see: krita-plugin/INSTALLATION.md"
echo ""


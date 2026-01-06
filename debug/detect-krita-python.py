"""
Detect which Python interpreter Krita is using.

Run this script from Krita's Script Editor to determine:
1. Python version
2. Python executable path
3. Site-packages location
4. How to install packages

Instructions:
1. Open Krita
2. Settings -> Dockers -> Python Plugin Manager
3. Open "Scripting" or "Script Editor"
4. Copy/paste this script and run it
"""

import sys
import os
import site

print("=" * 60)
print("KRITA PYTHON ENVIRONMENT DETECTION")
print("=" * 60)
print()

print("Python Version:")
print(f"  {sys.version}")
print()

print("Python Executable:")
print(f"  {sys.executable}")
print()

print("Python Prefix:")
print(f"  {sys.prefix}")
print()

print("Site Packages:")
for path in site.getsitepackages():
    print(f"  {path}")
print()

print("User Site Packages:")
print(f"  {site.getusersitepackages()}")
print()

print("Sys Path (first 10 entries):")
for i, path in enumerate(sys.path[:10]):
    print(f"  {i}: {path}")
print()

print("=" * 60)
print("HOW TO INSTALL C2PA-PYTHON")
print("=" * 60)
print()

# Determine pip command
if sys.executable:
    pip_cmd = f"{sys.executable} -m pip install c2pa-python"
    print(f"Recommended command:")
    print(f"  {pip_cmd}")
else:
    print("  Could not determine pip command automatically")
    print("  Try: python3 -m pip install c2pa-python")

print()
print("If pip is not available, you may need to:")
print("  1. Install pip in this Python environment")
print("  2. Use system Python instead (if Krita allows)")
print("  3. Install packages to user site-packages")
print()

# Check if pip is available
try:
    import pip
    print("✅ pip is available in this environment")
    print(f"   pip version: {pip.__version__}")
except ImportError:
    print("❌ pip is NOT available in this environment")
    print("   You'll need to install pip first")

print()
print("=" * 60)



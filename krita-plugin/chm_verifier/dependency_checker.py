"""
Dependency Checker for CHM Plugin

Verifies that required Python dependencies (PIL, imagehash) are available.
Provides graceful degradation if dependencies are missing.
"""

def check_dependencies():
    """
    Check if PIL and imagehash are available.
    
    Returns:
        dict: {
            'pil_available': bool,
            'imagehash_available': bool,
            'missing': list of str (missing package names),
            'perceptual_hash_enabled': bool
        }
    """
    result = {
        'pil_available': False,
        'imagehash_available': False,
        'missing': [],
        'perceptual_hash_enabled': False
    }
    
    # Check PIL (Pillow)
    try:
        from PIL import Image
        result['pil_available'] = True
        print("[CHM] ✓ PIL (Pillow) available")
    except ImportError as e:
        result['missing'].append('Pillow (PIL)')
        print(f"[CHM] ✗ PIL (Pillow) not available: {e}")
    
    # Check imagehash
    try:
        import imagehash
        result['imagehash_available'] = True
        print("[CHM] ✓ imagehash available")
    except ImportError as e:
        result['missing'].append('imagehash')
        print(f"[CHM] ✗ imagehash not available: {e}")
    
    # Perceptual hash requires both
    result['perceptual_hash_enabled'] = result['pil_available'] and result['imagehash_available']
    
    if result['perceptual_hash_enabled']:
        print("[CHM] ✓ Perceptual hashing ENABLED (both PIL and imagehash available)")
    else:
        print(f"[CHM] ⚠️  Perceptual hashing DISABLED (missing: {', '.join(result['missing'])})")
        print("[CHM]    File hash (SHA-256) will still be computed for duplicate detection")
    
    return result


def show_dependency_warning(missing_packages):
    """
    Show warning dialog if dependencies are missing.
    
    Args:
        missing_packages: list of str - names of missing packages
    """
    try:
        from PyQt5.QtWidgets import QMessageBox
        
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Warning)
        msg.setWindowTitle("CHM - Optional Dependencies Missing")
        msg.setText("Some optional dependencies are not installed.")
        msg.setInformativeText(
            f"Missing packages: {', '.join(missing_packages)}\n\n"
            "Impact:\n"
            "• Perceptual hashing will be disabled\n"
            "• Duplicate detection will use file hash only\n"
            "• Plugin will still work normally\n\n"
            "To enable perceptual hashing:\n"
            "1. See installation guide in plugin README\n"
            "2. Install dependencies to Krita's Python environment"
        )
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec_()
    except Exception as e:
        print(f"[CHM] Could not show dependency warning dialog: {e}")


if __name__ == "__main__":
    # Test dependency checking
    print("Testing CHM dependency checker...")
    result = check_dependencies()
    print(f"\nResult: {result}")
    
    if result['missing']:
        print(f"\nMissing: {result['missing']}")
    else:
        print("\nAll dependencies available!")


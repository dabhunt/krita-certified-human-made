"""
CHM Library Loader

Loads the CHM Python implementation.

For MVP, we use pure Python implementation because:
1. Works on all platforms (no code signing issues)
2. Single codebase to maintain
3. Sufficient performance for typical sessions
4. No native library complexity

Future: Consider Rust optimization if performance becomes an issue.
"""

# Import the Python implementation
from . import chm_core as chm

CHM_AVAILABLE = True
CHM_IMPLEMENTATION = "python"

# Re-export for convenience
__all__ = ['chm', 'CHM_IMPLEMENTATION', 'CHM_AVAILABLE']


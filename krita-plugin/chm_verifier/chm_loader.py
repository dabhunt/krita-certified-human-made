"""
CHM Library Loader

Loads the CHM Python implementation - the primary and only implementation.

Python implementation provides:
1. Cross-platform compatibility (no code signing issues)
2. Single codebase to maintain
3. Easy debugging and modification
4. Sufficient performance for session tracking
5. Direct integration with Krita's Python API
"""

# Import the CHM implementation
from . import chm_core as chm

CHM_AVAILABLE = True
CHM_IMPLEMENTATION = "python"

# Re-export for convenience
__all__ = ['chm', 'CHM_IMPLEMENTATION', 'CHM_AVAILABLE']


"""
Certified Human-Made (CHM) Verifier - Krita Plugin

This plugin captures art creation events to generate cryptographic proofs of human authorship.
"""

try:
    from krita import Krita
    from .chm_extension import CHMExtension
    
    # Register the extension with Krita
    Krita.instance().addExtension(CHMExtension(Krita.instance()))
    print("CHM Verifier: Plugin registered successfully")
    
except Exception as e:
    print(f"CHM Verifier: Failed to load plugin: {e}")
    import traceback
    traceback.print_exc()

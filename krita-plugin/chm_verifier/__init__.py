"""
Certified Human-Made (CHM) Verifier - Krita Plugin

This plugin captures art creation events to generate cryptographic proofs of human authorship.
"""

from krita import Krita
from .chm_extension import CHMExtension

# Krita plugin's metadata
Krita.instance().addExtension(CHMExtension(Krita.instance()))


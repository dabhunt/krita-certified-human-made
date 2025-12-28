"""
Certified Human-Made (CHM) Verifier - Krita Plugin

This plugin captures art creation events to generate cryptographic proofs of human authorship.
"""

from .chm_extension import CHMExtension

# Kritaplugin's metadata
Krita.instance().addExtension(CHMExtension(Krita.instance()))


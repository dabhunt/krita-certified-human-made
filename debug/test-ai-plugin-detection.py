#!/usr/bin/env python3
"""
Test AI Plugin Detection Logic

Tests the two-tier detection system:
1. Registry-based exact matching
2. Keyword-based fallback detection

This script simulates the plugin detection without needing Krita running.
"""

import sys
import os

# Add parent directory to path to import plugin_monitor
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'krita-plugin', 'chm_verifier'))

from plugin_monitor import PluginMonitor

def test_plugin_detection():
    """Test various plugin names to ensure detection works"""
    
    print("=" * 60)
    print("AI PLUGIN DETECTION TEST")
    print("=" * 60)
    
    monitor = PluginMonitor(debug_log=True)
    
    # Test cases: (plugin_name, should_detect, description)
    test_cases = [
        # Known registry entries (should match via Tier 1)
        ("ai_diffusion", True, "AI Diffusion (exact registry match)"),
        ("krita-ai-diffusion", True, "Krita AI Diffusion (exact registry match)"),
        ("auto-sd-paint-ext", True, "Auto SD Paint (exact registry match)"),
        
        # Variants (should match via Tier 2: keywords)
        ("AI-Diffusion", True, "AI Diffusion with capital letters (keyword match)"),
        ("ai-diffusion-plugin", True, "AI Diffusion with suffix (keyword match)"),
        ("krita_ai_diffusion", True, "AI Diffusion with underscores (keyword match)"),
        ("aidiffusion", True, "AI Diffusion no separator (keyword match)"),
        
        # Other AI plugins via keywords
        ("stable-diffusion", True, "Stable Diffusion generic (keyword match)"),
        ("sd-webui", True, "SD WebUI (keyword match)"),
        ("neural-paint", True, "Neural Paint (keyword match)"),
        ("ml-assistant", True, "ML Assistant (keyword match)"),
        ("gan-art-generator", True, "GAN Art Generator (keyword match)"),
        
        # Non-AI plugins (should NOT match)
        ("layer-manager", False, "Layer Manager (not AI)"),
        ("brush-presets", False, "Brush Presets (not AI)"),
        ("color-palette", False, "Color Palette (not AI)"),
        ("animation-helper", False, "Animation Helper (not AI)"),
    ]
    
    print()
    print("Testing plugin detection...")
    print()
    
    passed = 0
    failed = 0
    
    for plugin_name, should_detect, description in test_cases:
        result = monitor.is_ai_plugin(plugin_name)
        
        if result == should_detect:
            status = "✅ PASS"
            passed += 1
        else:
            status = "❌ FAIL"
            failed += 1
        
        detection_str = "DETECTED" if result else "not detected"
        expected_str = "should detect" if should_detect else "should NOT detect"
        
        print(f"{status}: '{plugin_name}' → {detection_str} ({expected_str})")
        print(f"         {description}")
        print()
    
    print("=" * 60)
    print(f"RESULTS: {passed} passed, {failed} failed out of {len(test_cases)} tests")
    print("=" * 60)
    
    if failed == 0:
        print("✅ ALL TESTS PASSED!")
        return 0
    else:
        print(f"❌ {failed} TEST(S) FAILED!")
        return 1

def test_registry_and_keywords():
    """Print out the registry and keywords for verification"""
    
    print()
    print("=" * 60)
    print("REGISTRY & KEYWORDS")
    print("=" * 60)
    
    monitor = PluginMonitor(debug_log=False)
    
    print()
    print(f"Registry entries: {len(monitor.AI_PLUGINS_REGISTRY)}")
    for entry in monitor.AI_PLUGINS_REGISTRY:
        print(f"  - {entry['name']} ({entry['display_name']})")
    
    print()
    print(f"Keyword patterns: {len(monitor.AI_KEYWORDS)}")
    for keyword in monitor.AI_KEYWORDS:
        print(f"  - {keyword}")
    
    print()

if __name__ == "__main__":
    # Show registry and keywords
    test_registry_and_keywords()
    
    # Run detection tests
    exit_code = test_plugin_detection()
    
    sys.exit(exit_code)


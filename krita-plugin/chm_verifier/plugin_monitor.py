"""
Plugin Monitor

Detects installed Krita plugins, particularly AI generation plugins.
Maintains a registry of known AI plugins and scans for them.
"""

import os
import json


class PluginMonitor:
    """Monitors and detects installed Krita plugins"""
    
    # Known AI plugins registry (will be fetched from GitHub in production)
    AI_PLUGINS_REGISTRY = [
        {"name": "krita-ai-diffusion", "type": "AI_GENERATION"},
        {"name": "auto-sd-paint-ext", "type": "AI_GENERATION"},
        {"name": "defuser", "type": "AI_GENERATION"},
        {"name": "stable-diffusion-krita", "type": "AI_GENERATION"},
    ]
    
    def __init__(self, debug_log=True):
        self.DEBUG_LOG = debug_log
        self.detected_plugins = []
        
    def scan_plugins(self, plugin_directories):
        """
        Scan plugin directories for installed plugins
        
        Args:
            plugin_directories: List of paths to scan
            
        Returns:
            List of detected plugin dictionaries
        """
        # TODO: Implement in Task 1.7
        # - Scan directories for .desktop files
        # - Parse plugin metadata
        # - Cross-reference with AI plugins registry
        # - Return list of detected plugins
        
        self.detected_plugins = []
        return self.detected_plugins
    
    def is_ai_plugin(self, plugin_name):
        """Check if a plugin is in the AI registry"""
        for ai_plugin in self.AI_PLUGINS_REGISTRY:
            if ai_plugin["name"].lower() in plugin_name.lower():
                return True
        return False
    
    def get_ai_plugins(self):
        """Get list of detected AI plugins"""
        return [p for p in self.detected_plugins if self.is_ai_plugin(p.get("name", ""))]
    
    def _log(self, message):
        """Debug logging helper"""
        if self.DEBUG_LOG:
            print(f"PluginMonitor: {message}")


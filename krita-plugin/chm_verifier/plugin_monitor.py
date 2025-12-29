"""
Plugin Monitor

Detects installed Krita plugins, particularly AI generation plugins.
Maintains a registry of known AI plugins and scans for them.

Detection Strategy:
1. Scan pykrita directory for .desktop files
2. Parse desktop files for plugin metadata
3. Cross-reference with AI plugins registry
4. Optional: Fetch latest registry from GitHub (future enhancement)
"""

import os
import json
import configparser
from pathlib import Path


class PluginMonitor:
    """Monitors and detects installed Krita plugins"""
    
    # Known AI plugins registry
    # Future: Fetch from GitHub with local cache fallback
    AI_PLUGINS_REGISTRY = [
        {"name": "krita-ai-diffusion", "display_name": "Krita AI Diffusion", "type": "AI_GENERATION"},
        {"name": "auto-sd-paint-ext", "display_name": "Auto SD Paint", "type": "AI_GENERATION"},
        {"name": "defuser", "display_name": "Defuser", "type": "AI_GENERATION"},
        {"name": "stable-diffusion-krita", "display_name": "Stable Diffusion Krita", "type": "AI_GENERATION"},
        {"name": "krita_diff", "display_name": "Krita Diffusion", "type": "AI_GENERATION"},
        {"name": "sd-webui-krita", "display_name": "SD WebUI Krita", "type": "AI_GENERATION"},
        {"name": "ai-paint", "display_name": "AI Paint", "type": "AI_GENERATION"},
        {"name": "ml-paint", "display_name": "ML Paint", "type": "AI_GENERATION"},
    ]
    
    def __init__(self, debug_log=True):
        self.DEBUG_LOG = debug_log
        self.detected_plugins = []
        self._log("Plugin monitor initialized")
        
    def scan_plugins(self, plugin_directories):
        """
        Scan plugin directories for installed plugins
        
        Args:
            plugin_directories: List of paths to scan (pykrita directories)
            
        Returns:
            List of detected plugin dictionaries with:
            - name: Plugin folder/ID name
            - display_name: Human-readable name from .desktop file
            - enabled: Whether plugin is enabled (from .desktop)
            - is_ai: Whether it's an AI plugin (from registry)
            - type: Plugin type if AI (AI_GENERATION, etc.)
        """
        self.detected_plugins = []
        
        if not plugin_directories:
            self._log("No plugin directories provided")
            return self.detected_plugins
        
        self._log(f"Scanning {len(plugin_directories)} directories...")
        
        for plugin_dir in plugin_directories:
            if not os.path.exists(plugin_dir):
                self._log(f"Directory does not exist: {plugin_dir}")
                continue
                
            self._scan_directory(plugin_dir)
        
        ai_count = len(self.get_ai_plugins())
        self._log(f"Scan complete: {len(self.detected_plugins)} plugins detected ({ai_count} AI plugins)")
        
        return self.detected_plugins
    
    def _scan_directory(self, plugin_dir):
        """
        Scan a single directory for plugin .desktop files
        
        Args:
            plugin_dir: Path to pykrita directory
        """
        try:
            # List all entries in the directory
            entries = os.listdir(plugin_dir)
            
            # Find all .desktop files
            desktop_files = [f for f in entries if f.endswith('.desktop')]
            
            self._log(f"Found {len(desktop_files)} .desktop files in {plugin_dir}")
            
            for desktop_file in desktop_files:
                desktop_path = os.path.join(plugin_dir, desktop_file)
                plugin_info = self._parse_desktop_file(desktop_path)
                
                if plugin_info:
                    # Check if it's an AI plugin
                    plugin_info['is_ai'] = self.is_ai_plugin(plugin_info['name'])
                    
                    if plugin_info['is_ai']:
                        # Add AI type from registry
                        for ai_plugin in self.AI_PLUGINS_REGISTRY:
                            if ai_plugin["name"].lower() in plugin_info['name'].lower():
                                plugin_info['ai_type'] = ai_plugin.get('type', 'UNKNOWN')
                                break
                    
                    self.detected_plugins.append(plugin_info)
                    
                    if plugin_info['is_ai']:
                        self._log(f"⚠️  AI Plugin detected: {plugin_info['display_name']} ({plugin_info['name']})")
                    else:
                        self._log(f"Plugin: {plugin_info['display_name']}")
                        
        except Exception as e:
            self._log(f"Error scanning directory {plugin_dir}: {str(e)}")
    
    def _parse_desktop_file(self, desktop_path):
        """
        Parse a .desktop file to extract plugin metadata
        
        Args:
            desktop_path: Path to .desktop file
            
        Returns:
            Dictionary with plugin info or None if parsing fails
        """
        try:
            config = configparser.ConfigParser()
            config.read(desktop_path)
            
            # .desktop files use [Desktop Entry] section
            if 'Desktop Entry' not in config:
                self._log(f"No [Desktop Entry] section in {desktop_path}")
                return None
            
            section = config['Desktop Entry']
            
            # Extract key fields
            name = section.get('Name', 'Unknown')
            x_python_2_compatible = section.get('X-Python-2-Compatible', 'false').lower() == 'true'
            
            # Plugin name is the .desktop filename without extension
            plugin_name = Path(desktop_path).stem
            
            # Check if enabled (some .desktop files have X-KDE-PluginInfo-EnabledByDefault)
            enabled = section.get('X-KDE-PluginInfo-EnabledByDefault', 'true').lower() == 'true'
            
            return {
                'name': plugin_name,
                'display_name': name,
                'enabled': enabled,
                'python2_compatible': x_python_2_compatible,
                'desktop_path': desktop_path
            }
            
        except Exception as e:
            self._log(f"Error parsing {desktop_path}: {str(e)}")
            return None
    
    def is_ai_plugin(self, plugin_name):
        """
        Check if a plugin is in the AI registry
        
        Args:
            plugin_name: Plugin name to check (case-insensitive)
            
        Returns:
            True if plugin is known AI plugin, False otherwise
        """
        plugin_lower = plugin_name.lower()
        for ai_plugin in self.AI_PLUGINS_REGISTRY:
            if ai_plugin["name"].lower() in plugin_lower:
                return True
        return False
    
    def get_ai_plugins(self):
        """
        Get list of detected AI plugins
        
        Returns:
            List of AI plugin dictionaries
        """
        return [p for p in self.detected_plugins if p.get('is_ai', False)]
    
    def get_enabled_ai_plugins(self):
        """
        Get list of detected AI plugins that are enabled
        
        Returns:
            List of enabled AI plugin dictionaries
        """
        return [p for p in self.get_ai_plugins() if p.get('enabled', False)]
    
    def _log(self, message):
        """Debug logging helper"""
        if self.DEBUG_LOG:
            print(f"[PluginMonitor] {message}")


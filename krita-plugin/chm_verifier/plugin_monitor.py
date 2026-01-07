"""
Plugin Monitor

Detects installed Krita plugins, particularly AI generation plugins.
Maintains a registry of known AI plugins and scans for them.

Detection Strategy (Two-Tier Approach):
1. Scan pykrita directory for .desktop files
2. Parse desktop files for plugin metadata
3. Cross-reference with AI plugins registry (Tier 1: Exact match)
4. Fallback to keyword detection (Tier 2: Catches variants/new plugins)
5. Optional: Fetch latest registry from GitHub (future enhancement)

This two-tier approach ensures comprehensive detection:
- Registry provides precise control and metadata
- Keywords catch new plugins, variants (ai_diffusion vs ai-diffusion), and typos
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
        # AI Diffusion (various naming variants)
        {"name": "ai_diffusion", "display_name": "AI Diffusion", "type": "AI_GENERATION"},
        {"name": "krita-ai-diffusion", "display_name": "Krita AI Diffusion", "type": "AI_GENERATION"},
        {"name": "aidiffusion", "display_name": "AI Diffusion", "type": "AI_GENERATION"},
        
        # Other AI plugins
        {"name": "auto-sd-paint-ext", "display_name": "Auto SD Paint", "type": "AI_GENERATION"},
        {"name": "defuser", "display_name": "Defuser", "type": "AI_GENERATION"},
        {"name": "stable-diffusion-krita", "display_name": "Stable Diffusion Krita", "type": "AI_GENERATION"},
        {"name": "krita_diff", "display_name": "Krita Diffusion", "type": "AI_GENERATION"},
        {"name": "sd-webui-krita", "display_name": "SD WebUI Krita", "type": "AI_GENERATION"},
        {"name": "ai-paint", "display_name": "AI Paint", "type": "AI_GENERATION"},
        {"name": "ml-paint", "display_name": "ML Paint", "type": "AI_GENERATION"},
    ]
    
    # Keyword patterns for fallback detection
    # Catches AI plugins not in registry (new plugins, variants, etc.)
    AI_KEYWORDS = [
        # AI/Diffusion patterns
        "ai-diffusion", "ai_diffusion", "aidiffusion",
        "ai-paint", "ai_paint", "ai-generator", "aigenerator",
        
        # Stable Diffusion patterns
        "stablediffusion", "stable-diffusion", "sd-webui", "sd_webui",
        
        # ML/Neural patterns  
        "neural", "ml-", "ml_",  # ml- and ml_ catch ml-paint, ml-assistant, etc.
        
        # Specific AI tools
        "defuser", "gan"
    ]
    
    def __init__(self, debug_log=True):
        self.DEBUG_LOG = debug_log
        self.detected_plugins = []
        self.kritarc_config = None
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
            - enabled: Whether plugin is enabled (from kritarc runtime config)
            - is_ai: Whether it's an AI plugin (from registry)
            - type: Plugin type if AI (AI_GENERATION, etc.)
        """
        self.detected_plugins = []
        
        if not plugin_directories:
            self._log("No plugin directories provided")
            return self.detected_plugins
        
        # CRITICAL: Load kritarc to get actual runtime plugin state
        self._load_kritarc()
        
        self._log(f"Scanning {len(plugin_directories)} directories...")
        
        for plugin_dir in plugin_directories:
            if not os.path.exists(plugin_dir):
                self._log(f"Directory does not exist: {plugin_dir}")
                continue
                
            self._scan_directory(plugin_dir)
        
        ai_count = len(self.get_ai_plugins())
        ai_enabled_count = len(self.get_enabled_ai_plugins())
        self._log(f"Scan complete: {len(self.detected_plugins)} plugins detected ({ai_count} AI plugins, {ai_enabled_count} enabled)")
        
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
                        # Add AI type from registry (if exact match found)
                        ai_type_found = False
                        for ai_plugin in self.AI_PLUGINS_REGISTRY:
                            if ai_plugin["name"].lower() in plugin_info['name'].lower():
                                plugin_info['ai_type'] = ai_plugin.get('type', 'UNKNOWN')
                                ai_type_found = True
                                break
                        
                        # If detected via keyword but not in registry, use default type
                        if not ai_type_found:
                            plugin_info['ai_type'] = 'AI_GENERATION'
                    
                    self.detected_plugins.append(plugin_info)
                    
                    if plugin_info['is_ai']:
                        self._log(f"⚠️  AI Plugin detected: {plugin_info['display_name']} ({plugin_info['name']})")
                    else:
                        self._log(f"Plugin: {plugin_info['display_name']}")
                        
        except Exception as e:
            self._log(f"Error scanning directory {plugin_dir}: {str(e)}")
    
    def _load_kritarc(self):
        """
        Load kritarc configuration file to get actual runtime plugin state.
        This is CRITICAL because users can enable/disable plugins in Krita UI,
        and that state is stored in kritarc, NOT in .desktop files.
        """
        import platform
        
        # Find kritarc based on platform
        kritarc_path = None
        system = platform.system()
        
        if system == 'Darwin':  # macOS
            kritarc_path = os.path.expanduser("~/Library/Preferences/kritarc")
        elif system == 'Linux':
            kritarc_path = os.path.expanduser("~/.config/kritarc")
        elif system == 'Windows':
            appdata = os.environ.get('APPDATA', '')
            if appdata:
                kritarc_path = os.path.join(appdata, 'krita', 'kritarc')
        
        if not kritarc_path or not os.path.exists(kritarc_path):
            self._log(f"[KRITARC] ⚠️  kritarc not found at {kritarc_path}, will use .desktop defaults")
            return
        
        try:
            self.kritarc_config = configparser.ConfigParser()
            self.kritarc_config.read(kritarc_path)
            
            if self.DEBUG_LOG:
                self._log(f"[KRITARC] ✓ Loaded kritarc from {kritarc_path}")
                # Log all python plugin states for debugging
                if 'python' in self.kritarc_config:
                    python_section = self.kritarc_config['python']
                    for key in python_section:
                        if key.startswith('enable_'):
                            plugin_name = key[7:]  # Remove 'enable_' prefix
                            enabled = python_section[key].lower() == 'true'
                            self._log(f"[KRITARC]   - {plugin_name}: {'ENABLED' if enabled else 'DISABLED'}")
        except Exception as e:
            self._log(f"[KRITARC] ⚠️  Error loading kritarc: {e}")
            self.kritarc_config = None
    
    def _get_runtime_enabled_state(self, plugin_name):
        """
        Get the actual runtime enabled state for a plugin from kritarc.
        Falls back to .desktop file default if not found in kritarc.
        
        Args:
            plugin_name: Plugin name (from .desktop filename)
            
        Returns:
            True if enabled, False if disabled
        """
        if not self.kritarc_config or 'python' not in self.kritarc_config:
            # No kritarc, return default (enabled)
            return True
        
        # Check for enable_<plugin_name> in [python] section
        enable_key = f"enable_{plugin_name}"
        python_section = self.kritarc_config['python']
        
        if enable_key in python_section:
            enabled = python_section[enable_key].lower() == 'true'
            if self.DEBUG_LOG:
                self._log(f"[RUNTIME-STATE] {plugin_name}: {enable_key}={'true' if enabled else 'false'} → {'ENABLED' if enabled else 'DISABLED'}")
            return enabled
        
        # Not in kritarc, return default (enabled)
        if self.DEBUG_LOG:
            self._log(f"[RUNTIME-STATE] {plugin_name}: not in kritarc, using default (enabled)")
        return True
    
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
            
            # CRITICAL: Get ACTUAL runtime state from kritarc, not .desktop default
            # Users can disable plugins in Krita UI, which updates kritarc
            enabled = self._get_runtime_enabled_state(plugin_name)
            
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
        Check if a plugin is an AI plugin using two-tier detection:
        1. Exact registry match (precise, curated list)
        2. Keyword fallback (catches variants and new plugins)
        
        Args:
            plugin_name: Plugin name to check (case-insensitive)
            
        Returns:
            True if plugin is known AI plugin, False otherwise
        """
        plugin_lower = plugin_name.lower()
        
        # Tier 1: Check exact registry match
        for ai_plugin in self.AI_PLUGINS_REGISTRY:
            if ai_plugin["name"].lower() in plugin_lower:
                if self.DEBUG_LOG:
                    self._log(f"[AI-DETECT] ✓ Registry match: {plugin_name} → {ai_plugin['name']}")
                return True
        
        # Tier 2: Keyword fallback for variants/new plugins
        for keyword in self.AI_KEYWORDS:
            if keyword in plugin_lower:
                if self.DEBUG_LOG:
                    self._log(f"[AI-DETECT] ✓ Keyword match: {plugin_name} → '{keyword}'")
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


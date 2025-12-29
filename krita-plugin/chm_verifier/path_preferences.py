"""
Path Preferences Manager

Manages user preferences for file save locations, including:
- Last used save directory (persistent across sessions)
- Default save directory (Documents folder)

Uses QSettings for cross-platform persistent storage.
"""

import os
from PyQt5.QtCore import QSettings, QStandardPaths


class PathPreferences:
    """Manages file path preferences with persistent storage"""
    
    def __init__(self):
        """Initialize path preferences with QSettings"""
        # Use QSettings for cross-platform persistent storage
        # Organization: "CHM", Application: "KritaPlugin"
        self.settings = QSettings("CHM", "KritaPlugin")
        
        # Get platform-specific Documents directory
        self.default_documents_path = self._get_documents_path()
    
    def _get_documents_path(self):
        """
        Get platform-specific Documents directory.
        
        Returns:
            str: Path to Documents folder
        """
        # QStandardPaths provides platform-appropriate paths
        documents_locations = QStandardPaths.standardLocations(
            QStandardPaths.DocumentsLocation
        )
        
        if documents_locations:
            return documents_locations[0]
        else:
            # Fallback to home directory if Documents not found
            return os.path.expanduser("~")
    
    def get_last_export_directory(self):
        """
        Get the last used export directory.
        Falls back to Documents if no previous location exists.
        
        Returns:
            str: Directory path for file save dialog
        """
        last_dir = self.settings.value("export/last_directory", "")
        
        # Validate that the directory still exists
        if last_dir and os.path.isdir(last_dir):
            return last_dir
        else:
            # Fall back to Documents
            return self.default_documents_path
    
    def save_last_export_directory(self, filepath):
        """
        Save the directory from a file path as the last used location.
        
        Args:
            filepath (str): Full path to a file that was saved
        """
        if not filepath:
            return
        
        # Extract directory from full file path
        directory = os.path.dirname(filepath)
        
        # Save to persistent storage
        self.settings.setValue("export/last_directory", directory)
        self.settings.sync()  # Force write to disk
    
    def get_last_proof_directory(self):
        """
        Get the last used proof JSON save directory.
        Falls back to Documents if no previous location exists.
        
        Returns:
            str: Directory path for proof JSON save dialog
        """
        last_dir = self.settings.value("proof/last_directory", "")
        
        # Validate that the directory still exists
        if last_dir and os.path.isdir(last_dir):
            return last_dir
        else:
            # Fall back to Documents
            return self.default_documents_path
    
    def save_last_proof_directory(self, filepath):
        """
        Save the directory from a proof JSON path as the last used location.
        
        Args:
            filepath (str): Full path to a proof JSON file that was saved
        """
        if not filepath:
            return
        
        # Extract directory from full file path
        directory = os.path.dirname(filepath)
        
        # Save to persistent storage
        self.settings.setValue("proof/last_directory", directory)
        self.settings.sync()  # Force write to disk
    
    def get_default_export_filename(self, doc_name=None):
        """
        Generate a default filename for export based on document name.
        
        Args:
            doc_name (str, optional): Krita document name
            
        Returns:
            str: Full path with filename for the save dialog
        """
        directory = self.get_last_export_directory()
        
        # Generate filename from document name or default
        if doc_name:
            # Replace .kra extension with .png
            filename = doc_name.replace(".kra", ".png")
        else:
            filename = "artwork.png"
        
        return os.path.join(directory, filename)
    
    def get_default_proof_filename(self, base_filename=None):
        """
        Generate a default filename for proof JSON export.
        
        Args:
            base_filename (str, optional): Base filename to derive proof name from
            
        Returns:
            str: Full path with filename for the save dialog
        """
        directory = self.get_last_proof_directory()
        
        if base_filename:
            # Extract just the filename without directory
            filename = os.path.basename(base_filename)
            # Generate proof filename
            proof_filename = filename.replace('.png', '_proof.json') \
                                    .replace('.jpg', '_proof.json') \
                                    .replace('.jpeg', '_proof.json')
        else:
            proof_filename = "proof.json"
        
        return os.path.join(directory, proof_filename)
    
    def reset_preferences(self):
        """Reset all path preferences to defaults"""
        self.settings.remove("export/last_directory")
        self.settings.remove("proof/last_directory")
        self.settings.sync()


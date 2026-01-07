"""
Export Confirmation Dialog

PyQt5 dialog for showing export success with structured information.
Similar structure to VerificationDialog for consistency.
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QPushButton, QTextEdit,
    QHBoxLayout, QGroupBox, QFormLayout, QApplication
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QDesktopServices, QCursor
from PyQt5.QtCore import QUrl


class ExportConfirmationDialog(QDialog):
    """Dialog for showing export success and status"""
    
    def __init__(self, export_data=None, parent=None):
        """
        Create export confirmation dialog.
        
        Args:
            export_data: Dictionary containing export information
            parent: Parent widget (optional)
        """
        super().__init__(parent)
        
        self.export_data = export_data or {}
        
        self.setWindowTitle("CHM Export Successful")
        self.setMinimumSize(650, 600)
        self.setup_ui()
        
        if self.export_data:
            self.display_export_info(self.export_data)
    
    def setup_ui(self):
        """Setup the UI components"""
        layout = QVBoxLayout()
        
        # Title
        title = QLabel("✅ Image Exported with CHM Proof!")
        title.setStyleSheet("font-size: 16pt; font-weight: bold; margin: 10px; color: green;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Files group
        files_group = QGroupBox("Exported Files")
        files_layout = QFormLayout()
        
        self.image_path_label = QLabel("N/A")
        self.image_path_label.setWordWrap(True)
        self.proof_path_label = QLabel("N/A")
        self.proof_path_label.setWordWrap(True)
        
        files_layout.addRow("Image:", self.image_path_label)
        files_layout.addRow("Proof:", self.proof_path_label)
        files_group.setLayout(files_layout)
        layout.addWidget(files_group)
        
        # Classification group
        class_group = QGroupBox("Classification")
        class_layout = QFormLayout()
        
        self.classification_label = QLabel("Loading...")
        self.strokes_label = QLabel("N/A")
        self.duration_label = QLabel("N/A")
        self.drawing_time_label = QLabel("N/A")
        
        class_layout.addRow("Classification:", self.classification_label)
        class_layout.addRow("Brush Strokes:", self.strokes_label)
        class_layout.addRow("Session Duration:", self.duration_label)
        class_layout.addRow("Drawing Time:", self.drawing_time_label)
        class_group.setLayout(class_layout)
        layout.addWidget(class_group)
        
        # Verification status group
        verify_group = QGroupBox("Verification & Timestamps")
        verify_layout = QFormLayout()
        
        self.timestamp_label = QLabel("N/A")
        self.timestamp_label.setWordWrap(True)
        self.c2pa_label = QLabel("N/A")
        self.c2pa_label.setWordWrap(True)
        
        verify_layout.addRow("Timestamps:", self.timestamp_label)
        verify_layout.addRow("C2PA:", self.c2pa_label)
        verify_group.setLayout(verify_layout)
        layout.addWidget(verify_group)
        
        # Public verification links (if available)
        self.verification_link_group = QGroupBox("Public Verification")
        verification_link_layout = QVBoxLayout()
        
        # CHM Website Verification Button (primary)
        self.view_proof_btn = QPushButton("✅ View Proof on certified-human-made.org")
        self.view_proof_btn.setStyleSheet("""
            QPushButton {
                background-color: #55BF6E;
                color: white;
                font-weight: bold;
                padding: 12px;
                border-radius: 6px;
                font-size: 12pt;
            }
            QPushButton:hover {
                background-color: #4AAF62;
            }
        """)
        self.view_proof_btn.clicked.connect(self.open_proof_website)
        self.view_proof_btn.hide()  # Hidden by default
        verification_link_layout.addWidget(self.view_proof_btn)
        
        # GitHub Gist Link (secondary, for technical users)
        gist_link_label = QLabel("Technical proof data:")
        gist_link_label.setStyleSheet("color: gray; font-size: 9pt; margin-top: 8px;")
        verification_link_layout.addWidget(gist_link_label)
        
        self.timestamp_url_label = QLabel("")
        self.timestamp_url_label.setWordWrap(True)
        self.timestamp_url_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.timestamp_url_label.setCursor(QCursor(Qt.PointingHandCursor))
        self.timestamp_url_label.linkActivated.connect(self.open_url)
        self.timestamp_url_label.setStyleSheet("font-size: 9pt;")
        
        verification_link_layout.addWidget(self.timestamp_url_label)
        self.verification_link_group.setLayout(verification_link_layout)
        self.verification_link_group.hide()  # Hidden by default, shown if URL available
        layout.addWidget(self.verification_link_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.open_folder_btn = QPushButton("Open Folder")
        self.open_folder_btn.clicked.connect(self.open_export_folder)
        
        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.close)
        
        button_layout.addWidget(self.open_folder_btn)
        button_layout.addStretch()
        button_layout.addWidget(self.close_btn)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def display_export_info(self, export_data):
        """Display export information in the dialog"""
        
        # File paths
        image_path = export_data.get("image_path", "N/A")
        proof_path = export_data.get("proof_path", "N/A")
        
        self.image_path_label.setText(image_path)
        self.proof_path_label.setText(proof_path)
        
        # Classification
        proof_data = export_data.get("proof_data", {})
        classification = proof_data.get("classification", "Unknown")
        
        # Format classification display name
        classification_display = classification
        if classification == "HumanMade":
            classification_display = "100% Human Made"
        elif classification == "MixedMedia":
            classification_display = "Mixed Media"
        
        self.classification_label.setText(classification_display)
        
        # Style classification based on type
        if classification == "HumanMade":
            self.classification_label.setStyleSheet("color: green; font-weight: bold;")
        elif classification == "AI-Assisted":
            self.classification_label.setStyleSheet("color: orange; font-weight: bold;")
        elif classification == "MixedMedia":
            self.classification_label.setStyleSheet("color: blue; font-weight: bold;")
        
        # Event summary
        event_summary = proof_data.get("event_summary", {})
        stroke_count = event_summary.get("stroke_count", 0)
        session_duration = event_summary.get("session_duration_secs", 0)
        drawing_time = event_summary.get("drawing_time_secs", 0)
        
        self.strokes_label.setText(str(stroke_count))
        self.duration_label.setText(
            f"{session_duration}s ({session_duration // 60}m {session_duration % 60}s)"
        )
        self.drawing_time_label.setText(
            f"{drawing_time}s ({drawing_time // 60}m {drawing_time % 60}s)"
        )
        
        # Verification status
        timestamp_status = export_data.get("timestamp_status", "Not timestamped")
        c2pa_status = export_data.get("c2pa_status", "Not embedded")
        
        # Style status labels based on success/failure
        self.timestamp_label.setText(timestamp_status)
        if timestamp_status.startswith("✓"):
            self.timestamp_label.setStyleSheet("color: green;")
        elif timestamp_status.startswith("⚠️"):
            self.timestamp_label.setStyleSheet("color: orange;")
        
        self.c2pa_label.setText(c2pa_status)
        if c2pa_status.startswith("✓"):
            self.c2pa_label.setStyleSheet("color: green;")
        elif c2pa_status.startswith("⚠️"):
            self.c2pa_label.setStyleSheet("color: orange;")
        
        # Public timestamp URL (if available)
        timestamp_url = export_data.get("timestamp_url", None)
        if timestamp_url:
            # Extract gist ID from GitHub URL for our verification website
            gist_id = self._extract_gist_id(timestamp_url)
            if gist_id:
                self.proof_website_url = f"https://certified-human-made.org/proof/{gist_id}"
                self.view_proof_btn.show()
            
            # Show GitHub gist link as secondary option
            self.timestamp_url_label.setText(
                f'<a href="{timestamp_url}">View on GitHub</a>'
            )
            self.verification_link_group.show()
    
    def open_export_folder(self):
        """Open the folder containing the exported files"""
        import os
        
        image_path = self.export_data.get("image_path", "")
        if image_path and os.path.exists(image_path):
            folder_path = os.path.dirname(image_path)
            QDesktopServices.openUrl(QUrl.fromLocalFile(folder_path))
    
    def open_url(self, url):
        """Open URL in default browser"""
        QDesktopServices.openUrl(QUrl(url))
    
    def open_proof_website(self):
        """Open the CHM proof verification website"""
        if hasattr(self, 'proof_website_url'):
            QDesktopServices.openUrl(QUrl(self.proof_website_url))
    
    def _extract_gist_id(self, gist_url):
        """
        Extract gist ID from GitHub gist URL.
        
        Args:
            gist_url: Full GitHub gist URL (e.g., https://gist.github.com/username/abc123)
            
        Returns:
            Gist ID string or None if extraction fails
        """
        if not gist_url:
            return None
        
        # GitHub gist URLs have format: https://gist.github.com/{username}/{gist_id}
        # or sometimes: https://gist.github.com/{gist_id}
        try:
            parts = gist_url.rstrip('/').split('/')
            # The gist ID is always the last part of the URL
            gist_id = parts[-1]
            
            # Validate it looks like a gist ID (alphanumeric)
            if gist_id and gist_id.replace('_', '').replace('-', '').isalnum():
                return gist_id
        except Exception:
            pass
        
        return None


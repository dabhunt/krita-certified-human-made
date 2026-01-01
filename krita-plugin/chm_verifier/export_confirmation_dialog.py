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
        self.database_label = QLabel("N/A")
        self.database_label.setWordWrap(True)
        self.c2pa_label = QLabel("N/A")
        self.c2pa_label.setWordWrap(True)
        
        verify_layout.addRow("Timestamps:", self.timestamp_label)
        verify_layout.addRow("Database:", self.database_label)
        verify_layout.addRow("C2PA:", self.c2pa_label)
        verify_group.setLayout(verify_layout)
        layout.addWidget(verify_group)
        
        # Public timestamp link (if available)
        self.timestamp_link_group = QGroupBox("Public Timestamp Proof")
        timestamp_link_layout = QVBoxLayout()
        
        self.timestamp_url_label = QLabel("")
        self.timestamp_url_label.setWordWrap(True)
        self.timestamp_url_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.timestamp_url_label.setCursor(QCursor(Qt.PointingHandCursor))
        self.timestamp_url_label.linkActivated.connect(self.open_url)
        
        timestamp_link_layout.addWidget(self.timestamp_url_label)
        self.timestamp_link_group.setLayout(timestamp_link_layout)
        self.timestamp_link_group.hide()  # Hidden by default, shown if URL available
        layout.addWidget(self.timestamp_link_group)
        
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
        elif classification == "Traced":
            self.classification_label.setStyleSheet("color: red; font-weight: bold;")
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
        database_status = export_data.get("database_status", "Not submitted")
        c2pa_status = export_data.get("c2pa_status", "Not embedded")
        
        # Style status labels based on success/failure
        self.timestamp_label.setText(timestamp_status)
        if timestamp_status.startswith("✓"):
            self.timestamp_label.setStyleSheet("color: green;")
        elif timestamp_status.startswith("⚠️"):
            self.timestamp_label.setStyleSheet("color: orange;")
        
        self.database_label.setText(database_status)
        if database_status.startswith("✓"):
            self.database_label.setStyleSheet("color: green;")
        elif database_status.startswith("⚠️"):
            self.database_label.setStyleSheet("color: orange;")
        
        self.c2pa_label.setText(c2pa_status)
        if c2pa_status.startswith("✓"):
            self.c2pa_label.setStyleSheet("color: green;")
        elif c2pa_status.startswith("⚠️"):
            self.c2pa_label.setStyleSheet("color: orange;")
        
        # Public timestamp URL (if available)
        timestamp_url = export_data.get("timestamp_url", None)
        if timestamp_url:
            self.timestamp_url_label.setText(
                f'<a href="{timestamp_url}">{timestamp_url}</a>'
            )
            self.timestamp_link_group.show()
    
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


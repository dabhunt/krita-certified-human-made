"""
Verification Dialog

PyQt5 dialog for viewing session proof data and exporting certificates.
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QPushButton, QTextEdit,
    QHBoxLayout, QGroupBox, QFormLayout
)
from PyQt5.QtCore import Qt
import json


class VerificationDialog(QDialog):
    """Dialog for viewing and exporting CHM proofs"""
    
    def __init__(self, proof_data=None, parent=None):
        super().__init__(parent)
        self.proof_data = proof_data
        self.setWindowTitle("CHM Verification Proof")
        self.setMinimumSize(600, 500)
        self.setup_ui()
        
        if proof_data:
            self.display_proof(proof_data)
    
    def setup_ui(self):
        """Setup the UI components"""
        layout = QVBoxLayout()
        
        # Title
        title = QLabel("Certified Human-Made Verification Proof")
        title.setStyleSheet("font-size: 16pt; font-weight: bold; margin: 10px;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Classification group
        class_group = QGroupBox("Classification")
        class_layout = QFormLayout()
        
        self.class_label = QLabel("Loading...")
        self.confidence_label = QLabel("Loading...")
        
        class_layout.addRow("Classification:", self.class_label)
        class_layout.addRow("Confidence:", self.confidence_label)
        class_group.setLayout(class_layout)
        layout.addWidget(class_group)
        
        # Session info group
        session_group = QGroupBox("Session Information")
        session_layout = QFormLayout()
        
        self.session_id_label = QLabel("N/A")
        self.duration_label = QLabel("N/A")
        self.events_label = QLabel("N/A")
        self.strokes_label = QLabel("N/A")
        
        session_layout.addRow("Session ID:", self.session_id_label)
        session_layout.addRow("Duration:", self.duration_label)
        session_layout.addRow("Total Events:", self.events_label)
        session_layout.addRow("Brush Strokes:", self.strokes_label)
        session_group.setLayout(session_layout)
        layout.addWidget(session_group)
        
        # Full proof JSON viewer
        proof_group = QGroupBox("Full Proof Data (JSON)")
        proof_layout = QVBoxLayout()
        
        self.proof_text = QTextEdit()
        self.proof_text.setReadOnly(True)
        self.proof_text.setFontFamily("Courier")
        proof_layout.addWidget(self.proof_text)
        proof_group.setLayout(proof_layout)
        layout.addWidget(proof_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.copy_btn = QPushButton("Copy to Clipboard")
        self.copy_btn.clicked.connect(self.copy_to_clipboard)
        
        self.save_btn = QPushButton("Save JSON")
        self.save_btn.clicked.connect(self.save_json)
        
        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.close)
        
        button_layout.addWidget(self.copy_btn)
        button_layout.addWidget(self.save_btn)
        button_layout.addStretch()
        button_layout.addWidget(self.close_btn)
        layout.addLayout(button_layout)
        
        # Privacy notice
        notice = QLabel("Your artwork data stays 100% local. Only an encrypted hash is timestamped.")
        notice.setStyleSheet("color: gray; font-size: 9pt; margin: 5px;")
        notice.setWordWrap(True)
        layout.addWidget(notice)
        
        self.setLayout(layout)
    
    def display_proof(self, proof_data):
        """Display proof data in the dialog"""
        # Classification
        classification = proof_data.get("classification", "Unknown")
        confidence = proof_data.get("confidence", 0.0)
        
        self.class_label.setText(classification)
        self.confidence_label.setText(f"{confidence * 100:.1f}%")
        
        # Session info
        self.session_id_label.setText(proof_data.get("session_id", "N/A")[:16] + "...")
        
        event_summary = proof_data.get("event_summary", {})
        duration = event_summary.get("session_duration_secs", 0)
        self.duration_label.setText(f"{duration} seconds ({duration // 60}m {duration % 60}s)")
        self.events_label.setText(str(event_summary.get("total_events", 0)))
        self.strokes_label.setText(str(event_summary.get("stroke_count", 0)))
        
        # Full JSON
        json_str = json.dumps(proof_data, indent=2)
        self.proof_text.setPlainText(json_str)
    
    def copy_to_clipboard(self):
        """Copy proof JSON to clipboard"""
        from PyQt5.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        clipboard.setText(self.proof_text.toPlainText())
        
        # TODO: Show success message
    
    def save_json(self):
        """Save proof JSON to file"""
        from PyQt5.QtWidgets import QFileDialog
        
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Save Proof JSON",
            "",
            "JSON Files (*.json)"
        )
        
        if filename:
            with open(filename, 'w') as f:
                f.write(self.proof_text.toPlainText())
            # TODO: Show success message


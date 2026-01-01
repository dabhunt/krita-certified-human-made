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
from .path_preferences import PathPreferences


class VerificationDialog(QDialog):
    """Dialog for viewing and exporting CHM proofs"""
    
    def __init__(self, proof_data=None, parent=None):
        super().__init__(parent)
        
        # Initialize path preferences
        self.path_prefs = PathPreferences()
        
        # Handle both CHMProof objects and dictionaries
        if proof_data:
            if hasattr(proof_data, 'to_dict'):
                # CHMProof object
                self.proof_data = proof_data.to_dict()
                print(f"[FLOW-5a] 📦 Received CHMProof object, extracted dict with {len(self.proof_data)} keys")
            elif isinstance(proof_data, dict):
                # Direct dictionary
                self.proof_data = proof_data
                print(f"[FLOW-5a] 📦 Received proof dict with {len(self.proof_data)} keys")
            else:
                self.proof_data = None
                print(f"[FLOW-ERROR] ❌ Unknown proof type: {type(proof_data)}")
        else:
            self.proof_data = None
        
        import sys
        sys.stdout.flush()
        
        self.setWindowTitle("CHM Verification Proof")
        self.setMinimumSize(600, 500)
        self.setup_ui()
        
        if self.proof_data:
            self.display_proof(self.proof_data)
    
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
        
        class_layout.addRow("Classification:", self.class_label)
        class_group.setLayout(class_layout)
        layout.addWidget(class_group)
        
        # Session info group
        session_group = QGroupBox("Session Information")
        session_layout = QFormLayout()
        
        self.session_id_label = QLabel("N/A")
        self.duration_label = QLabel("N/A")
        self.events_label = QLabel("N/A")
        self.strokes_label = QLabel("N/A")
        self.imports_label = QLabel("N/A")
        self.tracing_label = QLabel("N/A")
        
        session_layout.addRow("Session ID:", self.session_id_label)
        session_layout.addRow("Duration:", self.duration_label)
        session_layout.addRow("Total Events:", self.events_label)
        session_layout.addRow("Brush Strokes:", self.strokes_label)
        session_layout.addRow("Imported Images:", self.imports_label)
        session_layout.addRow("Tracing %:", self.tracing_label)
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
        import sys
        print(f"[FLOW-5] 📊 Displaying proof in dialog")
        print(f"[FLOW-5] Proof data keys: {list(proof_data.keys())}")
        sys.stdout.flush()
        
        # Classification
        classification = proof_data.get("classification", "Unknown")
        
        print(f"[FLOW-6] Classification: {classification}")
        sys.stdout.flush()
        
        # Format classification display name
        classification_display = classification
        if classification == "HumanMade":
            classification_display = "100% Human Made"
        elif classification == "MixedMedia":
            classification_display = "Mixed Media"
        
        self.class_label.setText(classification_display)
        
        # Session info
        session_id = proof_data.get("session_id", "N/A")
        print(f"[FLOW-6] Session ID: {session_id}")
        sys.stdout.flush()
        
        self.session_id_label.setText(session_id[:16] + "..." if len(session_id) > 16 else session_id)
        
        event_summary = proof_data.get("event_summary", {})
        duration = event_summary.get("session_duration_secs", 0)
        total_events = event_summary.get("total_events", 0)
        stroke_count = event_summary.get("stroke_count", 0)
        import_count = proof_data.get("import_count", 0)
        tracing_percentage = proof_data.get("tracing_percentage", 0.0)
        
        print(f"[FLOW-6] Events: {total_events}, Strokes: {stroke_count}, Duration: {duration}s, Imports: {import_count}")
        sys.stdout.flush()
        
        self.duration_label.setText(f"{duration} seconds ({duration // 60}m {duration % 60}s)")
        self.events_label.setText(str(total_events))
        self.strokes_label.setText(str(stroke_count))
        self.imports_label.setText(f"{import_count} images")
        
        # Show tracing percentage (0% if not traced)
        if tracing_percentage > 0:
            self.tracing_label.setText(f"{tracing_percentage*100:.1f}%")
            self.tracing_label.setStyleSheet("color: red; font-weight: bold;")
        else:
            self.tracing_label.setText("0% (not traced)")
            self.tracing_label.setStyleSheet("color: green;")
        
        # Full JSON
        json_str = json.dumps(proof_data, indent=2)
        print(f"[FLOW-7] ✓ JSON exported ({len(json_str)} bytes)")
        sys.stdout.flush()
        
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
        import os
        
        # Get default path from preferences (Documents folder or last used location)
        default_path = self.path_prefs.get_default_proof_filename()
        
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Save Proof JSON",
            default_path,
            "JSON Files (*.json)"
        )
        
        if filename:
            with open(filename, 'w') as f:
                f.write(self.proof_text.toPlainText())
            
            # Remember this directory for next time
            self.path_prefs.save_last_proof_directory(filename)
            
            # TODO: Show success message


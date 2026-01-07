"""
Session Info Dialog

PyQt5 dialog for viewing active session data without finalizing.
Similar structure to VerificationDialog for consistency.
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QPushButton, QTextEdit,
    QHBoxLayout, QGroupBox, QFormLayout
)
from PyQt5.QtCore import Qt
import json


class SessionInfoDialog(QDialog):
    """Dialog for viewing active session info (non-finalized)"""
    
    def __init__(self, session_data=None, parent=None):
        """
        Create session info dialog.
        
        Args:
            session_data: Dictionary containing session information
            parent: Parent widget (optional)
        """
        super().__init__(parent)
        
        self.session_data = session_data or {}
        
        self.setWindowTitle("CHM Active Session")
        self.setMinimumSize(600, 500)
        self.setup_ui()
        
        if self.session_data:
            self.display_session(self.session_data)
    
    def setup_ui(self):
        """Setup the UI components"""
        layout = QVBoxLayout()
        
        # Title
        title = QLabel("📊 Current Session Status")
        title.setStyleSheet("font-size: 16pt; font-weight: bold; margin: 10px;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Document info group
        doc_group = QGroupBox("Document Information")
        doc_layout = QFormLayout()
        
        self.doc_name_label = QLabel("N/A")
        self.canvas_size_label = QLabel("N/A")
        self.session_id_label = QLabel("N/A")
        
        doc_layout.addRow("Document:", self.doc_name_label)
        doc_layout.addRow("Canvas Size:", self.canvas_size_label)
        doc_layout.addRow("Session ID:", self.session_id_label)
        doc_group.setLayout(doc_layout)
        layout.addWidget(doc_group)
        
        # Time metrics group
        time_group = QGroupBox("Time Metrics")
        time_layout = QFormLayout()
        
        self.session_duration_label = QLabel("N/A")
        self.drawing_time_label = QLabel("N/A")
        
        time_layout.addRow("Session Duration:", self.session_duration_label)
        time_layout.addRow("Drawing Time:", self.drawing_time_label)
        time_group.setLayout(time_layout)
        layout.addWidget(time_group)
        
        # Activity group
        activity_group = QGroupBox("Activity")
        activity_layout = QFormLayout()
        
        self.total_events_label = QLabel("N/A")
        self.strokes_label = QLabel("N/A")
        self.layers_label = QLabel("N/A")
        self.imports_label = QLabel("N/A")
        
        activity_layout.addRow("Total Events:", self.total_events_label)
        activity_layout.addRow("Brush Strokes:", self.strokes_label)
        activity_layout.addRow("Total Layers:", self.layers_label)
        activity_layout.addRow("Images Imported:", self.imports_label)
        activity_group.setLayout(activity_layout)
        layout.addWidget(activity_group)
        
        # Classification group
        class_group = QGroupBox("Classification (Preview)")
        class_layout = QFormLayout()
        
        self.classification_label = QLabel("Loading...")
        self.imports_visible_label = QLabel("N/A")
        self.ai_tools_label = QLabel("N/A")
        
        class_layout.addRow("Current Classification:", self.classification_label)
        class_layout.addRow("Imports Visible:", self.imports_visible_label)
        class_layout.addRow("AI Tools:", self.ai_tools_label)
        class_group.setLayout(class_layout)
        layout.addWidget(class_group)
        
        # Status notice
        notice = QLabel(
            "⚠️ Session is still ACTIVE\n"
            "Classification may change as you continue working.\n"
            "Final classification determined on export."
        )
        notice.setStyleSheet(
            "padding: 10px; "
            "color: orange; "
            "font-size: 10pt;"
        )
        notice.setWordWrap(True)
        notice.setAlignment(Qt.AlignCenter)
        layout.addWidget(notice)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.close)
        
        button_layout.addStretch()
        button_layout.addWidget(self.close_btn)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def display_session(self, session_data):
        """Display session data in the dialog"""
        
        # Document info
        doc_name = session_data.get("document_name", "N/A")
        canvas_width = session_data.get("canvas_width", 0)
        canvas_height = session_data.get("canvas_height", 0)
        session_id = session_data.get("session_id", "N/A")
        
        self.doc_name_label.setText(doc_name)
        self.canvas_size_label.setText(f"{canvas_width}x{canvas_height}px")
        self.session_id_label.setText(
            session_id[:16] + "..." if len(session_id) > 16 else session_id
        )
        
        # Time metrics
        session_duration = session_data.get("session_duration", 0)
        drawing_time = session_data.get("drawing_time", 0)
        
        self.session_duration_label.setText(
            f"{session_duration}s ({session_duration // 60}m {session_duration % 60}s)"
        )
        self.drawing_time_label.setText(
            f"{drawing_time}s ({drawing_time // 60}m {drawing_time % 60}s)"
        )
        
        # Activity
        total_events = session_data.get("total_events", 0)
        stroke_count = session_data.get("stroke_count", 0)
        layer_count = session_data.get("layer_count", 0)
        import_count = session_data.get("import_count", 0)
        
        self.total_events_label.setText(str(total_events))
        self.strokes_label.setText(str(stroke_count))
        self.layers_label.setText(str(layer_count))
        self.imports_label.setText(str(import_count))
        
        # Classification
        classification = session_data.get("classification", "Unknown")
        
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
        
        # Imports visibility
        imports_visible = session_data.get("imports_visible", None)
        if imports_visible is None:
            if import_count > 0:
                self.imports_visible_label.setText("Unknown")
            else:
                self.imports_visible_label.setText("N/A (no imports)")
        elif imports_visible:
            self.imports_visible_label.setText("Yes (MixedMedia)")
            self.imports_visible_label.setStyleSheet("color: blue; font-weight: bold;")
        else:
            self.imports_visible_label.setText("No (Hidden references)")
            self.imports_visible_label.setStyleSheet("color: green;")
        
        # AI tools
        ai_tools_used = session_data.get("ai_tools_used", False)
        ai_tools_list = session_data.get("ai_tools_list", [])
        
        if ai_tools_used and ai_tools_list:
            self.ai_tools_label.setText(f"🤖 {', '.join(ai_tools_list)}")
            self.ai_tools_label.setStyleSheet("color: orange; font-weight: bold;")
        elif ai_tools_used:
            self.ai_tools_label.setText("🤖 Yes (unknown tools)")
            self.ai_tools_label.setStyleSheet("color: orange; font-weight: bold;")
        else:
            self.ai_tools_label.setText("None")
            self.ai_tools_label.setStyleSheet("color: green;")


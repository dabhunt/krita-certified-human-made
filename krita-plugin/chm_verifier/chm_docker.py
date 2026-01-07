"""
CHM Docker Widget - Persistent UI panel for CHM plugin

Provides:
- Live session statistics (updates every 5 seconds)
- Quick Export with Proof button
- Quick View Current Session button
- Collapsible detailed information sections

This file is part of the Certified Human-Made Krita Plugin.
Copyright (C) 2026 Certified Human-Made

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QLabel, QFrame, QSizePolicy
)
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QFont
from krita import DockWidget


class CollapsibleSection(QWidget):
    """A collapsible section widget with header and content"""
    
    def __init__(self, title, parent=None):
        super().__init__(parent)
        self.is_expanded = False
        
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Header button (clickable)
        self.header_btn = QPushButton(f"▶ {title}")
        self.header_btn.setFlat(True)
        self.header_btn.setStyleSheet("""
            QPushButton {
                text-align: left;
                padding: 5px;
                font-weight: bold;
                background-color: palette(mid);
            }
            QPushButton:hover {
                background-color: palette(midlight);
            }
        """)
        self.header_btn.clicked.connect(self.toggle)
        layout.addWidget(self.header_btn)
        
        # Content widget (hidden by default)
        self.content = QWidget()
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(10, 5, 5, 5)
        self.content.hide()
        layout.addWidget(self.content)
        
        self.title = title
    
    def toggle(self):
        """Toggle expanded/collapsed state"""
        self.is_expanded = not self.is_expanded
        if self.is_expanded:
            self.header_btn.setText(f"▼ {self.title}")
            self.content.show()
        else:
            self.header_btn.setText(f"▶ {self.title}")
            self.content.hide()
    
    def add_widget(self, widget):
        """Add a widget to the content area"""
        self.content_layout.addWidget(widget)
    
    def add_label(self, text):
        """Add a text label to the content area"""
        label = QLabel(text)
        label.setWordWrap(True)
        self.content_layout.addWidget(label)
        return label


class CHMDockerWidget(DockWidget):
    """Main Docker widget for CHM plugin"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("CHM Proof Exporter")
        
        # Get extension reference (set by CHMExtension when registering)
        self.extension = None
        self.DEBUG_LOG = True
        
        # Create main widget
        main_widget = QWidget(self)
        self.setWidget(main_widget)
        
        # Main layout
        layout = QVBoxLayout(main_widget)
        layout.setSpacing(10)
        
        # === HEADER SECTION ===
        header = QLabel("Certified Human-Made")
        header_font = QFont()
        header_font.setPointSize(12)
        header_font.setBold(True)
        header.setFont(header_font)
        header.setAlignment(Qt.AlignCenter)
        layout.addWidget(header)
        
        # === SESSION STATUS (Always Visible) ===
        self.status_label = QLabel("Session: No document open")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)
        
        # Separator
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line)
        
        # === KEY STATS (Always Visible) ===
        stats_container = QWidget()
        stats_layout = QVBoxLayout(stats_container)
        stats_layout.setContentsMargins(0, 0, 0, 0)
        stats_layout.setSpacing(3)
        
        self.strokes_label = QLabel("Strokes: --")
        self.layers_label = QLabel("Layers: --")
        self.drawing_time_label_main = QLabel("Drawing Time: --")
        self.session_length_label = QLabel("Session Length: --")
        self.classification_label = QLabel("Classification: --")
        
        # Make classification stand out
        classification_font = QFont()
        classification_font.setBold(True)
        self.classification_label.setFont(classification_font)
        
        stats_layout.addWidget(self.strokes_label)
        stats_layout.addWidget(self.layers_label)
        stats_layout.addWidget(self.drawing_time_label_main)
        stats_layout.addWidget(self.session_length_label)
        stats_layout.addWidget(self.classification_label)
        
        layout.addWidget(stats_container)
        
        # === COLLAPSIBLE DETAILS ===
        # Advanced Stats Section
        self.advanced_section = CollapsibleSection("Advanced Stats")
        self.import_label = self.advanced_section.add_label("Imports: --")
        layout.addWidget(self.advanced_section)
        
        # AI Detection Section
        self.ai_section = CollapsibleSection("AI Detection")
        self.ai_status_label = self.ai_section.add_label("No AI plugins detected")
        layout.addWidget(self.ai_section)
        
        # Session Info Section
        self.session_section = CollapsibleSection("Session Info")
        self.session_id_label = self.session_section.add_label("Session ID: --")
        self.canvas_size_label = self.session_section.add_label("Canvas: --")
        layout.addWidget(self.session_section)
        
        # Separator
        line2 = QFrame()
        line2.setFrameShape(QFrame.HLine)
        line2.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line2)
        
        # === ACTION BUTTONS ===
        button_container = QWidget()
        button_layout = QVBoxLayout(button_container)
        button_layout.setSpacing(5)
        button_layout.setContentsMargins(0, 0, 0, 0)
        
        # Export button (primary action)
        self.export_btn = QPushButton("Export with Proof")
        self.export_btn.setStyleSheet("""
            QPushButton {
                padding: 8px;
                font-weight: bold;
                background-color: #4CAF50;
                color: white;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        self.export_btn.clicked.connect(self.on_export_clicked)
        self.export_btn.setEnabled(False)  # Disabled until document is open
        button_layout.addWidget(self.export_btn)
        
        # View session button
        self.view_btn = QPushButton("View Current Session")
        self.view_btn.setStyleSheet("""
            QPushButton {
                padding: 6px;
            }
        """)
        self.view_btn.clicked.connect(self.on_view_clicked)
        self.view_btn.setEnabled(False)  # Disabled until document is open
        button_layout.addWidget(self.view_btn)
        
        layout.addWidget(button_container)
        
        # Add spacer to push everything to top
        layout.addStretch()
        
        # === SETUP UPDATE TIMER ===
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_stats)
        self.update_timer.start(5000)  # Update every 5 seconds
        
        self._log("CHM Docker created successfully")
    
    def canvasChanged(self, canvas):
        """Called when the active canvas changes"""
        # Force immediate update when canvas changes
        self.update_stats()
    
    def set_extension(self, extension):
        """Set reference to CHMExtension for accessing session data"""
        self.extension = extension
        self.DEBUG_LOG = extension.DEBUG_LOG if extension else True
        self._log("Extension reference set")
        # Trigger immediate update
        self.update_stats()
    
    def update_stats(self):
        """Update all statistics from current session"""
        if not self.extension:
            self._log("Cannot update stats - no extension reference")
            return
        
        from krita import Krita
        app = Krita.instance()
        doc = app.activeDocument()
        
        if not doc:
            # No document open
            self.status_label.setText("Session: No document open")
            self.strokes_label.setText("Strokes: --")
            self.layers_label.setText("Layers: --")
            self.drawing_time_label_main.setText("Drawing Time: --")
            self.session_length_label.setText("Session Length: --")
            self.classification_label.setText("Classification: --")
            self.export_btn.setEnabled(False)
            self.view_btn.setEnabled(False)
            
            # Update collapsible sections
            self.import_label.setText("Imports: --")
            self.ai_status_label.setText("No AI plugins detected")
            self.session_id_label.setText("Session ID: --")
            self.canvas_size_label.setText("Canvas: --")
            return
        
        # Check if document is saved
        filepath = doc.fileName()
        if not filepath:
            self.status_label.setText("Session: Document not saved")
            self.export_btn.setEnabled(False)
            self.view_btn.setEnabled(False)
            return
        
        # Get session
        session = self.extension.session_manager.get_session(doc)
        
        if not session:
            self.status_label.setText("Session: Active (no events yet)")
            self.strokes_label.setText("Strokes: 0")
            self.layers_label.setText("Layers: 0")
            self.drawing_time_label_main.setText("Drawing Time: 0s")
            self.session_length_label.setText("Session Length: 0s")
            self.classification_label.setText("Classification: Pending")
            self.export_btn.setEnabled(True)  # Can export even with no events
            self.view_btn.setEnabled(True)
            return
        
        # === UPDATE MAIN STATS ===
        self.status_label.setText("Session: Active ✓")
        
        # Count events by type
        stroke_count = sum(1 for e in session.events if e.get("type") == "stroke")
        import_count = sum(1 for e in session.events if e.get("type") == "import")
        
        # Count actual layers in document
        layer_count = 0
        try:
            def count_all_layers(node):
                count = 1
                for child in node.childNodes():
                    count += count_all_layers(child)
                return count
            
            for top_node in doc.topLevelNodes():
                layer_count += count_all_layers(top_node)
        except Exception as e:
            self._log(f"Error counting layers: {e}")
            layer_count = sum(1 for e in session.events if e.get("type") in ["layer_created", "layer_added"])
        
        # Get time metrics
        session_duration = session.duration_secs if hasattr(session, 'duration_secs') else 0
        drawing_time = session.drawing_time_secs if hasattr(session, 'drawing_time_secs') else 0
        
        # Format times
        session_length_str = self._format_time(session_duration)
        drawing_time_str = self._format_time(drawing_time)
        
        # Get classification preview
        doc_key = self.extension.event_capture._get_doc_key(doc)
        classification = session._classify(
            doc=doc,
            doc_key=doc_key,
            import_tracker=self.extension.event_capture.import_tracker
        )
        
        # Update labels
        self.strokes_label.setText(f"Strokes: {stroke_count}")
        self.layers_label.setText(f"Layers: {layer_count}")
        self.drawing_time_label_main.setText(f"Drawing Time: {drawing_time_str}")
        self.session_length_label.setText(f"Session Length: {session_length_str}")
        self.classification_label.setText(f"Classification: {classification}")
        
        # Enable buttons
        self.export_btn.setEnabled(True)
        self.view_btn.setEnabled(True)
        
        # === UPDATE COLLAPSIBLE SECTIONS ===
        
        # Advanced Stats
        self.import_label.setText(f"Imports: {import_count}")
        
        # AI Detection
        metadata = session.get_metadata()
        ai_tools_used = metadata.get('ai_tools_used', False)
        ai_tools_list = metadata.get('ai_tools_list', [])
        
        if ai_tools_used and ai_tools_list:
            ai_text = f"⚠️ {len(ai_tools_list)} AI plugin(s) detected:\n"
            ai_text += "\n".join(f"• {tool}" for tool in ai_tools_list[:5])  # Show max 5
            if len(ai_tools_list) > 5:
                ai_text += f"\n• ... and {len(ai_tools_list) - 5} more"
            self.ai_status_label.setText(ai_text)
        else:
            self.ai_status_label.setText("✓ No AI plugins detected")
        
        # Session Info
        self.session_id_label.setText(f"Session ID: {session.id[:16]}...")
        self.canvas_size_label.setText(f"Canvas: {doc.width()}x{doc.height()}px")
    
    def _format_time(self, seconds):
        """Format seconds into human-readable time"""
        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            minutes = int(seconds / 60)
            secs = int(seconds % 60)
            return f"{minutes}m {secs}s"
        else:
            hours = int(seconds / 3600)
            minutes = int((seconds % 3600) / 60)
            return f"{hours}h {minutes}m"
    
    def on_export_clicked(self):
        """Handle Export button click"""
        if self.extension:
            self._log("Export button clicked")
            self.extension.export_with_proof()
        else:
            self._log("Cannot export - no extension reference")
    
    def on_view_clicked(self):
        """Handle View Session button click"""
        if self.extension:
            self._log("View Session button clicked")
            self.extension.view_current_session()
        else:
            self._log("Cannot view session - no extension reference")
    
    def _log(self, message):
        """Debug logging helper"""
        if self.DEBUG_LOG:
            print(f"CHM-Docker: {message}")


# Factory class required by Krita
class CHMDockerFactory:
    """Factory for creating CHM Docker instances"""
    
    def __init__(self, extension):
        self.extension = extension
    
    def createDockWidget(self):
        """Create and return a new Docker instance"""
        docker = CHMDockerWidget()
        docker.set_extension(self.extension)
        return docker


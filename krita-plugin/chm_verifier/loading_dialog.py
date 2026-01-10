"""
Loading Dialog

Shows animated spinner during long-running operations like server verification.
"""

from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont


class LoadingDialog(QDialog):
    """Modal dialog with animated terminal-style spinner"""
    
    # Terminal spinner frames (classic braille spinner)
    SPINNER_FRAMES = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
    
    def __init__(self, message="Loading...", parent=None):
        """
        Create loading dialog with animated spinner.
        
        Args:
            message: Text to display (spinner will be appended)
            parent: Parent widget (optional)
        """
        super().__init__(parent)
        self.message = message
        self.current_frame = 0
        
        self.setWindowTitle("CHM")
        self.setModal(True)
        self.setMinimumWidth(350)
        self.setMinimumHeight(100)
        
        # Remove window decorations for cleaner look
        self.setWindowFlags(Qt.Dialog | Qt.CustomizeWindowHint | Qt.WindowTitleHint)
        
        self.setup_ui()
        self.setup_timer()
    
    def setup_ui(self):
        """Setup UI components"""
        layout = QVBoxLayout()
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Spinner + message label
        self.label = QLabel()
        self.label.setAlignment(Qt.AlignCenter)
        font = QFont()
        font.setPointSize(12)
        self.label.setFont(font)
        
        self.update_spinner()
        
        layout.addWidget(self.label)
        self.setLayout(layout)
    
    def setup_timer(self):
        """Setup animation timer"""
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_spinner)
        self.timer.start(100)  # Update every 100ms
    
    def update_spinner(self):
        """Update spinner animation"""
        spinner = self.SPINNER_FRAMES[self.current_frame]
        self.label.setText(f"{self.message} {spinner}")
        self.current_frame = (self.current_frame + 1) % len(self.SPINNER_FRAMES)
    
    def set_message(self, message):
        """Update the message text"""
        self.message = message
        self.update_spinner()
    
    def closeEvent(self, event):
        """Clean up timer on close"""
        if hasattr(self, 'timer'):
            self.timer.stop()
        super().closeEvent(event)


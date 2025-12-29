"""
Event Capture

Captures Krita events (strokes, layers, imports) and records them to CHM sessions.

IMPLEMENTATION NOTE (Dec 28, 2025):
Krita's Python API has limitations with stroke signal detection:
- view.strokeBegin/strokeEnd signals exist in API docs but are not reliably
  exposed through PyQt5 SIP wrappers (objects appear as generic QObject)
- SOLUTION: Use polling-based detection via document.modified() flag changes
- FUTURE: Consider QEvent filter on canvas widget for direct event capture

Based on Krita API research (docs/krita-api-research.md):
- Stroke events: Document modification polling (strokeBegin/End unavailable via SIP)
- Document events: notifier.imageSaved, imageClosed, imageCreated (working)
- Layer events: Polling-based detection (nodeCreated signal poorly documented)
"""

from krita import Krita
from PyQt5.QtCore import QTimer, QObject, QEvent
from PyQt5.QtWidgets import QOpenGLWidget
import time


class CanvasEventFilter(QObject):
    """
    Qt Event Filter for canvas to capture stroke events directly.
    
    This is a fallback for when Krita's strokeBegin/strokeEnd signals
    are not accessible via Python SIP wrappers.
    """
    
    def __init__(self, session_manager, debug_log=True):
        super().__init__()
        self.session_manager = session_manager
        self.DEBUG_LOG = debug_log
        self.stroke_in_progress = False
        self.stroke_start_time = None
        
    def eventFilter(self, obj, event):
        """Intercept Qt events from canvas to detect strokes"""
        try:
            # Detect stroke beginning
            if event.type() in (QEvent.MouseButtonPress, QEvent.TabletPress):
                if not self.stroke_in_progress:
                    self.stroke_in_progress = True
                    self.stroke_start_time = time.time()
                    self._on_stroke_begin()
                    
            # Detect stroke ending
            elif event.type() in (QEvent.MouseButtonRelease, QEvent.TabletRelease):
                if self.stroke_in_progress:
                    self.stroke_in_progress = False
                    self._on_stroke_end()
                    
        except Exception as e:
            if self.DEBUG_LOG:
                print(f"CanvasEventFilter error: {e}")
        
        # Don't block the event - let Krita process it normally
        return False
    
    def _on_stroke_begin(self):
        """Handle stroke beginning"""
        if self.DEBUG_LOG:
            print("[EventFilter] Stroke began (via canvas event filter)")
    
    def _on_stroke_end(self):
        """Handle stroke ending"""
        # Get active document and session
        app = Krita.instance()
        doc = app.activeDocument()
        
        if not doc:
            return
            
        session = self.session_manager.get_session(doc)
        if session:
            try:
                # Record stroke with placeholder values
                # (event filter doesn't give us coordinates easily)
                session.record_stroke(
                    x=0.0,
                    y=0.0,
                    pressure=0.5,
                    brush_name="Unknown"
                )
                
                if self.DEBUG_LOG:
                    duration = time.time() - self.stroke_start_time if self.stroke_start_time else 0
                    print(f"[EventFilter] Stroke recorded (duration: {duration:.2f}s, total: {session.event_count})")
            except Exception as e:
                if self.DEBUG_LOG:
                    print(f"[EventFilter] Error recording stroke: {e}")


class EventCapture:
    """Captures and records Krita events to CHM sessions"""
    
    def __init__(self, session_manager, debug_log=True):
        self.session_manager = session_manager
        self.DEBUG_LOG = debug_log
        self.connected_views = set()  # Track which views have signals connected
        self.connected_documents = set()  # Track which documents have signals
        self.layer_cache = {}  # Cache layer names per document for change detection
        self.current_brush_name = None  # Track current brush (not in stroke signals)
        
        # Canvas event filter (alternative stroke detection)
        self.canvas_event_filter = CanvasEventFilter(session_manager, debug_log)
        self.canvas_filter_installed = False
        
        # Timer for polling-based layer detection (fallback)
        self.layer_poll_timer = QTimer()
        self.layer_poll_timer.timeout.connect(self.poll_changes)
        self.layer_poll_timer.setInterval(2000)  # Poll every 2 seconds
        
        # Track document modification state for stroke detection fallback
        self.doc_modified_state = {}  # doc_id -> bool (was modified last poll)
        
    def start_capture(self):
        """Start capturing events globally"""
        app = Krita.instance()
        notifier = app.notifier()
        
        # Log Krita version
        self._log(f"Krita version: {app.version()}")
        
        # Connect global document lifecycle events
        notifier.imageCreated.connect(self.on_image_created)
        notifier.imageClosed.connect(self.on_image_closed)
        notifier.imageSaved.connect(self.on_image_saved)
        notifier.viewCreated.connect(self.on_view_created)
        
        # Try to install canvas event filter for stroke detection
        self._install_canvas_event_filter()
        
        # Start layer polling
        self.layer_poll_timer.start()
        
        self._log("Event capture started (global signals connected)")
        
        # Connect to any already-open documents/views
        for doc in app.documents():
            self.connect_document_signals(doc)
        
        for window in app.windows():
            for view in window.views():
                self.connect_view_signals(view)
    
    def stop_capture(self):
        """Stop capturing events"""
        self.layer_poll_timer.stop()
        self._log("Event capture stopped")
    
    def _install_canvas_event_filter(self):
        """
        Install event filter on canvas widget for direct stroke detection.
        
        This is a workaround for Krita's strokeBegin/strokeEnd signals
        not being accessible through Python SIP wrappers.
        """
        try:
            app = Krita.instance()
            active_window = app.activeWindow()
            
            if not active_window:
                self._log("No active window - will retry canvas filter on view creation")
                return False
            
            # Get the Qt window widget
            qwindow = active_window.qwindow()
            if not qwindow:
                self._log("No qwindow available - canvas filter unavailable")
                return False
            
            # Find the canvas widget (typically QOpenGLWidget)
            canvas = qwindow.findChild(QOpenGLWidget)
            if canvas:
                canvas.installEventFilter(self.canvas_event_filter)
                self.canvas_filter_installed = True
                self._log("✓ Canvas event filter installed for stroke detection")
                return True
            else:
                self._log("Canvas widget not found - using fallback polling")
                return False
                
        except Exception as e:
            self._log(f"Could not install canvas event filter: {e}")
            self._log("Will use fallback document polling for stroke detection")
            return False
    
    def connect_document_signals(self, document):
        """Connect to document-level signals"""
        doc_id = id(document)
        
        if doc_id in self.connected_documents:
            return  # Already connected
        
        self.connected_documents.add(doc_id)
        self._log(f"Connected to document signals: {document.name()}")
        
        # Initialize layer cache for this document
        self.update_layer_cache(document)
    
    def connect_view_signals(self, view):
        """
        Connect to view-level signals.
        
        NOTE: Krita's strokeBegin/strokeEnd signals are not accessible via
        Python SIP wrappers (objects appear as generic PyQt5.QtCore.QObject).
        We use canvas event filter instead for stroke detection.
        """
        view_id = id(view)
        
        if view_id in self.connected_views:
            return  # Already connected
        
        if self.DEBUG_LOG:
            self._log(f"View created: {view_id}")
            self._log(f"View type: {type(view).__name__} (expected: generic QObject due to SIP wrapping)")
        
        # Try to install canvas event filter if not already installed
        if not self.canvas_filter_installed:
            self._install_canvas_event_filter()
        
        # Try to connect viewChanged for basic activity tracking
        try:
            if hasattr(view, 'viewChanged'):
                view.viewChanged.connect(lambda: self.on_view_changed(view))
                if self.DEBUG_LOG:
                    self._log(f"✓ Connected viewChanged signal for view {view_id}")
        except Exception as e:
            if self.DEBUG_LOG:
                self._log(f"Could not connect viewChanged: {e}")
        
        self.connected_views.add(view_id)
        
        if self.DEBUG_LOG:
            detection_method = "canvas event filter" if self.canvas_filter_installed else "document modification polling"
            self._log(f"✓ View {view_id} connected (stroke detection via {detection_method})")
    
    def on_image_created(self):
        """Handler for new document creation"""
        app = Krita.instance()
        doc = app.activeDocument()
        
        if not doc:
            return
        
        self._log(f"Document created: {doc.name()}")
        
        # Create CHM session for new document
        if not self.session_manager.has_session(doc):
            session = self.session_manager.create_session(doc)
            
            # Set metadata
            try:
                import platform
                session.set_metadata(
                    document_name=doc.name(),
                    canvas_width=doc.width(),
                    canvas_height=doc.height(),
                    krita_version=app.version(),
                    os_info=f"{platform.system()} {platform.release()}"
                )
            except Exception as e:
                self._log(f"Error setting metadata: {e}")
        
        # Connect signals for this document
        self.connect_document_signals(doc)
    
    def on_image_closed(self):
        """Handler for document close"""
        # Note: The document is already closed at this point
        # Session cleanup happens when user explicitly finalizes
        self._log("Document closed event received")
    
    def on_image_saved(self):
        """Handler for document save"""
        app = Krita.instance()
        doc = app.activeDocument()
        
        if not doc:
            return
        
        self._log(f"Document saved: {doc.name()}")
        
        # Update session metadata with current document name
        session = self.session_manager.get_session(doc)
        if session:
            try:
                session.set_metadata(
                    document_name=doc.name(),
                    canvas_width=doc.width(),
                    canvas_height=doc.height(),
                    krita_version=None,  # Keep existing
                    os_info=None  # Keep existing
                )
            except Exception as e:
                self._log(f"Error updating metadata on save: {e}")
    
    def on_view_created(self, view):
        """Handler for new view creation"""
        self._log(f"View created: {id(view)}")
        self.connect_view_signals(view)
    
    def on_view_changed(self, view):
        """Handler for view changes (zoom, pan, or potential drawing activity)"""
        # This fires on zoom/pan/rotation, but also potentially during drawing
        # We can use this as a fallback to detect activity
        doc = view.document()
        if not doc:
            return
        
        # Check if document has been modified (indicates drawing/editing occurred)
        if doc.modified():
            session = self.session_manager.get_session(doc)
            if session:
                # Document was modified - record generic activity
                # This is a fallback since we don't have strokeBegin/strokeEnd
                pass  # For now, just know activity happened
    
    def on_stroke_begin(self, view):
        """Handler for stroke beginning"""
        # Query current brush (not included in stroke signals)
        try:
            app = Krita.instance()
            # Note: currentBrush() may not exist in all Krita versions
            # This is a best-effort capture
            self.current_brush_name = "Unknown Brush"
            self._log("Stroke began")
        except Exception as e:
            self._log(f"Error in stroke_begin: {e}")
    
    def on_stroke_end(self, view):
        """Handler for stroke ending"""
        doc = view.document()
        
        if not doc:
            return
        
        session = self.session_manager.get_session(doc)
        
        if not session:
            self._log(f"Warning: No session found for document on stroke_end")
            return
        
        try:
            # Stroke signal doesn't include coordinates or pressure
            # Record a representative stroke event
            # Note: Using placeholder values since stroke data not available in signal
            session.record_stroke(
                x=0.0,  # Placeholder - actual coordinates not in signal
                y=0.0,  # Placeholder
                pressure=0.5,  # Default pressure (actual not available)
                brush_name=self.current_brush_name
            )
            
            if self.DEBUG_LOG:
                self._log(f"Stroke recorded (total: {session.event_count})")
        except Exception as e:
            self._log(f"Error recording stroke: {e}")
    
    def update_layer_cache(self, document):
        """Update the cached layer list for a document"""
        doc_id = id(document)
        
        try:
            layer_names = set()
            for node in document.topLevelNodes():
                layer_names.add(node.name())
            
            self.layer_cache[doc_id] = layer_names
        except Exception as e:
            self._log(f"Error updating layer cache: {e}")
    
    def poll_changes(self):
        """
        Poll for changes (fallback for missing signals).
        Detects: layer changes, document modifications (strokes)
        """
        app = Krita.instance()
        doc = app.activeDocument()
        
        if not doc:
            return
        
        doc_id = id(doc)
        
        # Poll layer changes
        self.poll_layer_changes(doc, doc_id)
        
        # Poll document modification (stroke detection fallback)
        self.poll_document_modification(doc, doc_id)
    
    def poll_layer_changes(self, doc, doc_id):
        """Poll for layer changes"""
        try:
            current_layers = set()
            for node in doc.topLevelNodes():
                current_layers.add(node.name())
        except Exception as e:
            self._log(f"Error polling layers: {e}")
            return
        
        # Check if we have a cached version
        if doc_id not in self.layer_cache:
            self.layer_cache[doc_id] = current_layers
            return
        
        previous_layers = self.layer_cache[doc_id]
        
        # Detect new layers
        new_layers = current_layers - previous_layers
        
        if new_layers:
            session = self.session_manager.get_session(doc)
            if session:
                for layer_name in new_layers:
                    try:
                        node = doc.nodeByName(layer_name)
                        if node:
                            session.record_layer_added(
                                layer_id=str(id(node)),
                                layer_type=node.type()
                            )
                            self._log(f"Layer added: {layer_name} ({node.type()})")
                    except Exception as e:
                        self._log(f"Error recording layer: {e}")
        
        # Update cache
        self.layer_cache[doc_id] = current_layers
    
    def poll_document_modification(self, doc, doc_id):
        """
        Poll document modification state to detect drawing activity.
        Fallback for when strokeBegin/strokeEnd signals are unavailable.
        """
        try:
            current_modified = doc.modified()
            previous_modified = self.doc_modified_state.get(doc_id, False)
            
            # Detect transition from unmodified to modified (drawing occurred)
            if current_modified and not previous_modified:
                session = self.session_manager.get_session(doc)
                if session:
                    # Record a stroke event (generic since we don't have coordinates)
                    session.record_stroke(
                        x=0.0,  # Placeholder
                        y=0.0,  # Placeholder
                        pressure=0.5,  # Default
                        brush_name="Unknown"
                    )
                    self._log(f"Activity detected (modified flag changed, total events: {session.event_count})")
            
            # Update state
            self.doc_modified_state[doc_id] = current_modified
            
        except Exception as e:
            self._log(f"Error polling modification state: {e}")
    
    def _log(self, message):
        """Debug logging helper"""
        if self.DEBUG_LOG:
            import sys
            from datetime import datetime
            import os
            
            full_message = f"EventCapture: {message}"
            print(full_message)
            sys.stdout.flush()
            
            # Also write to debug file
            try:
                log_dir = os.path.expanduser("~/.local/share/chm")
                os.makedirs(log_dir, exist_ok=True)
                log_file = os.path.join(log_dir, "plugin_debug.log")
                
                with open(log_file, "a") as f:
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    f.write(f"[{timestamp}] CHM: {full_message}\n")
                    f.flush()
            except Exception as e:
                print(f"EventCapture: Could not write to log file: {e}")


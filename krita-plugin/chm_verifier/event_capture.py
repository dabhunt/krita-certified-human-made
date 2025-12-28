"""
Event Capture

Captures Krita events (strokes, layers, imports) and records them to CHM sessions.
Implements signal handlers for Krita API events.

Based on Krita API research (docs/krita-api-research.md):
- Stroke events: view.strokeBegin, view.strokeEnd (no pressure data)
- Document events: notifier.imageSaved, imageClosed, imageCreated
- Layer events: Polling-based detection (nodeCreated signal poorly documented)
"""

from krita import Krita
from PyQt5.QtCore import QTimer
import time


class EventCapture:
    """Captures and records Krita events to CHM sessions"""
    
    def __init__(self, session_manager, debug_log=True):
        self.session_manager = session_manager
        self.DEBUG_LOG = debug_log
        self.connected_views = set()  # Track which views have signals connected
        self.connected_documents = set()  # Track which documents have signals
        self.layer_cache = {}  # Cache layer names per document for change detection
        self.current_brush_name = None  # Track current brush (not in stroke signals)
        
        # Timer for polling-based layer detection (fallback)
        self.layer_poll_timer = QTimer()
        self.layer_poll_timer.timeout.connect(self.poll_layer_changes)
        self.layer_poll_timer.setInterval(5000)  # Poll every 5 seconds
        
    def start_capture(self):
        """Start capturing events globally"""
        app = Krita.instance()
        notifier = app.notifier()
        
        # Connect global document lifecycle events
        notifier.imageCreated.connect(self.on_image_created)
        notifier.imageClosed.connect(self.on_image_closed)
        notifier.imageSaved.connect(self.on_image_saved)
        notifier.viewCreated.connect(self.on_view_created)
        
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
        """Connect to view-level signals (stroke events)"""
        view_id = id(view)
        
        if view_id in self.connected_views:
            return  # Already connected
        
        # Connect stroke signals
        try:
            view.strokeBegin.connect(lambda: self.on_stroke_begin(view))
            view.strokeEnd.connect(lambda: self.on_stroke_end(view))
            self.connected_views.add(view_id)
            self._log(f"Connected to view signals: view {view_id}")
        except AttributeError as e:
            self._log(f"Warning: Could not connect stroke signals: {e}")
    
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
    
    def poll_layer_changes(self):
        """Poll for layer changes (fallback for missing signals)"""
        app = Krita.instance()
        doc = app.activeDocument()
        
        if not doc:
            return
        
        doc_id = id(doc)
        
        # Get current layers
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
    
    def _log(self, message):
        """Debug logging helper"""
        if self.DEBUG_LOG:
            print(f"EventCapture: {message}")


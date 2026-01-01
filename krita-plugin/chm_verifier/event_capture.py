"""
Event Capture

Captures Krita events (strokes, layers, imports) and records them to CHM sessions.

IMPLEMENTATION NOTE (Dec 28, 2025 - BFROS CONCLUSION):
After systematic testing (ROAA/BFROS sessions), we confirmed:

❌ FAILED APPROACHES:
1. view.strokeBegin/strokeEnd - NOT exposed through PyQt5 SIP wrappers
2. canvas.pointerPress/pointerRelease - NOT exposed (hasattr returns False)
3. Qt Event Filter on QOpenGLWidget - Filters VIEWPORT (1938x781), not document (500x500)
   - QOpenGLWidget is the display renderer, NOT the input canvas
   - Drawing events don't pass through the GL widget

✅ WORKING SOLUTION (per krita-api-research.md):
- **Document modification polling** via `doc.modified()` flag
- Poll every 500ms to detect drawing activity
- Simple, reliable, works with all tools

Based on Krita API research (docs/krita-api-research.md):
- Stroke events: Document modification polling (strokeBegin/End unavailable via SIP)
- Document events: notifier.imageSaved, imageClosed, imageCreated (working)
- Layer events: Polling-based detection (nodeCreated signal poorly documented)
"""

from krita import Krita
from PyQt5.QtCore import QTimer, QObject, QEvent, Qt
from PyQt5.QtWidgets import QOpenGLWidget, QWidget
import time
from .tracing_detector import TracingDetector


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
        self.event_count = 0  # BFROS: Track if eventFilter is called at all
        self.last_log_time = 0  # BFROS: Rate limit logging
        
    def eventFilter(self, obj, event):
        """Intercept Qt events from canvas to detect strokes (Approach 3 fallback)"""
        try:
            self.event_count += 1
            event_type = event.type()
            
            # ROAA-Approach3: Log first 20 events with names to see what we're getting
            if self.event_count <= 20 and self.DEBUG_LOG:
                event_name = self._get_event_name(event_type)
                print(f"[ROAA-Approach3] Event #{self.event_count}: type={event_type} ({event_name})")
                import sys
                sys.stdout.flush()
            
            # Log event count periodically
            current_time = time.time()
            if self.DEBUG_LOG and (current_time - self.last_log_time > 10):
                self.last_log_time = current_time
                print(f"[ROAA-Approach3] Received {self.event_count} events total")
                import sys
                sys.stdout.flush()
            
            # Detect stroke beginning (try various event types)
            if event_type in (QEvent.MouseButtonPress, QEvent.TabletPress, QEvent.MouseMove):
                # On first MouseMove or Press, consider it stroke start
                if not self.stroke_in_progress and event_type in (QEvent.MouseButtonPress, QEvent.TabletPress):
                    self.stroke_in_progress = True
                    self.stroke_start_time = time.time()
                    self._on_stroke_begin()
                    
            # Detect stroke ending
            elif event_type in (QEvent.MouseButtonRelease, QEvent.TabletRelease):
                if self.stroke_in_progress:
                    self.stroke_in_progress = False
                    self._on_stroke_end()
                    
        except Exception as e:
            if self.DEBUG_LOG:
                import traceback
                print(f"[EventFilter] ERROR: {e}")
                print(f"Traceback: {traceback.format_exc()}")
                import sys
                sys.stdout.flush()
        
        # Don't block the event - let Krita process it normally
        return False
    
    def _get_event_name(self, event_type):
        """Convert QEvent type number to human-readable name"""
        # Common Qt event types
        event_names = {
            0: "None", 1: "Timer", 2: "MouseButtonPress", 3: "MouseButtonRelease",
            4: "MouseButtonDblClick", 5: "MouseMove", 6: "KeyPress", 7: "KeyRelease",
            8: "FocusIn", 9: "FocusOut", 10: "Enter", 11: "Leave",
            12: "Paint", 13: "Move", 14: "Resize", 17: "Show", 18: "Hide",
            24: "WindowActivate", 25: "WindowDeactivate",
            68: "ChildAdded", 69: "ChildPolished", 71: "ChildRemoved",
            87: "TabletMove", 88: "TabletPress", 89: "TabletRelease",
            129: "DynamicPropertyChange", 152: "UpdateRequest"
        }
        return event_names.get(event_type, f"Unknown({event_type})")
    
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
    
    def __init__(self, session_manager, session_storage=None, debug_log=True):
        self.session_manager = session_manager
        self.session_storage = session_storage  # For persisting sessions
        self.DEBUG_LOG = debug_log
        self.connected_views = set()  # Track which views have signals connected
        self.connected_documents = set()  # Track which documents have signals
        self.layer_cache = {}  # Cache layer names per document for change detection
        self.current_brush_name = None  # Track current brush (not in stroke signals)
        
        # Canvas event filter (alternative stroke detection)
        self.canvas_event_filter = CanvasEventFilter(session_manager, debug_log)
        self.canvas_filter_installed = False
        
        # Timer for polling-based detection (PRIMARY METHOD per krita-api-research.md)
        self.poll_timer = QTimer()
        self.poll_timer.timeout.connect(self.poll_changes)
        self.poll_timer.setInterval(500)  # Poll every 500ms for responsive stroke detection
        
        # Track document modification state for stroke detection fallback
        self.doc_modified_state = {}  # doc_id -> bool (was modified last poll)
        
        # BFROS FIX: Track document content hash to detect ACTUAL changes
        # Since modified() is a boolean flag, we need to detect pixel changes
        self.doc_content_hash = {}  # doc_id -> str (hash of document content)
        
        # BFROS FIX: Initialize last stroke time tracking
        self._last_stroke_time = {}  # doc_id -> timestamp (for future features)
        
        # BFROS: Track additional metrics to detect ongoing activity
        self.doc_undo_count = {}  # doc_id -> int (undo stack count)
        
        # AFK Detection: Track polls without content changes
        # After 2 polls (1 second) without changes, stop incrementing drawing time
        self.polls_without_change = {}  # doc_id -> int (consecutive polls with no change)
        self.AFK_POLL_THRESHOLD = 2  # 2 polls × 500ms = 1 second idle before AFK
        
        # BUG#008 FIX: Simple poll-based drawing time tracking (excludes AFK)
        # Count active polls instead of calculating elapsed time (simpler, less error-prone)
        self.active_poll_count = {}  # doc_id -> int (number of polls user was actively drawing)
        
        # Tracing Detection: Perceptual hash comparison
        self.tracing_detector = TracingDetector(debug_log=debug_log)
        
        # BUG#003 FIX: Delayed import detection for paste operations
        # Paste may create layer before pixels are loaded - need delayed check
        self.pending_import_checks = {}  # doc_key -> [(layer_name, check_count)]
        # BUG#006 FIX: Increased timeout for SVG and complex imports
        self.IMPORT_CHECK_DELAY = 6  # Check for 6 polls (3 seconds) after layer creation
    
    def _get_doc_key(self, doc):
        """
        BUG#005 FIX: Get consistent document key (DRY with session manager).
        
        This ensures tracing detector and session manager use the SAME key,
        preventing data loss during session migration (unsaved → saved).
        
        Args:
            doc: Krita document
            
        Returns:
            str: Document key (filepath or unsaved_ID)
        """
        return self.session_manager._get_document_key(doc)
        
    def start_capture(self):
        """Start capturing events globally"""
        app = Krita.instance()
        notifier = app.notifier()
        
        # Log Krita version
        self._log(f"Krita version: {app.version()}")
        
        # BFROS: Log which signals we're connecting to
        if self.DEBUG_LOG:
            self._log("[BFROS] Connecting to Krita signals: imageCreated, imageClosed, imageSaved, viewCreated")
        
        # Connect global document lifecycle events
        notifier.imageCreated.connect(self.on_image_created)
        notifier.imageClosed.connect(self.on_image_closed)
        notifier.imageSaved.connect(self.on_image_saved)
        notifier.viewCreated.connect(self.on_view_created)
        
        # Start polling timer (PRIMARY stroke detection method)
        self.poll_timer.start()
        
        if self.DEBUG_LOG:
            self._log("[BFROS-FINAL] Using document.modified() polling for stroke detection (500ms interval)")
        
        self._log("Event capture started (global signals connected)")
        
        # BFROS: Check if documents already exist (opened before plugin loaded)
        existing_docs = app.documents()
        
        if self.DEBUG_LOG:
            self._log(f"[BFROS-STARTUP] Checking for existing documents: {existing_docs}")
            self._log(f"[BFROS-STARTUP] Number of existing documents: {len(existing_docs) if existing_docs else 0}")
        
        if existing_docs:
            if self.DEBUG_LOG:
                self._log(f"[BFROS] Found {len(existing_docs)} existing document(s) - will create sessions")
        else:
            if self.DEBUG_LOG:
                self._log(f"[BFROS] No existing documents at startup - sessions will be created via on_image_created signal")
        
        # Connect to any already-open documents/views  
        # THIS IS WHERE "part2" gets handled when Krita starts with file already open!
        for doc in existing_docs:
            self.connect_document_signals(doc)
            
            if self.DEBUG_LOG:
                self._log(f"[BFROS] Existing document: {doc.name()} ({doc.width()}x{doc.height()})")
            
            # === RESUME SESSION FOR EXISTING DOCUMENT ===
            if not self.session_manager.has_session(doc):
                self._try_resume_or_create_session(doc, "existing doc at startup")
            else:
                self._log(f"[BFROS] Session already exists in memory for: {doc.name()}")
            
            # Retry canvas filter for this existing document (with delays)
            QTimer.singleShot(100, lambda d=doc: self._delayed_canvas_retry(d, "100ms after detecting existing doc"))
            QTimer.singleShot(500, lambda d=doc: self._delayed_canvas_retry(d, "500ms after detecting existing doc"))
            QTimer.singleShot(1000, lambda d=doc: self._delayed_canvas_retry(d, "1000ms after detecting existing doc"))
        
        for window in app.windows():
            for view in window.views():
                self.connect_view_signals(view)
    
    def stop_capture(self):
        """Stop capturing events"""
        self.poll_timer.stop()
        self._log("Event capture stopped")
    
    def _try_resume_or_create_session(self, doc, context=""):
        """
        Try to resume session from disk, or create new session if not found.
        
        DRY helper used by both:
        - start_capture() for existing documents at plugin startup
        - on_image_created() for newly opened documents
        
        Args:
            doc: Krita document
            context: Description of when this is called (for logging)
        """
        from krita import Krita
        import os
        app = Krita.instance()
        
        session_resumed = False
        
        self._log(f"[RESUME-1] ========== RESUME/CREATE SESSION ({context}) ==========")
        self._log(f"[RESUME-1a] Document: {doc.name()}")
        
        # Check session_storage availability
        storage_status = "available" if self.session_storage else "None"
        self._log(f"[RESUME-2] SessionStorage: {storage_status}")
        
        if self.session_storage:
            try:
                filepath = doc.fileName()
                
                filepath_status = filepath if filepath else "None (unsaved document)"
                self._log(f"[RESUME-3] Document filepath: {filepath_status}")
                
                if filepath:  # Existing file (not a new unsaved document)
                    # Check if file exists on disk
                    file_exists = os.path.exists(filepath)
                    self._log(f"[RESUME-4] File exists on disk: {file_exists}")
                    
                    if not file_exists:
                        self._log(f"[RESUME-4a] ⚠️  File doesn't exist yet (might be newly created)")
                    
                    # Generate session key for this file
                    session_key = self.session_storage.get_session_key_for_file(filepath)
                    
                    key_status = f"{session_key[:16]}..." if session_key else "None"
                    self._log(f"[RESUME-5] Session key generated: {key_status}")
                    
                    if session_key:
                        # Check if session file exists on disk
                        session_file_path = self.session_storage._get_session_filepath(session_key)
                        session_file_exists = os.path.exists(session_file_path)
                        self._log(f"[RESUME-6] Session file exists: {session_file_exists}")
                        self._log(f"[RESUME-6a] Session file path: {session_file_path}")
                        
                        # Try to load session from disk
                        session_json = self.session_storage.load_session(session_key)
                        
                        json_status = f"{len(session_json)} bytes" if session_json else "None (not found)"
                        self._log(f"[RESUME-7] Session JSON loaded: {json_status}")
                        
                        if session_json:
                            # Resume existing session
                            self._log(f"[RESUME-8] ✓ Found persisted session, importing...")
                            
                            # Show snippet of JSON for debugging
                            json_snippet = session_json[:200] if len(session_json) > 200 else session_json
                            self._log(f"[RESUME-8a] JSON snippet: {json_snippet}...")
                            
                            session = self.session_manager.import_session(doc, session_json)
                            
                            if session:
                                self._log(f"[RESUME-9] ✅ Session resumed: {session.id} (events: {session.event_count})")
                                session_resumed = True
                            else:
                                self._log(f"[RESUME-9] ❌ Session import failed (import_session returned None)")
                        else:
                            self._log(f"[RESUME-8] No persisted session found (first time opening this file)")
                            
                            # List all session files to help debug
                            all_sessions = self.session_storage.list_sessions()
                            self._log(f"[RESUME-8a] Total session files on disk: {len(all_sessions)}")
                            if all_sessions:
                                self._log(f"[RESUME-8b] Session files: {all_sessions[:5]}...")  # Show first 5
                    else:
                        self._log(f"[RESUME-5] ❌ Could not generate session key (file doesn't exist?)")
                else:
                    self._log(f"[RESUME-4] Unsaved document, skipping resume attempt")
                
            except Exception as e:
                self._log(f"[RESUME-ERROR] ❌ Error during resumption: {e}")
                import traceback
                self._log(f"[RESUME-ERROR] Traceback: {traceback.format_exc()}")
        else:
            self._log(f"[RESUME-2] ❌ No SessionStorage available, cannot resume")
        
        # Create new session if resume failed
        if not session_resumed:
            if self.DEBUG_LOG:
                self._log(f"[RESUME-9] Creating NEW session for: {doc.name()}")
            
            try:
                session = self.session_manager.create_session(doc)
                
                if self.DEBUG_LOG:
                    self._log(f"[RESUME-10] ✓ Session created: {session.id}")
                
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
                    if self.DEBUG_LOG:
                        self._log(f"[RESUME-11] ✓ Metadata set")
                except Exception as e:
                    self._log(f"[RESUME-11] Error setting metadata: {e}")
            except Exception as e:
                self._log(f"[RESUME-10] ❌ ERROR creating session: {e}")
                import traceback
                self._log(f"[RESUME-10] Traceback: {traceback.format_exc()}")
        
        return session_resumed
    
    def _persist_session(self, doc, session, context="unknown"):
        """
        Persist session to disk.
        
        DRY helper called when session should be saved:
        - on_image_saved() - when user saves file (Ctrl+S)
        - on_image_closed() - when user closes file
        
        Args:
            doc: Krita document
            session: CHMSession to persist
            context: Description of when this is called (for logging)
        """
        if not self.session_storage:
            self._log(f"[PERSIST-{context}] ❌ No SessionStorage available")
            return
        
        try:
            self._log(f"[PERSIST-1] ========== PERSIST SESSION ({context}) ==========")
            self._log(f"[PERSIST-2] Session ID: {session.id}, Events: {session.event_count}")
            
            filepath = doc.fileName()
            
            if not filepath:
                self._log(f"[PERSIST-3] ⚠️  Document has no filepath (unsaved), skipping")
                return
            
            self._log(f"[PERSIST-3] Document: {doc.name()}")
            self._log(f"[PERSIST-3a] Filepath: {filepath}")
            
            # Generate session key for this file
            session_key = self.session_storage.get_session_key_for_file(filepath)
            
            if not session_key:
                self._log(f"[PERSIST-4] ❌ Could not generate session key")
                return
            
            key_snippet = f"{session_key[:16]}..."
            self._log(f"[PERSIST-4] Session key: {key_snippet}")
            
            # Export session to JSON using session_manager helper
            self._log(f"[PERSIST-5] Serializing session...")
            session_json = self.session_manager.session_to_json(session)
            
            if not session_json:
                self._log(f"[PERSIST-6] ❌ Serialization failed")
                return
            
            json_size = len(session_json)
            self._log(f"[PERSIST-6] ✓ Serialized: {json_size} bytes")
            
            # Save to disk using session key as filename
            self._log(f"[PERSIST-7] Saving to disk...")
            success = self.session_storage.save_session(session_key, session_json)
            
            if success:
                session_file_path = self.session_storage._get_session_filepath(session_key)
                self._log(f"[PERSIST-8] ✅ SAVED SUCCESSFULLY!")
                self._log(f"[PERSIST-8a] File: {session_file_path}")
                self._log(f"[PERSIST-8b] Session ID: {session.id}")
                self._log(f"[PERSIST-8c] Events saved: {session.event_count}")
            else:
                self._log(f"[PERSIST-8] ❌ Save failed")
                
        except Exception as e:
            self._log(f"[PERSIST-ERROR] ❌ Exception: {e}")
            import traceback
            self._log(f"[PERSIST-ERROR] Traceback: {traceback.format_exc()}")
    
    def _install_canvas_event_filter(self):
        """
        Install event filter on canvas widget for direct stroke detection.
        
        This is a workaround for Krita's strokeBegin/strokeEnd signals
        not being accessible through Python SIP wrappers.
        """
        if self.DEBUG_LOG:
            self._log("=== ATTEMPTING TO INSTALL CANVAS EVENT FILTER ===")
        
        try:
            app = Krita.instance()
            active_window = app.activeWindow()
            
            if not active_window:
                self._log("No active window - will retry canvas filter on view creation")
                return False
            
            if self.DEBUG_LOG:
                self._log(f"Active window found: {active_window}")
            
            # Get the Qt window widget
            qwindow = active_window.qwindow()
            if not qwindow:
                self._log("No qwindow available - canvas filter unavailable")
                return False
            
            if self.DEBUG_LOG:
                self._log(f"QWindow found: {type(qwindow)}")
                # List all child widgets to see what's available
                all_children = qwindow.findChildren(QObject)
                self._log(f"Total child objects in window: {len(all_children)}")
                
                # Look for OpenGL widgets
                opengl_widgets = qwindow.findChildren(QOpenGLWidget)
                self._log(f"QOpenGLWidget children found: {len(opengl_widgets)}")
                
                # Try to find ANY widget type that might be the canvas
                from PyQt5.QtWidgets import QWidget
                all_widgets = qwindow.findChildren(QWidget)
                self._log(f"Total QWidget children: {len(all_widgets)}")
                
                # Log first few widget types
                widget_types = {}
                for i, w in enumerate(all_widgets[:20]):  # First 20
                    wtype = type(w).__name__
                    widget_types[wtype] = widget_types.get(wtype, 0) + 1
                self._log(f"Widget types found: {widget_types}")
            
            # Find ALL canvas widgets (there are multiple)
            all_canvases = qwindow.findChildren(QOpenGLWidget)
            
            if not all_canvases:
                self._log("❌ No QOpenGLWidget children found - using fallback polling")
                return False
            
            # BFROS FIX: Install filter on ALL canvases, but prioritize the largest visible one
            installed_count = 0
            main_canvas_found = False
            
            # BFROS: Check if filter is still alive (Python GC issue check)
            if self.DEBUG_LOG:
                #self._log(f"[BFROS] Canvas filter object: {self.canvas_event_filter}")
                
                #self._log(f"[BFROS] Filter events received so far: {self.canvas_event_filter.event_count}")
                
                # BFROS: Search for ALL possible input widgets (not just QOpenGLWidget)
                from PyQt5.QtWidgets import QWidget
                all_widgets = qwindow.findChildren(QWidget)
                #self._log(f"[BFROS] Searching {len(all_widgets)} widgets for input-enabled ones...")
                
                input_widgets = []
                for widget in all_widgets:
                    # Look for widgets that accept mouse/tablet input
                    if widget.isEnabled() and widget.testAttribute(Qt.WA_InputMethodEnabled) or True:  # Check all for now
                        widget_info = f"{type(widget).__name__} size={widget.width()}x{widget.height()} visible={widget.isVisible()}"
                        # Look for widgets close to document size (500x500)
                        #if 400 < widget.width() < 600 and 400 < widget.height() < 600:
                        input_widgets.append((widget, widget_info))
                        #self._log(f"[BFROS] ★ POTENTIAL DOCUMENT CANVAS: {widget_info}")
                
                if not input_widgets:
                    self._log(f"[BFROS] No widgets matching document size (500x500) found!")
            
            for i, canvas in enumerate(all_canvases):
                if self.DEBUG_LOG:
                    self._log(f"QOpenGLWidget #{i}: visible={canvas.isVisible()}, enabled={canvas.isEnabled()}, size={canvas.width()}x{canvas.height()}")
                
                # BFROS: Remove old filter first (prevent multiple installs on same object)
                canvas.removeEventFilter(self.canvas_event_filter)
                
                # Install filter on ALL canvases (we don't know which is the drawing canvas)
                canvas.installEventFilter(self.canvas_event_filter)
                installed_count += 1
                
                if self.DEBUG_LOG:
                    self._log(f"  → Filter installed on canvas #{i}")
                
                # Track if we found a likely main canvas (large, visible, enabled)
                if canvas.isVisible() and canvas.isEnabled() and canvas.width() > 200:
                    main_canvas_found = True
                    if self.DEBUG_LOG:
                        self._log(f"  ↑ This looks like the main drawing canvas (filter should receive events here)")
            
            if installed_count > 0:
                self.canvas_filter_installed = True
                self._log(f"✓ Canvas event filter installed on {installed_count} canvas(es)")
                
                if not main_canvas_found and self.DEBUG_LOG:
                    self._log("⚠️  Warning: No large visible canvas found - main canvas may not be ready yet")
                
                if self.DEBUG_LOG:
                    self._log("=== EVENT FILTER INSTALLATION COMPLETE ===")
                return True
            else:
                self._log("❌ Could not install canvas filter - using fallback polling")
                return False
                
        except Exception as e:
            self._log(f"❌ Could not install canvas event filter: {e}")
            import traceback
            self._log(f"Traceback: {traceback.format_exc()}")
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
        
        ROAA APPROACH: Try ALL possible methods systematically:
        1. view.strokeBegin/strokeEnd (official API - try it!)
        2. canvas.pointerPress/pointerRelease (official Canvas API)
        3. Event filter fallback (if signals don't work)
        """
        view_id = id(view)
        
        if view_id in self.connected_views:
            return  # Already connected
        
        if self.DEBUG_LOG:
            self._log(f"[ROAA] View created: {view_id}, type: {type(view)}")
        
        stroke_method_found = False
        
        # APPROACH 1: Try view.strokeBegin/strokeEnd (SIMPLEST - official Krita API)
        if self.DEBUG_LOG:
            self._log(f"[ROAA] Approach 1: Trying view.strokeBegin/strokeEnd signals...")
        
        try:
            if hasattr(view, 'strokeBegin') and hasattr(view, 'strokeEnd'):
                view.strokeBegin.connect(lambda: self.on_stroke_begin(view))
                view.strokeEnd.connect(lambda: self.on_stroke_end(view))
                stroke_method_found = True
                if self.DEBUG_LOG:
                    self._log(f"[ROAA] ✓ SUCCESS: view.strokeBegin/strokeEnd connected!")
            else:
                if self.DEBUG_LOG:
                    self._log(f"[ROAA] ✗ view.strokeBegin/strokeEnd not available (hasattr failed)")
        except Exception as e:
            if self.DEBUG_LOG:
                self._log(f"[ROAA] ✗ Could not connect view.strokeBegin/strokeEnd: {e}")
        
        # APPROACH 2: Try canvas.pointerPress/pointerRelease (Krita Canvas API)
        if not stroke_method_found:
            if self.DEBUG_LOG:
                self._log(f"[ROAA] Approach 2: Trying canvas.pointerPress/pointerRelease signals...")
            
            try:
                if hasattr(view, 'canvas'):
                    canvas = view.canvas()
                    if canvas:
                        if self.DEBUG_LOG:
                            self._log(f"[ROAA] Canvas object: {type(canvas)}, has pointerPress: {hasattr(canvas, 'pointerPress')}")
                        
                        if hasattr(canvas, 'pointerPress') and hasattr(canvas, 'pointerRelease'):
                            canvas.pointerPress.connect(lambda: self._on_canvas_pointer_press(view))
                            canvas.pointerRelease.connect(lambda: self._on_canvas_pointer_release(view))
                            stroke_method_found = True
                            if self.DEBUG_LOG:
                                self._log(f"[ROAA] ✓ SUCCESS: canvas.pointerPress/pointerRelease connected!")
                        else:
                            if self.DEBUG_LOG:
                                self._log(f"[ROAA] ✗ canvas.pointerPress/pointerRelease not available")
            except Exception as e:
                if self.DEBUG_LOG:
                    self._log(f"[ROAA] ✗ Could not connect canvas signals: {e}")
        
        # APPROACH 3: Event filter fallback (if signals don't work)
        if not stroke_method_found:
            if self.DEBUG_LOG:
                self._log(f"[ROAA] Approach 3: Falling back to Qt event filter...")
            
            if not self.canvas_filter_installed:
                self._install_canvas_event_filter()
        
        # Connect viewChanged for basic activity tracking
        try:
            if hasattr(view, 'viewChanged'):
                view.viewChanged.connect(lambda: self.on_view_changed(view))
        except:
            pass
        
        self.connected_views.add(view_id)
        
        method_used = "strokeBegin/strokeEnd" if stroke_method_found else "event filter fallback"
        if self.DEBUG_LOG:
            self._log(f"[ROAA] ✓ View {view_id} configured (using: {method_used})")
    
    def on_image_created(self):
        """Handler for new document creation or file open - tries to resume session"""
        self._log("[SESSION-FLOW] ========== on_image_created SIGNAL FIRED ==========")
        
        app = Krita.instance()
        doc = app.activeDocument()
        
        if not doc:
            self._log("[SESSION-FLOW] ❌ No activeDocument!")
            return
        
        doc_name = doc.name()
        doc_filepath = doc.fileName()
        doc_id = id(doc)
        
        self._log(f"[SESSION-FLOW-1] Document: {doc_name}")
        self._log(f"[SESSION-FLOW-2] Filepath: {doc_filepath if doc_filepath else 'None (unsaved)'}")
        self._log(f"[SESSION-FLOW-3] Document ID: {doc_id}")
        
        # Check if session already exists in memory
        has_session = self.session_manager.has_session(doc)
        self._log(f"[SESSION-FLOW-4] Session exists in memory: {has_session}")
        
        if has_session:
            existing_session = self.session_manager.get_session(doc)
            event_count = existing_session.event_count if existing_session else "N/A"
            self._log(f"[SESSION-FLOW-5] ⚠️  Session already in memory, skipping resume (events: {event_count})")
        else:
            self._log(f"[SESSION-FLOW-5] No session in memory, will try to resume or create...")
            self._try_resume_or_create_session(doc, "imageCreated signal")
        
        if self.DEBUG_LOG:
            try:
                self._log(f"[BFROS] Document details: {doc.width()}x{doc.height()}")
            except Exception as e:
                self._log(f"[BFROS] Error getting document size: {e}")
        
        # BFROS FIX #3: Try IMMEDIATELY after document creation
        if self.DEBUG_LOG:
            self._log("[BFROS] Attempting canvas filter installation IMMEDIATELY after imageCreated")
        self._install_canvas_event_filter()
        
        # BFROS FIX #3: Also try with delays (canvas might need time to initialize)
        QTimer.singleShot(500, lambda: self._delayed_canvas_retry(doc, "500ms delay"))
        QTimer.singleShot(1000, lambda: self._delayed_canvas_retry(doc, "1000ms delay"))
        QTimer.singleShot(2000, lambda: self._delayed_canvas_retry(doc, "2000ms delay"))
        
        # Connect signals for this document
        self.connect_document_signals(doc)
        
        self._log("[SESSION-FLOW] ========== on_image_created COMPLETE ==========")

    
    def on_image_closed(self):
        """Handler for document close"""
        if self.DEBUG_LOG:
            self._log("[BFROS] ===== on_image_closed SIGNAL FIRED =====")
        
        # CRITICAL: Persist session before document is gone
        # Note: We need to get the document reference from active documents
        # before it's fully closed
        app = Krita.instance()
        
        # Try to find the document that's being closed
        # This is tricky because the signal doesn't pass the doc reference
        # and activeDocument() might already be None
        for doc in app.documents():
            session = self.session_manager.get_session(doc)
            if session:
                self._persist_session(doc, session, "on_close")
        
        self._log("Document closed event received")
    
    def on_image_saved(self):
        """Handler for document save"""
        if self.DEBUG_LOG:
            self._log("[BFROS] ===== on_image_saved SIGNAL FIRED =====")
        
        app = Krita.instance()
        doc = app.activeDocument()
        
        if not doc:
            return
        
        self._log(f"Document saved: {doc.name()}")
        
        # CRITICAL BUG#002 FIX: Migrate session key if document was just saved for first time
        # When a new unsaved document is saved, the key changes from "unsaved_ID" to filepath
        # We need to migrate the session from old key to new key to prevent session loss
        filepath = doc.fileName()
        if filepath:
            unsaved_key = f"unsaved_{id(doc)}"
            if self.session_manager.migrate_session_key(unsaved_key, filepath):
                if self.DEBUG_LOG:
                    self._log(f"[SAVE-MIGRATE] ✅ Session migrated to filepath: {filepath}")
        
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
                
                # CRITICAL: Persist session to disk when file is saved
                self._persist_session(doc, session, "on_save")
                
            except Exception as e:
                self._log(f"Error updating metadata on save: {e}")
        else:
            if self.DEBUG_LOG:
                self._log(f"[SAVE-ERROR] ⚠️ No session found for {doc.name()} after save (migration may have failed)")
    
    def on_view_created(self, view):
        """Handler for new view creation"""
        if self.DEBUG_LOG:
            self._log(f"[BFROS] ===== on_view_created SIGNAL FIRED (view: {id(view)}) =====")
        
        self._log(f"View created: {id(view)}")
        
        # BFROS: Check if this view has a document
        try:
            view_doc = view.document()
            if view_doc and self.DEBUG_LOG:
                self._log(f"[BFROS] View's document: {view_doc.name()} ({view_doc.width()}x{view_doc.height()})")
        except Exception as e:
            if self.DEBUG_LOG:
                self._log(f"[BFROS] Error getting view's document: {e}")
        
        # BFROS FIX #3: Try canvas filter when view is created (canvas might be ready now)
        if self.DEBUG_LOG:
            self._log("[BFROS] View created - attempting canvas filter installation")
        self._install_canvas_event_filter()
        
        # Also try with small delay (view might need time to fully initialize)
        QTimer.singleShot(200, lambda: self._delayed_canvas_retry_simple("200ms after viewCreated"))
        QTimer.singleShot(500, lambda: self._delayed_canvas_retry_simple("500ms after viewCreated"))
        QTimer.singleShot(1000, lambda: self._delayed_canvas_retry_simple("1000ms after viewCreated"))
        QTimer.singleShot(2000, lambda: self._delayed_canvas_retry_simple("2000ms after viewCreated"))
        
        self.connect_view_signals(view)
    
    def _delayed_canvas_retry(self, doc, delay_label):
        """
        Retry canvas filter installation after a delay.
        Canvas widget might not be fully initialized immediately after imageCreated.
        """
        if self.DEBUG_LOG:
            self._log(f"[BFROS] Retrying canvas filter installation ({delay_label})")
        
        # Check document size to see if canvas should exist
        try:
            doc_width = doc.width()
            doc_height = doc.height()
            self._log(f"[BFROS] Document size: {doc_width}x{doc_height} (expected canvas of this size)")
        except:
            pass
        
        result = self._install_canvas_event_filter()
        
        if result and self.DEBUG_LOG:
            self._log(f"[BFROS] ✓ Canvas filter installed successfully at {delay_label}")
    
    def _delayed_canvas_retry_simple(self, delay_label):
        """Simpler delayed retry without document reference"""
        if self.DEBUG_LOG:
            self._log(f"[BFROS] Retrying canvas filter installation ({delay_label})")
        self._install_canvas_event_filter()
    
    def on_view_changed(self, view):
        """Handler for view changes (zoom, pan, or potential drawing activity)"""
        # This fires on zoom/pan/rotation, but also potentially during drawing
        # We can use this as a fallback to detect activity
        doc = view.document()
        if not doc:
            return
        
        # BFROS FIX #3: Try to install canvas filter on view change (canvas might now be ready)
        if not self.canvas_filter_installed:
            if self.DEBUG_LOG:
                self._log("[BFROS] View changed - retrying canvas filter")
            self._install_canvas_event_filter()
        
        # Check if document has been modified (indicates drawing/editing occurred)
        if doc.modified():
            session = self.session_manager.get_session(doc)
            if session:
                # Document was modified - record generic activity
                # This is a fallback since we don't have strokeBegin/strokeEnd
                pass  # For now, just know activity happened
    
    def _on_canvas_pointer_press(self, view):
        """Handler for canvas pointer press (Approach 2)"""
        if not self.stroke_in_progress:
            self.stroke_in_progress = True
            self.stroke_start_time = time.time()
            if self.DEBUG_LOG:
                self._log("[ROAA-Approach2] Stroke began (canvas.pointerPress)")
    
    def _on_canvas_pointer_release(self, view):
        """Handler for canvas pointer release (Approach 2)"""
        if self.stroke_in_progress:
            self.stroke_in_progress = False
            self._record_stroke_for_view(view, method="canvas.pointerRelease")
    
    def on_stroke_begin(self, view):
        """Handler for stroke beginning (Approach 1 - view.strokeBegin)"""
        # Query current brush (not included in stroke signals)
        try:
            app = Krita.instance()
            # Note: currentBrush() may not exist in all Krita versions
            # This is a best-effort capture
            self.current_brush_name = "Unknown Brush"
            if self.DEBUG_LOG:
                self._log("[ROAA-Approach1] Stroke began (view.strokeBegin)")
        except Exception as e:
            self._log(f"Error in stroke_begin: {e}")
    
    def on_stroke_end(self, view):
        """Handler for stroke ending (Approach 1 - view.strokeEnd)"""
        self._record_stroke_for_view(view, method="view.strokeEnd")
    
    def _record_stroke_for_view(self, view, method="unknown"):
        """Common stroke recording logic for all approaches"""
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
                duration = time.time() - self.stroke_start_time if hasattr(self, 'stroke_start_time') else 0
                self._log(f"[ROAA-{method}] ✓ Stroke recorded (duration: {duration:.2f}s, total: {session.event_count})")
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
        Poll for changes (PRIMARY stroke detection method).
        Detects: layer changes, document modifications (strokes)
        """
        app = Krita.instance()
        doc = app.activeDocument()
        
        if self.DEBUG_LOG:
            # Log every 10th poll to confirm it's running
            if not hasattr(self, '_poll_count'):
                self._poll_count = 0
            self._poll_count += 1
            if self._poll_count % 10 == 0:
                doc_name = doc.name() if doc else "None"
                self._log(f"[POLLING] Poll #{self._poll_count}, active document: {doc_name}")
        
        if not doc:
            return
        
        doc_id = id(doc)
        
        # Poll layer changes
        self.poll_layer_changes(doc, doc_id)
        
        # BUG#003 FIX: Process pending import checks (delayed paste detection)
        self.poll_pending_imports(doc, doc_id)
        
        # Poll document modification (PRIMARY stroke detection)
        self.poll_document_modification(doc, doc_id)
    
    def poll_layer_changes(self, doc, doc_id):
        """Poll for layer changes"""
        try:
            current_layers = set()
            all_nodes = []  # BFROS: Track all nodes for debugging
            for node in doc.topLevelNodes():
                current_layers.add(node.name())
                all_nodes.append((node.name(), node.type()))
            
            # BFROS: Log all layers periodically for debugging
            if self.DEBUG_LOG and not hasattr(self, '_layer_debug_count'):
                self._layer_debug_count = 0
            if self.DEBUG_LOG:
                self._layer_debug_count += 1
                if self._layer_debug_count % 20 == 0:  # Every 20 polls
                    self._log(f"[LAYER-DEBUG] Total layers: {len(all_nodes)}")
                    for name, ltype in all_nodes:
                        self._log(f"[LAYER-DEBUG]   - {name} (type: {ltype})")
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
                            layer_type = node.type()
                            session.record_layer_added(
                                layer_id=str(id(node)),
                                layer_type=layer_type
                            )
                            self._log(f"[LAYER-ADD] Layer added: {layer_name} (type: {layer_type})")
                            
                            # BUG#006 FIX: Enhanced diagnostic logging for layer detection
                            if self.DEBUG_LOG:
                                try:
                                    bounds = node.bounds()
                                    bounds_info = f"{bounds.width()}x{bounds.height()}" if bounds else "None"
                                    self._log(f"[BUG006-DIAG] Layer: {layer_name}")
                                    self._log(f"[BUG006-DIAG]   Type: {layer_type}")
                                    self._log(f"[BUG006-DIAG]   Bounds: {bounds_info}")
                                    self._log(f"[BUG006-DIAG]   Visible: {node.visible()}")
                                except Exception as e:
                                    self._log(f"[BUG006-DIAG] Could not get diagnostics: {e}")
                            
                            # BFROS FIX: Detect imports by checking if layer has pixel data
                            # Copy-paste creates "paintlayer" with imported pixels, NOT "filelayer"!
                            # We need to detect ANY layer that might contain imported content
                            is_import = False
                            import_type = "unknown"
                            
                            # Method 1: Check if it's a file layer (File → Import Layer)
                            if layer_type == "filelayer":
                                is_import = True
                                import_type = "file_layer"
                                self._log(f"[IMPORT-DETECT] File layer: {layer_name}")
                            
                            # BUG#006 FIX: Method 1b - Check if it's a vector layer (SVG, etc.)
                            elif layer_type == "vectorlayer":
                                is_import = True
                                import_type = "vector_layer"
                                self._log(f"[IMPORT-DETECT] Vector layer: {layer_name}")
                            
                            # BUG#006 FIX: Method 1c - Check if it's a group layer (complex imports like SVG)
                            elif layer_type == "grouplayer":
                                # Group layers can be created by importing complex files
                                # Check if the group name suggests it's an import
                                is_import = True
                                import_type = "group_layer"
                                self._log(f"[IMPORT-DETECT] Group layer (possible import): {layer_name}")
                            
                            # Method 2: Check if it's a paint layer with suspicious characteristics
                            # (likely pasted image)
                            elif layer_type == "paintlayer":
                                # BUG#003 FIX: Paste may create layer before pixels load
                                # Check immediately, but also add to pending checks for delayed verification
                                try:
                                    # Get layer bounds to see if it has content
                                    bounds = node.bounds()
                                    if bounds and bounds.width() > 0 and bounds.height() > 0:
                                        # Layer has content immediately - definitely imported
                                        is_import = True
                                        import_type = "paste_immediate"
                                        self._log(f"[IMPORT-DETECT] Paint layer with immediate content: {layer_name} ({bounds.width()}x{bounds.height()})")
                                    else:
                                        # No bounds yet - may be paste operation loading pixels
                                        # Add to pending checks for delayed verification
                                        self._log(f"[IMPORT-DETECT] Paint layer with no bounds yet: {layer_name} - adding to pending checks")
                                        
                                        # BUG#005 FIX: Use doc_key for pending checks
                                        doc_key = self._get_doc_key(doc)
                                        
                                        if doc_key not in self.pending_import_checks:
                                            self.pending_import_checks[doc_key] = []
                                        
                                        self.pending_import_checks[doc_key].append({
                                            'layer_name': layer_name,
                                            'node': node,
                                            'checks_remaining': self.IMPORT_CHECK_DELAY
                                        })
                                except Exception as e:
                                    self._log(f"[IMPORT-DETECT] Could not check bounds: {e}")
                            
                            # BUG#006 FIX: Method 3 - Extension-based fallback detection
                            # If not detected by layer type, check layer name for image extensions
                            if not is_import:
                                IMPORT_EXTENSIONS = [
                                    '.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', 
                                    '.bmp', '.tif', '.tiff', '.psd', '.ora', '.exr'
                                ]
                                layer_lower = layer_name.lower()
                                
                                for ext in IMPORT_EXTENSIONS:
                                    if ext in layer_lower:
                                        is_import = True
                                        import_type = "file_import_by_extension"
                                        if self.DEBUG_LOG:
                                            self._log(f"[IMPORT-DETECT] Import detected by extension '{ext}' in name: {layer_name}")
                                        break
                            
                            # If detected as import, record it
                            if is_import:
                                # Record as import
                                session.record_import(
                                    file_path=layer_name,  # Use layer name as placeholder
                                    import_type=import_type,
                                    timestamp=time.time()
                                )
                                
                                # BUG#005 FIX: Use doc_key instead of doc_id
                                doc_key = self._get_doc_key(doc)
                                
                                # Register with tracing detector
                                self.tracing_detector.register_import(
                                    doc_key=doc_key,
                                    layer_node=node,
                                    layer_name=layer_name
                                )
                                
                                self._log(f"[IMPORT] ✓ Import detected: {layer_name} (type: {import_type})")
                    except Exception as e:
                        self._log(f"[LAYER-ADD] Error recording layer: {e}")
                        import traceback
                        self._log(f"[LAYER-ADD] Traceback: {traceback.format_exc()}")
        
        # Update cache
        self.layer_cache[doc_id] = current_layers
    
    def poll_pending_imports(self, doc, doc_id):
        """
        BUG#003 FIX: Check pending import detections (delayed paste detection).
        BUG#005 FIX: Uses doc_key for consistency with session manager.
        
        Paste operations may create layers before pixels are loaded.
        This method re-checks layers after a delay to catch late-loading content.
        """
        # BUG#005 FIX: Use doc_key instead of doc_id
        doc_key = self._get_doc_key(doc)
        
        if doc_key not in self.pending_import_checks:
            return
        
        pending = self.pending_import_checks[doc_key]
        if not pending:
            return
        
        session = self.session_manager.get_session(doc)
        if not session:
            return
        
        # Process each pending check
        still_pending = []
        
        for check in pending:
            layer_name = check['layer_name']
            node = check['node']
            checks_remaining = check['checks_remaining']
            
            try:
                # Re-fetch layer to ensure we have current state
                current_node = doc.nodeByName(layer_name)
                if not current_node:
                    self._log(f"[IMPORT-PENDING] Layer disappeared: {layer_name}")
                    continue  # Layer was deleted, skip
                
                # Check if layer now has bounds (pixels loaded)
                bounds = current_node.bounds()
                
                if bounds and bounds.width() > 0 and bounds.height() > 0:
                    # SUCCESS: Layer now has content - register as import!
                    self._log(f"[IMPORT-PENDING] ✓ Delayed detection SUCCESS: {layer_name} ({bounds.width()}x{bounds.height()})")
                    
                    # Record as import
                    session.record_import(
                        file_path=layer_name,
                        import_type="paste_delayed",
                        timestamp=time.time()
                    )
                    
                    # BUG#005 FIX: Use doc_key instead of doc_id
                    doc_key = self._get_doc_key(doc)
                    
                    # Register with tracing detector
                    self.tracing_detector.register_import(
                        doc_key=doc_key,
                        layer_node=current_node,
                        layer_name=layer_name
                    )
                    
                    self._log(f"[IMPORT] ✓ Import detected (delayed): {layer_name} (type: paste_delayed)")
                    # Don't add back to pending - detection complete
                    
                else:
                    # Still no bounds - decrement counter and check again
                    checks_remaining -= 1
                    
                    if checks_remaining > 0:
                        # Still have checks remaining, keep in pending
                        check['checks_remaining'] = checks_remaining
                        still_pending.append(check)
                        
                        if self.DEBUG_LOG and checks_remaining == 1:
                            self._log(f"[IMPORT-PENDING] Layer still empty, last check: {layer_name}")
                    else:
                        # Out of checks - assume it's not an import (manual layer creation)
                        self._log(f"[IMPORT-PENDING] ✗ Layer remained empty, not an import: {layer_name}")
                        
            except Exception as e:
                self._log(f"[IMPORT-PENDING] Error checking {layer_name}: {e}")
        
        # Update pending list
        self.pending_import_checks[doc_key] = still_pending
    
    def poll_document_modification(self, doc, doc_id):
        """
        Poll document modification state to detect drawing activity.
        PRIMARY METHOD per krita-api-research.md (signals unavailable via SIP).
        
        BFROS FIX: Use lightweight thumbnail hash to detect ACTUAL pixel changes.
        The modified() flag is boolean - once True, stays True until save.
        We need to detect when pixels actually change (new strokes).
        
        BUG#008 FIX: Enhanced AFK diagnostic logging to reveal detection logic.
        """
        DEBUG_AFK = True  # Global flag for AFK-specific diagnostic logging
        
        try:
            # AFK-DIAG-1: Entry point
            if DEBUG_AFK and self.DEBUG_LOG:
                if not hasattr(self, '_mod_poll_count'):
                    self._mod_poll_count = 0
                self._mod_poll_count += 1
                
                # Log every 10 polls for AFK diagnostics
                if self._mod_poll_count % 10 == 0:
                    idle_polls = self.polls_without_change.get(doc_id, 0)
                    is_afk = idle_polls >= self.AFK_POLL_THRESHOLD
                    self._log(f"[AFK-DIAG-1] === POLL #{self._mod_poll_count} === idle_polls={idle_polls}, is_afk={is_afk}, threshold={self.AFK_POLL_THRESHOLD}")
            
            current_modified = doc.modified()
            previous_modified = self.doc_modified_state.get(doc_id, False)
            
            # AFK-DIAG-2: Modified state
            if DEBUG_AFK and self.DEBUG_LOG and self._mod_poll_count % 10 == 0:
                self._log(f"[AFK-DIAG-2] Modified: current={current_modified}, previous={previous_modified}")
            
            # BFROS FIX: Detect ACTUAL content changes using lightweight thumbnail hash
            # This solves the "modified flag stays True" problem
            
            should_record = False
            
            # Only check for changes if document is modified
            if current_modified:
                try:
                    # AFK-DIAG-3: Document is modified, checking for content changes
                    if DEBUG_AFK and self.DEBUG_LOG and self._mod_poll_count % 10 == 0:
                        self._log(f"[AFK-DIAG-3] Doc is modified, checking for actual content changes...")
                    
                    # Get lightweight hash of document content
                    # Use thumbnail() method - fast and sufficient for change detection
                    import hashlib
                    
                    # Get 100x100 thumbnail (fast to compute)
                    thumbnail = doc.thumbnail(100, 100)
                    
                    if DEBUG_AFK and self.DEBUG_LOG and self._mod_poll_count % 10 == 0:
                        thumb_status = "exists" if thumbnail else "None"
                        self._log(f"[AFK-DIAG-4] Thumbnail retrieved: {thumb_status}")
                    
                    if thumbnail:
                        # DIAGNOSTIC: Check if metadata-based hash is actually changing
                        metadata_hash = f"{thumbnail.width()}x{thumbnail.height()}x{thumbnail.byteCount()}"
                        
                        if DEBUG_AFK and self.DEBUG_LOG and self._mod_poll_count % 10 == 0:
                            self._log(f"[AFK-DIAG-5] Thumbnail metadata: {metadata_hash}")
                        
                        # ACTUAL FIX: Hash the pixel data, not just metadata
                        # Metadata (width/height/byteCount) is CONSTANT for same thumbnail size!
                        try:
                            # Get actual pixel data from thumbnail
                            from PyQt5.QtCore import QBuffer, QIODevice, QByteArray
                            
                            buffer = QBuffer()
                            buffer.open(QIODevice.WriteOnly)
                            thumbnail.save(buffer, "PNG")  # Save to memory buffer
                            thumbnail_bytes = buffer.data().data()  # Get bytes
                            
                            # Hash the actual pixel content
                            thumbnail_hash = hashlib.md5(thumbnail_bytes).hexdigest()[:16]
                            
                            if DEBUG_AFK and self.DEBUG_LOG and self._mod_poll_count % 10 == 0:
                                self._log(f"[AFK-DIAG-6] Pixel content hash: {thumbnail_hash}")
                            
                        except Exception as hash_error:
                            # Fallback to metadata hash if pixel hashing fails
                            thumbnail_hash = metadata_hash
                            if DEBUG_AFK and self.DEBUG_LOG:
                                self._log(f"[AFK-DIAG-6-ERROR] Pixel hash failed, using metadata: {hash_error}")
                        
                        previous_hash = self.doc_content_hash.get(doc_id)
                        
                        # AFK-DIAG-7: Hash comparison
                        if DEBUG_AFK and self.DEBUG_LOG and self._mod_poll_count % 10 == 0:
                            match_status = "MATCH" if previous_hash == thumbnail_hash else "DIFFERENT"
                            prev_display = previous_hash[:8] if previous_hash else 'None'
                            curr_display = thumbnail_hash[:8] if thumbnail_hash else 'None'
                            self._log(f"[AFK-DIAG-7] Hash comparison: prev={prev_display}... vs curr={curr_display}... → {match_status}")
                        
                        # Detect ACTUAL change in content
                        if previous_hash != thumbnail_hash:
                            # Content changed - reset AFK counter and record stroke
                            self.polls_without_change[doc_id] = 0
                            should_record = True
                            self.doc_content_hash[doc_id] = thumbnail_hash
                            
                            if DEBUG_AFK and self.DEBUG_LOG:
                                self._log(f"[AFK-DIAG-8] ✓ CONTENT CHANGED - Stroke detected, AFK counter RESET to 0")
                        else:
                            # Content unchanged - increment AFK counter
                            old_count = self.polls_without_change.get(doc_id, 0)
                            self.polls_without_change[doc_id] = old_count + 1
                            new_count = self.polls_without_change[doc_id]
                            
                            # AFK-DIAG-9: Log AFK counter increments (frequent early, then every 10)
                            if DEBUG_AFK and self.DEBUG_LOG and (new_count <= 5 or new_count % 10 == 0):
                                idle_secs = new_count * 0.5  # 500ms per poll = 0.5 seconds
                                is_now_afk = new_count >= self.AFK_POLL_THRESHOLD
                                afk_status = "AFK" if is_now_afk else "active"
                                self._log(f"[AFK-DIAG-9] Content unchanged - idle_polls={new_count} ({idle_secs}s idle) - Status: {afk_status}")
                    
                except Exception as e:
                    # Fallback: If thumbnail fails, use transition detection only
                    if current_modified and not previous_modified:
                        should_record = True
                        if self.DEBUG_LOG:
                            self._log(f"[BFROS-STROKE] Fallback: Transition detected (thumbnail failed: {e})")
            
            # Alternative simple approach: Only detect transition False → True
            # This catches first stroke after save, but misses subsequent strokes
            # We'll use this as additional trigger
            elif current_modified and not previous_modified:
                should_record = True
                if self.DEBUG_LOG:
                    self._log(f"[BFROS-STROKE] ✓ Transition detected (False → True)")
            
            # BUG#008 FIX v2: Simple poll-based drawing time (excludes AFK)
            # Count active polls instead of time calculations - simpler and less error-prone
            session = self.session_manager.get_session(doc)
            
            # BFROS DIAG-1: Check if session exists
            if DEBUG_AFK and self.DEBUG_LOG and self._mod_poll_count % 10 == 0:
                if session:
                    self._log(f"[BFROS-DT-1] Session exists: {session.id[:16]}...")
                else:
                    self._log(f"[BFROS-DT-1] ❌ No session found for doc_id={doc_id}")
            
            if session:
                idle_polls = self.polls_without_change.get(doc_id, 0)
                is_afk_now = idle_polls >= self.AFK_POLL_THRESHOLD
                
                # BFROS DIAG-2: Check AFK status
                if DEBUG_AFK and self.DEBUG_LOG and self._mod_poll_count % 10 == 0:
                    self._log(f"[BFROS-DT-2] idle_polls={idle_polls}, is_afk={is_afk_now}, threshold={self.AFK_POLL_THRESHOLD}")
                
                # Simple approach: Increment poll counter when not AFK
                if not is_afk_now:
                    # Increment active poll counter
                    old_count = self.active_poll_count.get(doc_id, 0)
                    self.active_poll_count[doc_id] = old_count + 1
                    
                    # Calculate drawing time from poll count (500ms per poll)
                    # Every 2 polls = 1 second, so update session every 2 polls
                    if self.active_poll_count[doc_id] % 2 == 0:
                        # Add 1 second to drawing time (2 polls × 500ms = 1s)
                        current_dt = session.drawing_time_secs if hasattr(session, 'drawing_time_secs') else 0
                        
                        if DEBUG_AFK and self.DEBUG_LOG and self._mod_poll_count % 10 == 0:
                            poll_count = self.active_poll_count[doc_id]
                            self._log(f"[BFROS-DT-3] Active polls={poll_count}, adding 1s (current={current_dt}s)")
                        
                        session.add_drawing_time(1)
                        
                        if DEBUG_AFK and self.DEBUG_LOG and self._mod_poll_count % 10 == 0:
                            new_dt = session.drawing_time_secs if hasattr(session, 'drawing_time_secs') else 0
                            self._log(f"[BFROS-DT-4] ✓ Drawing time updated: {new_dt}s")
                    else:
                        # Odd poll, just log the counter increment
                        if DEBUG_AFK and self.DEBUG_LOG and self._mod_poll_count % 10 == 0:
                            poll_count = self.active_poll_count[doc_id]
                            self._log(f"[BFROS-DT-3] Active polls={poll_count} (waiting for next poll to add 1s)")
                else:
                    # User is AFK - don't increment poll counter
                    if DEBUG_AFK and self.DEBUG_LOG and self._mod_poll_count % 20 == 0:
                        self._log(f"[DRAWING-TIME] User AFK - not incrementing active poll counter")
            
            # AFK-DIAG-10: Session metrics check
            if DEBUG_AFK and self.DEBUG_LOG and self._mod_poll_count % 10 == 0:
                if session:
                    duration = session.duration_secs if hasattr(session, 'duration_secs') else 'N/A'
                    drawing_time = session.drawing_time_secs if hasattr(session, 'drawing_time_secs') else 'N/A'
                    event_count = session.event_count if hasattr(session, 'event_count') else 'N/A'
                    idle_polls = self.polls_without_change.get(doc_id, 0)
                    is_afk_now = idle_polls >= self.AFK_POLL_THRESHOLD
                    self._log(f"[AFK-DIAG-10] Session: duration={duration}s, drawing={drawing_time}s, events={event_count}, idle_polls={idle_polls}, is_afk={is_afk_now}")
            
            if should_record:
                import time
                current_time = time.time()  # BFROS FIX: Define current_time before use
                
                # Check if user was AFK and is now resuming
                idle_polls = self.polls_without_change.get(doc_id, 0)
                was_afk = idle_polls >= self.AFK_POLL_THRESHOLD
                
                if was_afk:
                    # User was AFK, now resuming - log the resumption
                    idle_secs = idle_polls * 0.5  # 500ms per poll
                    if DEBUG_AFK and self.DEBUG_LOG:
                        self._log(f"[AFK-DIAG-11] ▶️  User RESUMED after {idle_polls} polls ({idle_secs}s) AFK")
                
                session = self.session_manager.get_session(doc)
                
                # ROAA FALLBACK: If no session exists, create one NOW (cleaner approach)
                if not session:
                    if self.DEBUG_LOG:
                        self._log(f"[ROAA-FALLBACK] ⚠️  No session found for {doc.name()}, creating on-the-fly...")
                    
                    try:
                        from krita import Krita
                        app = Krita.instance()
                        session = self.session_manager.create_session(doc)
                        
                        # Set metadata
                        import platform
                        session.set_metadata(
                            document_name=doc.name(),
                            canvas_width=doc.width(),
                            canvas_height=doc.height(),
                            krita_version=app.version(),
                            os_info=f"{platform.system()} {platform.release()}"
                        )
                        
                        if self.DEBUG_LOG:
                            self._log(f"[ROAA-FALLBACK] ✓ Emergency session created: {session.id}")
                    except Exception as e:
                        self._log(f"[ROAA-FALLBACK] ❌ Failed to create emergency session: {e}")
                        import traceback
                        self._log(f"[ROAA-FALLBACK] Traceback: {traceback.format_exc()}")
                
                if session:
                    # Record a stroke event (generic since we don't have coordinates)
                    if DEBUG_AFK and self.DEBUG_LOG:
                        self._log(f"[AFK-DIAG-12] 🎨 Stroke detected! Recording to session {session.id}")
                        self._log(f"[AFK-DIAG-12a] Event count BEFORE recording: {session.event_count}")
                    
                    session.record_stroke(
                        x=0.0,  # Placeholder - polling doesn't provide coordinates
                        y=0.0,  # Placeholder
                        pressure=0.5,  # Default
                        brush_name="Unknown"
                    )
                    
                    # Update last stroke time (not used for detection anymore, but kept for future features)
                    self._last_stroke_time[doc_id] = current_time
                    
                    if DEBUG_AFK and self.DEBUG_LOG:
                        self._log(f"[AFK-DIAG-12b] ✓ Stroke recorded! Event count AFTER: {session.event_count}")
                        self._log(f"[AFK-DIAG-12c] Session duration after recording: {session.duration_secs}s")
                    
                    # BUG#005 FIX: Use doc_key instead of doc_id
                    doc_key = self._get_doc_key(doc)
                    
                    # Check for tracing (every N strokes for efficiency)
                    tracing_percentage = self.tracing_detector.check_for_tracing(doc, doc_key, session)
                    if tracing_percentage is not None:
                        self._log(f"[FLOW-2-TRACE] ⚠️  TRACING DETECTED: {tracing_percentage*100:.1f}%")
                else:
                    if self.DEBUG_LOG:
                        self._log(f"[FLOW-ERROR] ❌ Could not create or find session for document {doc.name()}!")
            
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


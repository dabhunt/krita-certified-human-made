"""
Tracing Detection Module

Pure Python implementation of perceptual hashing for tracing detection.
No external libraries - uses only Krita API + Python stdlib.

Approach: Perceptual Hash Comparison 
- Harder to game than simple edge detection
- Efficient: Only checks when drawing over import layers
- Minimal performance impact: Runs periodically, not every stroke

Algorithm:
1. When import detected: Store perceptual hash of imported image
2. Periodically (every 10 strokes): Check if current layer resembles import
3. If similarity > 33%: Mark as traced (STICKY)

Perceptual Hash Implementation:
- Resize to 8x8 grayscale
- Compute average pixel value
- Generate 64-bit hash (1 if pixel > average, 0 otherwise)
- Compare hashes using Hamming distance
"""

import hashlib
from typing import Optional, Tuple, List, Dict
from PyQt5.QtGui import QImage
from PyQt5.QtCore import QByteArray, QBuffer, QIODevice


DEBUG_LOG = True

# Tracing threshold: >33% similarity = traced
TRACING_THRESHOLD = 0.33

# Check frequency: Every N strokes
CHECK_FREQUENCY = 10


class TracingDetector:
    """Detects tracing by comparing perceptual hashes of layers"""
    
    def __init__(self, debug_log: bool = True):
        self.DEBUG_LOG = debug_log
        # BUG#005 FIX: Use doc_key (not doc_id) to match session manager
        # This prevents data loss during session migration (unsaved → saved)
        self.import_hashes = {}  # doc_key -> {layer_id: phash}
        self.stroke_count_since_check = {}  # doc_key -> int
        self.traced_documents = set()  # doc_keys that are traced (STICKY)
        
    def register_import(self, doc_key: str, layer_node, layer_name: str):
        """
        Register an imported image layer for tracing detection.
        
        BUG#005 FIX: Uses doc_key (session key) instead of doc_id (Python object ID)
        to ensure data persists across session migration.
        
        Args:
            doc_key: Document key (from session manager, e.g., filepath or unsaved_ID)
            layer_node: Krita layer node
            layer_name: Layer name for logging
        """
        try:
            if self.DEBUG_LOG:
                self._log(f"[TRACE-REG] Registering import: {layer_name}")
            
            # Get layer thumbnail for perceptual hashing
            # Use 100x100 thumbnail for efficiency
            thumbnail = layer_node.thumbnail(100, 100)
            
            if not thumbnail:
                self._log(f"[TRACE-REG] ⚠️  Could not get thumbnail for {layer_name}")
                return
            
            # Compute perceptual hash
            phash = self._compute_perceptual_hash(thumbnail)
            
            if phash is None:
                self._log(f"[TRACE-REG] ⚠️  Could not compute hash for {layer_name}")
                return
            
            # Store hash
            if doc_key not in self.import_hashes:
                self.import_hashes[doc_key] = {}
            
            layer_id = str(id(layer_node))
            self.import_hashes[doc_key][layer_id] = {
                'phash': phash,
                'layer_name': layer_name,
                'layer_node': layer_node
            }
            
            if self.DEBUG_LOG:
                self._log(f"[TRACE-REG] ✓ Registered: {layer_name} (hash: {phash[:16]}...)")
                
        except Exception as e:
            self._log(f"[TRACE-REG] ❌ Error registering import: {e}")
            import traceback
            self._log(f"[TRACE-REG] Traceback: {traceback.format_exc()}")
    
    def check_for_tracing(self, doc, doc_key: str, session) -> Optional[float]:
        """
        Check if current document shows signs of tracing.
        
        Called periodically (every N strokes) to minimize performance impact.
        
        BUG#005 FIX: Uses doc_key instead of doc_id for consistency.
        
        Args:
            doc: Krita document
            doc_key: Document key (from session manager)
            session: CHM session
            
        Returns:
            Tracing percentage (0.0-1.0) if traced, None otherwise
        """
        # Skip if already marked as traced (STICKY)
        if doc_key in self.traced_documents:
            return None
        
        # Skip if no imports registered
        if doc_key not in self.import_hashes or not self.import_hashes[doc_key]:
            return None
        
        # Increment stroke count
        if doc_key not in self.stroke_count_since_check:
            self.stroke_count_since_check[doc_key] = 0
        
        self.stroke_count_since_check[doc_key] += 1
        
        # Only check every N strokes (efficiency)
        if self.stroke_count_since_check[doc_key] < CHECK_FREQUENCY:
            return None
        
        # Reset counter
        self.stroke_count_since_check[doc_key] = 0
        
        if self.DEBUG_LOG:
            self._log(f"[TRACE-CHECK] Checking for tracing (imports: {len(self.import_hashes[doc_key])})")
        
        try:
            # Get all paint layers (where user draws)
            paint_layers = self._get_paint_layers(doc)
            
            if not paint_layers:
                if self.DEBUG_LOG:
                    self._log(f"[TRACE-CHECK] No paint layers found")
                return None
            
            # Check each paint layer against import layers
            max_similarity = 0.0
            traced_layer = None
            import_layer = None
            
            for paint_layer in paint_layers:
                # Skip if this IS an import layer
                paint_layer_id = str(id(paint_layer))
                if paint_layer_id in self.import_hashes[doc_key]:
                    continue
                
                # Get paint layer thumbnail
                paint_thumbnail = paint_layer.thumbnail(100, 100)
                if not paint_thumbnail:
                    continue
                
                # Compute perceptual hash
                paint_phash = self._compute_perceptual_hash(paint_thumbnail)
                if paint_phash is None:
                    continue
                
                # Compare against all import hashes
                for import_id, import_data in self.import_hashes[doc_key].items():
                    import_phash = import_data['phash']
                    similarity = self._compare_hashes(paint_phash, import_phash)
                    
                    if similarity > max_similarity:
                        max_similarity = similarity
                        traced_layer = paint_layer.name()
                        import_layer = import_data['layer_name']
            
            if self.DEBUG_LOG:
                self._log(f"[TRACE-CHECK] Max similarity: {max_similarity*100:.1f}%")
            
            # Check if exceeds threshold
            if max_similarity >= TRACING_THRESHOLD:
                # TRACED! Mark as sticky
                self.traced_documents.add(doc_key)
                session.mark_as_traced(max_similarity)
                
                if self.DEBUG_LOG:
                    self._log(f"[TRACE-CHECK] ⚠️  TRACING DETECTED!")
                    self._log(f"[TRACE-CHECK]   Paint layer: {traced_layer}")
                    self._log(f"[TRACE-CHECK]   Import layer: {import_layer}")
                    self._log(f"[TRACE-CHECK]   Similarity: {max_similarity*100:.1f}%")
                
                return max_similarity
            
            return None
            
        except Exception as e:
            self._log(f"[TRACE-CHECK] ❌ Error checking for tracing: {e}")
            import traceback
            self._log(f"[TRACE-CHECK] Traceback: {traceback.format_exc()}")
            return None
    
    def check_mixed_media(self, doc, doc_key: str) -> bool:
        """
        Check if imported images are visible in final export (MixedMedia).
        
        BUG#005 FIX: Uses doc_key instead of doc_id for consistency.
        
        Args:
            doc: Krita document
            doc_key: Document key (from session manager)
            
        Returns:
            True if imports are visible, False otherwise
        """
        # Skip if no imports
        if doc_key not in self.import_hashes or not self.import_hashes[doc_key]:
            if self.DEBUG_LOG:
                self._log(f"[MIXED-MEDIA] No imports registered for doc_key: {doc_key}")
            return False
        
        if self.DEBUG_LOG:
            self._log(f"[MIXED-MEDIA] Checking {len(self.import_hashes[doc_key])} registered imports")
        
        try:
            # BUG#004 FIX: Re-fetch layers by name instead of using stored references
            # Stored layer_node references may become stale
            for import_id, import_data in self.import_hashes[doc_key].items():
                layer_name = import_data['layer_name']
                
                if self.DEBUG_LOG:
                    self._log(f"[MIXED-MEDIA] Checking layer: {layer_name}")
                
                # Re-fetch layer from document (more reliable than stored reference)
                layer_node = doc.nodeByName(layer_name)
                
                if not layer_node:
                    if self.DEBUG_LOG:
                        self._log(f"[MIXED-MEDIA] ⚠️  Layer not found by name: {layer_name}")
                    continue
                
                # Check if layer is visible
                is_visible = layer_node.visible()
                
                if self.DEBUG_LOG:
                    self._log(f"[MIXED-MEDIA] Layer '{layer_name}' visible: {is_visible}")
                
                if is_visible:
                    if self.DEBUG_LOG:
                        self._log(f"[MIXED-MEDIA] ✓ Import layer visible: {layer_name}")
                    return True
            
            if self.DEBUG_LOG:
                self._log(f"[MIXED-MEDIA] No visible import layers found")
            return False
            
        except Exception as e:
            self._log(f"[MIXED-MEDIA] ❌ Error checking visibility: {e}")
            import traceback
            self._log(f"[MIXED-MEDIA] Traceback: {traceback.format_exc()}")
            return False
    
    def _get_paint_layers(self, doc) -> List:
        """Get all paint layers from document (recursive)"""
        paint_layers = []
        
        def traverse(node):
            if node.type() == "paintlayer":
                paint_layers.append(node)
            
            # Recurse into children
            for child in node.childNodes():
                traverse(child)
        
        # Start from root nodes
        for root in doc.topLevelNodes():
            traverse(root)
        
        return paint_layers
    
    def _compute_perceptual_hash(self, qimage: QImage) -> Optional[str]:
        """
        Compute perceptual hash (pHash) of image.
        
        Pure Python implementation:
        1. Resize to 8x8 grayscale
        2. Compute average pixel value
        3. Generate 64-bit hash (1 if pixel > average, 0 otherwise)
        
        Args:
            qimage: QImage to hash
            
        Returns:
            64-character hex string (256-bit hash for better accuracy)
        """
        try:
            # Resize to 8x8 for perceptual hash
            small = qimage.scaled(8, 8)
            
            # Convert to grayscale and get pixel values
            pixels = []
            for y in range(8):
                for x in range(8):
                    # Get pixel color
                    pixel = small.pixel(x, y)
                    
                    # Extract RGB (QImage.pixel returns QRgb)
                    r = (pixel >> 16) & 0xFF
                    g = (pixel >> 8) & 0xFF
                    b = pixel & 0xFF
                    
                    # Convert to grayscale (standard luminance formula)
                    gray = int(0.299 * r + 0.587 * g + 0.114 * b)
                    pixels.append(gray)
            
            # Compute average
            avg = sum(pixels) / len(pixels)
            
            # Generate hash: 1 if pixel > average, 0 otherwise
            hash_bits = []
            for pixel in pixels:
                hash_bits.append('1' if pixel > avg else '0')
            
            # Convert to hex string
            hash_str = ''.join(hash_bits)
            hash_int = int(hash_str, 2)
            hash_hex = format(hash_int, '016x')  # 64-bit hash
            
            return hash_hex
            
        except Exception as e:
            self._log(f"[PHASH] ❌ Error computing hash: {e}")
            return None
    
    def _compare_hashes(self, hash1: str, hash2: str) -> float:
        """
        Compare two perceptual hashes using Hamming distance.
        
        Args:
            hash1: First hash (hex string)
            hash2: Second hash (hex string)
            
        Returns:
            Similarity score (0.0-1.0, where 1.0 = identical)
        """
        try:
            # Convert hex to binary
            int1 = int(hash1, 16)
            int2 = int(hash2, 16)
            
            # XOR to find differing bits
            xor = int1 ^ int2
            
            # Count differing bits (Hamming distance)
            hamming_distance = bin(xor).count('1')
            
            # Convert to similarity (0 = identical, 64 = completely different)
            max_distance = 64  # 64-bit hash
            similarity = 1.0 - (hamming_distance / max_distance)
            
            return similarity
            
        except Exception as e:
            self._log(f"[PHASH] ❌ Error comparing hashes: {e}")
            return 0.0
    
    def _log(self, message: str):
        """Debug logging helper"""
        if self.DEBUG_LOG:
            import sys
            from datetime import datetime
            import os
            
            full_message = f"TracingDetector: {message}"
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
                print(f"TracingDetector: Could not write to log file: {e}")


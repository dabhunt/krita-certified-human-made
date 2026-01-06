# Rust Python Binding TODOs

**Date**: December 29, 2025  
**Status**: Workarounds in place, proper fixes needed

---

## 1. Missing Session Serialization Methods

### Issue

**File**: `src/python_bindings.rs`  
**Missing**: `to_json()` and `from_json()` methods on `PySession`

**Impact**: Cannot persist/resume sessions properly without workaround

**Current Workaround**: Python-side serialization in `chm_session_manager.py`
- `session_to_json()` - Manually builds JSON from properties (id, event_count, metadata, etc.)
- `import_session()` - Creates new session, restores metadata only
- **LIMITATION**: Event history is NOT preserved (only metadata + counts)

### Proper Fix

Add to `python_bindings.rs`:

```rust
#[pymethods]
impl PySession {
    /// Serialize session to JSON string
    fn to_json(&self) -> PyResult<String> {
        serde_json::to_string(&self.inner)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))
    }
    
    /// Deserialize session from JSON string
    #[staticmethod]
    fn from_json(json_str: &str) -> PyResult<Self> {
        let inner: CHMSession = serde_json::from_str(json_str)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;
        Ok(PySession { inner })
    }
}
```

**Requirements**:
1. `CHMSession` must derive `Serialize` and `Deserialize` (already done in `session.rs`)
2. All nested structs must also derive these traits
3. Private keys must be handled securely (don't serialize signing keys!)

**Risks**:
- ⚠️  Serializing `SigningKey` would be a **SECURITY ISSUE**
- Need to either:
  - Skip signing_key in serialization (sessions lose ability to sign after resume)
  - OR generate new signing key on deserialize (different signatures)
  - OR store encrypted signing key (complex)

**Recommended Approach**: Skip event serialization for MVP
- Only serialize metadata (doc name, canvas size, counts)
- Keep events in memory only during active session
- Proof generation happens at finalization (before close)
- Session resumption creates fresh session with restored metadata

### Testing After Fix

```python
# Python test
session = chm.CHMSession()
session.record_stroke(100, 200, 0.8, "Basic-5")
session.set_metadata(document_name="test.kra", canvas_width=500, canvas_height=500)

# Serialize
json_str = session.to_json()
print(f"Serialized: {len(json_str)} bytes")

# Deserialize
session2 = chm.CHMSession.from_json(json_str)
assert session2.id == session.id
assert session2.event_count == session.event_count
```

---

## 2. Missing Event Access Methods

### Issue

**Missing**: Methods to access individual events from Python

**Current State**: Events are stored internally but not accessible  
**Impact**: Cannot inspect event history, debug recording issues, or implement custom analytics

### Proper Fix

Add to `python_bindings.rs`:

```rust
#[pymethods]
impl PySession {
    /// Get all events as list of dicts
    fn get_events(&self) -> PyResult<PyObject> {
        Python::with_gil(|py| {
            let events_list = pyo3::types::PyList::empty(py);
            
            for event in &self.inner.events {
                let event_dict = PyDict::new(py);
                event_dict.set_item("event_type", format!("{:?}", event.event_type))?;
                event_dict.set_item("timestamp", event.timestamp.to_rfc3339())?;
                
                // Add type-specific data
                match &event.event_type {
                    EventType::Stroke { x, y, pressure, brush_name } => {
                        event_dict.set_item("x", x)?;
                        event_dict.set_item("y", y)?;
                        event_dict.set_item("pressure", pressure)?;
                        if let Some(ref brush) = brush_name {
                            event_dict.set_item("brush_name", brush)?;
                        }
                    }
                    EventType::LayerAdded { layer_id, layer_type } => {
                        event_dict.set_item("layer_id", layer_id)?;
                        event_dict.set_item("layer_type", layer_type)?;
                    }
                    // ... other event types
                    _ => {}
                }
                
                events_list.append(event_dict)?;
            }
            
            Ok(events_list.into())
        })
    }
    
    /// Get event at specific index
    fn get_event(&self, index: usize) -> PyResult<PyObject> {
        if index >= self.inner.events.len() {
            return Err(PyErr::new::<pyo3::exceptions::PyIndexError, _>(
                format!("Index {} out of range (0-{})", index, self.inner.events.len() - 1)
            ));
        }
        
        // Convert event to dict (similar to above)
        // ... implementation
    }
}
```

**Use Cases**:
- Debugging: "Show me the last 10 events recorded"
- Analytics: "How many strokes in the last 5 minutes?"
- Testing: "Verify event X was recorded correctly"

---

## 3. Session Cloning/Copying

### Issue

**Missing**: Ability to clone a session (useful for testing, branching workflows)

### Proper Fix

```rust
#[pymethods]
impl PySession {
    /// Create a deep copy of the session
    fn clone(&self) -> PyResult<Self> {
        let cloned_inner = self.inner.clone();
        Ok(PySession { inner: cloned_inner })
    }
}
```

**Requirements**: `CHMSession` must derive `Clone` (check if signing keys can be cloned safely)

---

## 4. Better Error Messages

### Issue

Current Python errors are generic: `'CHMSession' object has no attribute 'to_json'`

### Improvement

Add custom exception types:

```rust
// In python_bindings.rs
pyo3::create_exception!(chm, CHMSerializationError, pyo3::exceptions::PyException);
pyo3::create_exception!(chm, CHMCryptoError, pyo3::exceptions::PyException);
pyo3::create_exception!(chm, CHMSessionError, pyo3::exceptions::PyException);

// Register in module
#[pymodule]
fn chm(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add("CHMSerializationError", py.get_type::<CHMSerializationError>())?;
    m.add("CHMCryptoError", py.get_type::<CHMCryptoError>())?;
    m.add("CHMSessionError", py.get_type::<CHMSessionError>())?;
    // ... rest
}

// Use in methods
fn to_json(&self) -> PyResult<String> {
    serde_json::to_string(&self.inner)
        .map_err(|e| CHMSerializationError::new_err(
            format!("Failed to serialize session: {}", e)
        ))
}
```

**Benefit**: Better error handling in Python code

---

## 5. Documentation Strings

### Issue

Methods have docstrings in Rust but not all are detailed

### Improvement

Use `#[pyo3(text_signature = "...")]` for accurate Python signatures:

```rust
#[pymethods]
impl PySession {
    #[pyo3(text_signature = "($self, x, y, pressure, brush_name=None)")]
    /// Record a brush stroke event
    /// 
    /// Args:
    ///     x (float): X coordinate
    ///     y (float): Y coordinate  
    ///     pressure (float): Brush pressure (0.0 to 1.0)
    ///     brush_name (str, optional): Name of the brush
    fn record_stroke(...) { ... }
}
```

**Benefit**: Better IDE autocomplete, help() output

---

## Priority Order

1. **HIGH**: `to_json()` / `from_json()` - Critical for session persistence
2. **MEDIUM**: Better error messages - Improves debugging experience
3. **LOW**: `get_events()` - Nice to have for debugging
4. **LOW**: `clone()` - Future enhancement
5. **LOW**: Documentation improvements - Gradual enhancement

---

## Testing Plan

After adding methods:

1. **Unit Tests** (Rust side):
   ```rust
   #[cfg(test)]
   mod tests {
       #[test]
       fn test_session_serialization() {
           let session = CHMSession::new().unwrap();
           let json = serde_json::to_string(&session).unwrap();
           let session2: CHMSession = serde_json::from_str(&json).unwrap();
           assert_eq!(session.id, session2.id);
       }
   }
   ```

2. **Integration Tests** (Python side):
   ```python
   # In krita-plugin/tests/
   import chm
   
   def test_session_serialization():
       session = chm.CHMSession()
       session.record_stroke(100, 200, 0.8, "brush")
       
       json_str = session.to_json()
       session2 = chm.CHMSession.from_json(json_str)
       
       assert session2.event_count == 1
   ```

3. **Manual Test** (in Krita):
   - Create session, draw strokes, save file
   - Close Krita
   - Reopen file, verify session resumes with events intact

---

## Notes

- **Current workaround is acceptable for MVP**: Metadata persistence works
- **Event history not critical**: Most important data is in final proof
- **Proper fix should be implemented** before public release
- **Security review needed**: Don't accidentally expose private keys!

---

## Related Files

- `src/python_bindings.rs` - Where fixes go
- `src/session.rs` - Core session implementation
- `krita-plugin/chm_verifier/chm_session_manager.py` - Python workaround
- `krita-plugin/chm_verifier/event_capture.py` - Uses serialization



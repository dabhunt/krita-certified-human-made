/*
 * Python Bindings for CHM Core Library
 * 
 * This module exposes Rust functionality to Python via PyO3.
 * Used by the Krita plugin to access cryptographic operations and session management.
 */

 use pyo3::prelude::*;
 use pyo3::types::PyDict;
 use crate::session::CHMSession;
 
 /// Python-wrapped CHM Session
 /// 
 /// This is the main interface that the Krita plugin uses to record
 /// drawing events and generate proofs.
 #[pyclass(name = "CHMSession")]
 pub struct PySession {
     inner: CHMSession,
 }
 
 #[pymethods]
 impl PySession {
     /// Create a new CHM session
     #[new]
     fn new() -> PyResult<Self> {
         let session = CHMSession::new()
             .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;
         
         Ok(PySession { inner: session })
     }
     
     /// Get the session ID
     #[getter]
     fn id(&self) -> String {
         self.inner.id.to_string()
     }
     
     /// Get the session start time (ISO 8601 format)
     #[getter]
     fn start_time(&self) -> String {
         self.inner.start_time.to_rfc3339()
     }
     
     /// Check if session is finalized
     #[getter]
     fn is_finalized(&self) -> bool {
         self.inner.is_finalized
     }
     
     /// Get the count of recorded events
     #[getter]
     fn event_count(&self) -> usize {
         self.inner.events.len()
     }
     
     /// Record a brush stroke event
     /// 
     /// Args:
     ///     x (float): X coordinate
     ///     y (float): Y coordinate
     ///     pressure (float): Brush pressure (0.0 to 1.0)
     ///     brush_name (str, optional): Name of the brush used
     fn record_stroke(
         &mut self,
         x: f64,
         y: f64,
         pressure: f64,
         brush_name: Option<String>,
     ) -> PyResult<()> {
         self.inner
             .record_stroke(x, y, pressure, brush_name)
             .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))
     }
     
     /// Record a layer added event
     /// 
     /// Args:
     ///     layer_id (str): Unique identifier for the layer
     ///     layer_type (str): Type of layer (e.g., "paint", "group", "filter")
     fn record_layer_added(
         &mut self,
         layer_id: String,
         layer_type: String,
     ) -> PyResult<()> {
         self.inner
             .record_layer_added(layer_id, layer_type)
             .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))
     }
     
     /// Record an import event
     /// 
     /// Args:
     ///     file_hash (str): SHA-256 hash of the imported file
     ///     import_type (str): Type of import (e.g., "reference_image", "brush_preset")
     ///     file_size (int, optional): Size of imported file in bytes
     fn record_import(
         &mut self,
         file_hash: String,
         import_type: String,
         file_size: Option<u64>,
     ) -> PyResult<()> {
         self.inner
             .record_import(file_hash, import_type, file_size)
             .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))
     }
     
     /// Record a plugin usage event
     /// 
     /// Args:
     ///     plugin_name (str): Name of the plugin used
     ///     plugin_type (str): Type of plugin (e.g., "AI_GENERATION", "FILTER")
     fn record_plugin_used(
         &mut self,
         plugin_name: String,
         plugin_type: String,
     ) -> PyResult<()> {
         self.inner
             .record_plugin_used(plugin_name, plugin_type)
             .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))
     }
     
     /// Record an undo/redo event (indicates human behavior)
     /// 
     /// Args:
     ///     action (str): Type of action ("undo" or "redo")
     fn record_undo_redo(&mut self, action: String) -> PyResult<()> {
         self.inner
             .record_undo_redo(action)
             .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))
     }
     
     /// Set session metadata
     /// 
     /// Args:
     ///     document_name (str, optional): Name of the document
     ///     canvas_width (int, optional): Canvas width in pixels
     ///     canvas_height (int, optional): Canvas height in pixels
     ///     krita_version (str, optional): Krita version string
     ///     os_info (str, optional): OS information
     fn set_metadata(
         &mut self,
         document_name: Option<String>,
         canvas_width: Option<u32>,
         canvas_height: Option<u32>,
         krita_version: Option<String>,
         os_info: Option<String>,
     ) -> PyResult<()> {
         use crate::session::SessionMetadata;
         
         let metadata = SessionMetadata {
             document_name,
             canvas_width,
             canvas_height,
             krita_version,
             os_info,
         };
         
         self.inner.set_metadata(metadata);
         Ok(())
     }
     
     /// Get the public key for this session (for verification)
     #[getter]
     fn public_key(&self) -> String {
         self.inner.public_key_base64()
     }
     
    /// Get session duration in seconds (total elapsed time)
    #[getter]
    fn duration_secs(&self) -> i64 {
        self.inner.duration_secs()
    }
    
    /// Get active drawing time in seconds (excludes AFK periods)
    #[getter]
    fn active_drawing_time_secs(&self) -> i64 {
        self.inner.active_drawing_time_secs()
    }
    
    /// Add active drawing time (called when user is actively drawing)
    fn add_active_time(&mut self, seconds: i64) {
        self.inner.add_active_time(seconds);
    }
    
    /// Set active drawing time (for session restoration)
    fn set_active_time(&mut self, seconds: i64) {
        self.inner.set_active_time(seconds);
    }
     
    /// Finalize the session and generate a proof
    /// 
    /// Args:
    ///     artwork_path (str, optional): Path to the exported artwork file.
    ///         If provided, computes file_hash and perceptual_hash for dual-hash verification.
    /// 
    /// Returns:
    ///     dict: Session proof data including classification, timestamps, and hashes
    fn finalize(&mut self, artwork_path: Option<String>) -> PyResult<PyObject> {
        use std::path::Path;
        
        // Create a new session and swap it with the current one (finalize consumes self)
        let session = std::mem::replace(
            &mut self.inner,
            CHMSession::new().map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?
        );
        
        // Convert artwork_path to Path reference if provided
        let path_ref = artwork_path.as_ref().map(|s| Path::new(s.as_str()));
        
        let proof = session
            .finalize(path_ref)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))?;
        
        // Convert proof to Python dict
        Python::with_gil(|py| {
            let dict = PyDict::new(py);
            dict.set_item("version", proof.version.clone())?;
            dict.set_item("session_id", proof.session_id.to_string())?;
            dict.set_item("encrypted_events_hash", proof.encrypted_events_hash.clone())?;
            dict.set_item("file_hash", proof.file_hash.clone())?;
            dict.set_item("perceptual_hash", proof.perceptual_hash.clone())?;
            dict.set_item("classification", format!("{:?}", proof.classification))?;
            dict.set_item("confidence", proof.confidence)?;
            dict.set_item("timestamp", proof.timestamp.to_rfc3339())?;
            dict.set_item("signature", proof.signature.clone())?;
            dict.set_item("artist_public_key", proof.artist_public_key.clone())?;
            
            // Add event summary
            let summary_dict = PyDict::new(py);
            summary_dict.set_item("total_events", proof.event_summary.total_events)?;
            summary_dict.set_item("stroke_count", proof.event_summary.stroke_count)?;
            summary_dict.set_item("layer_count", proof.event_summary.layer_count)?;
            summary_dict.set_item("session_duration_secs", proof.event_summary.session_duration_secs)?;
            summary_dict.set_item("imports_count", proof.event_summary.imports_count)?;
            summary_dict.set_item("undo_redo_count", proof.event_summary.undo_redo_count)?;
            summary_dict.set_item("plugins_used", proof.event_summary.plugins_used.clone())?;
            dict.set_item("event_summary", summary_dict)?;
            
            // Add optional fields
            if let Some(ref doc_name) = proof.document_name {
                dict.set_item("document_name", doc_name)?;
            }
            
            Ok(dict.into())
        })
    }
     
     /// Get session metadata as a dict
     /// 
     /// Returns:
     ///     dict: Session metadata including document name, canvas size, etc.
     fn get_metadata(&self) -> PyResult<PyObject> {
         Python::with_gil(|py| {
             let dict = PyDict::new(py);
             if let Some(ref doc_name) = self.inner.metadata.document_name {
                 dict.set_item("document_name", doc_name)?;
             }
             if let Some(width) = self.inner.metadata.canvas_width {
                 dict.set_item("canvas_width", width)?;
             }
             if let Some(height) = self.inner.metadata.canvas_height {
                 dict.set_item("canvas_height", height)?;
             }
             if let Some(ref krita_version) = self.inner.metadata.krita_version {
                 dict.set_item("krita_version", krita_version)?;
             }
             
             Ok(dict.into())
         })
     }
 }
 
 /// Simple "Hello World" function for testing PyO3 bindings
 #[pyfunction]
 fn hello_from_rust() -> String {
     "Hello from Certified Human-Made (Rust core)! 🎨".to_string()
 }
 
 /// Get the version of the CHM library
 #[pyfunction]
 fn get_version() -> String {
     env!("CARGO_PKG_VERSION").to_string()
 }
 
 /// Test function that demonstrates Rust->Python data passing
 #[pyfunction]
 fn test_data_types(
     string_val: String,
     int_val: i64,
     float_val: f64,
     bool_val: bool,
 ) -> PyResult<PyObject> {
     Python::with_gil(|py| {
         let dict = PyDict::new(py);
         dict.set_item("string_echo", string_val)?;
         dict.set_item("int_doubled", int_val * 2)?;
         dict.set_item("float_squared", float_val * float_val)?;
         dict.set_item("bool_inverted", !bool_val)?;
         
         Ok(dict.into())
     })
 }
 
 /// Compute SHA-256 hash of data
 /// 
 /// Args:
 ///     data (bytes): Data to hash
 /// 
 /// Returns:
 ///     str: Hex-encoded SHA-256 hash
 #[pyfunction]
 fn sha256(data: &[u8]) -> String {
     crate::crypto::sha256_hash(data)
 }
 
/// Compute SHA-256 hash of a file
/// 
/// Args:
///     path (str): Path to the file
/// 
/// Returns:
///     str: Hex-encoded SHA-256 hash
#[pyfunction]
fn sha256_file(path: String) -> PyResult<String> {
    use std::path::Path;
    crate::crypto::sha256_file(Path::new(&path))
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e.to_string()))
}

/// Sign data using ED25519
/// 
/// Args:
///     data (bytes): Data to sign
///     secret_key_bytes (bytes): ED25519 secret key (32 bytes)
/// 
/// Returns:
///     bytes: ED25519 signature (64 bytes)
#[pyfunction]
fn sign_bytes(data: Vec<u8>, secret_key_bytes: Vec<u8>) -> PyResult<Vec<u8>> {
    use crate::crypto::SigningKey;
    
    // Create SigningKey from raw bytes
    let signing_key = SigningKey::from_bytes(&secret_key_bytes)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(format!("Invalid ED25519 key: {}", e)))?;
    
    // Sign the data
    let signature = signing_key.sign(&data)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(format!("Signing failed: {}", e)))?;
    
    Ok(signature)
}
 
 /// Python module definition
 /// 
 /// This is the entry point that Python sees when importing the module:
 /// `from chm import CHMSession, hello_from_rust, get_version, sha256, sha256_file`
 #[pymodule]
 fn chm(_py: Python, m: &PyModule) -> PyResult<()> {
     // Register the main session class
     m.add_class::<PySession>()?;
     
    // Register utility functions
    m.add_function(wrap_pyfunction!(hello_from_rust, m)?)?;
    m.add_function(wrap_pyfunction!(get_version, m)?)?;
    m.add_function(wrap_pyfunction!(test_data_types, m)?)?;
    m.add_function(wrap_pyfunction!(sha256, m)?)?;
    m.add_function(wrap_pyfunction!(sha256_file, m)?)?;
    m.add_function(wrap_pyfunction!(sign_bytes, m)?)?;
     
     // Add module metadata
     m.add("__version__", env!("CARGO_PKG_VERSION"))?;
     m.add("__doc__", "Certified Human-Made art verification library")?;
     
     Ok(())
 }
 
 
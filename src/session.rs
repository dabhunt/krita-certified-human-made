use crate::analysis::Classification;
use crate::crypto::{self, EncryptionKey, SigningKey};
use crate::error::{CHMError, Result};
use crate::events::SessionEvent;
use crate::proof::{EventSummary, SessionProof};
use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use uuid::Uuid;

/// Configuration for a CHM session
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SessionConfig {
    pub max_events: usize,
    pub auto_encrypt_threshold: usize, // Encrypt events after this many
    pub enable_privacy_mode: bool,     // Exclude detailed stroke data
}

impl Default for SessionConfig {
    fn default() -> Self {
        Self {
            max_events: 50_000,
            auto_encrypt_threshold: 100,
            enable_privacy_mode: false,
        }
    }
}

/// Metadata about the art creation session
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SessionMetadata {
    pub document_name: Option<String>,
    pub canvas_width: Option<u32>,
    pub canvas_height: Option<u32>,
    pub krita_version: Option<String>,
    pub os_info: Option<String>,
}

/// Main session structure that tracks art creation events
#[derive(Debug)]
pub struct CHMSession {
    pub id: Uuid,
    pub start_time: DateTime<Utc>,
    pub events: Vec<SessionEvent>,
    pub metadata: SessionMetadata,
    pub config: SessionConfig,
    encryption_key: EncryptionKey,
    signing_key: SigningKey,
    pub is_finalized: bool,
}

impl CHMSession {
    /// Create a new session with default configuration
    pub fn new() -> Result<Self> {
        Self::with_config(SessionConfig::default())
    }

    /// Create a new session with custom configuration
    pub fn with_config(config: SessionConfig) -> Result<Self> {
        let encryption_key = EncryptionKey::generate()?;
        let signing_key = SigningKey::generate()?;
        
        let session = Self {
            id: Uuid::new_v4(),
            start_time: Utc::now(),
            events: Vec::new(),
            metadata: SessionMetadata {
                document_name: None,
                canvas_width: None,
                canvas_height: None,
                krita_version: None,
                os_info: None,
            },
            config,
            encryption_key,
            signing_key,
            is_finalized: false,
        };

        log::info!("Created new CHM session: {}", session.id);
        Ok(session)
    }

    /// Get the public key for this session (for verification)
    pub fn public_key_base64(&self) -> String {
        self.signing_key.public_key_base64()
    }

    /// Set session metadata
    pub fn set_metadata(&mut self, metadata: SessionMetadata) {
        self.metadata = metadata;
    }

    /// Record a stroke event
    pub fn record_stroke(
        &mut self,
        x: f64,
        y: f64,
        pressure: f64,
        brush_name: Option<String>,
    ) -> Result<()> {
        self.check_not_finalized()?;
        self.check_event_limit()?;

        let event = SessionEvent::Stroke {
            x,
            y,
            pressure,
            timestamp: Utc::now().timestamp(),
            brush_name,
        };

        self.record_event(event)
    }

    /// Record a layer event
    pub fn record_layer_added(&mut self, layer_id: String, layer_type: String) -> Result<()> {
        self.check_not_finalized()?;

        let event = SessionEvent::LayerAdded {
            layer_id,
            layer_type,
            timestamp: Utc::now().timestamp(),
        };

        self.record_event(event)
    }

    /// Record an import event
    pub fn record_import(
        &mut self,
        file_hash: String,
        import_type: String,
        file_size: Option<u64>,
    ) -> Result<()> {
        self.check_not_finalized()?;

        log::info!("Import event recorded: {}", file_hash);

        let event = SessionEvent::ImportEvent {
            file_hash,
            import_type,
            timestamp: Utc::now().timestamp(),
            file_size,
        };

        self.record_event(event)
    }

    /// Record a plugin usage event
    pub fn record_plugin_used(&mut self, plugin_name: String, plugin_type: String) -> Result<()> {
        self.check_not_finalized()?;

        let event = SessionEvent::PluginUsed {
            plugin_name: plugin_name.clone(),
            plugin_type,
            timestamp: Utc::now().timestamp(),
        };

        log::warn!("Plugin used: {}", plugin_name);
        self.record_event(event)
    }

    /// Record an undo/redo event (indicates human behavior)
    pub fn record_undo_redo(&mut self, action: String) -> Result<()> {
        self.check_not_finalized()?;

        let event = SessionEvent::UndoRedo {
            action,
            timestamp: Utc::now().timestamp(),
        };

        self.record_event(event)
    }

    /// Internal method to record any event
    fn record_event(&mut self, event: SessionEvent) -> Result<()> {
        self.events.push(event);

        // Auto-encrypt if threshold reached (will implement in crypto module)
        if self.events.len() % self.config.auto_encrypt_threshold == 0 {
            log::debug!(
                "Event threshold reached: {} events",
                self.events.len()
            );
            // TODO: Implement batch encryption
        }

        Ok(())
    }

    /// Finalize the session and generate a proof
    pub fn finalize(mut self) -> Result<SessionProof> {
        self.check_not_finalized()?;
        self.is_finalized = true;

        log::info!(
            "Finalizing session {} with {} events",
            self.id,
            self.events.len()
        );

        // 1. Serialize events to JSON
        let events_json = serde_json::to_vec(&self.events)
            .map_err(|e| CHMError::serialization(format!("Failed to serialize events: {}", e)))?;

        // 2. Encrypt events
        let encrypted_events = crypto::encrypt_data(&events_json, &self.encryption_key)?;
        
        // 3. Hash encrypted events
        let encrypted_json = serde_json::to_vec(&encrypted_events)
            .map_err(|e| CHMError::serialization(format!("Failed to serialize encrypted data: {}", e)))?;
        let encrypted_events_hash = crypto::sha256_hash(&encrypted_json);

        // 4. Analyze events for classification
        let classification = self.analyze_classification();
        let confidence = self.calculate_confidence(&classification);

        // 5. Create event summary (aggregated, not raw events)
        let event_summary = self.create_event_summary();

        // 6. Create proof struct (without signature yet)
        let proof = SessionProof {
            version: "1.0".to_string(),
            session_id: self.id,
            artist_public_key: self.signing_key.public_key_base64(),
            classification,
            confidence,
            event_summary,
            encrypted_events_hash: encrypted_events_hash.clone(),
            signature: String::new(), // Will be filled after signing
            triple_timestamp_receipt: None,
            timestamp: Utc::now(),
            document_name: self.metadata.document_name.clone(),
        };

        // 7. Sign the proof (sign all fields except signature itself)
        let proof_json_for_signing = serde_json::to_vec(&(
            &proof.version,
            &proof.session_id,
            &proof.artist_public_key,
            &proof.classification,
            proof.confidence,
            &proof.event_summary,
            &encrypted_events_hash,
            &proof.timestamp,
        ))
        .map_err(|e| CHMError::serialization(format!("Failed to serialize proof for signing: {}", e)))?;

        let signature = self.signing_key.sign_base64(&proof_json_for_signing)?;

        // 8. Return proof with signature
        let final_proof = SessionProof {
            signature,
            ..proof
        };

        log::info!(
            "Proof generated successfully for session {}: {:?} (confidence: {:.1}%)",
            self.id,
            final_proof.classification,
            final_proof.confidence * 100.0
        );

        Ok(final_proof)
    }

    /// Analyze events to determine classification
    fn analyze_classification(&self) -> Classification {
        // Check for AI plugins
        let has_ai_plugin = self.events.iter().any(|e| {
            if let SessionEvent::PluginUsed { plugin_type, .. } = e {
                plugin_type.contains("AI")
            } else {
                false
            }
        });

        if has_ai_plugin {
            return Classification::AIAssisted;
        }

        // Check for imports
        let has_imports = self.events.iter().any(|e| matches!(e, SessionEvent::ImportEvent { .. }));

        if has_imports {
            // For MVP, classify as Referenced if imports exist
            // Phase 2 will add tracing detection and visibility checking
            return Classification::Referenced;
        }

        // No AI plugins, no imports = Pure human-made
        Classification::PureHumanMade
    }

    /// Calculate confidence score based on session patterns
    fn calculate_confidence(&self, classification: &Classification) -> f64 {
        let mut confidence = classification.base_confidence();

        // Adjust based on event count
        if self.events.len() < 10 {
            confidence *= 0.5; // Very few events = low confidence
        } else if self.events.len() < 50 {
            confidence *= 0.8; // Some events but not many
        }

        // Adjust based on session duration
        let duration_secs = self.duration_secs();
        if duration_secs < 60 {
            confidence *= 0.7; // Very short session
        }

        // Boost for high undo/redo frequency (indicates human behavior)
        let undo_count = self.events.iter()
            .filter(|e| matches!(e, SessionEvent::UndoRedo { .. }))
            .count();
        
        if undo_count > 0 {
            let undo_rate = undo_count as f64 / self.events.len() as f64;
            if undo_rate > 0.05 && undo_rate < 0.20 {
                // Healthy undo rate (5-20%)
                confidence *= 1.1;
            }
        }

        // Clamp to 0.0-1.0
        confidence.clamp(0.0, 1.0)
    }

    /// Create aggregated event summary (not raw events for privacy)
    fn create_event_summary(&self) -> EventSummary {
        let stroke_count = self.events.iter()
            .filter(|e| matches!(e, SessionEvent::Stroke { .. }))
            .count();

        let layer_count = self.events.iter()
            .filter(|e| matches!(e, SessionEvent::LayerAdded { .. }))
            .count();

        let imports_count = self.events.iter()
            .filter(|e| matches!(e, SessionEvent::ImportEvent { .. }))
            .count();

        let undo_redo_count = self.events.iter()
            .filter(|e| matches!(e, SessionEvent::UndoRedo { .. }))
            .count();

        let plugins_used: Vec<String> = self.events.iter()
            .filter_map(|e| {
                if let SessionEvent::PluginUsed { plugin_name, .. } = e {
                    Some(plugin_name.clone())
                } else {
                    None
                }
            })
            .collect::<std::collections::HashSet<_>>()
            .into_iter()
            .collect();

        EventSummary {
            total_events: self.events.len(),
            stroke_count,
            layer_count,
            session_duration_secs: self.duration_secs() as u64,
            plugins_used,
            imports_count,
            undo_redo_count,
        }
    }

    /// Get current event count
    pub fn event_count(&self) -> usize {
        self.events.len()
    }

    /// Get session duration in seconds
    pub fn duration_secs(&self) -> i64 {
        (Utc::now() - self.start_time).num_seconds()
    }

    /// Check if session is finalized
    fn check_not_finalized(&self) -> Result<()> {
        if self.is_finalized {
            Err(CHMError::session("Session is already finalized"))
        } else {
            Ok(())
        }
    }

    /// Check if event limit reached
    fn check_event_limit(&self) -> Result<()> {
        if self.events.len() >= self.config.max_events {
            Err(CHMError::session(format!(
                "Event limit reached: {}",
                self.config.max_events
            )))
        } else {
            Ok(())
        }
    }
}

impl Default for CHMSession {
    fn default() -> Self {
        Self::new().expect("Failed to create default session")
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_session_creation() {
        let session = CHMSession::new().unwrap();
        assert_eq!(session.events.len(), 0);
        assert!(!session.is_finalized);
    }

    #[test]
    fn test_record_stroke() {
        let mut session = CHMSession::new().unwrap();
        session
            .record_stroke(100.0, 200.0, 0.8, Some("Test Brush".to_string()))
            .unwrap();
        assert_eq!(session.events.len(), 1);
    }

    #[test]
    fn test_event_limit() {
        let mut config = SessionConfig::default();
        config.max_events = 5;
        let mut session = CHMSession::with_config(config).unwrap();

        // Add 5 events (should work)
        for _ in 0..5 {
            session.record_stroke(0.0, 0.0, 1.0, None).unwrap();
        }

        // 6th event should fail
        let result = session.record_stroke(0.0, 0.0, 1.0, None);
        assert!(result.is_err());
    }

    #[test]
    fn test_finalized_session_rejects_events() {
        let session = CHMSession::new().unwrap();
        // This will fail because finalize is not yet implemented
        // When implemented, test that after finalize(), record_stroke() fails
    }

    #[test]
    fn test_session_duration() {
        let session = CHMSession::new().unwrap();
        std::thread::sleep(std::time::Duration::from_millis(100));
        assert!(session.duration_secs() >= 0);
    }
}


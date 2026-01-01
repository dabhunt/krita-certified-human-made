use crate::analysis::Classification;
use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use uuid::Uuid;

/// Summary of events in a session (aggregated, not raw events)
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EventSummary {
    pub total_events: usize,
    pub stroke_count: usize,
    pub layer_count: usize,
    /// Total session duration (first to last event, includes brief pauses)
    pub session_duration_secs: u64,
    /// Active drawing time (excludes AFK periods, tracks actual work time)
    pub active_drawing_time_secs: u64,
    pub plugins_used: Vec<String>,
    pub imports_count: usize,
    pub undo_redo_count: usize,
}

/// Triple timestamp verification receipt
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TripleTimestampReceipt {
    pub github_gist_url: String,
    pub github_commit_sha: String,
    pub github_timestamp: String,
    pub wayback_snapshot_url: String,
    pub wayback_timestamp: String,
    pub chm_log_url: String,
    pub chm_log_index: u64,
    pub chm_timestamp: String,
}

/// The main proof structure that can be shared and verified
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SessionProof {
    /// Proof format version
    pub version: String,

    /// Unique session identifier
    pub session_id: Uuid,

    /// Artist's public key (ED25519, base64 encoded)
    pub artist_public_key: String,

    /// Classification result
    pub classification: Classification,

    /// Confidence score (0.0 - 1.0)
    pub confidence: f64,

    /// Aggregated event summary (not raw events for privacy)
    pub event_summary: EventSummary,

    /// SHA-256 hash of encrypted events blob
    pub encrypted_events_hash: String,

    /// SHA-256 hash of exact exported file bytes (for exact match verification)
    pub file_hash: String,

    /// Perceptual hash of visual content (base64, 256-bit, survives re-encoding)
    pub perceptual_hash: String,

    /// ED25519 signature of this proof (signs all fields except this one)
    pub signature: String,

    /// Optional triple timestamp receipt
    #[serde(skip_serializing_if = "Option::is_none")]
    pub triple_timestamp_receipt: Option<TripleTimestampReceipt>,

    /// Proof creation timestamp
    pub timestamp: DateTime<Utc>,

    /// Optional metadata
    #[serde(skip_serializing_if = "Option::is_none")]
    pub document_name: Option<String>,
}

impl SessionProof {
    /// Verify the proof signature (stub for now)
    pub fn verify_signature(&self, _public_key: &str) -> bool {
        // TODO: Implement ED25519 signature verification
        log::warn!("Signature verification not yet implemented");
        false
    }

    /// Convert proof to shareable JSON string
    pub fn to_json(&self) -> Result<String, serde_json::Error> {
        serde_json::to_string_pretty(self)
    }

    /// Parse proof from JSON string
    pub fn from_json(json: &str) -> Result<Self, serde_json::Error> {
        serde_json::from_str(json)
    }

    /// Get a human-readable summary
    pub fn summary(&self) -> String {
        format!(
            "Classification: {:?}\nConfidence: {:.1}%\nEvents: {}\nDuration: {}s\nPlugins: {}\nImports: {}",
            self.classification,
            self.confidence * 100.0,
            self.event_summary.total_events,
            self.event_summary.session_duration_secs,
            self.event_summary.plugins_used.len(),
            self.event_summary.imports_count
        )
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::analysis::Classification;

    #[test]
    fn test_proof_serialization() {
        let proof = SessionProof {
            version: "1.0".to_string(),
            session_id: Uuid::new_v4(),
            artist_public_key: "test_key".to_string(),
            classification: Classification::PureHumanMade,
            confidence: 0.95,
            event_summary: EventSummary {
                total_events: 1000,
                stroke_count: 850,
                layer_count: 10,
                session_duration_secs: 3600,
                plugins_used: vec![],
                imports_count: 0,
                undo_redo_count: 50,
            },
            encrypted_events_hash: "abc123".to_string(),
            file_hash: "sha256:abc123def456".to_string(),
            perceptual_hash: "AQIDBAUGBwgJ".to_string(),
            signature: "sig123".to_string(),
            triple_timestamp_receipt: None,
            timestamp: Utc::now(),
            document_name: Some("Test Artwork".to_string()),
        };

        let json = proof.to_json().unwrap();
        let parsed = SessionProof::from_json(&json).unwrap();

        assert_eq!(proof.session_id, parsed.session_id);
        assert_eq!(proof.confidence, parsed.confidence);
        assert_eq!(proof.file_hash, parsed.file_hash);
        assert_eq!(proof.perceptual_hash, parsed.perceptual_hash);
    }

    #[test]
    fn test_proof_summary() {
        let proof = SessionProof {
            version: "1.0".to_string(),
            session_id: Uuid::new_v4(),
            artist_public_key: "test_key".to_string(),
            classification: Classification::Referenced,
            confidence: 0.85,
            event_summary: EventSummary {
                total_events: 500,
                stroke_count: 400,
                layer_count: 5,
                session_duration_secs: 1800,
                plugins_used: vec![],
                imports_count: 1,
                undo_redo_count: 20,
            },
            encrypted_events_hash: "hash".to_string(),
            file_hash: "sha256:filehash123".to_string(),
            perceptual_hash: "phash456".to_string(),
            signature: "sig".to_string(),
            triple_timestamp_receipt: None,
            timestamp: Utc::now(),
            document_name: None,
        };

        let summary = proof.summary();
        assert!(summary.contains("Referenced"));
        assert!(summary.contains("85.0%"));
    }
}


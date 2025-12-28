use serde::{Deserialize, Serialize};
use std::collections::HashMap;

/// Represents different types of events that can occur during an art creation session
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "type")]
pub enum SessionEvent {
    /// A brush stroke event
    Stroke {
        x: f64,
        y: f64,
        pressure: f64,
        timestamp: i64,
        #[serde(skip_serializing_if = "Option::is_none")]
        brush_name: Option<String>,
    },

    /// Layer added to the document
    LayerAdded {
        layer_id: String,
        layer_type: String,
        timestamp: i64,
    },

    /// Layer modified (renamed, opacity changed, etc.)
    LayerModified {
        layer_id: String,
        modification_type: String,
        timestamp: i64,
    },

    /// Layer deleted
    LayerDeleted {
        layer_id: String,
        timestamp: i64,
    },

    /// Image or resource imported into the document
    ImportEvent {
        file_hash: String,
        import_type: String, // "reference_image", "texture", etc.
        timestamp: i64,
        #[serde(skip_serializing_if = "Option::is_none")]
        file_size: Option<u64>,
    },

    /// Plugin used during session
    PluginUsed {
        plugin_name: String,
        plugin_type: String, // "AI_GENERATION", "UTILITY", etc.
        timestamp: i64,
    },

    /// Filter or effect applied
    FilterApplied {
        filter_name: String,
        params: HashMap<String, String>,
        timestamp: i64,
    },

    /// Session metadata event (start, pause, resume)
    SessionControl {
        action: String, // "start", "pause", "resume", "end"
        timestamp: i64,
    },

    /// Undo/Redo action (indicates human behavior)
    UndoRedo {
        action: String, // "undo", "redo"
        timestamp: i64,
    },
}

impl SessionEvent {
    /// Get the timestamp of any event
    pub fn timestamp(&self) -> i64 {
        match self {
            SessionEvent::Stroke { timestamp, .. }
            | SessionEvent::LayerAdded { timestamp, .. }
            | SessionEvent::LayerModified { timestamp, .. }
            | SessionEvent::LayerDeleted { timestamp, .. }
            | SessionEvent::ImportEvent { timestamp, .. }
            | SessionEvent::PluginUsed { timestamp, .. }
            | SessionEvent::FilterApplied { timestamp, .. }
            | SessionEvent::SessionControl { timestamp, .. }
            | SessionEvent::UndoRedo { timestamp, .. } => *timestamp,
        }
    }

    /// Get a human-readable description of the event
    pub fn description(&self) -> String {
        match self {
            SessionEvent::Stroke { .. } => "Brush stroke".to_string(),
            SessionEvent::LayerAdded { layer_type, .. } => {
                format!("Layer added ({})", layer_type)
            }
            SessionEvent::LayerModified {
                modification_type, ..
            } => format!("Layer modified ({})", modification_type),
            SessionEvent::LayerDeleted { .. } => "Layer deleted".to_string(),
            SessionEvent::ImportEvent { import_type, .. } => {
                format!("Import ({})", import_type)
            }
            SessionEvent::PluginUsed { plugin_name, .. } => {
                format!("Plugin used: {}", plugin_name)
            }
            SessionEvent::FilterApplied { filter_name, .. } => {
                format!("Filter applied: {}", filter_name)
            }
            SessionEvent::SessionControl { action, .. } => {
                format!("Session {}", action)
            }
            SessionEvent::UndoRedo { action, .. } => action.clone(),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_event_serialization() {
        let event = SessionEvent::Stroke {
            x: 100.0,
            y: 200.0,
            pressure: 0.8,
            timestamp: 1234567890,
            brush_name: Some("Basic Brush".to_string()),
        };

        let json = serde_json::to_string(&event).unwrap();
        let deserialized: SessionEvent = serde_json::from_str(&json).unwrap();

        assert_eq!(event.timestamp(), deserialized.timestamp());
    }

    #[test]
    fn test_event_description() {
        let event = SessionEvent::PluginUsed {
            plugin_name: "AI Diffusion".to_string(),
            plugin_type: "AI_GENERATION".to_string(),
            timestamp: 1234567890,
        };

        assert!(event.description().contains("AI Diffusion"));
    }
}


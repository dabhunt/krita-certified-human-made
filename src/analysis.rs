use serde::{Deserialize, Serialize};

/// Classification of the artwork based on creation analysis
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum Classification {
    /// Purely human-made with no AI assistance or tracing
    PureHumanMade,

    /// Used reference images but hand-drawn
    Referenced,

    /// AI plugins or tools were used during creation
    AIAssisted,

    /// High overlap with imported images (likely traced)
    Traced,

    /// Combination of multiple categories above
    MixedWorkflow,

    /// Unable to determine (not enough data)
    Unknown,
}

impl Classification {
    /// Get a human-readable description
    pub fn description(&self) -> &'static str {
        match self {
            Classification::PureHumanMade => {
                "This artwork was created entirely by human hand with no AI assistance or tracing"
            }
            Classification::Referenced => {
                "This artwork used reference images but was hand-drawn by a human"
            }
            Classification::AIAssisted => {
                "This artwork was created with AI assistance (generation or editing tools)"
            }
            Classification::Traced => {
                "This artwork shows high overlap with imported images (likely traced)"
            }
            Classification::MixedWorkflow => {
                "This artwork combines multiple creation methods (AI, references, manual drawing)"
            }
            Classification::Unknown => {
                "Unable to determine classification (insufficient data)"
            }
        }
    }

    /// Get confidence modifier based on classification
    pub fn base_confidence(&self) -> f64 {
        match self {
            Classification::PureHumanMade => 0.95,
            Classification::Referenced => 0.90,
            Classification::AIAssisted => 0.98, // Easy to detect AI plugins
            Classification::Traced => 0.85,     // Depends on detection algorithm
            Classification::MixedWorkflow => 0.80,
            Classification::Unknown => 0.0,
        }
    }
}

/// Analysis flags used during classification
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum AnalysisFlag {
    AIPluginDetected,
    ImportsPresent,
    HighImageOverlap,
    SuspiciousTimingPatterns,
    HighUndoRedoFrequency,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_classification_serialization() {
        let class = Classification::PureHumanMade;
        let json = serde_json::to_string(&class).unwrap();
        let parsed: Classification = serde_json::from_str(&json).unwrap();
        assert_eq!(class, parsed);
    }

    #[test]
    fn test_classification_descriptions() {
        assert!(Classification::PureHumanMade
            .description()
            .contains("human hand"));
        assert!(Classification::AIAssisted
            .description()
            .contains("AI assistance"));
    }

    #[test]
    fn test_base_confidence() {
        assert!(Classification::PureHumanMade.base_confidence() > 0.9);
        assert!(Classification::Unknown.base_confidence() == 0.0);
    }
}


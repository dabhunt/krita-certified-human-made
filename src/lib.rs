// Certified Human-Made (CHM) - Core Library
// This library provides cryptographic verification for human-made digital art

pub mod session;
pub mod events;
pub mod crypto;
pub mod proof;
pub mod analysis;
pub mod error;

// Python bindings (PyO3)
pub mod python_bindings;

// Re-exports for convenience
pub use session::CHMSession;
pub use events::SessionEvent;
pub use proof::SessionProof;
pub use analysis::Classification;
pub use error::{CHMError, Result};

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_library_loads() {
        // Basic smoke test to ensure library compiles
        assert!(true);
    }
}


use thiserror::Error;

pub type Result<T> = std::result::Result<T, CHMError>;

#[derive(Error, Debug)]
pub enum CHMError {
    #[error("Session error: {0}")]
    SessionError(String),

    #[error("Cryptography error: {0}")]
    CryptoError(String),

    #[error("Analysis error: {0}")]
    AnalysisError(String),

    #[error("IO error: {0}")]
    IoError(#[from] std::io::Error),

    #[error("Serialization error: {0}")]
    SerializationError(#[from] serde_json::Error),

    #[error("Image processing error: {0}")]
    ImageError(String),

    #[error("Blockchain error: {0}")]
    BlockchainError(String),

    #[error("Configuration error: {0}")]
    ConfigError(String),
}

impl CHMError {
    pub fn session(msg: impl Into<String>) -> Self {
        CHMError::SessionError(msg.into())
    }

    pub fn crypto(msg: impl Into<String>) -> Self {
        CHMError::CryptoError(msg.into())
    }

    pub fn analysis(msg: impl Into<String>) -> Self {
        CHMError::AnalysisError(msg.into())
    }

    pub fn image(msg: impl Into<String>) -> Self {
        CHMError::ImageError(msg.into())
    }

    pub fn blockchain(msg: impl Into<String>) -> Self {
        CHMError::BlockchainError(msg.into())
    }

    pub fn config(msg: impl Into<String>) -> Self {
        CHMError::ConfigError(msg.into())
    }
}


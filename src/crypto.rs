use crate::error::{CHMError, Result};
use aes_gcm::{
    aead::{Aead, KeyInit},
    Aes256Gcm, Nonce,
};
use ed25519_dalek::{Signature, Signer, SigningKey as Ed25519SigningKey, Verifier, VerifyingKey};
use rand::RngCore;
use serde::{Deserialize, Serialize};

/// AES-256-GCM encryption key (32 bytes)
#[derive(Clone, Debug)]
pub struct EncryptionKey {
    key: [u8; 32],
}

impl EncryptionKey {
    /// Generate a new random encryption key
    pub fn generate() -> Result<Self> {
        let mut key = [0u8; 32];
        rand::thread_rng().fill_bytes(&mut key);
        log::debug!("Generated new encryption key");
        Ok(Self { key })
    }

    /// Create from existing key bytes
    pub fn from_bytes(key: [u8; 32]) -> Self {
        Self { key }
    }

    /// Get the raw key bytes (for internal use only)
    pub(crate) fn as_bytes(&self) -> &[u8; 32] {
        &self.key
    }

    /// Export key as hex string (for storage)
    pub fn to_hex(&self) -> String {
        hex::encode(self.key)
    }

    /// Import key from hex string
    pub fn from_hex(hex_str: &str) -> Result<Self> {
        let bytes = hex::decode(hex_str)
            .map_err(|e| CHMError::crypto(format!("Invalid hex string: {}", e)))?;
        
        if bytes.len() != 32 {
            return Err(CHMError::crypto(format!(
                "Invalid key length: {} (expected 32)",
                bytes.len()
            )));
        }

        let mut key = [0u8; 32];
        key.copy_from_slice(&bytes);
        Ok(Self { key })
    }
}

/// ED25519 signing keypair
#[derive(Debug)]
pub struct SigningKey {
    secret: Ed25519SigningKey,
}

impl SigningKey {
    /// Generate a new signing keypair
    pub fn generate() -> Result<Self> {
        // Generate random 32 bytes for secret key
        let mut secret_bytes = [0u8; 32];
        rand::thread_rng().fill_bytes(&mut secret_bytes);
        
        let secret = Ed25519SigningKey::from_bytes(&secret_bytes);
        log::info!("Generated new ED25519 signing keypair");
        Ok(Self { secret })
    }

    /// Create from existing secret key bytes
    pub fn from_bytes(bytes: &[u8]) -> Result<Self> {
        if bytes.len() != 32 {
            return Err(CHMError::crypto(format!(
                "Invalid secret key length: {} (expected 32)",
                bytes.len()
            )));
        }

        let mut key_bytes = [0u8; 32];
        key_bytes.copy_from_slice(bytes);
        
        let secret = Ed25519SigningKey::from_bytes(&key_bytes);
        Ok(Self { secret })
    }

    /// Sign data and return signature as bytes
    pub fn sign(&self, data: &[u8]) -> Result<Vec<u8>> {
        let signature = self.secret.sign(data);
        Ok(signature.to_bytes().to_vec())
    }

    /// Sign data and return signature as base64 string
    pub fn sign_base64(&self, data: &[u8]) -> Result<String> {
        let signature_bytes = self.sign(data)?;
        Ok(base64::encode(&signature_bytes))
    }

    /// Get the public key for this signing key
    pub fn verifying_key(&self) -> VerifyingKey {
        self.secret.verifying_key()
    }

    /// Get public key as base64 string
    pub fn public_key_base64(&self) -> String {
        base64::encode(&self.verifying_key().to_bytes())
    }

    /// Export secret key as base64 (WARNING: Keep this secure!)
    pub fn to_base64(&self) -> String {
        base64::encode(&self.secret.to_bytes())
    }

    /// Import secret key from base64
    pub fn from_base64(b64_str: &str) -> Result<Self> {
        let bytes = base64::decode(b64_str)
            .map_err(|e| CHMError::crypto(format!("Invalid base64: {}", e)))?;
        Self::from_bytes(&bytes)
    }
}

/// Encrypted data with nonce
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EncryptedBlob {
    pub ciphertext: Vec<u8>,
    pub nonce: Vec<u8>,
}

/// Encrypt data using AES-256-GCM
pub fn encrypt_data(data: &[u8], key: &EncryptionKey) -> Result<EncryptedBlob> {
    // Create cipher instance
    let cipher = Aes256Gcm::new_from_slice(key.as_bytes())
        .map_err(|e| CHMError::crypto(format!("Failed to create cipher: {}", e)))?;

    // Generate random nonce (96 bits for GCM)
    let mut nonce_bytes = [0u8; 12];
    rand::thread_rng().fill_bytes(&mut nonce_bytes);
    let nonce = Nonce::from_slice(&nonce_bytes);

    // Encrypt
    let ciphertext = cipher
        .encrypt(nonce, data)
        .map_err(|e| CHMError::crypto(format!("Encryption failed: {}", e)))?;

    log::debug!(
        "Encrypted {} bytes into {} bytes ciphertext",
        data.len(),
        ciphertext.len()
    );

    Ok(EncryptedBlob {
        ciphertext,
        nonce: nonce_bytes.to_vec(),
    })
}

/// Decrypt data using AES-256-GCM
pub fn decrypt_data(encrypted: &EncryptedBlob, key: &EncryptionKey) -> Result<Vec<u8>> {
    // Create cipher instance
    let cipher = Aes256Gcm::new_from_slice(key.as_bytes())
        .map_err(|e| CHMError::crypto(format!("Failed to create cipher: {}", e)))?;

    // Verify nonce length
    if encrypted.nonce.len() != 12 {
        return Err(CHMError::crypto(format!(
            "Invalid nonce length: {} (expected 12)",
            encrypted.nonce.len()
        )));
    }

    let nonce = Nonce::from_slice(&encrypted.nonce);

    // Decrypt
    let plaintext = cipher
        .decrypt(nonce, encrypted.ciphertext.as_ref())
        .map_err(|e| CHMError::crypto(format!("Decryption failed: {}", e)))?;

    log::debug!(
        "Decrypted {} bytes ciphertext into {} bytes",
        encrypted.ciphertext.len(),
        plaintext.len()
    );

    Ok(plaintext)
}

/// Verify an ED25519 signature
pub fn verify_signature(data: &[u8], signature_base64: &str, public_key_base64: &str) -> Result<bool> {
    // Decode public key
    let public_key_bytes = base64::decode(public_key_base64)
        .map_err(|e| CHMError::crypto(format!("Invalid public key base64: {}", e)))?;
    
    if public_key_bytes.len() != 32 {
        return Err(CHMError::crypto(format!(
            "Invalid public key length: {} (expected 32)",
            public_key_bytes.len()
        )));
    }

    let mut pk_bytes = [0u8; 32];
    pk_bytes.copy_from_slice(&public_key_bytes);
    let verifying_key = VerifyingKey::from_bytes(&pk_bytes)
        .map_err(|e| CHMError::crypto(format!("Invalid public key: {}", e)))?;

    // Decode signature
    let signature_bytes = base64::decode(signature_base64)
        .map_err(|e| CHMError::crypto(format!("Invalid signature base64: {}", e)))?;
    
    let signature = Signature::from_slice(&signature_bytes)
        .map_err(|e| CHMError::crypto(format!("Invalid signature: {}", e)))?;

    // Verify
    match verifying_key.verify(data, &signature) {
        Ok(_) => {
            log::debug!("Signature verification successful");
            Ok(true)
        }
        Err(_) => {
            log::warn!("Signature verification failed");
            Ok(false)
        }
    }
}

/// Compute SHA-256 hash
pub fn sha256_hash(data: &[u8]) -> String {
    use sha2::{Digest, Sha256};
    let mut hasher = Sha256::new();
    hasher.update(data);
    let result = hasher.finalize();
    hex::encode(result)
}

/// Compute SHA-256 hash of a file
pub fn sha256_file(path: &std::path::Path) -> Result<String> {
    use sha2::{Digest, Sha256};
    use std::fs::File;
    use std::io::Read;

    let mut file = File::open(path)
        .map_err(|e| CHMError::io(format!("Failed to open file: {}", e)))?;

    let mut hasher = Sha256::new();
    let mut buffer = [0u8; 8192];

    loop {
        let n = file
            .read(&mut buffer)
            .map_err(|e| CHMError::io(format!("Failed to read file: {}", e)))?;
        
        if n == 0 {
            break;
        }
        hasher.update(&buffer[..n]);
    }

    let result = hasher.finalize();
    Ok(hex::encode(result))
}

// Re-export base64 for convenience
mod base64_impl {
    use base64::{engine::general_purpose, Engine as _};

    pub fn encode(data: &[u8]) -> String {
        general_purpose::STANDARD.encode(data)
    }

    pub fn decode(s: &str) -> Result<Vec<u8>, base64::DecodeError> {
        general_purpose::STANDARD.decode(s)
    }
}

use base64_impl as base64;

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_encryption_key_generation() {
        let key = EncryptionKey::generate().unwrap();
        assert_eq!(key.as_bytes().len(), 32);
    }

    #[test]
    fn test_encryption_key_hex_roundtrip() {
        let key1 = EncryptionKey::generate().unwrap();
        let hex = key1.to_hex();
        let key2 = EncryptionKey::from_hex(&hex).unwrap();
        assert_eq!(key1.as_bytes(), key2.as_bytes());
    }

    #[test]
    fn test_aes_gcm_encryption_decryption() {
        let key = EncryptionKey::generate().unwrap();
        let plaintext = b"This is a secret message that needs encryption!";

        // Encrypt
        let encrypted = encrypt_data(plaintext, &key).unwrap();
        assert_ne!(encrypted.ciphertext, plaintext);
        assert_eq!(encrypted.nonce.len(), 12);

        // Decrypt
        let decrypted = decrypt_data(&encrypted, &key).unwrap();
        assert_eq!(decrypted, plaintext);
    }

    #[test]
    fn test_aes_gcm_wrong_key_fails() {
        let key1 = EncryptionKey::generate().unwrap();
        let key2 = EncryptionKey::generate().unwrap();
        let plaintext = b"Secret data";

        let encrypted = encrypt_data(plaintext, &key1).unwrap();
        let result = decrypt_data(&encrypted, &key2);
        
        assert!(result.is_err());
    }

    #[test]
    fn test_signing_key_generation() {
        let key = SigningKey::generate().unwrap();
        let public_key = key.public_key_base64();
        assert!(!public_key.is_empty());
    }

    #[test]
    fn test_signing_key_roundtrip() {
        let key1 = SigningKey::generate().unwrap();
        let b64 = key1.to_base64();
        let key2 = SigningKey::from_base64(&b64).unwrap();
        
        // Both keys should produce same public key
        assert_eq!(key1.public_key_base64(), key2.public_key_base64());
    }

    #[test]
    fn test_sign_and_verify() {
        let key = SigningKey::generate().unwrap();
        let data = b"Important message to sign";

        // Sign
        let signature = key.sign_base64(data).unwrap();
        assert!(!signature.is_empty());

        // Verify
        let public_key = key.public_key_base64();
        let is_valid = verify_signature(data, &signature, &public_key).unwrap();
        assert!(is_valid);
    }

    #[test]
    fn test_verify_tampered_data_fails() {
        let key = SigningKey::generate().unwrap();
        let data = b"Original message";
        let signature = key.sign_base64(data).unwrap();
        let public_key = key.public_key_base64();

        // Tamper with data
        let tampered_data = b"Modified message";
        let is_valid = verify_signature(tampered_data, &signature, &public_key).unwrap();
        assert!(!is_valid);
    }

    #[test]
    fn test_verify_wrong_public_key_fails() {
        let key1 = SigningKey::generate().unwrap();
        let key2 = SigningKey::generate().unwrap();
        let data = b"Message";

        let signature = key1.sign_base64(data).unwrap();
        let wrong_public_key = key2.public_key_base64();

        let is_valid = verify_signature(data, &signature, &wrong_public_key).unwrap();
        assert!(!is_valid);
    }

    #[test]
    fn test_sha256_hash() {
        let data = b"Hello, World!";
        let hash = sha256_hash(data);
        assert_eq!(hash.len(), 64); // SHA-256 produces 64 hex chars
        // Known hash for "Hello, World!"
        assert_eq!(
            hash,
            "dffd6021bb2bd5b0af676290809ec3a53191dd81c7f70a4b28688a362182986f"
        );
    }

    #[test]
    fn test_encrypt_large_data() {
        let key = EncryptionKey::generate().unwrap();
        // 1MB of data
        let large_data = vec![42u8; 1024 * 1024];

        let encrypted = encrypt_data(&large_data, &key).unwrap();
        let decrypted = decrypt_data(&encrypted, &key).unwrap();

        assert_eq!(decrypted, large_data);
    }
}


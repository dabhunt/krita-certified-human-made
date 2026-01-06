# C2PA Test Certificates

This directory contains **self-signed test certificates** for C2PA manifest signing during development.

## ⚠️ Important: Test Certificates Only

These certificates are **NOT trusted by production systems**:
- ❌ Will not validate on Adobe Content Credentials Verify
- ❌ Will not validate on social media platforms
- ❌ Not suitable for production use
- ✅ Good for development and testing C2PA structure

## Files

- `chm_signing_key.pem` - RSA 4096-bit private key (KEEP SECRET!)
- `chm_cert.pem` - Self-signed X.509 certificate (valid 1 year)

## Certificate Details

```
Issuer: C=US, ST=California, L=San Francisco, O=Certified Human Made, OU=Development, CN=CHM Test Certificate
Validity: 1 year from generation date
Algorithm: RSA 4096-bit + SHA-256
```

## Security Notes

1. **Private Key Security**: The `chm_signing_key.pem` file should be kept secure. In production, this would be stored in an HSM (Hardware Security Module) or secure key vault.

2. **Git Ignore**: These files are included in the repository for MVP/testing convenience. In production, keys must NEVER be committed to version control.

3. **Regeneration**: If keys are compromised, regenerate with:
   ```bash
   openssl genrsa -out chm_signing_key.pem 4096
   openssl req -new -x509 -key chm_signing_key.pem -out chm_cert.pem -days 365 \
     -subj "/C=US/ST=California/L=San Francisco/O=Certified Human Made/OU=Development/CN=CHM Test Certificate"
   ```

## Upgrade Path to Production Certificates

For production use, artists will need to obtain trusted certificates from:

### Option 1: Commercial Certificate Authorities
- **DigiCert** ($300-400/year) - Industry standard
- **Sectigo/Comodo** ($100-200/year) - Budget option
- **GlobalSign** ($200-300/year) - Mid-range

### Option 2: Artist-Focused Certificate Providers (Future)
- Adobe Content Credentials certificates
- Wacom artist certificates
- CHM partnership programs (TBD)

### What Artists Need:
1. Purchase code signing or document signing certificate
2. Download certificate + private key
3. Configure CHM plugin with cert paths
4. Export images with signed C2PA manifests

## Testing Signed Manifests

Validate C2PA structure (even with self-signed certs) using `c2patool`:

```bash
# Install c2patool (Rust CLI)
cargo install c2patool

# Validate signed PNG
c2patool /path/to/exported_image.png

# Expected output:
# - Manifest structure will be valid
# - Signature will be present
# - Trust validation will fail (self-signed)
```

## License

These test certificates are provided for development purposes only. Production certificates must be obtained from trusted CAs.



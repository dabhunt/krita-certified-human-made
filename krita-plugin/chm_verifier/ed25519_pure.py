"""
Pure Python ED25519 Implementation (Minimal)

This is a minimal pure Python implementation of ED25519 signing.
NO external dependencies - uses only Python stdlib (hashlib).

Based on the ED25519 specification (RFC 8032).
Simplified for signing only (no verification needed for C2PA).

Uses Python 3.x integer arithmetic and hashlib.sha512.
"""

import hashlib
import os

# ED25519 curve parameters
b = 256
q = 2**255 - 19
l = 2**252 + 27742317777372353535851937790883648493

def H(m):
    """SHA-512 hash function"""
    return hashlib.sha512(m).digest()

def expmod(b, e, m):
    """Modular exponentiation"""
    if e == 0:
        return 1
    t = expmod(b, e // 2, m) ** 2 % m
    if e & 1:
        t = (t * b) % m
    return t

def inv(x):
    """Modular inverse"""
    return expmod(x, q - 2, q)

# Curve parameters
d = -121665 * inv(121666)
I = expmod(2, (q - 1) // 4, q)

def xrecover(y):
    """Recover x coordinate from y"""
    xx = (y * y - 1) * inv(d * y * y + 1)
    x = expmod(xx, (q + 3) // 8, q)
    if (x * x - xx) % q != 0:
        x = (x * I) % q
    if x % 2 != 0:
        x = q - x
    return x

# Base point
By = 4 * inv(5)
Bx = xrecover(By)
B = [Bx % q, By % q]

def edwards_add(P, Q):
    """Edwards curve point addition"""
    x1, y1 = P
    x2, y2 = Q
    x3 = (x1 * y2 + x2 * y1) * inv(1 + d * x1 * x2 * y1 * y2)
    y3 = (y1 * y2 + x1 * x2) * inv(1 - d * x1 * x2 * y1 * y2)
    return [x3 % q, y3 % q]

def scalarmult(P, e):
    """Scalar multiplication on Edwards curve"""
    if e == 0:
        return [0, 1]
    Q = scalarmult(P, e // 2)
    Q = edwards_add(Q, Q)
    if e & 1:
        Q = edwards_add(Q, P)
    return Q

def encodeint(y):
    """Encode integer as 32 bytes (little-endian)"""
    bits = [(y >> i) & 1 for i in range(b)]
    return bytes([sum([bits[i * 8 + j] << j for j in range(8)]) for i in range(b // 8)])

def encodepoint(P):
    """Encode curve point as 32 bytes"""
    x, y = P
    bits = [(y >> i) & 1 for i in range(b - 1)] + [x & 1]
    return bytes([sum([bits[i * 8 + j] << j for j in range(8)]) for i in range(b // 8)])

def bit(h, i):
    """Extract bit i from bytes h"""
    return (h[i // 8] >> (i % 8)) & 1

def publickey(sk):
    """
    Generate public key from secret key.
    
    Args:
        sk: 32-byte secret key
        
    Returns:
        32-byte public key
    """
    h = H(sk)
    a = 2 ** (b - 2) + sum(2 ** i * bit(h, i) for i in range(3, b - 2))
    A = scalarmult(B, a)
    return encodepoint(A)

def Hint(m):
    """Hash to integer (for signing)"""
    h = H(m)
    return sum(2 ** i * bit(h, i) for i in range(2 * b))

def signature(m, sk, pk):
    """
    Sign message with secret key.
    
    Args:
        m: Message bytes to sign
        sk: 32-byte secret key
        pk: 32-byte public key
        
    Returns:
        64-byte signature
    """
    h = H(sk)
    a = 2 ** (b - 2) + sum(2 ** i * bit(h, i) for i in range(3, b - 2))
    r = Hint(bytes([h[i] for i in range(b // 8, b // 4)]) + m)
    R = scalarmult(B, r)
    S = (r + Hint(encodepoint(R) + pk + m) * a) % l
    return encodepoint(R) + encodeint(S)

def sign(message, secret_key):
    """
    Sign a message using ED25519.
    
    Args:
        message: bytes to sign
        secret_key: 32-byte secret key
        
    Returns:
        64-byte signature
    """
    if len(secret_key) != 32:
        raise ValueError(f"Secret key must be 32 bytes, got {len(secret_key)}")
    
    public_key = publickey(secret_key)
    return signature(message, secret_key, public_key)


def decodepoint(s):
    """Decode 32 bytes to curve point"""
    y = sum(2 ** i * bit(s, i) for i in range(0, b - 1))
    x = xrecover(y)
    if x & 1 != bit(s, b - 1):
        x = q - x
    P = [x, y]
    return P


def decodeint(s):
    """Decode 32 bytes to integer (little-endian)"""
    return sum(2 ** i * bit(s, i) for i in range(0, b))


def verify(message, signature, public_key):
    """
    Verify an ED25519 signature.
    
    Args:
        message: bytes that were signed
        signature: 64-byte signature
        public_key: 32-byte public key
        
    Returns:
        bool: True if signature is valid, False otherwise
    """
    if len(signature) != 64:
        return False
    if len(public_key) != 32:
        return False
    
    try:
        # Decode public key
        A = decodepoint(public_key)
        
        # Decode signature
        Rs = signature[:32]
        R = decodepoint(Rs)
        S = decodeint(signature[32:])
        
        # Compute hash
        h = Hint(Rs + public_key + message)
        
        # Verify equation: [S]B = R + [H(R,A,M)]A
        # Left side
        left = scalarmult(B, S)
        
        # Right side
        right = edwards_add(R, scalarmult(A, h))
        
        # Compare
        return left == right
        
    except Exception:
        return False


def verify_pem(message, signature_b64, public_key_pem):
    """
    Verify ED25519 signature using PEM-format public key.
    
    Args:
        message: bytes that were signed
        signature_b64: base64-encoded signature
        public_key_pem: PEM-format public key
        
    Returns:
        bool: True if signature is valid
    """
    import base64
    
    # Decode signature from base64
    try:
        signature = base64.b64decode(signature_b64)
    except Exception:
        return False
    
    # Extract raw public key bytes from PEM
    # PEM format: -----BEGIN PUBLIC KEY-----\nbase64\n-----END PUBLIC KEY-----
    try:
        # Remove header/footer and whitespace
        pem_clean = public_key_pem.replace('-----BEGIN PUBLIC KEY-----', '')
        pem_clean = pem_clean.replace('-----END PUBLIC KEY-----', '')
        pem_clean = pem_clean.strip()
        
        # Decode from base64
        der_bytes = base64.b64decode(pem_clean)
        
        # DER format for ED25519 public key:
        # 30 2a (SEQUENCE, 42 bytes)
        #   30 05 (SEQUENCE, 5 bytes) - algorithm identifier
        #     06 03 2b 65 70 (OID for ED25519)
        #   03 21 (BIT STRING, 33 bytes)
        #     00 (padding)
        #     [32 bytes of actual public key]
        
        # Extract the last 32 bytes (the actual public key)
        if len(der_bytes) >= 32:
            public_key_bytes = der_bytes[-32:]
        else:
            return False
        
        # Verify signature
        return verify(message, signature, public_key_bytes)
        
    except Exception as e:
        print(f"[ED25519-VERIFY] Error parsing PEM: {e}")
        return False



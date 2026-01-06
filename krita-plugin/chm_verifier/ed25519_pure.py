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



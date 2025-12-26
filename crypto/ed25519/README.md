# Ed25519 Consensus-Critical Test Vectors

## Overview

Ed25519 is an elliptic curve signature scheme using Curve25519. While standardized in RFC 8032, the specification has ambiguities that lead to incompatible implementations. This breaks consensus in distributed systems.

An attacker can craft signatures that some implementations accept and others reject, causing network partitions or consensus forks.

This repository generates 196 test vectors (14×14 combinations) using torsion points and non-canonical encodings to expose implementation divergence as described in Henry de Valence's blog post [It's 25519AM. Do you know what your validation criteria are?](https://hdevalence.ca/blog/2020-10-04-its-25519am/). These vectors test compliance with ZIP 215, which defines explicit validation rules for consensus-critical systems.

## Notation

- Group base point: `B`
- Secret key: `a`
- Public key: `A = a·B`
- Message: `M`
- Point encoding: `P_bytes`
- Signature: `(R, s)` where:
  - `R = r·B` (commitment)
  - `s = r + k·a` (response)
  - `k = H(R_bytes || A_bytes || M)` (challenge)

## Sources of Implementation Divergence

### 1. Scalar Encoding Validation

Ed25519 signatures are 64 bytes: `sig = R_bytes || s_bytes` (32 bytes each).

Issue: Whether to reject non-canonical scalar values where `s ≥ q` (where `q` is the prime order of the curve).

- Strict: Reject signatures with `s ≥ q`
- Permissive: Accept any 32-byte scalar value

Most implementations enforce canonical scalar encoding.

### 2. Point Encoding Validation

Issue: Whether to require canonical encodings of verification key `A` and commitment point `R`.

Ed25519 points are encoded in 32 bytes as `y || sign(x)`. Point coordinates are scalars modulo `p = 2^255 - 19`. Non-canonical encodings arise from:

- Non-canonical y-coordinates: Values `y ∈ [p, p+18]` that represent `y mod p ∈ [0, 18]`. Only a subset correspond to valid curve points.
- Non-canonical sign bits: For points where `x = 0` (implying `y = ±1`), the sign bit is technically unconstrained since `-0 = 0`. Canonical encoding uses sign bit 0.

This affects verification because the Fiat-Shamir challenge `k = H(R_bytes || A_bytes || M)` is computed over encoded points. Implementations that skip validation when computing `k` may accept non-canonical encodings.

### 3. Equality Checking

Issue: How to compare points in the verification equation.

- Algebraic: Direct point comparison
- Byte-wise: Compare encoded byte strings after re-encoding

Since encoding produces canonical representations, non-canonical `R_bytes` may fail byte-wise comparison even when `R' = R` algebraically.


### 4. Verification Equation

Issue: Different verification equations accept different signatures.

- Unbatched: `[s]B = R + [k]A`
- Cofactor-8: `[8][s]B = [8]R + [8][k]A`

The cofactor-8 equation projects to the prime-order subgroup, which eliminates torsion components.

#### Why Batch Verification Requires Cofactor Multiplication

Curve25519 has group structure ℤ/qℤ × ℤ/8ℤ. Every point decomposes into a prime-order component plus a torsion component. Scalar arithmetic in Ed25519 only works correctly on the prime-order subgroup.

Without cofactor multiplication, batch verification breaks:

1. Random batch coefficients can cancel torsion components unpredictably.
2. Verification results depend on which signatures you batch together.
3. A signature can pass individual verification but fail when "batched" alone, since implementations may compute `k mod q` before multiplication, changing divisibility by 8.

Multiplying by 8 projects to the prime-order subgroup where `[8]T = 0` for any torsion point T, giving consistent results regardless of how you batch.

## ZIP 215 Validation Rules

ZIP 215 specifies explicit validation for consensus-critical applications:

1. `A` and `R` must be encodings of points on Ed25519
2. `s < q` (canonical scalar encoding)
3. Non-canonical point encodings permitted (y-coordinates need not be reduced mod `p`)
4. Cofactor-8 verification equation `[8][s]B = [8]R + [8][k]A` required

Compliant implementations:
- [`ed25519-zebra`](https://github.com/ZcashFoundation/ed25519-zebra) (Rust)
- [`ed25519-consensus`](https://github.com/penumbra-zone/ed25519-consensus) (Rust)
- [`ed25519consensus`](https://github.com/hdevalence/ed25519consensus) (Go)

## References

- [RFC 8032: Edwards-Curve Digital Signature Algorithm (EdDSA)](https://www.rfc-editor.org/rfc/rfc8032)
- [It's 25519AM. Do you know what your validation criteria are?](https://hdevalence.ca/blog/2020-10-04-its-25519am/) (Henry de Valence)
- [ZIP 215: Explicit Ed25519 Validation Rules](https://zips.z.cash/zip-0215)

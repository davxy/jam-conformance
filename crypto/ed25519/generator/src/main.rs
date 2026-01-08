//! Ed25519 Consensus-Critical Test Vector Generator
//!
//! Generates 196 test vectors that expose implementation divergence in Ed25519 signature
//! verification libraries, which can cause consensus forks in distributed systems.
//!
//! ## Test Vector Construction
//!
//! Creates 14×14 = 196 test cases combining:
//! - **8 canonical encodings**: Compressed points from the 8-torsion subgroup (EIGHT_TORSION)
//! - **6 non-canonical encodings**: Valid points with non-reduced y-coordinates or non-canonical sign bits
//!
//! Based on Henry de Valence's post:
//! [It's 25519AM. Do you know what your validation criteria are?](https://hdevalence.ca/blog/2020-10-04-its-25519am/)
//!
//! ## Implementation Divergence
//!
//! The test vectors expose differences in:
//! 1. **Point encoding validation**: Whether non-canonical encodings are accepted
//! 2. **Torsion handling**: Whether signatures with torsion components pass verification
//! 3. **Verification equation**: Unbatched (`R = [s]B - [k]A`) vs batched (`[8]R = [8]([s]B - [k]A)`)
//!
//! ZIP 215-compliant implementations (ed25519-consensus, ed25519-zebra) accept all 196 vectors,
//! while stricter implementations (libsodium, ring, dalek) reject most non-canonical cases.

use curve25519_dalek::constants::EIGHT_TORSION;
use curve25519_dalek::edwards::CompressedEdwardsY;
use serde::{Deserialize, Serialize};

// Test vectors file
const VECTORS_FILE: &str = "vectors.json";

/// Generate 19 non-canonical field element encodings
///
/// These represent values in the range [p, p+18] where p = 2^255 - 19
fn non_canonical_field_encodings() -> Vec<[u8; 32]> {
    // p = 2^255 - 19 in byte representation (big-endian)
    // p = 0x7fffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffed
    // p+i for i in [0..18] can be represented as:
    // [237+i, 255, 255, ..., 255, 127] where we increment the first byte

    // little-endian
    let mut bytes = [
        237, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255,
        255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 127,
    ];

    let mut encodings = Vec::new();
    for i in 0..19u8 {
        bytes[0] = 237 + i;
        encodings.push(bytes);
    }
    encodings
}

/// Generate non-canonical point encodings
///
/// Returns approximately 25 encodings, but we only use the first 6 for the test vectors
fn non_canonical_point_encodings() -> Vec<[u8; 32]> {
    let mut encodings = Vec::new();

    // Explicit encodings for y=1 and y=-1 with non-canonical sign bits
    //
    // y=1 with sign bit set
    let y1_noncanonical_sign_bit = [
        1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
        0, 128,
    ];
    encodings.push(y1_noncanonical_sign_bit);

    // y=-1 with sign bit set
    let ym1_noncanonical_sign_bit = [
        236, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255,
        255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255, 255,
    ];
    encodings.push(ym1_noncanonical_sign_bit);

    let mut process_bytes = |bytes| {
        if let Some(point) = CompressedEdwardsY(bytes).decompress() {
            // Check that it's actually non-canonical
            assert_ne!(bytes, point.compress().to_bytes());
            encodings.push(bytes);
        }
    };

    // Try non-canonical field element encodings
    for mut bytes in non_canonical_field_encodings() {
        process_bytes(bytes);
        bytes[31] |= 128; // Try with sign bit set
        process_bytes(bytes);
    }

    encodings
}

#[derive(Serialize, Deserialize)]
struct TestVector {
    /// Index of the test case
    number: u8,
    /// Description of the test case
    desc: String,
    /// Public key A (32 bytes hex)
    pk: String,
    /// Commitment R (32 bytes hex)
    r: String,
    /// Scalar s (32 bytes hex, always 0 in our case)
    s: String,
    /// Message (hex)
    msg: String,
    /// Whether A encoding is canonical
    pk_canonical: bool,
    /// Whether R encoding is canonical
    r_canonical: bool,
}

fn main() {
    println!("Generating ZIP-215 test-vectors...");

    // Generate 8 canonical encodings from the torsion points
    let canonical_encodings: Vec<[u8; 32]> = EIGHT_TORSION
        .iter()
        .map(|point| point.compress().to_bytes())
        .collect();
    println!(
        "* Generated {} canonical encodings for the 8-torsion points",
        canonical_encodings.len()
    );

    // Generate non-canonical encodings (we pick the first 6)
    let all_non_canonical = non_canonical_point_encodings();
    let non_canonical_encodings: Vec<[u8; 32]> = all_non_canonical.into_iter().take(6).collect();
    println!(
        "* Generated {} non-canonical encodings (from {} total)",
        non_canonical_encodings.len(),
        non_canonical_point_encodings().len()
    );

    // Combine all encodings: 8 canonical + 6 non-canonical = 14 total
    let mut all_encodings: Vec<([u8; 32], bool, String)> = Vec::new();

    for (i, enc) in canonical_encodings.iter().enumerate() {
        all_encodings.push((*enc, true, format!("canonical-{}", i)));
    }

    for (i, enc) in non_canonical_encodings.iter().enumerate() {
        all_encodings.push((*enc, false, format!("non-canonical-{}", i)));
    }

    // Generate all 14 × 14 = 196 combinations
    let mut test_vectors = Vec::new();
    let mut counter = 0;

    for (r_bytes, r_canonical, r_desc) in &all_encodings {
        for (a_bytes, a_canonical, a_desc) in &all_encodings {
            counter += 1;
            let test_vector = TestVector {
                number: counter,
                pk: hex::encode(a_bytes),
                r: hex::encode(r_bytes),
                s: hex::encode([0u8; 32]),
                msg: hex::encode("dummy"),
                pk_canonical: *a_canonical,
                r_canonical: *r_canonical,
                desc: format!("R: {} | A: {} | s=0", r_desc, a_desc),
            };

            test_vectors.push(test_vector);
        }
    }

    println!("Generated {} test vectors", test_vectors.len());

    // Output to JSON
    let json = serde_json::to_string_pretty(&test_vectors).unwrap();
    std::fs::write(VECTORS_FILE, json).unwrap();

    println!("Test vectors written to {VECTORS_FILE}");
}

#[cfg(test)]
mod tests {
    use super::*;

    /// Test result tracking
    struct TestResults {
        passed: usize,
        failed: usize,
    }

    impl TestResults {
        fn new() -> Self {
            Self {
                passed: 0,
                failed: 0,
            }
        }

        fn print_summary(&self, impl_name: &str, total: usize) {
            println!("\n=== {} Results ===", impl_name);
            println!("Total: {}", total);
            println!("Passed: {}", self.passed);
            println!("Failed: {}", self.failed);
        }
    }

    /// Decoded test vector components
    struct DecodedTestVector {
        vk_array: [u8; 32],
        sig_bytes: [u8; 64],
        message: Vec<u8>,
    }

    /// Load test vectors from JSON file
    fn load_test_vectors() -> Vec<TestVector> {
        let json_data = std::fs::read_to_string(VECTORS_FILE)
            .expect("Failed to read {VECTORS_FILE}. Run the binary first to generate it.");
        serde_json::from_str(&json_data).expect("Failed to parse {VECTORS_FILE}")
    }

    /// Decode a test vector into byte arrays
    fn decode_test_vector(tv: &TestVector) -> DecodedTestVector {
        let vk_bytes = hex::decode(&tv.pk).expect("Invalid public key hex");
        let r_bytes = hex::decode(&tv.r).expect("Invalid R hex");
        let s_bytes = hex::decode(&tv.s).expect("Invalid s hex");
        let message = hex::decode(&tv.msg).expect("Invalid message hex");

        // Construct the signature: sig = R || s (64 bytes)
        let mut sig_bytes = [0u8; 64];
        sig_bytes[0..32].copy_from_slice(&r_bytes);
        sig_bytes[32..64].copy_from_slice(&s_bytes);

        // Construct the verification key (32 bytes)
        let mut vk_array = [0u8; 32];
        vk_array.copy_from_slice(&vk_bytes);

        DecodedTestVector {
            vk_array,
            sig_bytes,
            message,
        }
    }

    /// Verification result
    #[derive(Debug)]
    enum Error {
        Verification,
        ParseKey,
        ParseSig,
    }

    /// Run tests with a custom verifier function
    fn run_test_suite<F>(impl_name: &str, mut verifier: F)
    where
        F: FnMut(&DecodedTestVector) -> Result<(), Error>,
    {
        let test_vectors = load_test_vectors();
        println!(
            "Testing {} test vectors with '{impl_name}'",
            test_vectors.len(),
        );

        let mut results = TestResults::new();

        for tv in &test_vectors {
            let decoded = decode_test_vector(tv);

            match verifier(&decoded) {
                Ok(_) => {
                    results.passed += 1;
                    println!("✓ Test {}: PASS - {}", tv.number, tv.desc);
                }
                Err(err) => {
                    results.failed += 1;
                    println!("✗ Test {}: FAIL - {} ({err:?} error)", tv.number, tv.desc);
                }
            }
        }

        results.print_summary(impl_name, test_vectors.len());
        assert_eq!(results.failed, 0);
    }

    #[test]
    fn test_vectors_with_ed25519_consensus() {
        use ed25519_consensus::{Signature, VerificationKey};

        run_test_suite("ed25519-consensus", |decoded| {
            let vk = VerificationKey::try_from(decoded.vk_array).map_err(|_| Error::ParseKey)?;
            let sig = Signature::try_from(decoded.sig_bytes).map_err(|_| Error::ParseSig)?;
            vk.verify(&sig, &decoded.message)
                .map_err(|_| Error::Verification)
        });
    }

    #[test]
    fn test_vectors_with_ed25519_dalek_strict() {
        use ed25519_dalek::{Signature, VerifyingKey};

        run_test_suite("ed25519-dalek-strict", |decoded| {
            let vk = VerifyingKey::from_bytes(&decoded.vk_array).map_err(|_| Error::ParseKey)?;
            let sig = Signature::from_bytes(&decoded.sig_bytes);
            vk.verify_strict(&decoded.message, &sig)
                .map_err(|_| Error::Verification)
        });
    }

    #[test]
    fn test_vectors_with_ed25519_dalek() {
        use ed25519_dalek::{Signature, Verifier, VerifyingKey};

        run_test_suite("ed25519-dalek", |decoded| {
            let vk = VerifyingKey::from_bytes(&decoded.vk_array).map_err(|_| Error::ParseKey)?;
            let sig = Signature::from_bytes(&decoded.sig_bytes);
            vk.verify(&decoded.message, &sig)
                .map_err(|_| Error::Verification)
        });
    }

    #[test]
    fn test_vectors_with_ed25519_zebra() {
        use ed25519_zebra::{Signature, VerificationKey};

        run_test_suite("ed25519-zebra", |decoded| {
            let vk = VerificationKey::try_from(decoded.vk_array).map_err(|_| Error::ParseKey)?;
            let sig = Signature::try_from(decoded.sig_bytes).map_err(|_| Error::ParseSig)?;
            vk.verify(&sig, &decoded.message)
                .map_err(|_| Error::Verification)
        });
    }

    #[test]
    fn test_vectors_with_ed25519_zebra_v1() {
        use ed25519_zebra_v1::{Signature, VerificationKey};

        run_test_suite("ed25519-zebra v1.0.0", |decoded| {
            let vk = VerificationKey::try_from(decoded.vk_array).map_err(|_| Error::ParseKey)?;
            let sig = Signature::try_from(decoded.sig_bytes).map_err(|_| Error::ParseSig)?;
            vk.verify(&sig, &decoded.message)
                .map_err(|_| Error::Verification)
        });
    }

    // Wrapper for BoringSSL (OpenSSL fork)
    #[test]
    fn test_vectors_with_ring() {
        use ring::signature::{UnparsedPublicKey, ED25519};

        run_test_suite("ring", |decoded| {
            let vk = UnparsedPublicKey::new(&ED25519, &decoded.vk_array);
            vk.verify(&decoded.message, &decoded.sig_bytes)
                .map_err(|_| Error::Verification)
        });
    }

    #[test]
    fn test_vectors_with_sodiumoxide() {
        use sodiumoxide::crypto::sign::ed25519;

        sodiumoxide::init().expect("Failed to initialize sodiumoxide");

        run_test_suite("sodiumoxide (libsodium)", |decoded| {
            let vk = ed25519::PublicKey::from_slice(&decoded.vk_array).ok_or(Error::ParseKey)?;
            let sig =
                ed25519::Signature::from_bytes(&decoded.sig_bytes).map_err(|_| Error::ParseSig)?;
            ed25519::verify_detached(&sig, &decoded.message, &vk)
                .then(|| ())
                .ok_or(Error::Verification)
        });
    }

    #[test]
    fn test_vectors_with_ed25519_compact() {
        use ed25519_compact::{PublicKey, Signature};

        run_test_suite("ed25519-compact", |decoded| {
            let vk = PublicKey::from_slice(&decoded.vk_array).map_err(|_| Error::ParseKey)?;
            let sig = Signature::from_slice(&decoded.sig_bytes).map_err(|_| Error::ParseSig)?;
            vk.verify(&decoded.message, &sig)
                .map_err(|_| Error::Verification)
        });
    }
}

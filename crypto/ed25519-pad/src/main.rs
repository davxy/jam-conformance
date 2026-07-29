//! Derives a second edwards25519 generator with unknown discrete log, by
//! try-and-increment over SHA-512 of a domain string.
//!
//! What does matter is clearing the cofactor. A decompressed point lives in the
//! full group of order 8*l, so roughly 7 candidates in 8 carry a torsion
//! component.
//!
//! `--raw` skips that multiplication and takes the hash-derived y as the
//! generator directly. The encoding is then the hash itself, so anyone with
//! SHA-512 can confirm it without touching curve arithmetic — at the price of
//! keeping whatever torsion the candidate came with, which is 7 cases in 8.

use curve25519_dalek::edwards::{CompressedEdwardsY, EdwardsPoint};
use num_bigint::BigUint;
use sha2::{Digest, Sha512};

/// Domain string the generator is derived from, unless one is given on the
/// command line.
const DOMAIN: &str = "jam_banned_key";

/// p = 2^255 - 19, little-endian.
const P_BYTES: [u8; 32] = {
    let mut p = [0xffu8; 32];
    p[0] = 0xed;
    p[31] = 0x7f;
    p
};

/// Is the candidate y-coordinate canonical, i.e. y < p?
fn y_is_canonical(y: &[u8; 32]) -> bool {
    for i in (0..32).rev() {
        if y[i] != P_BYTES[i] {
            return y[i] < P_BYTES[i];
        }
    }
    false // y == p
}

/// SHA-512(domain || counter), low 32 bytes as a y-coordinate with the sign bit
/// of x forced to zero, first counter that decompresses, then times 8 to clean
/// the cofactor — unless `raw`, in which case the candidate is taken as it is and
/// its encoding stays equal to the hash.
fn derive(domain: &[u8], raw: bool) -> (EdwardsPoint, u8) {
    for counter in 0u8..=255 {
        let digest = Sha512::new().chain(domain).chain([counter]).finalize();

        let mut y = [0u8; 32];
        y.copy_from_slice(&digest[..32]);
        y[31] &= 0x7f;

        if !y_is_canonical(&y) {
            continue;
        }

        // x^2 = (y^2 - 1)/(d*y^2 + 1) is a non-square for about half of all y.
        let Some(candidate) = CompressedEdwardsY(y).decompress() else {
            continue;
        };

        // Clean cofactor, or keep the candidate so that its encoding is the hash.
        let point = if raw {
            candidate
        } else {
            candidate.mul_by_cofactor()
        };

        // With the cofactor cleared this can only be the identity, since [8]C is
        // in the prime-order subgroup. Raw keeps order 2, 4 and 8 in play too, so
        // ask the stronger question; both are one hash in ~2^249 territory.
        if point.is_small_order() {
            continue;
        }

        return (point, counter);
    }

    unreachable!("256 consecutive rejections has probability ~2^-256")
}

/// Affine coordinates, recovered from the canonical encoding rather than read
/// out of the curve library, which keeps them private anyway.
///
/// Returns (compressed, x, y).
fn affine(point: &EdwardsPoint) -> ([u8; 32], BigUint, BigUint) {
    let compressed = point.compress().to_bytes();
    let x_is_odd = compressed[31] >> 7 == 1;
    let mut y_bytes = compressed;
    y_bytes[31] &= 0x7f;

    let p = (BigUint::from(1u32) << 255u32) - 19u32;
    // Both derived rather than pasted: d = -121665/121666, sqrt(-1) = 2^((p-1)/4).
    let d = (&p - 121665u32) * BigUint::from(121666u32).modpow(&(&p - 2u32), &p) % &p;
    let sqrt_m1 = BigUint::from(2u32).modpow(&((&p - 1u32) >> 2u32), &p);

    let y = BigUint::from_bytes_le(&y_bytes);
    let yy = &y * &y % &p;
    let xx = (&yy + &p - 1u32) * (&d * &yy + 1u32).modpow(&(&p - 2u32), &p) % &p;

    // p = 5 mod 8, so a^((p+3)/8) is a square root of a up to a factor sqrt(-1).
    let mut x = xx.modpow(&((&p + 3u32) >> 3u32), &p);
    if &x * &x % &p != xx {
        x = x * &sqrt_m1 % &p;
    }
    // The sign bit encodes the parity of x, and the roots are x and p - x.
    if x.bit(0) != x_is_odd {
        x = &p - &x;
    }

    (compressed, x, y)
}

fn hex_le(v: &BigUint) -> String {
    let mut bytes = [0u8; 32];
    let le = v.to_bytes_le();
    bytes[..le.len()].copy_from_slice(&le);
    hex::encode(bytes)
}

fn usage(complaint: &str) -> ! {
    eprintln!("{complaint}");
    eprintln!("usage: derive-generator [--raw] [domain-string]");
    eprintln!("quote the domain; it selects the point");
    eprintln!("--raw  take the hash-derived y as the generator directly, skipping the");
    eprintln!("       cofactor step, so the encoding is the hash and torsion is kept");
    std::process::exit(1)
}

fn main() {
    let args: Vec<String> = std::env::args().skip(1).collect();
    let mut raw = false;
    let mut domain = None;
    for arg in &args {
        match arg.as_str() {
            "--raw" => raw = true,
            flag if flag.starts_with('-') => usage(&format!("unknown flag {flag:?}")),
            // Reject a second positional rather than taking the first: an unquoted
            // multi-word domain would otherwise silently derive from its first word,
            // and the domain is the one input that picks the point.
            _ if domain.is_some() => usage("more than one domain string"),
            positional => domain = Some(positional),
        }
    }
    let domain = domain.unwrap_or(DOMAIN);

    let (point, counter) = derive(domain.as_bytes(), raw);
    let (compressed, x, y) = affine(&point);

    println!("domain      {:?}", domain);
    println!("counter     {}", counter);
    if raw {
        println!(
            "mode        raw, y is the hash (torsion free: {})",
            point.is_torsion_free()
        );
    }
    println!("x (le)      {}", hex_le(&x));
    println!("y (le)      {}", hex_le(&y));
    println!("compressed  {}", hex::encode(compressed));
}

#[cfg(test)]
mod tests {
    use super::*;

    /// Pins the default derivation to the hash it comes from.
    ///
    /// The compressed point is not SHA-512(DOMAIN || 0). The low 32 bytes of that
    /// hash are the *candidate* y; the point is that candidate times 8, and the
    /// cofactor step lands on an unrelated encoding. The chain below is the
    /// relationship that actually holds.
    #[test]
    fn default_domain_derivation() {
        let digest = Sha512::new().chain(DOMAIN.as_bytes()).chain([0u8]).finalize();
        let mut candidate_y = [0u8; 32];
        candidate_y.copy_from_slice(&digest[..32]);
        candidate_y[31] &= 0x7f;
        assert_eq!(
            hex::encode(candidate_y),
            "b3c218d8319b04d0ae6098db9abbfafb10c8010973c1f35f5833d4557bfd4b00"
        );

        let (point, counter) = derive(DOMAIN.as_bytes(), false);
        assert_eq!(counter, 0, "the default domain is picked to land on counter 0");

        // The point is [8] applied to the counter-0 candidate, nothing else.
        let candidate = CompressedEdwardsY(candidate_y)
            .decompress()
            .expect("counter 0 decompresses, which is why it is counter 0");
        assert_eq!(point, candidate.mul_by_cofactor());

        // Pinned bytes. x guards the recovery arithmetic, which has no runtime check.
        let (compressed, x, y) = affine(&point);
        assert_eq!(
            hex::encode(compressed),
            "d86b4edf12b3b277e51e2e77de072b1a3238c615f1bb4fdad041b09352dec69f"
        );
        assert_eq!(
            hex_le(&x),
            "cb1c83c131224e5d7daff04dcb23ff2cea5db86e534de9f0595f67380d220b4c"
        );
        assert_eq!(
            hex_le(&y),
            "d86b4edf12b3b277e51e2e77de072b1a3238c615f1bb4fdad041b09352dec61f"
        );
    }

    /// The property `--raw` exists for: the encoding *is* the hash.
    ///
    /// Note what this does and does not buy. It pins the default domain's hash
    /// bytes, and it documents the contract executably. It is not a check on
    /// arithmetic: with the sign bit cleared and y canonical, compress(decompress(y))
    /// returns y for free. The point keeps its torsion, which is the trade.
    #[test]
    fn raw_mode_encoding_is_the_hash() {
        let (point, counter) = derive(DOMAIN.as_bytes(), true);
        assert_eq!(counter, 0);

        let digest = Sha512::new()
            .chain(DOMAIN.as_bytes())
            .chain([counter])
            .finalize();
        let mut expected = [0u8; 32];
        expected.copy_from_slice(&digest[..32]);
        expected[31] &= 0x7f;

        let (compressed, _, _) = affine(&point);
        assert_eq!(compressed, expected);
        assert_eq!(
            hex::encode(compressed),
            "b3c218d8319b04d0ae6098db9abbfafb10c8010973c1f35f5833d4557bfd4b00"
        );
    }
}

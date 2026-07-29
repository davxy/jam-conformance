//! Derives a second edwards25519 generator with unknown discrete log, by
//! try-and-increment over SHA-512 of a domain string.
//!
//! What does matter is clearing the cofactor. A decompressed point lives in the
//! full group of order 8*l, so roughly 7 candidates in 8 carry a torsion
//! component.

use curve25519_dalek::{
    edwards::{CompressedEdwardsY, EdwardsPoint},
    traits::IsIdentity,
};
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
/// the cofactor.
fn derive(domain: &[u8]) -> (EdwardsPoint, u8) {
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

        // Clean cofactor
        let point = candidate.mul_by_cofactor();

        // Only if the candidate was one of the 8 torsion points.
        if point.is_identity() {
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

fn main() {
    let args: Vec<String> = std::env::args().skip(1).collect();
    // Not `nth(1)`: an unquoted multi-word domain would silently derive from its
    // first word, and the domain is the one input that picks the point.
    let domain: &str = match args.as_slice() {
        [] => DOMAIN,
        [domain] => domain,
        _ => {
            eprintln!("usage: derive-generator [domain-string]");
            eprintln!("quote it; the domain string selects the point");
            std::process::exit(1);
        }
    };

    let (point, counter) = derive(domain.as_bytes());
    let (compressed, x, y) = affine(&point);

    println!("domain      {:?}", domain);
    println!("counter     {}", counter);
    println!("x (le)      {}", hex_le(&x));
    println!("y (le)      {}", hex_le(&y));
    println!("compressed  {}", hex::encode(compressed));
}

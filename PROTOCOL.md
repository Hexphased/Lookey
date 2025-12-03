# CIVCOCTAIL Protocol Specification
* Version: 1.0.0
* Status: Active Implementation

## 1. Abstract
The CIVCOCTAIL (Cryptographic Image Verification, Chain Of Custody, Timestamping And Identity Ledger) protocol is a decentralized standard for embedding provenance data into digital images. It utilizes a hybrid approach of Cryptographic Metadata for integrity and Frequency Domain Steganography for resilience against social media compression.

## 2. Identity & Keys
The protocol relies on Ed25519 (Edwards-curve Digital Signature Algorithm) for identity generation.
*   Keys: Ed25519 Keypair (Private/Public).
*   Distribution: Users share their Public Key via an Invite Code (Base64 JSON blob).
*   Verification: There is no central authority. Identity is verified against a local "Web of Trust" (Contact List).

## 3. The Deep Embed (Lookey Mark)
The "Lookey Mark" is an 8-character string embedded into the image's frequency domain.

### 3.1 Payload Structure
The payload consists of exactly 8 ASCII characters (64 bits).

| Byte Offset | Length | Name | Description |
| :--- | :--- | :--- | :--- |
| 0 - 3 | 4 chars | Identity Hash | The first 4 characters of the SHA-256 hash of the Signer's Public Key (Hex). |
| 4 - 7 | 4 chars | Timestamp | A custom Base36 encoded time value. |

### 3.2 Timestamp Encoding
Time is stored as "Ticks" since the Epoch.
*   Epoch: `2025-01-01 00:00:00`
*   Resolution: 5 Minutes per Tick.
*   Calculation: `(Current_Time - Epoch) / 5 minutes`
*   Encoding: Converted to Base36 `[0-9, a-z]`.
*   Capacity: Approximately 16 years.

### 3.3 Transport Layer (Embedding)
*   Algorithm: Discrete Wavelet Transform (DWT) variant `dwtDct`.
*   Signal Injection: Synchronized modification of RGB channels (Grayscale Noise) to modulate luminance without introducing chromatic artifacts.
*   Adaptive Strength: The embedding strength scales based on image texture (Standard Deviation) to prevent visual degradation.
*   Entropy Threshold: If the image texture is insufficient for watermarking (e.g., solid white or flat vector art), the protocol mandates an abort of the Deep Embed process to preserve visual fidelity, falling back to Metadata Signing only.

## 4. The Metadata Layer (Standard Sign)
For strict integrity verification, a JSON object is injected into the file structure.

*   Format: JSON.
*   Location:
    *   JPEG: `Exif.Photo.UserComment`
    *   PNG: `tEXt` chunk labeled `LookeyData`
*   Schema:
    ```json
    {
      "lookey_version": "1.0",
      "payload": {
        "pixel_hash": "SHA256 hash of image pixel data",
        "timestamp": "ISO 8601 UTC String",
        "author": "Display Name"
      },
      "signature": "Base64 encoded Ed25519 signature of the payload",
      "signer_pubkey": "Base64 encoded Public Key"
    }
    ```

## 5. Verification Logic
A compliant verifier must follow this hierarchy:

1.  Check Metadata:
    *   If present, verify the Cryptographic Signature against the `pixel_hash`.
    *   Match: Integrity Confirmed (Green).
    *   Mismatch: Tamper Detected (Red).

2.  Check Deep Embed:
    *   If Metadata is missing, scan for DWT watermarks.
    *   Compare the found `Identity Hash` (Bytes 0-3) against the local Contact List.
    *   Hamming Distance: Allow a bit-error tolerance of < 6 bits to account for compression artifacts while maintaining identity strictness.
    *   Match: Source Confirmed (Purple).

## 6. Implementation Notes
*   Reference Implementation: [Lookey](https://github.com/Hexphased/Lookey)
*   The protocol is designed for Source Verification. Verification should ideally be performed on the original signed file hosted on a compliant file host (GitHub, Drive). Social media feeds that heavily compress images or strip color profiles may destroy the DWT grid.

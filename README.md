# Lookey
The Official Implementation of the CIVCOCTAIL Protocol
(Cryptographic Image Verification, Chain Of Custody, Timestamping And Identity Ledger)

![Lookey Logo](assets/logo.png)

**Lookey** is a decentralized identity tool designed to cryptographically verify the authorship of images. It tackles the "Metadata Problem":

**Most social media platforms (Discord, Twitter) strip EXIF data to save bandwidth, destroying traditional digital signatures.**

Lookey solves this by implementing **Invisible Frequency Watermarking (Steganography)** alongside standard **Ed25519 Cryptography**.

---

## Features

*   **Deep Embed (Lookey Mark):** Uses **Discrete Wavelet Transforms (DWT)** to hide your identity hash inside the image frequency waves. This allows the signature to survive re-encoding, PNG compression, and platform uploads that preserve PNG format. **Note: Conversion to JPEG will destroy the watermark.**
*   **Standard Sign:** Injects a standard cryptographic signature into the file metadata (EXIF or PNG Chunks).
*   **Adaptive Logic:** Lookey analyzes the image texture before signing.
    *   *Photos/Complex UI/Colorful artwork/images with big color variety:* Signed invisibly using DWT.
    *   *Flat Images/White Backgrounds:* Automatically falls back to **Standard Signing** to prevent visual artifacts (grain).
*   **Time-Lock Protocol:** Every signature includes a **5-minute precision timestamp** embedded into the watermark, preventing replay attacks.
*   **Web of Trust:** No central servers. You verify images against your own local Contact List.

Deep Embed signatures are designed to be invisible. However, in some cases (high-strength signing), microscopic grain may be visible if zoomed in to 300-500%. This is normal and required for the signal to survive compression on certain platforms.

---

## Social Media Survival Guide

Not all platforms treat images equally. Lookey is designed to be as robust as physically possible, but platform compression varies.

| Platform | Status | Deep Embed Survival | Notes |
| :--- | :--- | :--- | :--- |
| **GitHub / Drive / DropBox** | **Safe** | **100%** | Hosts raw binary files. Metadata & Deep Embed both survive. Use these as a fallback when your target platform strips off both marks. |
| **Reddit, Imgur** | **Safe** | **High** | Lookey Mark survives in most images.|
| **Discord** | **Mixed** | **Medium** | Compression is rougher, but Lookey Mark survives in many cases. |
| **Twitter (X)** | **Hostile** | **Low** | Aggressively converts images to low-res JPEG. PNG format is kept for images under the resolution of 900x900, but even then both marks may be destroyed. Unreliable, and sometimes dependent on factors outside of user's control. **Use a link to GitHub/Imgur/DropBox for verification.** |

---

## Forensic Report Guide

When verifying an image, Lookey provides a report of both layers.

### 1. `Metadata: VALID`
The file has not been modified since signing, and the metadata has not been wiped. The cryptographic signature matches the author. This is the strongest form of proof.

### 2. `Deep Embed: FOUND`
The invisible watermark was detected. Even if metadata was stripped (e.g., by Reddit), this proves the image content originated from the author and provides an approximate timestamp of the signing.

### 3. `Deep Embed: UNKNOWN ID`
A watermark was detected, but the identity doesn't match anyone in your contacts.
**Possible causes:**

- `ffffff` or `000000` patterns: Image too bright/dark for embedding
- Random hex patterns (e.g., `a3f7b2`): Signal corruption from heavy compression
- Actual unknown author: Valid mark from someone not in your contact list
  
**Note:** Lookey tries to avoid embedding on vulnerable images, but platform 
compression can still rarely corrupt previously-valid marks.

### 4. `Deep Embed: Missing` (on a Signed File)
Lookey recognized the file as too fragile to withstand deep embedding, and defaulted to metadata signing only. If uploaded to a site that strips metadata (X), both proofs may be lost. Ensure you have a fallback host (GitHub/Drive/DropBox) available for these files if you wish to prove authorship.

### 5. `Metadata: INVALID (Pixels Modified)`
The file contains a Metadata signature, but the pixels have been altered after signing. The Lookey Mark may still identify the original author, but the content cannot be trusted.

---

## Threat Model & Defense Scenarios

How Lookey protects creators in adversarial situations. Involving Alice (Creator) and Bob (Attacker).

### Scenario 1: The "Smear Campaign" (Tampering)
Bob downloads Alice's signed art from Twitter (where metadata is stripped), adds offensive text, and reposts it to frame her.
*   **Lookey verification:** **Source Confirmed - Alice** (It confirms Alice created the base canvas).
*   **Defense:** Alice produces her Originally-signed File (hosted on GitHub/Drive). It displays **Verified Authentic**.

Since Bob cannot produce a **Verified** version of his offensive edit (he lacks Alice's private key to sign the new pixels), the offensive image is proven to be a modified fork with broken integrity. Lookey proves Alice made the original, not the edit.

### Scenario 2: The "Repost" (Theft)
Bob downloads Alice's art from Discord (where metadata is stripped, but Lookey Mark remains) and posts it on Reddit claiming it is his.
The **Deep Embed** (Lookey Mark) survives the platform transition.
*   **Lookey Verification:** **Source Confirmed - Alice.**

Anyone verifying Bob's post will see Alice's name embedded in the image frequencies. Bob cannot remove this without re-signing the image with his own key, which will overwrite the original timestamp.

### Scenario 3: The "Squatter" (Time Paradox)
Alice posts an **unsigned** image. Bob downloads it, signs it with *his* Lookey Key, and claims he is the original creator.
*   **Defense:** **Temporal Precedence.**
*   **Result:** **Alice Wins.**

Bob's signature timestamp will necessarily be *later* than Alice's original public post. It is impossible to cryptographically sign a file before you possess it. Alice's upload date (on Twitter/Blog) serves as the "Prior Art" proof, proving Bob signed a file that already existed.

Lookey cannot stop people from right-clicking. It **can** provide indisputable mathematical proof of who owned the file first.

---

## Installation

### Option A: The Binary (Windows)
Download the latest `Lookey.exe` from the **[Releases Page](https://github.com/Hexphased/Lookey/releases/latest)**. No Python required. Just unzip and run.

### Option B: Run from Source (Python)
Requirements: Python 3.10+

1.  **Clone the repo:**
    ```bash
    git clone https://github.com/Hexphased/Lookey.git
    cd Lookey
    ```
2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
3.  **Run the GUI:**
    ```bash
    python lookey_gui.py
    ```

---

## Quick Start

1.  **Setup:** Enter your Display Name to generate your keys. This name will be used to map your public key to your identity when passing invite codes and verifying your images.
2.  **Deep Embed:** Use this for images you plan to share online. It attempts to apply both Metadata and Invisible Watermarks.
3.  **Verify:** Send any image into Lookey to check its origin and whether it is signed.
4.  **Share Identity:** Click "Show Invite QR" to let others verify your work, or copy your Lookey invite link to allow others to add you to their contact list.

---

## Try It Yourself

In the `assets` folder of this repository, you will find the Lookey icon (logo.png), and an additional `BeautifulAurora.png` image. These are signed by the creator (Hexicon), and can be freely downloaded to test the application's functionality.

To verify them as **Trusted**, add my identity to your contact list using this Invite Code:
```
eyJ2IjogMSwgIm5hbWUiOiAiSGV4aWNvbiIsICJrZXkiOiAiTFMwdExTMUNSVWRKVGlCUVZVSk1TVU1nUzBWWkxTMHRMUzBLVFVOdmQwSlJXVVJMTWxaM1FYbEZRUzlOUjNSMWFERXlaVmhqWjNKbldYaHRRbkoyTW5WQ1RrdzNTSEZsVVhOWU9ITXpTSHBhT1hGWk4xazlDaTB0TFMwdFJVNUVJRkJWUWt4SlF5QkxSVmt0TFMwdExRbz0ifQ==
```

Using the CLI version:
`lookey_cli add-contact <INVITE CODE HERE>`

Or the GUI version:
`Open the app > click "Add Contact" > Paste the invite code and confirm`

---

## The Network Effect

Lookey relies on a decentralized **Web of Trust**. The tool becomes exponentially more powerful as the community grows.

1.  **Defensive Standard:** As more creators use Lookey, signing images becomes more common. Thieves will find it harder to claim ownership of unsigned work because the community will ask: *"Where is the Lookey Mark?"*
2.  **Shared Identity:** By sharing your Invite Code in your bio (Twitter, GitHub, Blog), you create a permanent link between your online persona and your content.

---

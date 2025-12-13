import os
import sys
import json
import base64
import hashlib
import datetime
import argparse
import piexif
import qrcode
import io
import cv2
import numpy as np
from PIL import Image, PngImagePlugin
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
from colorama import init, Fore, Style
from imwatermark import WatermarkEncoder, WatermarkDecoder

init(autoreset=True)



if getattr(sys, 'frozen', False):
    APP_DIR = os.path.dirname(sys.executable)
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))

DATA_DIR = os.path.join(APP_DIR, "lookey_data")
KEY_FILE = os.path.join(DATA_DIR, "my_private_key.pem")
PUB_FILE = os.path.join(DATA_DIR, "my_public_key.pem")
CONFIG_FILE = os.path.join(DATA_DIR, "user_config.json")
CONTACTS_FILE = os.path.join(DATA_DIR, "contacts.json")

class LookeyBackend:
    def __init__(self):
        os.makedirs(DATA_DIR, exist_ok=True)
        self.load_contacts()
        self.user_name = self.load_config()

    def is_setup(self):
        return os.path.exists(KEY_FILE) and self.user_name is not None

    def setup_user(self, display_name):
        print(f" Generating secure identity for {display_name}...")
        private_key = ed25519.Ed25519PrivateKey.generate()
        public_key = private_key.public_key()

        with open(KEY_FILE, "wb") as f:
            f.write(private_key.private_bytes(
                serialization.Encoding.PEM,
                serialization.PrivateFormat.PKCS8,
                serialization.NoEncryption()
            ))

        with open(PUB_FILE, "wb") as f:
            f.write(public_key.public_bytes(
                serialization.Encoding.PEM,
                serialization.PublicFormat.SubjectPublicKeyInfo
            ))

        self.user_name = display_name
        with open(CONFIG_FILE, "w") as f:
            json.dump({"display_name": display_name}, f)
        return True

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r") as f:
                return json.load(f).get("display_name")
        return None

    def get_my_public_key_string(self):
        if not os.path.exists(PUB_FILE):
            return None
        with open(PUB_FILE, "rb") as f:
            return base64.b64encode(f.read()).decode('utf-8')

    def load_contacts(self):
        if os.path.exists(CONTACTS_FILE):
            with open(CONTACTS_FILE, "r") as f:
                self.contacts = json.load(f)
        else:
            self.contacts = {}

    def add_contact(self, name, pubkey_b64):
        try:
            pubkey_bytes = base64.b64decode(pubkey_b64)
            fingerprint = hashlib.sha256(pubkey_bytes).hexdigest()
            self.contacts[fingerprint] = {"name": name, "key": pubkey_b64}
            with open(CONTACTS_FILE, "w") as f:
                json.dump(self.contacts, f, indent=4)
            return True, f"Added {name} to trusted contacts."
        except Exception as e:
            return False, "Invalid Key Format"

    def rotate_identity(self):

        if not self.is_setup():
            return False, "No identity to rotate."

        try:
            current_pub = self.get_my_public_key_string()
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d")
            archive_name = f"{self.user_name} (Old {timestamp})"
            
            self.add_contact(archive_name, current_pub)
            
            archive_dir = os.path.join(DATA_DIR, "archive_keys")
            os.makedirs(archive_dir, exist_ok=True)
            
            import shutil
            shutil.copy(KEY_FILE, os.path.join(archive_dir, f"private_{timestamp}.pem"))
            shutil.copy(PUB_FILE, os.path.join(archive_dir, f"public_{timestamp}.pem"))

            self.setup_user(self.user_name)
            
            return True, f"Identity Rotated. Old key saved as '{archive_name}'."

        except Exception as e:
            return False, f"Rotation failed: {str(e)}"
                
    def _inject_jpeg(self, path, json_str):
            try:
                exif_dict = piexif.load(path)
            except:
                exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "Interop": {}, "1st": {}, "thumbnail": None}
            
            exif_dict["Exif"][piexif.ExifIFD.UserComment] = json_str.encode('utf-8')
            exif_bytes = piexif.dump(exif_dict)
            piexif.insert(exif_bytes, path)

    def _inject_png(self, path, img_obj, json_str):
            meta = PngImagePlugin.PngInfo()
            meta.add_text("LookeyData", json_str)
            img_obj.save(path, "PNG", pnginfo=meta)
            
    def sign_image(self, image_path):
        if not self.is_setup():
            return False, "Setup required first."

        try:
            img = Image.open(image_path)
            fmt = img.format
            
            pixel_hash = self._get_image_pixel_hash(image_path)
            timestamp = datetime.datetime.utcnow().isoformat()
            
            payload_data = {
                "pixel_hash": pixel_hash,
                "timestamp": timestamp,
                "author": self.user_name
            }
            payload_json = json.dumps(payload_data, sort_keys=True)
            
            with open(KEY_FILE, "rb") as f:
                private_key = serialization.load_pem_private_key(f.read(), password=None)
            signature = private_key.sign(payload_json.encode('utf-8'))
            
            with open(PUB_FILE, "rb") as f:
                my_pub_key_bytes = f.read()

            metadata_dict = {
                "lookey_version": "1.0",
                "payload": payload_data,
                "signature": base64.b64encode(signature).decode('utf-8'),
                "signer_pubkey": base64.b64encode(my_pub_key_bytes).decode('utf-8')
            }
            json_str = json.dumps(metadata_dict)

            parent_dir = os.path.dirname(image_path)
            filename = os.path.basename(image_path)
            
            save_dir = os.path.join(parent_dir, "Lookey_Tagged")
            os.makedirs(save_dir, exist_ok=True)
            
            output_path = os.path.join(save_dir, filename)
            
            img.save(output_path, quality=100, subsampling=0) 

            if fmt == "JPEG":
                self._inject_jpeg(output_path, json_str)
            elif fmt == "PNG":
                img_copy = Image.open(output_path)
                self._inject_png(output_path, img_copy, json_str)
            else:
                return False, f"Unsupported format: {fmt}"

            return True, f"Saved to: Lookey_Tagged/{filename}"

        except Exception as e:
            return False, str(e)
    
    def verify_image(self, image_path):
        try:
            meta_report = "Metadata: Missing"
            spy_report = " Deep Embed: Missing"
            
            final_status = "NO_SIG"
            final_timestamp = "Unknown"
            is_trusted = False

            img = Image.open(image_path)
            raw_json = None
            if img.format == "PNG":
                raw_json = img.info.get("LookeyData")
            if not raw_json:
                raw_json = self._extract_exif_metadata(image_path)
            
            if raw_json:
                try:
                    if isinstance(raw_json, str): metadata = json.loads(raw_json)
                    else: metadata = raw_json

                    payload = metadata["payload"]
                    signature = base64.b64decode(metadata["signature"])
                    signer_pubkey_bytes = base64.b64decode(metadata["signer_pubkey"])
                    public_key = serialization.load_pem_public_key(signer_pubkey_bytes)
                    
                    payload_check_json = json.dumps(payload, sort_keys=True)
                    public_key.verify(signature, payload_check_json.encode('utf-8'))

                    current_pixel_hash = self._get_image_pixel_hash(image_path)
                    
                    if current_pixel_hash == payload["pixel_hash"]:
                        fingerprint = hashlib.sha256(signer_pubkey_bytes).hexdigest()
                        user = payload['author']
                        if fingerprint in self.contacts:
                            user = self.contacts[fingerprint]['name']
                            is_trusted = True
                        
                        meta_report = f"Metadata: VALID ({user})"
                        final_timestamp = payload["timestamp"]
                        if final_status == "NO_SIG": final_status = "TRUSTED" if is_trusted else "UNKNOWN_AUTHOR"
                    else:
                        meta_report = "Metadata: INVALID (Pixels Modified)"
                        final_status = "TAMPERED"
                except Exception as e:
                    meta_report = "Metadata: CORRUPTED"

            scan_result = self._verify_invisible_scan(image_path)
            
            if scan_result:
                if len(scan_result) == 2:
                    name, time = scan_result
                    spy_report = f" Deep Embed: FOUND ({name})"
                    
                    if final_status == "NO_SIG":
                        final_timestamp = f"~{time}"
                        final_status = "TRUSTED"
                
                elif len(scan_result) == 3:
                    _, time, raw_id = scan_result
                    spy_report = f"Deep Embed: UNKNOWN ID ({raw_id[:6]}...)"
                    
                    if final_status == "NO_SIG":
                        final_status = "UNKNOWN_AUTHOR"
                        final_timestamp = f"~{time}"

            if "Missing" in meta_report and "Missing" in spy_report:
                return {"status": "NO_SIG", "msg": "No Lookey signature found."}

            full_msg = f"{meta_report}\n{spy_report}"
            
            return {
                "status": final_status,
                "msg": full_msg,
                "timestamp": final_timestamp
            }

        except Exception as e:
            return {"status": "INVALID", "msg": f"Verification Error: {str(e)}"}

    def _get_image_pixel_hash(self, path):
        img = Image.open(path).convert("RGB")
        return hashlib.sha256(img.tobytes()).hexdigest()

    def _extract_exif_metadata(self, path):
        try:
            exif_dict = piexif.load(path)
            raw = exif_dict["Exif"].get(piexif.ExifIFD.UserComment)
            if raw:
                clean_raw = raw.decode('utf-8', errors='ignore')
                start = clean_raw.find('{')
                end = clean_raw.rfind('}') + 1
                if start != -1 and end != -1:
                    return json.loads(clean_raw[start:end])
        except:
            pass
        return None
    
    def sign_invisible(self, image_path):
        if not self.is_setup():
            return False, "Setup required."

        try:
            bgr = cv2.imread(image_path)
            if bgr is None: return False, "Could not read image."
            
            h, w = bgr.shape[:2]
            new_h = h if h % 2 == 0 else h - 1
            new_w = w if w % 2 == 0 else w - 1
            if new_h != h or new_w != w:
                bgr = bgr[:new_h, :new_w]

            key_hash = hashlib.sha256(self.get_my_public_key_string().encode()).hexdigest()[:4]
            time_code = self._get_timestamp_code()
            payload = f"{key_hash}{time_code}"
            
            encoder = WatermarkEncoder()
            encoder.set_watermark('bytes', payload.encode('utf-8'))

            parent_dir = os.path.dirname(image_path)
            filename = os.path.basename(image_path)
            name_only = os.path.splitext(filename)[0]
            save_dir = os.path.join(parent_dir, "Lookey_Marked")
            os.makedirs(save_dir, exist_ok=True)
            output_path = os.path.join(save_dir, name_only + ".png")

            gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
            
            (mean, std_dev) = cv2.meanStdDev(bgr)
            avg_std = sum(std_dev) / len(std_dev)
            
            void_pixels = np.sum((gray < 10) | (gray > 245))
            void_ratio = void_pixels / gray.size
            
            strategies = []
            
            strategies.append((0, 36))
            strategies.append((0, 60))
            
            if self._is_safe_for_noise(bgr):
                strategies.append((2, 50))
                
                (mean, global_std) = cv2.meanStdDev(bgr)
                if sum(global_std)/3 < 20:
                    strategies.append((4, 90))
            
            spy_success = False
            final_bgr = None

            for noise_level, strength in strategies:
                current_bgr = bgr.copy()
                
                if noise_level > 0:
                    bgr_float = current_bgr.astype(np.float32)
                    noise_map = np.random.normal(0, noise_level, (new_h, new_w)).astype(np.float32)
                    noise_3ch = cv2.merge([noise_map, noise_map, noise_map])
                    bgr_noisy = cv2.add(bgr_float, noise_3ch)
                    np.clip(bgr_noisy, 0, 255, out=bgr_noisy)
                    current_bgr = bgr_noisy.astype(np.uint8)

                bgr_encoded = encoder.encode(current_bgr, 'dwtDct', scales=[0, strength, 0])

                temp_jpg = output_path + ".temp_check.jpg"
                cv2.imwrite(temp_jpg, bgr_encoded, [int(cv2.IMWRITE_JPEG_QUALITY), 95])
                
                scan_result = self._verify_invisible_scan(temp_jpg)
                try: os.remove(temp_jpg)
                except: pass

                if scan_result and scan_result[0] == self.user_name:
                    final_bgr = bgr_encoded
                    spy_success = True
                    break
            
            if spy_success:
                rgb_encoded = cv2.cvtColor(final_bgr, cv2.COLOR_BGR2RGB)
                pil_img = Image.fromarray(rgb_encoded)
            else:
                rgb_clean = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
                pil_img = Image.fromarray(rgb_clean)

            pil_img.save(output_path, "PNG")

            pixel_hash = self._get_image_pixel_hash(output_path)
            timestamp = datetime.datetime.utcnow().isoformat()
            std_payload = { "pixel_hash": pixel_hash, "timestamp": timestamp, "author": self.user_name }
            std_json = json.dumps(std_payload, sort_keys=True)
            
            with open(KEY_FILE, "rb") as f:
                private_key = serialization.load_pem_private_key(f.read(), password=None)
            signature = private_key.sign(std_json.encode('utf-8'))
            with open(PUB_FILE, "rb") as f:
                my_pub_key_bytes = f.read()

            meta_dict = {
                "lookey_version": "1.0",
                "payload": std_payload,
                "signature": base64.b64encode(signature).decode('utf-8'),
                "signer_pubkey": base64.b64encode(my_pub_key_bytes).decode('utf-8')
            }
            
            img_obj = Image.open(output_path)
            self._inject_png(output_path, img_obj, json.dumps(meta_dict))
            
            if spy_success:
                return True, f"Saved to: Lookey_Marked/{name_only}.png (Deep Embed Active)"
            else:
                return True, f"Image too fragile for Deep Embed. Applied Standard Signature to Lookey_Marked/{name_only}.png"

        except Exception as e:
            return False, f"Deep Embed Error: {str(e)}"
    
    def _verify_invisible_scan(self, image_path):
        try:
            bgr = cv2.imread(image_path)
            if bgr is None: return None

            decoder = WatermarkDecoder('bytes', 64) 
            raw_bytes = decoder.decode(bgr, 'dwtDct')
            
            candidates = {}
            candidates[self.user_name] = self.get_my_public_key_string()
            for data in self.contacts.values():
                candidates[data['name']] = data['key']

            best_match_name = None
            found_timestamp = "Unknown"
            lowest_error = 999

            for name, pubkey in candidates.items():
                expected_hash_str = hashlib.sha256(pubkey.encode()).hexdigest()[:4]
                
                found_hash_bytes = raw_bytes[:4]
                expected_hash_bytes = expected_hash_str.encode('utf-8')
                
                error_count = self._hamming_distance(found_hash_bytes, expected_hash_bytes)
                
                if error_count < 6: 
                    if error_count < lowest_error:
                        lowest_error = error_count
                        best_match_name = name
                        
                        try:
                            time_bytes = raw_bytes[4:8] 
                            time_str = time_bytes.decode('utf-8', errors='ignore')
                            found_timestamp = self._decode_timestamp_code(time_str)
                        except:
                            found_timestamp = "Corrupted Time"

            if best_match_name:
                return (best_match_name, found_timestamp)
                
            try:
                time_bytes = raw_bytes[4:8] 
                time_str = time_bytes.decode('utf-8', errors='ignore')
                orphan_timestamp = self._decode_timestamp_code(time_str)
                
                if orphan_timestamp != "Corrupted Time":
                    raw_id_hash = raw_bytes[:4].hex() 
                    
                    if raw_id_hash == "ffffffff" or raw_id_hash == "00000000":
                        return None

                    return ("UNKNOWN", orphan_timestamp, raw_id_hash)
            except:
                pass

        except Exception as e:
            pass
        return None
        
    def _is_safe_for_noise(self, bgr):
    
        h, w = bgr.shape[:2]
        rows, cols = 4, 4
        step_h, step_w = h // rows, w // cols
        
        risky_sectors = 0
        total_sectors = rows * cols
        
        for r in range(rows):
            for c in range(cols):
                y1, y2 = r * step_h, (r + 1) * step_h
                x1, x2 = c * step_w, (c + 1) * step_w
                
                sector = bgr[y1:y2, x1:x2]
                gray_sec = cv2.cvtColor(sector, cv2.COLOR_BGR2GRAY)
                
                (mean, std_dev) = cv2.meanStdDev(sector)
                avg_std = sum(std_dev) / len(std_dev)
                
                avg_bright = np.mean(gray_sec)
                
                if avg_bright < 60 and avg_std < 20:
                    risky_sectors += 1
        
        if risky_sectors > (total_sectors * 0.25):
            return False
            
        return True
        
    def _hamming_distance(self, s1, s2):
        if len(s1) != len(s2): return 999
        diff = 0
        for b1, b2 in zip(s1, s2):
            diff += bin(b1 ^ b2).count('1')
        return diff
        
    def _get_timestamp_code(self):
        epoch = datetime.datetime(2025, 1, 1)
        now = datetime.datetime.now()
        total_minutes = int((now - epoch).total_seconds() / 60)
        ticks = total_minutes // 5
        
        chars = "0123456789abcdefghijklmnopqrstuvwxyz"
        base36 = ""
        for i in range(4):
            base36 = chars[ticks % 36] + base36
            ticks //= 36
        return base36

    def _decode_timestamp_code(self, base36_str):
        try:
            chars = "0123456789abcdefghijklmnopqrstuvwxyz"
            ticks = 0
            for char in base36_str:
                ticks = ticks * 36 + chars.index(char)
            minutes = ticks * 5
            epoch = datetime.datetime(2025, 1, 1)
            final_time = epoch + datetime.timedelta(minutes=minutes)
            return final_time.strftime("%Y-%m-%d %H:%M")
        except:
            return "Corrupted Time"



def main():
    parser = argparse.ArgumentParser(description="Lookey - Image Integrity & Verification")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    subparsers.add_parser("setup", help="Create your identity").add_argument("name", help="Your Display Name")
    subparsers.add_parser("sign", help="Sign an image file").add_argument("file", help="Path to image file")
    subparsers.add_parser("deep-embed", help="Inject invisible Lookey Mark").add_argument("file", help="Path to image file")
    subparsers.add_parser("verify", help="Verify an image file").add_argument("file", help="Path to image file")
    subparsers.add_parser("me", help="Show my public key string")
    subparsers.add_parser("contacts", help="List trusted people")
    subparsers.add_parser("rotate", help="Generate new keys (Archives old ones)")
    
    contact_parser = subparsers.add_parser("add-contact", help="Trust a contact")
    contact_parser.add_argument("data", help="Name OR the full Invite Code")
    contact_parser.add_argument("key", nargs='?', help="The Public Key (Optional if using Code)")
    
    batch_parser = subparsers.add_parser("batch-embed", help="Deep Embed all images in a folder")
    batch_parser.add_argument("folder", help="Path to folder")

    args = parser.parse_args()
    backend = LookeyBackend()



    if args.command == "setup":
        if backend.is_setup():
            print(f"{Fore.YELLOW} You are already set up!{Style.RESET_ALL}")
        else:
            backend.setup_user(args.name)
            print(f"{Fore.GREEN} Identity created for '{args.name}'.")

    elif args.command == "sign":
        success, msg = backend.sign_image(args.file)
        if success:
            print(f"{Fore.GREEN} {msg}")
        else:
            print(f"{Fore.RED} Error: {msg}")

    elif args.command == "deep-embed":
        success, msg = backend.sign_invisible(args.file)
        if success:
            print(f"{Fore.GREEN} {msg}")
            print(f"{Fore.CYAN} This file contains a permanent Lookey Mark.")
        else:
            print(f"{Fore.RED} Error: {msg}")

    elif args.command == "verify":
        res = backend.verify_image(args.file)
        status = res["status"]
        
        if status == "TRUSTED":
            if "Lookey Mark" in res['msg']:
                print(f"{Fore.MAGENTA} {res['msg']}")
                print(f"{Fore.MAGENTA} Timestamp: {res['timestamp']}")
            else:
                print(f"{Fore.GREEN} {res['msg']}")
                print(f"{Fore.CYAN} Timestamp: {res['timestamp']}")
        elif status == "UNKNOWN_AUTHOR":
            print(f"{Fore.YELLOW} {res['msg']}")
            print(f"{Style.DIM} (To trust this person, ask for their Key and run 'add-contact')")
        elif status == "INVALID":
            print(f"{Fore.RED} {res['msg']}")
        else:
            print(f"{Fore.RED} {res['msg']}")

    elif args.command == "me":
        key = backend.get_my_public_key_string()
        name = backend.user_name
        
        if key:
            json_str = json.dumps({"v": 1, "name": name, "key": key})
            invite_code = base64.b64encode(json_str.encode('utf-8')).decode('utf-8')
            
            print(f"\n{Fore.CYAN} Your Lookey Invite Code:")
            print(f"{Style.DIM}" + "-" * 60)
            
            qr = qrcode.QRCode()
            qr.add_data(invite_code) 
            qr.make(fit=True)
            
            f = io.StringIO()
            qr.print_ascii(out=f, invert=True)
            f.seek(0)
            print(f.read())
            
            print(f"{Style.DIM}" + "-" * 60)
            print(f"{Fore.WHITE}Share this code (No quotes needed!):")
            print(f"{Fore.YELLOW}{invite_code}") 
            print(f"{Style.DIM}" + "-" * 60 + "\n")
        else:
            print(f"{Fore.RED} Run 'setup' first.")

    elif args.command == "add-contact":
        name_to_add = None
        key_to_add = None
        if args.key:
            name_to_add = args.data
            key_to_add = args.key
        else:
            try:
                if args.data.strip().startswith("{") or args.data.strip().startswith("'"):
                    clean_data = args.data.strip("'").strip('"')
                    invite = json.loads(clean_data)
                else:
                    decoded_json = base64.b64decode(args.data).decode('utf-8')
                    invite = json.loads(decoded_json)
                name_to_add = invite.get("name")
                key_to_add = invite.get("key")
                print(f"{Fore.CYAN} Detected Invite Code for '{name_to_add}'...")
            except:
                print(f"{Fore.RED} Error: Invalid Invite Code format.")
                name_to_add = None

        if name_to_add and key_to_add:
            success, msg = backend.add_contact(name_to_add, key_to_add)
            print(f"{Fore.GREEN if success else Fore.RED} {msg}")
        else:
            if not args.key:
                print(f"{Fore.RED} Error: Could not extract Name and Key.")

    elif args.command == "contacts":
        if not backend.contacts:
            print(f"{Fore.YELLOW} Your contact list is empty.")
        else:
            print(f"\n{Fore.CYAN} Trusted Contacts:")
            print(f"{Style.DIM}" + "-" * 60)
            print(f"{Fore.WHITE}{'NAME':<20} | {'FINGERPRINT (ID)':<40}")
            print(f"{Style.DIM}" + "-" * 60)
            for fp, data in backend.contacts.items():
                name = data['name']
                short_id = fp[:16] + "..."
                print(f"{Fore.GREEN}{name:<20} {Style.DIM}| {short_id}")
            print(f"{Style.DIM}" + "-" * 60 + "\n")
            
    elif args.command == "batch-embed":
        if not os.path.isdir(args.folder):
            print(f"{Fore.RED} Error: Not a directory.")
            return

        valid_exts = ('.jpg', '.jpeg', '.png')
        files = [f for f in os.listdir(args.folder) if f.lower().endswith(valid_exts)]
        
        print(f"{Fore.CYAN} Found {len(files)} images. Starting batch deep embed...")
        print(f"{Style.DIM}" + "-" * 40)
        
        count = 0
        for filename in files:
            full_path = os.path.join(args.folder, filename)
            success, msg = backend.sign_invisible(full_path)
            if success:
                print(f"{Fore.GREEN} {msg}")
                count += 1
            else:
                print(f"{Fore.RED} {filename}: {msg}")
        
        print(f"{Style.DIM}" + "-" * 40)
        print(f"{Fore.CYAN} Processed {count}/{len(files)} images.")
    
    elif args.command == "rotate":
        print(f"{Fore.RED} WARNING: This will change your Identity Key.")
        print(" Your old key will be saved in your Contacts list so you can still verify old photos.")
        print(" You must share your NEW Invite Code with friends.")
        confirm = input("Type 'CONFIRM' to proceed: ")
        
        if confirm == "CONFIRM":
            success, msg = backend.rotate_identity()
            if success:
                print(f"{Fore.GREEN} {msg}")
            else:
                print(f"{Fore.RED} {msg}")
        else:
            print(" Operation cancelled.")

    else:
        parser.print_help()

if __name__ == "__main__":
    main()
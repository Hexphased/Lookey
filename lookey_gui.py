import customtkinter as ctk
from tkinter import filedialog
from PIL import Image
import qrcode
import json
import base64
import sys
import os

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

from lookey_cli import LookeyBackend

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("green")

class LookeyApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.backend = LookeyBackend()
        self.title("Lookey")
        self.geometry("850x600")
        self.resizable(False, False)
        
        try:
            icon_path = resource_path(os.path.join("assets", "icon.ico"))
            self.iconbitmap(icon_path)
        except:
            pass
            
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        if not self.backend.is_setup():
            self.show_setup_screen()
        else:
            self.show_main_screen()

    def show_setup_screen(self):
        self.clear_window()
        
        frame = ctk.CTkFrame(self)
        frame.place(relx=0.5, rely=0.5, anchor="center")

        label = ctk.CTkLabel(frame, text="Welcome to Lookey", font=("Roboto Medium", 24))
        label.pack(pady=(20, 10), padx=40)

        sub = ctk.CTkLabel(frame, text="Create your secure digital identity.", text_color="gray")
        sub.pack(pady=(0, 20))

        self.name_entry = ctk.CTkEntry(frame, placeholder_text="Enter Display Name", width=250)
        self.name_entry.pack(pady=10)

        btn = ctk.CTkButton(frame, text="Generate Keys", command=self.create_identity, height=40)
        btn.pack(pady=20)

    def create_identity(self):
        name = self.name_entry.get()
        if name:
            self.backend.setup_user(name)
            self.show_main_screen()
    
    def show_main_screen(self):
        self.clear_window()

        self.sidebar = ctk.CTkFrame(self, width=220, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        
        try:
            logo_path = resource_path(os.path.join("assets", "logo.png"))
            pil_img = Image.open(logo_path)
            logo_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(50, 50))
            
            lbl_logo = ctk.CTkLabel(self.sidebar, text=" Lookey", image=logo_img, compound="left", font=("Roboto Medium", 24))
        except:
            lbl_logo = ctk.CTkLabel(self.sidebar, text="👁️ Lookey", font=("Roboto Medium", 24))
            
        lbl_logo.pack(pady=30)

        lbl_user = ctk.CTkLabel(self.sidebar, text=f"User: {self.backend.user_name}", text_color="gray", font=("Roboto", 12))
        lbl_user.pack(pady=0)

        btn_qr = ctk.CTkButton(self.sidebar, text="Show Invite QR", fg_color="transparent", border_width=2, command=self.show_qr_popup)
        btn_qr.pack(pady=20, padx=20)

        btn_contacts = ctk.CTkButton(self.sidebar, text="My Contacts", fg_color="#333", command=self.show_contacts_dialog)
        btn_contacts.pack(pady=(10, 10), padx=20)

        btn_add = ctk.CTkButton(self.sidebar, text="Add Contact", fg_color="#333", command=self.show_add_contact_dialog)
        btn_add.pack(pady=10, padx=20)

        self.sidebar.grid_rowconfigure(6, weight=1) 
        
        btn_rotate = ctk.CTkButton(self.sidebar, text="Cycle Identity ↻", fg_color="#922B21", hover_color="#641E16", height=30, command=self.show_rotate_dialog)
        btn_rotate.pack(side="bottom", pady=20, padx=20)

        self.main_area = ctk.CTkFrame(self, fg_color="transparent")
        self.main_area.grid(row=0, column=1, sticky="nsew")

        self.status_icon = ctk.CTkLabel(self.main_area, text="📷", font=("Arial", 60))
        self.status_icon.pack(pady=(60, 10))

        self.status_text = ctk.CTkLabel(self.main_area, text="Select an image to start", font=("Roboto Medium", 18))
        self.status_text.pack(pady=5)
        
        self.status_detail = ctk.CTkLabel(self.main_area, text="", text_color="gray")
        self.status_detail.pack(pady=5)

        btn_frame = ctk.CTkFrame(self.main_area, fg_color="transparent")
        btn_frame.pack(pady=50)

        self.btn_sign = ctk.CTkButton(btn_frame, text="Sign One", width=140, height=45, font=("Roboto", 14), command=self.gui_sign)
        self.btn_sign.grid(row=0, column=0, padx=10, pady=10)
        
        self.btn_spy = ctk.CTkButton(btn_frame, text="Deep Embed", width=140, height=45, font=("Roboto", 14), fg_color="#5B2C6F", hover_color="#4A235A", command=self.gui_deep_embed)
        self.btn_spy.grid(row=0, column=1, padx=10, pady=10)
        
        self.btn_verify = ctk.CTkButton(btn_frame, text="Verify Image", width=140, height=45, font=("Roboto", 14), fg_color="#444", hover_color="#555", command=self.gui_verify)
        self.btn_verify.grid(row=0, column=2, padx=10, pady=10)

        self.btn_batch = ctk.CTkButton(btn_frame, text="Batch Sign Folder", width=460, height=40, font=("Roboto", 14, "bold"), fg_color="#222", hover_color="#4A235A", border_width=1, border_color="#5B2C6F", command=self.gui_batch_sign)
        self.btn_batch.grid(row=1, column=0, columnspan=3, pady=(5, 0))

    def gui_sign(self):
        path = filedialog.askopenfilename(filetypes=[("Images", "*.jpg *.jpeg *.png")])
        if path:
            success, msg = self.backend.sign_image(path)
            if success:
                self.update_status("✅", "Signed (Standard)", msg, "#2CC985")
            else:
                self.update_status("❌", "Signing Failed", msg, "#FF4444")
                
    def gui_deep_embed(self):
        path = filedialog.askopenfilename(filetypes=[("Images", "*.jpg *.jpeg *.png")])
        if path:
            self.update_status("⏳", "Embedding Mark...", "Calculating frequencies...", "orange")
            self.update_idletasks()
            
            success, msg = self.backend.sign_invisible(path)
            
            if success:
                if "Standard Signature" in msg:
                    self.update_status("⚠️", "Deep Embed Failed", "Image too flat. Applied Standard Tag instead.", "#F39C12")
                else:
                    self.update_status("⚓", "Deep Embed Complete", msg, "#AF7AC5")
            else:
                self.update_status("❌", "Operation Failed", msg, "#FF4444")
                
    def gui_batch_sign(self):
        folder_path = filedialog.askdirectory()
        if not folder_path: return

        valid_exts = ('.jpg', '.jpeg', '.png')
        files = [f for f in os.listdir(folder_path) if f.lower().endswith(valid_exts)]
        
        if not files:
            self.update_status("⚠️", "No Images Found", "Folder contains no JPG/PNG files.", "orange")
            return

        deep_count = 0
        std_count = 0
        errors = 0
        total = len(files)
        
        self.update_status("⏳", "Batch Processing...", f"Starting on {total} images", "orange")
        self.update_idletasks()

        for filename in files:
            full_path = os.path.join(folder_path, filename)
            success, msg = self.backend.sign_invisible(full_path)
            
            if success:
                if "Standard Signature" in msg:
                    std_count += 1
                    print(f"[Batch] Fallback: {filename}")
                else:
                    deep_count += 1
                    print(f"[Batch] Deep Embed: {filename}")
            else:
                errors += 1
                print(f"[Batch] Error: {filename} - {msg}")
        
        summary = f"{deep_count} Deep Embedded | {std_count} Metadata Signed"
        
        if errors == 0:
            self.update_status("✅", "Batch Complete", summary, "#2CC985")
        else:
            self.update_status("⚠️", "Batch Finished", f"{summary} | {errors} Failed", "orange")
    
    def gui_verify(self):
        path = filedialog.askopenfilename(filetypes=[("Images", "*.jpg *.jpeg *.png")])
        if path:
            res = self.backend.verify_image(path)
            status = res["status"]

            time_display = ""
            if "timestamp" in res and res["timestamp"] != "Unknown":
                time_display = f"\nTime of signing: {res['timestamp']}"

            if status == "TRUSTED":
                if "Deep Embed: FOUND" in res['msg'] and "Metadata: VALID" not in res['msg']:

                    try:
                        name = res['msg'].split("(")[-1].strip(")")
                    except:
                        name = "Unknown"
                        
                    self.update_status(
                        "⚓", 
                        f"Source Confirmed: {name}", 
                        f"Deep Embed found. Metadata missing.\n{time_display.strip()}", 
                        "#AF7AC5"
                    )

                elif "Metadata:" in res['msg']:
                    self.update_status("✅", "Verified Authentic", f"{res['msg']}{time_display}", "#2CC985")
            
            elif status == "TAMPERED":
                self.update_status("❌", "TAMPER DETECTED", f"Metadata present but INVALID. Pixels modified.\n{res['msg']}", "#FF4444")

            elif status == "UNKNOWN_AUTHOR":
                if "Deep Embed" in res['msg']:
                    self.update_status("⚠️", "Unknown Lookey Mark", f"{res['msg']}{time_display}", "orange")
                else:
                    self.update_status("⚠️", "Valid Sig / Unknown Author", "Import their key to trust them.", "orange")
            
            elif status == "INVALID":
                self.update_status("❌", "Error", f"{res['msg']}", "#FF4444")
            
            else:
                self.update_status("❓", "No Signature", "This image is unsigned.", "gray")
                
    def update_status(self, icon, title, detail, color):
        self.status_icon.configure(text=icon, text_color=color)
        self.status_text.configure(text=title, text_color=color)
        self.status_detail.configure(text=detail, justify="center")

    def show_qr_popup(self):
        key = self.backend.get_my_public_key_string()
        json_str = json.dumps({"v": 1, "name": self.backend.user_name, "key": key})
        invite_code = base64.b64encode(json_str.encode('utf-8')).decode('utf-8')

        qr = qrcode.QRCode(box_size=10, border=2)
        qr.add_data(invite_code)
        qr.make(fit=True)
        
        qr_wrapper = qr.make_image(fill_color="black", back_color="white")
        img = qr_wrapper.get_image()

        top = ctk.CTkToplevel(self)
        self._apply_icon(top)
        top.title("My Invite QR")
        top.geometry("350x450")
        top.attributes("-topmost", True)
        
        my_image = ctk.CTkImage(light_image=img, dark_image=img, size=(250, 250))
        ctk.CTkLabel(top, image=my_image, text="").pack(pady=20)
        
        ctk.CTkButton(top, text="Copy Invite Code", command=lambda: self.copy_to_clipboard(invite_code)).pack(pady=10)

    def show_contacts_dialog(self):
        top = ctk.CTkToplevel(self)
        self._apply_icon(top)
        top.title("Trusted Contacts")
        top.geometry("400x500")
        top.attributes("-topmost", True)

        ctk.CTkLabel(top, text=f"Trusted People ({len(self.backend.contacts)})", font=("Roboto Medium", 18)).pack(pady=15)
        
        scroll = ctk.CTkScrollableFrame(top, width=350, height=400)
        scroll.pack(pady=10, padx=10, fill="both", expand=True)

        if not self.backend.contacts:
            ctk.CTkLabel(scroll, text="No contacts yet.", text_color="gray").pack(pady=20)
        else:
            for fp, data in self.backend.contacts.items():
                card = ctk.CTkFrame(scroll, fg_color="#2b2b2b")
                card.pack(fill="x", pady=5, padx=5)
                ctk.CTkLabel(card, text=data['name'], font=("Roboto", 16, "bold")).pack(anchor="w", padx=10, pady=(10,0))
                short_id = f"ID: {fp[:12]}..."
                ctk.CTkLabel(card, text=short_id, font=("Roboto", 12), text_color="gray").pack(anchor="w", padx=10, pady=(0,10))

    def show_add_contact_dialog(self):
        dialog = ctk.CTkInputDialog(text="Paste Lookey Invite Code:", title="Add Contact")
        code = dialog.get_input()
        if code:
            try:
                if code.strip().startswith("{"):
                    invite = json.loads(code)
                else:
                    decoded_json = base64.b64decode(code).decode('utf-8')
                    invite = json.loads(decoded_json)
                
                name = invite.get("name")
                key = invite.get("key")
                
                success, msg = self.backend.add_contact(name, key)
                if success:
                    self.update_status("👤", "Contact Added", f"You now trust {name}", "#2CC985")
                else:
                    self.update_status("❌", "Error", msg, "red")
            except:
                self.update_status("❌", "Invalid Code", "That code was garbage.", "red")

    def show_rotate_dialog(self):
        top = ctk.CTkToplevel(self)
        self._apply_icon(top)
        top.title("⚠️ Rotate Identity")
        top.geometry("400x300")
        top.attributes("-topmost", True)
        
        ctk.CTkLabel(top, text="⚠️ WARNING", font=("Arial", 24, "bold"), text_color="#FF4444").pack(pady=(20, 10))
        
        msg = (
            "This will generate a NEW Keypair.\n\n"
            "1. Your old key will be archived in Contacts.\n"
            "2. You can still verify your old photos.\n"
            "3. You MUST re-share your QR code with friends.\n"
        )
        ctk.CTkLabel(top, text=msg, wraplength=300, justify="left", font=("Roboto", 14)).pack(pady=10)
        
        def confirm_action():
            success, msg = self.backend.rotate_identity()
            top.destroy()
            if success:
                self.update_status("🔄", "Identity Rotated", "You have a new Keypair.", "#2CC985")
                self.show_main_screen()
            else:
                self.update_status("❌", "Rotation Failed", msg, "#FF4444")

        btn_confirm = ctk.CTkButton(top, text="I Understand, Rotate Keys", fg_color="#FF4444", hover_color="#990000", command=confirm_action)
        btn_confirm.pack(pady=20)

    def copy_to_clipboard(self, text):
        self.clipboard_clear()
        self.clipboard_append(text)
        self.update()
        
    def _apply_icon(self, window):
        try:
            icon_path = resource_path(os.path.join("assets", "icon.ico"))
            window.after(200, lambda: window.iconbitmap(icon_path))
        except:
            pass

    def clear_window(self):
        for widget in self.winfo_children():
            widget.destroy()

if __name__ == "__main__":
    app = LookeyApp()
    app.mainloop()
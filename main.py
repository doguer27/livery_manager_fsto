import sys
import os
import tkinter as tk
from tkinter import messagebox, filedialog
import json
import threading
import tempfile
import shutil
import zipfile
import re
import subprocess
import ctypes 
import time
import webbrowser 
import urllib.request
import ssl
import atexit
import glob
import gc 
import stat

try:
    import customtkinter as ctk
    from PIL import Image, ImageTk, ImageOps, ImageDraw 
    from tkinterdnd2 import DND_FILES, TkinterDnD 
except ImportError as e:
    root = tk.Tk()
    root.withdraw()
    messagebox.showerror("Dependency Error", f"Error: {e}\nPlease ensure 'customtkinter', 'Pillow' and 'tkinterdnd2' are installed.\n\npip install tkinterdnd2")
    sys.exit(1)

DEBUG_MODE = False
PATCH_NOTES_FILENAME = "patch_notes.txt"
CURRENT_VERSION = "v1.0.7" 

APP_BRAND_NAME = "doguer"
FOOTER_LINK_TEXT = "Donate Here"
FOOTER_LINK_URL = "https://paypal.me/doguer26"
FOOTER_BTN_COLOR = "#0079C1" 
FOOTER_BTN_HOVER = "#005ea6"
GITHUB_REPO = "doguer27/livery_manager_fsto"
WELCOME_TITLE = "Welcome to doguer's Livery Manager"

try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context

if getattr(sys, 'frozen', False):
    base_dir = sys._MEIPASS
else:
    base_dir = os.path.dirname(os.path.abspath(__file__))

modules_path = os.path.join(base_dir, "modules")
if os.path.exists(modules_path):
    sys.path.insert(0, modules_path)

ctk.set_appearance_mode("Dark")

# --- PALETTE ---
COLOR_BG = "#0F1225"            
COLOR_CARD = "#1A1E3F"          
COLOR_SURFACE = "#252A40"       
COLOR_ACCENT = "#00A8FF"        
COLOR_ACCENT_HOVER = "#008ACD" 
COLOR_GOLD = "#FFD700"          
COLOR_GOLD_HOVER = "#E6C200"    
COLOR_DANGER = "#FF3B30"        
COLOR_TEXT_PRIMARY = "#FFFFFF" 
COLOR_TEXT_SECONDARY = "#AEC6CF"
COLOR_SEARCH_BG = "#0A0C1A"    

CONFIG_FILE = "pmdg_manager_config.json"

def get_efficient_temp_dir(target_path):
    try:
        drive_root = os.path.splitdrive(target_path)[0]
        if not drive_root: drive_root = os.path.dirname(target_path)
        efficient_root = os.path.join(drive_root + os.sep, "_PMDG_WIP_CACHE")
        os.makedirs(efficient_root, exist_ok=True)
        return efficient_root
    except:
        return tempfile.gettempdir()

def cleanup_stale_temp_files():
    pattern = os.path.join(tempfile.gettempdir(), "pmdg_bulk_*")
    for d in glob.glob(pattern):
        try: shutil.rmtree(d, ignore_errors=True)
        except: pass
    
    for drive in range(65, 91): # A-Z
        root = f"{chr(drive)}:\\"
        for trash in ["_PMDG_TMP", "_PMDG_WIP_CACHE"]:
            d = os.path.join(root, trash)
            if os.path.exists(d):
                try: shutil.rmtree(d, ignore_errors=True)
                except: pass

cleanup_stale_temp_files()

AIRCRAFT_DB = {
    "PMDG 737-800": { 
        "type": "PMDG", 
        "sim_folder": "PMDG 737-800", 
        "wasm": "pmdg-aircraft-738",
        "has_variants": True,
        "variant_map": {
            "PAX": "b738_ext",
            "BDSF": "b738bdsf_ext",
            "BCF": "b738bcf_ext",
            "BBJ2": "b73bbj2_ext"
        },
        "has_winglets": True 
    },
    # --- PMDG 737-900 (900/900ER) ---
    "PMDG 737-900": { 
        "type": "PMDG", 
        "sim_folder": "PMDG 737-900", 
        "wasm": "pmdg-aircraft-739",
        "has_variants": True,
        "variant_map": {
            "900": "b739_ext",
            "900ER": "b739er_ext"
        },
        "has_winglets": True 
    },
    # --- PMDG 737-600 ---
    "PMDG 737-600": { 
        "type": "PMDG", 
        "sim_folder": "PMDG 737-600", 
        "wasm": "pmdg-aircraft-736",
        "has_variants": False,
        "has_winglets": False 
    },
    "PMDG 777F": { 
        "type": "PMDG", 
        "sim_folder": "PMDG 777F", 
        "wasm": "pmdg-aircraft-77f",
        "has_variants": False
    },
    "PMDG 777-300ER": { 
        "type": "PMDG", 
        "sim_folder": "PMDG 777-300ER", 
        "wasm": "pmdg-aircraft-77w",
        "has_variants": False
    },
    "PMDG 777-200ER": { 
        "type": "PMDG", 
        "sim_folder": "PMDG 777-200ER", 
        "wasm": "pmdg-aircraft-77er",
        "has_variants": True,
        "variant_map": {
            "General Electric": "engine_ge",
            "Rolls Royce": "engine_rr",
            "Pratt & Whitney": "engine_pw"
        }
    },
    "PMDG 777-200LR": { 
        "type": "PMDG", 
        "sim_folder": "PMDG 777-200LR", 
        "wasm": "pmdg-aircraft-77l",
        "has_variants": False
    },
    "iFly 737 MAX 8": { 
        "type": "IFLY", 
        "base_container": "..\\iFly 737-MAX8", 
        "wasm": "ifly-aircraft-737max8",
        "has_variants": False
    }
}

def safe_path(path):
    if os.name == 'nt':
        path = os.path.abspath(path)
        if len(path) > 240 and not path.startswith('\\\\?\\'):
            return '\\\\?\\' + path
    return path

class SimSelectorPopup(ctk.CTkToplevel):
    def __init__(self, parent_app):
        super().__init__(parent_app)
        self.parent_app = parent_app
        self.title("Welcome")
        self.geometry("450x380")
        self.resizable(False, False)
        self.configure(fg_color=COLOR_BG)
        self.update_idletasks()
        x = (self.winfo_screenwidth() - 450) // 2
        y = (self.winfo_screenheight() - 380) // 2
        self.geometry(f"+{x}+{y}")
        self.attributes("-topmost", True)
        self.lift()
        self.focus_force()
        self.grab_set() 
        self.protocol("WM_DELETE_WINDOW", self.do_nothing) 

        ctk.CTkLabel(self, text=WELCOME_TITLE, font=("Roboto", 20, "bold"), text_color=COLOR_ACCENT).pack(pady=(30, 10))
        ctk.CTkLabel(self, text="Please select your MSFS version or Custom Folder\nto auto-detect folders correctly.", 
                     font=("Roboto", 12), text_color="gray").pack(pady=(0, 20))

        ctk.CTkButton(self, text="Microsoft Store / Xbox App", height=45, width=300, 
                                  fg_color=COLOR_CARD, hover_color=COLOR_ACCENT_HOVER, border_width=2, border_color=COLOR_ACCENT,
                                  font=("Roboto", 14, "bold"), command=lambda: self.select_version("MS_STORE")).pack(pady=8)

        ctk.CTkButton(self, text="Steam Version", height=45, width=300, 
                                  fg_color=COLOR_CARD, hover_color=COLOR_GOLD_HOVER, border_width=2, border_color=COLOR_GOLD, text_color="white",
                                  font=("Roboto", 14, "bold"), command=lambda: self.select_version("STEAM")).pack(pady=8)
        
        ctk.CTkButton(self, text="Custom Folder Location", height=45, width=300, 
                                  fg_color=COLOR_CARD, hover_color="#303550", border_width=1, border_color="gray", text_color="white",
                                  font=("Roboto", 14), command=self.select_custom).pack(pady=8)

    def select_version(self, version):
        self.parent_app.sim_version.set(version)
        self.finish()

    def select_custom(self):
        self.attributes("-topmost", False)
        path = filedialog.askdirectory(title="Select Community Folder")
        self.attributes("-topmost", True)
        if path:
            self.parent_app.sim_version.set("CUSTOM")
            self.parent_app.community_path = path
            self.finish()

    def finish(self):
        self.grab_release()
        self.destroy()
        
    def do_nothing(self):
        pass

class PatchNotesPopup(ctk.CTkToplevel):
    def __init__(self, parent_app):
        super().__init__(parent_app)
        self.parent_app = parent_app
        self.title(f"What's New in {CURRENT_VERSION}")
        self.geometry("500x450")
        self.attributes("-topmost", True)
        ctk.CTkLabel(self, text="UPDATE SUCCESSFUL", font=("Roboto", 20, "bold"), text_color=COLOR_GOLD).pack(pady=20)
        self.textbox = ctk.CTkTextbox(self, width=450, height=250)
        self.textbox.pack(pady=10)
        self.load_notes()
        ctk.CTkButton(self, text="Let's Fly ✈️", command=self.destroy).pack(pady=20)

    def load_notes(self):
        txt_path = os.path.join(base_dir, PATCH_NOTES_FILENAME)
        if os.path.exists(txt_path):
            with open(txt_path, "r", encoding="utf-8") as f: self.textbox.insert("0.0", f.read())
        else: self.textbox.insert("0.0", "New version detected.\nChangelog here: https://flightsim.to/file/101755/pmdg-livery-manager-by-flightmods-and-doguer")

class FolderNameDialog(ctk.CTkToplevel):
    def __init__(self, parent, default_name, origin_name, callback_fn):
        super().__init__(parent)
        self.callback_fn = callback_fn
        self.final_name = default_name
        self.default_name = default_name
        
        self.transient(parent) 
        self.title("Folder Naming")
        self.geometry("500x280") 
        self.resizable(False, False)
        self.configure(fg_color=COLOR_BG)
        self.attributes("-topmost", True) 
        self.lift()
        self.focus_force()
        self.grab_set() 
        
        try:
            x = parent.winfo_x() + (parent.winfo_width() // 2) - 250
            y = parent.winfo_y() + (parent.winfo_height() // 2) - 140
            self.geometry(f"+{x}+{y}")
        except: pass

        self.protocol("WM_DELETE_WINDOW", self.on_close)

        ctk.CTkLabel(self, text="Set Custom Folder Name", font=("Roboto", 16, "bold"), text_color=COLOR_ACCENT).pack(pady=(20, 5))
        ctk.CTkLabel(self, text=f"Installing: {origin_name}", font=("Roboto", 12), text_color="gray").pack(pady=(0, 20))

        self.entry = ctk.CTkEntry(self, width=400, font=("Roboto", 14))
        self.entry.pack(pady=10)
        self.entry.insert(0, default_name)
        self.entry.select_range(0, 'end')
        self.entry.focus()
        
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=(15, 10))

        ctk.CTkButton(btn_frame, text="Use Default Name", fg_color=COLOR_SURFACE, hover_color="#303550", 
                      command=self.use_default).pack(side="left", padx=10)
        
        ctk.CTkButton(btn_frame, text="Confirm Custom Name", fg_color=COLOR_GOLD, hover_color=COLOR_GOLD_HOVER, text_color="black", font=("Roboto", 12, "bold"),
                      command=self.confirm).pack(side="left", padx=10)
        
        self.btn_clear = ctk.CTkButton(self, text="Clear Input", width=80, height=25, fg_color=COLOR_DANGER, hover_color="#B71C1C", 
                                       font=("Roboto", 10), command=self.clear_input)
        self.btn_clear.pack(pady=(0, 15))
        
        self.bind('<Return>', lambda e: self.confirm())

    def clear_input(self):
        self.entry.delete(0, 'end')
        self.entry.focus()

    def use_default(self):
        self.final_name = self.default_name
        self.finish()

    def confirm(self):
        val = self.entry.get().strip()
        if not val:
            messagebox.showwarning("Input Required", "Please enter a folder name or click 'Use Default Name'.", parent=self)
            return 
        val = re.sub(r'[\\/*?:"<>|]', "", val)
        self.final_name = val
        self.finish()

    def on_close(self):
        self.finish()

    def finish(self):
        self.grab_release()
        self.callback_fn(self.final_name)
        self.destroy()

class InstallerPopup(ctk.CTkToplevel):
    def __init__(self, parent_app, preloaded_files=None):
        super().__init__(parent_app)
        self.parent_app = parent_app
        self.title("Install New Livery & Configs")
        self.geometry("700x700") 
        self.resizable(False, False)
        self.configure(fg_color=COLOR_BG) 
        self.attributes("-topmost", True)
        self.lift()
        self.focus_force()
        self.protocol("WM_DELETE_WINDOW", self.on_close_save)

        self.drop_target_register(DND_FILES)
        self.dnd_bind('<<Drop>>', self.on_drop_files)

        self.files_list = [] 
        self.display_text = tk.StringVar()
        initial_path = parent_app.community_path
        if parent_app.last_install_path and os.path.exists(parent_app.last_install_path):
            initial_path = parent_app.last_install_path
        self.install_path = tk.StringVar(value=initial_path)
        
        self.custom_folder_name_var = ctk.BooleanVar(value=False)

        info_frame = ctk.CTkFrame(self, fg_color="transparent")
        info_frame.pack(fill="x", padx=20, pady=(20, 10))
        ctk.CTkLabel(info_frame, text=f"Target Aircraft: {parent_app.selected_aircraft.get()}", 
                     font=("Roboto", 16, "bold"), text_color=COLOR_ACCENT).pack(anchor="w")
        
        explanation = "Note: Liveries will be auto-installed to the correct aircraft variant.\nConfig files (.ini) will be sent to the aircraft selected in the Manager."
        ctk.CTkLabel(info_frame, text=explanation, font=("Roboto", 10), text_color="gray", justify="left").pack(anchor="w", pady=(2, 0))

        main_frame = ctk.CTkFrame(self, fg_color=COLOR_CARD)
        main_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        ctk.CTkLabel(main_frame, text="1. Select Files (Zip, Folder or .ini):", text_color=COLOR_TEXT_PRIMARY, font=("Roboto", 12, "bold")).pack(anchor="w", padx=20, pady=(20, 10))
        zip_row = ctk.CTkFrame(main_frame, fg_color="transparent")
        zip_row.pack(fill="x", padx=15)
        
        self.entry_zip = ctk.CTkEntry(zip_row, textvariable=self.display_text, placeholder_text="Drag files here (Liveries or Configs)...", fg_color=COLOR_BG, border_color=COLOR_ACCENT, height=35)
        self.entry_zip.configure(state="readonly")
        self.entry_zip.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        self.btn_browse = ctk.CTkButton(zip_row, text="Browse", width=100, height=35, fg_color=COLOR_ACCENT, hover_color=COLOR_ACCENT_HOVER, font=("Roboto", 12, "bold"), command=self.smart_browse)
        self.btn_browse.pack(side="right")

        ctk.CTkLabel(main_frame, text="2. Installation Location (Liveries):", text_color=COLOR_TEXT_PRIMARY, font=("Roboto", 12, "bold")).pack(anchor="w", padx=20, pady=(20, 10))
        loc_row = ctk.CTkFrame(main_frame, fg_color="transparent")
        loc_row.pack(fill="x", padx=15)
        self.entry_loc = ctk.CTkEntry(loc_row, textvariable=self.install_path, placeholder_text="Path to Community folder...", fg_color=COLOR_BG, border_color=COLOR_ACCENT, height=35)
        self.entry_loc.pack(side="left", fill="x", expand=True, padx=(0, 10))
        ctk.CTkButton(loc_row, text="Change", width=100, height=35, fg_color=COLOR_ACCENT, hover_color=COLOR_ACCENT_HOVER, font=("Roboto", 12, "bold"), command=self.browse_install_loc).pack(side="right")

        self.linker_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        self.linker_frame.pack(fill="x", padx=20, pady=(15, 0))
        
        self.chk_linker = ctk.CTkCheckBox(
            self.linker_frame, 
            text="Addon Linker Mode (Separate Folders)", 
            variable=self.parent_app.addon_linker_mode,
            command=self.on_linker_toggle,
            font=("Roboto", 12, "bold"),
            fg_color=COLOR_GOLD,
            hover_color=COLOR_GOLD_HOVER,
            text_color="white"
        )
        self.chk_linker.pack(side="left", anchor="w")

        self.chk_custom_name = ctk.CTkCheckBox(
            self.linker_frame,
            text="Custom name for the folder of each livery",
            variable=self.custom_folder_name_var,
            font=("Roboto", 12),
            fg_color=COLOR_ACCENT,
            hover_color=COLOR_ACCENT_HOVER,
            text_color="gray" 
        )

        warn_container = ctk.CTkFrame(main_frame, fg_color="transparent")
        warn_container.pack(fill="x", padx=20, pady=(15, 10))
        ctk.CTkLabel(warn_container, text="⚠", font=("Arial", 18), text_color=COLOR_GOLD).pack(side="left", anchor="n", pady=(2,0))
        warn_text = "Supports Mixed Bulk Install: Zip, Folders & Configs (.ini).\nConfigs are installed 'AS IS' to WASM/Work folder."
        ctk.CTkLabel(warn_container, text=warn_text, text_color=COLOR_GOLD, font=("Roboto", 11), justify="left", anchor="w").pack(side="left", padx=(10,0))

        action_frame = ctk.CTkFrame(self, fg_color="transparent")
        action_frame.pack(fill="x", padx=20, pady=20)
        
        self.lbl_status = ctk.CTkLabel(action_frame, text="Ready to install.", font=("Roboto", 12), text_color="gray")
        self.lbl_status.pack(anchor="w", padx=5, pady=(0, 5))

        self.progress_bar = ctk.CTkProgressBar(action_frame, height=12, corner_radius=6)
        self.progress_bar.set(0)
        self.progress_bar.pack(fill="x", pady=(0, 10))
        self.progress_bar.configure(progress_color=COLOR_ACCENT)

        self.btn_install = ctk.CTkButton(action_frame, text="INSTALL ALL", fg_color=COLOR_GOLD, hover_color=COLOR_GOLD_HOVER, text_color="black", height=50, font=("Roboto", 15, "bold"), command=self.start_install)
        self.btn_install.pack(side="top", fill="x", pady=(0, 15))

        bottom_row = ctk.CTkFrame(action_frame, fg_color="transparent")
        bottom_row.pack(fill="x")
        ctk.CTkButton(bottom_row, text="Clear All", fg_color=COLOR_DANGER, hover_color="#B71C1C", width=100, height=30, command=self.clear_fields).pack(side="left")
        ctk.CTkButton(bottom_row, text="Fix Long Paths (RegEdit) 🛠️", fg_color=COLOR_CARD, border_width=1, border_color=COLOR_GOLD, hover_color=COLOR_BG, text_color=COLOR_GOLD, height=30, command=self.run_long_paths_fix).pack(side="right")

        self.on_linker_toggle(silent=True)

        if preloaded_files:
            self.update_file_list(preloaded_files)

    def on_linker_toggle(self, silent=False):
        is_active = self.parent_app.addon_linker_mode.get()
        self.parent_app.save_current_config()
        
        if is_active:
            self.chk_custom_name.pack(side="left", padx=(20, 0))
        else:
            self.chk_custom_name.pack_forget()
            self.custom_folder_name_var.set(False)

        if not silent:
            self.attributes("-topmost", False)
            if is_active:
                msg = "Addon Linker Mode ENABLED.\n\nEach livery will be installed in its own separate folder inside Community.\nUseful for organization or using MSFS Addon Linker."
                messagebox.showinfo("Mode Changed", msg, parent=self)
            else:
                msg = "Addon Linker Mode DISABLED.\n\nAll liveries will be installed into the single main folder (pmdg-flightmods-manager)."
                messagebox.showinfo("Mode Changed", msg, parent=self)
            self.attributes("-topmost", True)

    def update_file_list(self, files):
        valid = [f for f in files if os.path.isdir(f) or f.lower().endswith('.zip') or f.lower().endswith('.ini')]
        self.files_list = valid
        count = len(valid)
        if count == 1:
            self.display_text.set(os.path.basename(valid[0]))
        else:
            self.display_text.set(f"{count} items loaded")
        self.lbl_status.configure(text=f"Ready to install {count} items.")
        self.progress_bar.set(0)

    def on_drop_files(self, event):
        raw_data = event.data
        if raw_data.startswith('{') and raw_data.endswith('}'):
            files = re.findall(r'\{.*?\}|\S+', raw_data)
            clean_files = [f.strip('{}') for f in files]
        else:
            clean_files = self.tk.splitlist(raw_data)
        
        valid_items = [f for f in clean_files if os.path.isdir(f) or f.lower().endswith('.zip') or f.lower().endswith('.ini')]
        
        if not valid_items and clean_files:
            messagebox.showerror("Invalid File", "Please drop a valid folder, .zip or .ini file.\n(Only these formats are supported)", parent=self)
            return

        if valid_items:
            self.update_file_list(valid_items)

    def on_close_save(self):
        self.parent_app.last_install_path = self.install_path.get().strip()
        self.parent_app.save_current_config()
        self.destroy()

    def smart_browse(self):
        menu = tk.Menu(self, tearoff=0, font=("Roboto", 10))
        menu.add_command(label="Select Archive Files (.zip)", command=self.browse_zips)
        menu.add_command(label="Select Config File (.ini)", command=self.browse_ini)
        menu.add_command(label="Select Folder", command=self.browse_folders)
        try:
            x = self.btn_browse.winfo_rootx()
            y = self.btn_browse.winfo_rooty() + self.btn_browse.winfo_height()
            menu.tk_popup(x, y)
        finally:
            menu.grab_release()

    def browse_zips(self):
        try:
            self.attributes("-topmost", False) 
            files = filedialog.askopenfilenames(filetypes=[("Zip files", "*.zip")])
        finally:
            if self.winfo_exists(): self.attributes("-topmost", True)
        if files:
            self.update_file_list(files)

    def browse_ini(self):
        try:
            self.attributes("-topmost", False) 
            files = filedialog.askopenfilenames(filetypes=[("Config files", "*.ini")])
        finally:
            if self.winfo_exists(): self.attributes("-topmost", True)
        if files:
            self.update_file_list(files)
            
    def browse_folders(self):
        try:
            self.attributes("-topmost", False) 
            folder = filedialog.askdirectory(title="Select Livery Folder")
        finally:
            if self.winfo_exists(): self.attributes("-topmost", True)
        if folder:
            self.update_file_list([folder])

    def browse_install_loc(self):
        try:
            self.attributes("-topmost", False) 
            d = filedialog.askdirectory(title="Select Destination Folder")
        finally:
            if self.winfo_exists(): self.attributes("-topmost", True)
        if d: self.install_path.set(d)

    def clear_fields(self):
        self.files_list = []; self.display_text.set(""); self.install_path.set(self.parent_app.community_path)
        self.progress_bar.set(0)
        self.lbl_status.configure(text="Ready.")

    def run_long_paths_fix(self):
        try:
            self.attributes("-topmost", False)
            if not messagebox.askyesno("System Fix", "Enable 'LongPathsEnabled'?", parent=self): return
            cmd = 'reg add "HKLM\\SYSTEM\\CurrentControlSet\\Control\\FileSystem" /v LongPathsEnabled /t REG_DWORD /d 1 /f'
            ctypes.windll.shell32.ShellExecuteW(None, "runas", "cmd.exe", f"/c {cmd}", None, 0)
        finally:
            if self.winfo_exists(): self.attributes("-topmost", True)

    def start_install(self):
        if not self.files_list: return
        self.btn_install.configure(state="disabled", text="PROCESSING...")
        self.progress_bar.set(0)
        threading.Thread(target=self.run_bulk_install_logic, daemon=True).start()

    def update_ui_progress(self, percent, text):
        if self.winfo_exists():
            self.after(0, lambda: self._safe_ui_update(percent, text))

    def _safe_ui_update(self, percent, text):
        if not self.winfo_exists(): return
        self.progress_bar.set(percent)
        self.lbl_status.configure(text=text)

    def finish_with_specific_error(self, message):
        self.attributes("-topmost", True)
        messagebox.showerror("Installation Failed", message, parent=self)
        self.parent_app.scan_liveries()
        self.destroy()

    def resolve_aircraft_from_files(self, root_path, default_key):
        """Intelligent Detection V2"""
        # 1. Check iFly (aircraft.cfg)
        for r, _, files in os.walk(root_path):
            if "aircraft.cfg" in [f.lower() for f in files]:
                try:
                    with open(os.path.join(r, "aircraft.cfg"), "r", encoding='utf-8', errors='ignore') as f:
                        content = f.read().lower()
                        if r'base_container = "..\ifly 737-max8"' in content or r'base_container = "..\\ifly 737-max8"' in content:
                            return "iFly 737 MAX 8"
                except: pass

        # 2. Check PMDG (livery.cfg -> required_tags)
        pmdg_tag_map = {
            "b77f_ext": "PMDG 777F",
            "b77w_ext": "PMDG 777-300ER",
            "b772_ext,engine_ge": "PMDG 777-200ER", 
            "b772_ext,engine_rr": "PMDG 777-200ER", 
            "b772_ext,engine_pw": "PMDG 777-200ER", 
            "b77l_ext": "PMDG 777-200LR",
            # 737
            "b738_ext": "PMDG 737-800",
            "b738bcf_ext": "PMDG 737-800",
            "b738bdsf_ext": "PMDG 737-800",
            "b73bbj2_ext": "PMDG 737-800",
            # 737-900 (NUEVO)
            "b739_ext": "PMDG 737-900",
            "b739er_ext": "PMDG 737-900",
            # 737-600 
            "b736_ext": "PMDG 737-600"
        }

        for r, _, files in os.walk(root_path):
            if "livery.cfg" in [f.lower() for f in files]:
                try:
                    with open(os.path.join(r, "livery.cfg"), "r", encoding='utf-8', errors='ignore') as f:
                        for line in f:
                            if "required_tags" in line.lower():
                                clean_line = line.lower()
                                for tag_key, ac_key in pmdg_tag_map.items():
                                    required_parts = [t.strip() for t in tag_key.split(",")]
                                    if all(part in clean_line for part in required_parts):
                                        return ac_key
                except: pass

        return default_key

    def get_user_folder_name_thread_safe(self, default_name, origin_name):
        container = {"value": default_name}
        done_event = threading.Event()
        
        def _launch():
            self.attributes("-topmost", False)
            FolderNameDialog(self, default_name, origin_name, lambda val: _set_result(val))

        def _set_result(val):
            container["value"] = val
            self.attributes("-topmost", True)
            self.lift()
            done_event.set()
        
        self.after(0, _launch)
        done_event.wait()
        return container["value"]

    def run_bulk_install_logic(self):
        success_count, fail_count = 0, 0
        install_folder = self.install_path.get()
        self.parent_app.last_install_path = install_folder
        self.parent_app.save_current_config()

        total_files = len(self.files_list)
        nested_error_list = []
        folders_to_regenerate = set()
        
        final_stats_counter = {}
        
        selected_default_ac = self.parent_app.selected_aircraft.get()
        fast_temp_base = get_efficient_temp_dir(install_folder)
        
        last_error_msg = "" 

        for idx, item_path in enumerate(self.files_list):
            if not self.winfo_exists(): break 
            
            filename = os.path.basename(item_path)
            
            def progress_callback(rel_pct, action_text):
                self.update_ui_progress(rel_pct, f"[{idx+1}/{total_files}] {filename}: {action_text}")

            if self.winfo_exists():
                self.after(0, lambda: self.btn_install.configure(text=f"Installing {idx+1}/{total_files}..."))
            
            progress_callback(0.0, "Starting...")
            
            # --- CASE 1: INI FILES ---
            if item_path.lower().endswith(".ini"):
                try:
                    self.parent_app.install_standalone_ini(item_path, selected_default_ac)
                    result, data = True, "INI_OK"
                    progress_callback(1.0, "Config Installed.")
                    lbl = f"{selected_default_ac} Config File"
                except Exception as e:
                    result, data = False, str(e)
            
            # --- CASE 2: FOLDERS ---
            elif os.path.isdir(item_path):
                target_ac = self.resolve_aircraft_from_files(item_path, selected_default_ac)
                result, data = self.core_install_logic(
                    item_path, 
                    filename, 
                    install_folder, 
                    progress_callback, 
                    target_ac, 
                    is_source_zip=False 
                )
            
            # --- CASE 3: ZIPS ---
            else:
                result, data = self.process_zip_wrapper(item_path, install_folder, progress_callback, fast_temp_base, selected_default_ac)
            
            if result:
                success_count += 1
                if isinstance(data, dict) and "installed_labels" in data and data["installed_labels"]:
                    for lbl in data["installed_labels"]:
                        full_lbl = f"{lbl} Livery"
                        final_stats_counter[full_lbl] = final_stats_counter.get(full_lbl, 0) + 1
                elif data == "INI_OK":
                     final_stats_counter[lbl] = final_stats_counter.get(lbl, 0) + 1
                else:
                    lbl = f"{selected_default_ac} Item"
                    final_stats_counter[lbl] = final_stats_counter.get(lbl, 0) + 1

                if data != "INI_OK":
                    if isinstance(data, dict):
                         paths = data.get("path")
                         if isinstance(paths, list):
                             for p in paths: folders_to_regenerate.add(p)
                         else:
                             folders_to_regenerate.add(paths)
                    elif isinstance(data, str) and "INI_OK" not in data: 
                         folders_to_regenerate.add(data)
            else:
                last_error_msg = data 
                if data == "NESTED_ZIP_ERROR":
                    nested_error_list.append(filename)
                fail_count += 1
        
        try: shutil.rmtree(fast_temp_base, ignore_errors=True)
        except: pass

        if folders_to_regenerate and not nested_error_list:
            total_layouts = len(folders_to_regenerate)
            for i, folder in enumerate(folders_to_regenerate):
                if os.path.exists(folder):
                    self.update_ui_progress(0.95, f"Regenerating Layout ({i+1}/{total_layouts}): {os.path.basename(folder)}...")
                    self.parent_app.run_layout_generator_safe_move(folder)

        if nested_error_list:
            fail_file = nested_error_list[0]
            msg = f"Cannot install livery from \"{fail_file}\".\n\nContains nested ZIP files. Please extract manually."
            if self.winfo_exists():
                self.after(0, lambda: self.finish_with_specific_error(msg))
        
        elif success_count == 0 and fail_count > 0:
            final_err_msg = f"Installation Failed.\n\nReason: {last_error_msg}"
            if self.winfo_exists():
                self.after(0, lambda: self.finish_with_specific_error(final_err_msg))
        
        else:
            self.update_ui_progress(1.0, "Done.")
            msg_lines = ["Installation Successful! ✈️", "", "You have installed:"]
            for lbl in sorted(final_stats_counter.keys()):
                msg_lines.append(f"- {final_stats_counter[lbl]} {lbl}")
            if fail_count > 0:
                msg_lines.append(f"\nFailed: {fail_count} (Error: {last_error_msg})")
            final_msg = "\n".join(msg_lines)
            if self.winfo_exists():
                self.after(0, lambda: self.finish_success(final_msg))

    def process_zip_wrapper(self, zip_file, install_folder, callback, temp_base_path, default_ac):
        try:
            try:
                with zipfile.ZipFile(zip_file, 'r') as z:
                    for filename in z.namelist():
                        if "__MACOSX" in filename: continue
                        if filename.lower().endswith(".zip"):
                            callback(0.0, "ERROR: Nested Zip Detected")
                            return False, "NESTED_ZIP_ERROR"
            except zipfile.BadZipFile:
                return False, "BAD_ZIP"

            with tempfile.TemporaryDirectory(dir=temp_base_path, prefix="pkg_") as temp_dir:
                callback(0.05, "Extracting...")
                with zipfile.ZipFile(zip_file, 'r') as z:
                    z.extractall(temp_dir)
                
                target_ac = self.resolve_aircraft_from_files(temp_dir, default_ac)
                result = self.core_install_logic(temp_dir, os.path.basename(zip_file), install_folder, callback, target_ac, is_source_zip=True)
                
                if result[0] and isinstance(result[1], dict):
                    result[1]["target_ac"] = target_ac
                
                return result

        except Exception as e:
            if DEBUG_MODE: print(f"Error processing zip {zip_file}: {e}")
            return False, str(e)

    def core_install_logic(self, source_root, package_name_ref, install_folder, callback, target_ac_key, is_source_zip=False):
        try:
            is_ifly_global_intent = ("iFly" in target_ac_key)
            if not is_ifly_global_intent:
                for r, dirs, files in os.walk(source_root):
                     if "aircraft.cfg" in [f.lower() for f in files]:
                        try:
                            with open(os.path.join(r, "aircraft.cfg"), "r", encoding='utf-8', errors='ignore') as f:
                                if "ifly" in f.read().lower():
                                    is_ifly_global_intent = True
                                    break
                        except: pass

            use_addon_linker = self.parent_app.addon_linker_mode.get()
            ask_custom_name = self.custom_folder_name_var.get()
            
            manager_name = "ifly-flightmods-manager" if is_ifly_global_intent else "pmdg-flightmods-manager"
            
            if not use_addon_linker:
                dest_root = os.path.join(install_folder, manager_name)
                os.makedirs(dest_root, exist_ok=True)
                l_path, m_path = os.path.join(dest_root, "layout.json"), os.path.join(dest_root, "manifest.json")
                if not os.path.exists(l_path):
                    with open(l_path, 'w') as f: f.write("{}")
                    manifest = {"dependencies": [], "content_type": "AIRCRAFT", "title": manager_name, "package_version": "1.0.4"}
                    with open(m_path, 'w') as f: json.dump(manifest, f)

            items_to_install = [] 
            if is_ifly_global_intent:
                self.parent_app.process_ifly_ini(source_root, target_ac_key)
                for root, dirs, files in os.walk(source_root, topdown=True):
                    lowercase_files = [f.lower() for f in files]
                    lowercase_dirs = [d.lower() for d in dirs]
                    if "aircraft.cfg" in lowercase_files:
                        items_to_install.append((os.path.basename(root), root))
                        dirs[:] = []; continue
                    if "simobjects" in lowercase_dirs: continue
                    has_real_textures = any(f.endswith(('.dds', '.png.dds')) for f in lowercase_files) or "texture.cfg" in lowercase_files
                    if has_real_textures:
                        items_to_install.append((os.path.basename(root), root))
                        dirs[:] = []; continue
            else:
                items_to_install = self.parent_app.find_liveries_direct_pmdg(source_root, callback)

            if not items_to_install:
                return False, "NO_LIVERIES"

            callback(0.75, "Installing content...")
            installed_labels = [] 
            
            modified_roots = [] 
            if not use_addon_linker: modified_roots.append(dest_root)

            for i, (original_name, src) in enumerate(items_to_install):
                pct = 0.75 + (0.20 * (i / len(items_to_install))) 
                
                item_target_ac_key = self.resolve_aircraft_from_files(src, target_ac_key)
                item_ac_data = AIRCRAFT_DB.get(item_target_ac_key, {})
                sim_folder = item_ac_data.get("sim_folder", "")
                is_ifly_item = (item_ac_data.get("type") == "IFLY") or is_ifly_global_intent
                
                callback(pct, f"Installing {original_name}...")
                
                if use_addon_linker:
                    # 1. Calcular Nombre por Defecto (Smart)
                    unique_name = f"mod-livery-{int(time.time())}"
                    
                    if is_ifly_item:
                        unique_name = original_name.lower().replace(" ", "-").replace("_", "-")
                    else:
                        try:
                            cfg_path = os.path.join(src, "livery.cfg")
                            if os.path.exists(cfg_path):
                                with open(cfg_path, 'r', encoding='utf-8', errors='ignore') as f:
                                    for line in f:
                                        clean_line = line.strip().lower()
                                        if clean_line.startswith("name") and "=" in clean_line:
                                            raw_name = clean_line.split("=", 1)[1].strip().replace('"', '')
                                            final_name = raw_name.lower().replace(" ", "-")
                                            final_name = re.sub(r'[^a-z0-9\-]', '', final_name)
                                            final_name = re.sub(r'-+', '-', final_name)
                                            if final_name: unique_name = final_name
                                            break
                        except: pass
                    
                    # 2. Intervención Usuario
                    if ask_custom_name:
                         callback(pct, "Waiting for user input...")
                         unique_name = self.get_user_folder_name_thread_safe(unique_name, original_name)
                         callback(pct, f"Installing as {unique_name}...")

                    # 3. Crear Carpeta
                    current_dest_root = os.path.join(install_folder, unique_name)
                    if current_dest_root not in modified_roots: modified_roots.append(current_dest_root)
                    os.makedirs(current_dest_root, exist_ok=True)
                    
                    l_path, m_path = os.path.join(current_dest_root, "layout.json"), os.path.join(current_dest_root, "manifest.json")
                    if not os.path.exists(l_path):
                        with open(l_path, 'w') as f: f.write("{}")
                        manifest = {"dependencies": [], "content_type": "AIRCRAFT", "title": unique_name, "package_version": "1.0.0"}
                        with open(m_path, 'w') as f: json.dump(manifest, f)
                else:
                    current_dest_root = dest_root


                if is_ifly_item:
                     target_base_path = os.path.join(current_dest_root, "SimObjects", "Airplanes")
                else:
                     target_base_path = os.path.join(current_dest_root, "SimObjects", "Airplanes", sim_folder, "liveries", "pmdg")
                
                os.makedirs(safe_path(target_base_path), exist_ok=True)

                final_folder_name = original_name 
                if is_source_zip and src == source_root:
                    final_folder_name = os.path.splitext(package_name_ref)[0]
                
                current_label = item_target_ac_key 
                
                if not is_ifly_item:
                    tags_content = ""
                    cfg_check_path = os.path.join(src, "livery.cfg")
                    if os.path.exists(cfg_check_path):
                        try:
                            with open(cfg_check_path, 'r', encoding='utf-8', errors='ignore') as f:
                                for line in f:
                                    if "required_tags" in line.lower():
                                        tags_content = line.split("=", 1)[1].strip()
                        except: pass

                    if tags_content: 
                        current_label = self.parent_app.get_variant_label(item_target_ac_key, tags_content)

                target = os.path.join(target_base_path, final_folder_name)
                
                if os.path.exists(target):
                    try: shutil.rmtree(target)
                    except: pass 
                
                if is_source_zip:
                    shutil.move(src, target)
                else:
                    shutil.copytree(src, target)

                if not is_ifly_item:
                    self.parent_app.process_options_ini(target, item_target_ac_key)
                else:
                    self.parent_app.process_ifly_ini(src, item_target_ac_key)
                
                installed_labels.append(current_label)

            callback(1.0, "Queued.")
            if len(modified_roots) == 1:
                return True, {"type": "MIXED", "path": modified_roots[0], "installed_labels": installed_labels}
            else:
                return True, {"type": "MIXED", "path": modified_roots, "installed_labels": installed_labels}

        except Exception as e:
            if DEBUG_MODE: print(f"Core Logic Error: {e}")
            return False, str(e)

    def is_valid_package(self, folder):
        try:
            contents = [f.lower() for f in os.listdir(folder)]
            return "layout.json" in contents and "manifest.json" in contents and "simobjects" in contents
        except: return False

    def finish_success(self, message):
        self.attributes("-topmost", True)
        messagebox.showinfo("Result", message, parent=self)
        self.parent_app.scan_liveries()
        self.destroy()

class PMDGManagerApp(ctk.CTk, TkinterDnD.DnDWrapper):
    def __init__(self):
        super().__init__()
        self.TkdndVersion = TkinterDnD._require(self) 

        self.title(f"PMDG/iFly Livery Manager - {APP_BRAND_NAME} ({CURRENT_VERSION})") 
        self.geometry("1300x850") 
        self.configure(fg_color=COLOR_BG) 
        
        self.drop_target_register(DND_FILES)
        self.dnd_bind('<<Drop>>', self.on_drop_files)
        
        self.is_first_run = not os.path.exists(CONFIG_FILE)
        self.config = ConfigManager.load_config()
        self.community_path = self.config.get("community_path", "")
        self.last_install_path = self.config.get("last_install_path", "")
        self.last_run_version = self.config.get("last_run_version", "0.0.0")
        self.sim_version = tk.StringVar(value=self.config.get("sim_version", "MS_STORE"))
        
        self.addon_linker_mode = tk.BooleanVar(value=self.config.get("addon_linker_mode", False))
        
        self.processing_lock = False 
        
        last_ac = self.config.get("last_aircraft", "PMDG 737-800")
        if last_ac not in AIRCRAFT_DB:
            last_ac = "PMDG 737-800" 
        self.selected_aircraft = tk.StringVar(value=last_ac)
        
        self.selected_variant = tk.StringVar(value="All")
        self.winglet_ssw_var = tk.BooleanVar(value=True)
        self.winglet_bw_var = tk.BooleanVar(value=True)
        
        self.image_cache = {} 
        self.card_widgets = {} 
        self.search_text = tk.StringVar()
        self.search_text.trace("w", self.on_search_change)
        self.all_liveries_data = []
        self.saved_scroll_pos = 0.0

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=0) 
        
        self.setup_header()
        self.setup_scroll_area()
        self.setup_footer() 
        self.after(100, self.validate_and_scan)
        threading.Thread(target=self.check_for_updates, daemon=True).start()

    def on_drop_files(self, event):
        raw_data = event.data
        if raw_data.startswith('{') and raw_data.endswith('}'):
            files = re.findall(r'\{.*?\}|\S+', raw_data)
            clean_files = [f.strip('{}') for f in files]
        else:
            clean_files = self.tk.splitlist(raw_data)
        
        valid_items = [f for f in clean_files if os.path.isdir(f) or f.lower().endswith('.zip') or f.lower().endswith('.ini')]
        if valid_items:
            popup = InstallerPopup(self, preloaded_files=valid_items)
        else:
            messagebox.showwarning("Drag & Drop", "Only .zip, .ini or folders are supported.")
            
    def get_variant_label(self, ac_key, tags_content):
        tags = tags_content.lower()
        label = ac_key 

        if ac_key == "PMDG 737-800":
            subtype = ""
            if "b738_ext" in tags: subtype = "PAX"
            elif "b738bcf_ext" in tags: subtype = "BCF"
            elif "b738bdsf_ext" in tags: subtype = "BDSF"
            elif "b73bbj2_ext" in tags: subtype = "BBJ2"
            
            winglet = ""
            if "ssw_l" in tags or "ssw_r" in tags: winglet = "SSW"
            elif "bw_l" in tags or "bw_r" in tags: winglet = "BW"
            
            if subtype: label += f" {subtype}"
            if winglet: label += f" {winglet}"

        elif ac_key == "PMDG 737-900":
            # --- 737-900 Logic ---
            is_er = "b739er_ext" in tags
            
            winglet = ""
            if "ssw_l" in tags or "ssw_r" in tags: 
                winglet = "SSW"
            elif "bw_l" in tags or "bw_r" in tags: 
                winglet = "BW"
            
            if is_er:
                # ERSSW or ERBW
                label += f" ER{winglet}"
            else:
                # SSW or BW
                label += f" {winglet}"

        elif ac_key == "PMDG 777-200ER":
            engine = ""
            if "engine_ge" in tags: engine = "GE"
            elif "engine_rr" in tags: engine = "RR"
            elif "engine_pw" in tags: engine = "PW"
            
            if engine: label += f" {engine}"
            
        return label

    def run_layout_generator_safe_move(self, full_path):
        if not os.path.exists(full_path): return

        generator_exe = os.path.join(base_dir, "msfs24_data", "MSFSLayoutGenerator.exe")
        if not os.path.exists(generator_exe):
            print("Layout Generator EXE not found.")
            return

        try:
            drive_root = os.path.splitdrive(full_path)[0] 
            if not drive_root: 
                drive_root = os.path.dirname(full_path)[:2]
            
            drive_root = drive_root + os.sep 
        except:
            drive_root = os.path.abspath(os.sep)

        temp_container = os.path.join(drive_root, "_PMDG_TMP")
        
        folder_name = os.path.basename(full_path)
        temp_work_path = os.path.join(temp_container, folder_name)

        try:
            if not os.path.exists(temp_container): 
                os.makedirs(temp_container, exist_ok=True)
            
            if os.path.exists(temp_work_path):
                shutil.rmtree(temp_work_path, ignore_errors=True)

            shutil.move(full_path, temp_work_path)

            gen_dest = os.path.join(temp_work_path, "MSFSLayoutGenerator.exe")
            shutil.copy2(generator_exe, gen_dest)
            
            my_env = os.environ.copy()
            my_env["PYTHONIOENCODING"] = "utf-8"

            subprocess.call(
                [gen_dest, "layout.json"], 
                cwd=temp_work_path,
                env=my_env, 
                creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0
            )

            if os.path.exists(gen_dest): os.remove(gen_dest)

        except Exception as e:
            print(f"Error during layout regeneration: {e}")
        
        finally:
            if os.path.exists(temp_work_path):
                if os.path.exists(full_path):
                    shutil.rmtree(full_path, ignore_errors=True)
                
                try:
                    shutil.move(temp_work_path, full_path)
                except Exception as restore_error:
                    messagebox.showerror(
                        "Critical Error", 
                        f"Could not restore folder from temp path!\n\nYour files are safe here:\n{temp_work_path}\n\nError: {restore_error}"
                    )

            try:
                if os.path.exists(temp_container) and not os.listdir(temp_container):
                    os.rmdir(temp_container)
            except: pass

    def find_liveries_direct_pmdg(self, root, cb):
        cb(0.6, "Scanning structure...")
        found = []
        for r, d, f in os.walk(root):
            if "__MACOSX" in r: continue
            files_lower = [x.lower() for x in f]
            if "livery.cfg" in files_lower:
                 subdirs = [sd.lower() for sd in os.listdir(r) if os.path.isdir(os.path.join(r, sd))]
                 if any(x.startswith("texture") for x in subdirs):
                     found.append((os.path.basename(r), r))
        return found

    def check_for_updates(self):
        try:
            api_url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
            req = urllib.request.Request(api_url, data=None, headers={'User-Agent': 'FlightModsManager'})
            with urllib.request.urlopen(req) as response:
                data = json.loads(response.read().decode())
                latest_tag = data.get("tag_name", "").strip()
                assets = data.get("assets", [])
                exe_url, txt_url = "", ""
                for asset in assets:
                    if asset["name"] == "FlightMods_Livery_Manager_PMDG.exe": exe_url = asset["browser_download_url"]
                    elif asset["name"] == PATCH_NOTES_FILENAME: txt_url = asset["browser_download_url"]
                if not exe_url: 
                    for asset in assets:
                        if asset["name"].endswith(".exe"): exe_url = asset["browser_download_url"]; break
                if latest_tag and latest_tag != CURRENT_VERSION and exe_url:
                    self.after(0, lambda: self.show_update_dialog(latest_tag, exe_url, txt_url))
        except: pass

    def show_update_dialog(self, new_version, url_exe, url_txt):
        msg = f"A new version is available!\n\nCurrent: {CURRENT_VERSION}\nLatest: {new_version}\n\nUpdate automatically now?"
        if messagebox.askyesno(f"Update Available - {APP_BRAND_NAME}", msg, icon='info', parent=self):
            self.download_and_restart(url_exe, url_txt, new_version) 

    def download_and_restart(self, url_exe, url_txt, new_version):
        if not getattr(sys, 'frozen', False): return
        wait_window = ctk.CTkToplevel(self); wait_window.title("Updating..."); wait_window.geometry("300x150")
        wait_window.update_idletasks()
        x, y = (self.winfo_screenwidth()-300)//2, (self.winfo_screenheight()-150)//2
        wait_window.geometry(f"+{x}+{y}"); wait_window.attributes("-topmost", True)
        ctk.CTkLabel(wait_window, text="Downloading update...\nPlease wait.", font=("Roboto", 14)).pack(expand=True)
        wait_window.update()

        def _download_thread():
            try:
                current_exe = sys.executable; current_dir = os.path.dirname(current_exe)
                orig_exe_name = os.path.basename(current_exe)
                temp_exe_name = f"update_{int(time.time())}.exe"
                downloaded_exe_path = os.path.join(current_dir, temp_exe_name)
                urllib.request.urlretrieve(url_exe, downloaded_exe_path)
                
                txt_cmd = ""
                if url_txt:
                    temp_txt = os.path.join(current_dir, "pn_temp.txt")
                    urllib.request.urlretrieve(url_txt, temp_txt)
                    txt_cmd = f'move /Y "{temp_txt}" "{os.path.join(current_dir, PATCH_NOTES_FILENAME)}"'
                
                bat_path = os.path.join(current_dir, "update_fix.bat")
                bat_content = f"""@echo off
chcp 65001 >nul
timeout /t 3 /nobreak > NUL
del "{current_exe}"
ren "{downloaded_exe_path}" "{orig_exe_name}"
{txt_cmd}
set _MEIPASS2=
set _MEIPASS=
start "" explorer.exe "{current_exe}"
del "%~f0"
exit
"""
                with open(bat_path, "w", encoding="utf-8") as f: 
                    f.write(bat_content)
                
                os.startfile(bat_path)
                os._exit(0)
            except Exception as e:
                print(f"Update failed: {e}")
                self.after(0, wait_window.destroy)
        
        threading.Thread(target=_download_thread, daemon=True).start()

    def setup_header(self):
        header = ctk.CTkFrame(self, height=90, fg_color="transparent") 
        header.grid(row=0, column=0, sticky="ew", padx=30, pady=(30, 15))
        header.grid_columnconfigure(6, weight=1) 

        # Col 0: Model
        ctk.CTkLabel(header, text="Aircraft Model:", font=("Roboto", 12, "bold"), text_color=COLOR_TEXT_SECONDARY).grid(row=0, column=0, sticky="w", padx=(0, 15))
        ac_menu = ctk.CTkOptionMenu(header, variable=self.selected_aircraft, values=list(AIRCRAFT_DB.keys()), command=self.on_aircraft_change, width=220, height=38, font=("Roboto", 13), fg_color=COLOR_SURFACE, button_color=COLOR_SURFACE, button_hover_color="#303550", text_color=COLOR_TEXT_PRIMARY)
        ac_menu.grid(row=1, column=0, sticky="w", padx=(0, 15))

        # Col 1: Variant (Dynamic)
        self.lbl_variant = ctk.CTkLabel(header, text="Aircraft Variant:", font=("Roboto", 12, "bold"), text_color=COLOR_TEXT_SECONDARY)
        self.variant_menu = ctk.CTkOptionMenu(header, variable=self.selected_variant, values=["All"], command=self.on_filter_change, width=160, height=38, font=("Roboto", 13), fg_color=COLOR_SURFACE, button_color=COLOR_SURFACE, button_hover_color="#303550", text_color=COLOR_TEXT_PRIMARY)
        
        # Col 2: Winglets Container (Placeholder)
        self.winglet_container = ctk.CTkFrame(header, fg_color="transparent")
        self.chk_ssw = ctk.CTkCheckBox(self.winglet_container, text="SSW", variable=self.winglet_ssw_var, command=self.on_filter_change, font=("Roboto", 12), width=45) 
        self.chk_ssw.pack(side="left", padx=0) 
        self.chk_bw = ctk.CTkCheckBox(self.winglet_container, text="BW", variable=self.winglet_bw_var, command=self.on_filter_change, font=("Roboto", 12), width=45) 
        self.chk_bw.pack(side="left", padx=10)

        # Col 3: Sim Version
        ctk.CTkLabel(header, text="Sim Version:", font=("Roboto", 12, "bold"), text_color=COLOR_TEXT_SECONDARY).grid(row=0, column=3, sticky="w", padx=10)
        ver_menu = ctk.CTkOptionMenu(header, variable=self.sim_version, values=["MS_STORE", "STEAM", "CUSTOM"], command=self.on_version_change, width=140, height=38, font=("Roboto", 13), fg_color=COLOR_SURFACE, button_color=COLOR_SURFACE, button_hover_color="#303550", text_color=COLOR_TEXT_PRIMARY)
        ver_menu.grid(row=1, column=3, sticky="w", padx=10)

        # Col 4: Search
        search_container = ctk.CTkFrame(header, width=250, height=38, corner_radius=19, fg_color=COLOR_SEARCH_BG, border_width=1, border_color="#3A3F55")
        search_container.grid(row=1, column=4, sticky="e", padx=(20, 10)); search_container.pack_propagate(False)
        ctk.CTkLabel(search_container, text="🔍", font=("Arial", 16), text_color=COLOR_TEXT_SECONDARY).pack(side="left", padx=(15, 5), pady=5)
        self.entry_search = ctk.CTkEntry(search_container, textvariable=self.search_text, placeholder_text="Search...", border_width=0, fg_color="transparent", height=30, font=("Roboto", 13), placeholder_text_color=COLOR_TEXT_SECONDARY, text_color=COLOR_TEXT_PRIMARY)
        self.entry_search.pack(side="left", fill="both", expand=True, padx=(0, 10), pady=2)
        self.btn_clear_search = ctk.CTkButton(search_container, text="✕", width=25, height=25, fg_color="transparent", hover_color=COLOR_SURFACE, text_color="gray", font=("Arial", 12, "bold"), command=self.clear_search)
        
        # Col 5: Refresh
        self.btn_refresh = ctk.CTkButton(header, text="🔄", width=40, height=38, fg_color="transparent", hover_color=COLOR_SURFACE, text_color="white", font=("Arial", 22), command=self.scan_liveries)
        self.btn_refresh.grid(row=1, column=5, sticky="e", padx=5)

        # Col 6: Add Button
        self.btn_add = ctk.CTkButton(header, text="➕ Add Livery", width=120, height=38, fg_color=COLOR_GOLD, hover_color=COLOR_GOLD_HOVER, text_color="black", font=("Roboto", 13, "bold"), command=self.open_installer_popup)
        self.btn_add.grid(row=1, column=6, sticky="e", padx=(15, 0))

    def setup_scroll_area(self):
        self.lbl_stats = ctk.CTkLabel(self, text="Ready.", font=("Roboto", 14, "bold"), text_color=COLOR_TEXT_SECONDARY)
        self.lbl_stats.grid(row=2, column=0, sticky="w", padx=30, pady=(0, 10))
        self.scroll_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 5))
        self.scroll_frame.grid_columnconfigure((0,1,2), weight=1)
        self.scroll_frame._parent_canvas.bind_all("<MouseWheel>", self._on_mouse_wheel)

    def _on_mouse_wheel(self, event):
        velocidad = 60 
        self.scroll_frame._parent_canvas.yview_scroll(int(-1*(event.delta/120)*velocidad), "units")

    def setup_footer(self):
        footer = ctk.CTkFrame(self, height=50, fg_color=COLOR_BG); footer.grid(row=3, column=0, sticky="ew", padx=20, pady=10)
        btn_action = ctk.CTkButton(footer, text=FOOTER_LINK_TEXT, fg_color=FOOTER_BTN_COLOR, hover_color=FOOTER_BTN_HOVER, font=("Roboto", 12, "bold"), height=30, width=120, command=lambda: webbrowser.open(FOOTER_LINK_URL))
        btn_action.pack(side="right", padx=20)
        ctk.CTkLabel(footer, text=f"@ {APP_BRAND_NAME} 2025 | {CURRENT_VERSION}", font=("Roboto", 12), text_color="gray").pack(side="left", padx=20)

    def validate_and_scan(self):
        if self.is_first_run:
            popup = SimSelectorPopup(self); self.wait_window(popup) 
            self.is_first_run = False; self.save_current_config()
            
        if self.last_run_version != CURRENT_VERSION:
            PatchNotesPopup(self)
            self.last_run_version = CURRENT_VERSION
            self.save_current_config() 

        if not self.community_path or not os.path.exists(self.community_path):
            detected = self.find_community_folder_auto()
            if detected: self.community_path = detected
            else:
                user_path = filedialog.askdirectory(title="Select Community Folder")
                if user_path: self.community_path = user_path
                else: return
        
        self.save_current_config()
        self.on_aircraft_change(self.selected_aircraft.get())

    def find_community_folder_auto(self):
        if self.sim_version.get() == "CUSTOM":
             return self.community_path if os.path.exists(self.community_path) else None

        cfg_path = os.path.expandvars(r"%localappdata%\Packages\Microsoft.Limitless_8wekyb3d8bbwe\LocalCache\UserCfg.opt") if self.sim_version.get()=="MS_STORE" else os.path.expandvars(r"%appdata%\Microsoft Flight Simulator 2024\UserCfg.opt")
        
        if os.path.exists(cfg_path):
            try:
                with open(cfg_path, "r", encoding="utf-8", errors="ignore") as f:
                    lines = f.readlines()
                    for line in reversed(lines):
                        line = line.strip()
                        if line.startswith('InstalledPackagesPath'):
                            path_part = line.split('InstalledPackagesPath')[1].strip()
                            path_part = path_part.replace('"', '').strip()
                            return os.path.join(path_part, "Community")
            except Exception as e: 
                print(f"Error reading UserCfg: {e}")
        return None

    def save_current_config(self):
        data = {
            "community_path": self.community_path, 
            "sim_version": self.sim_version.get(), 
            "last_aircraft": self.selected_aircraft.get(), 
            "last_install_path": getattr(self, "last_install_path", ""), 
            "last_run_version": getattr(self, "last_run_version", "0.0.0"),
            "addon_linker_mode": self.addon_linker_mode.get() 
        }
        ConfigManager.save_config(data)

    def on_aircraft_change(self, value):
        self.save_current_config()
        self.search_text.set("")
        self.image_cache = {}
        
        ac_data = AIRCRAFT_DB.get(value, {})
        has_variants = ac_data.get("has_variants", False)
        has_winglets = ac_data.get("has_winglets", False)

        if has_variants:
            self.lbl_variant.grid(row=0, column=1, sticky="w", padx=10)
            self.variant_menu.grid(row=1, column=1, sticky="w", padx=10)
            variants_list = list(ac_data.get("variant_map", {}).keys())
            self.variant_menu.configure(values=["All"] + variants_list)
            self.selected_variant.set("All")
        else:
            self.lbl_variant.grid_forget()
            self.variant_menu.grid_forget()
            self.selected_variant.set("All")

        if has_winglets:
            self.winglet_container.grid(row=1, column=2, sticky="w", padx=10)
        else:
            self.winglet_container.grid_forget()

        self.scan_liveries()

    def on_version_change(self, value): 
        if value == "CUSTOM":
            path = filedialog.askdirectory(title="Select Community Folder")
            if path:
                self.community_path = path
                self.save_current_config()
                self.scan_liveries()
            else:
                self.sim_version.set("MS_STORE")
                self.community_path = ""
                self.validate_and_scan()
        else:
            self.community_path = ""
            self.validate_and_scan()

    def on_search_change(self, *args):
        text = self.search_text.get()
        if text: self.btn_clear_search.pack(side="right", padx=(0, 10))
        else: self.btn_clear_search.pack_forget()
        self.saved_scroll_pos = 0.0
        self.render_grid(filter_text=text)
        self.scroll_frame._parent_canvas.yview_moveto(0.0)
    
    def on_filter_change(self, *args):
        self.scroll_frame._parent_canvas.yview_moveto(0.0)
        self.render_grid(filter_text=self.search_text.get())

    def clear_search(self): self.search_text.set("")
    def open_installer_popup(self): InstallerPopup(self)

    def scan_liveries(self, keep_scroll=False):
        if keep_scroll:
            try: self.saved_scroll_pos = self.scroll_frame._parent_canvas.yview()[0]
            except: self.saved_scroll_pos = 0.0
        else:
            self.saved_scroll_pos = 0.0

        self.scroll_frame._parent_canvas.yview_moveto(0.0)
        self.card_widgets = {} 
        for widget in self.scroll_frame.winfo_children(): widget.destroy()
        
        self.lbl_stats.configure(text="Scanning..."); self.update()
        threading.Thread(target=self._scan_thread_logic, daemon=True).start()

    def _scan_thread_logic(self):
        ac_key = self.selected_aircraft.get()
        ac_data = AIRCRAFT_DB.get(ac_key)
        
        found_data = []
        try:
            if os.path.exists(self.community_path):
                if ac_data["type"] == "IFLY":
                    base_container = ac_data["base_container"]
                    for package in os.listdir(self.community_path):
                        search_root = os.path.join(self.community_path, package, "SimObjects", "Airplanes")
                        if os.path.exists(search_root):
                            for fleet_folder in os.listdir(search_root):
                                cfg_path = os.path.join(search_root, fleet_folder, "aircraft.cfg")
                                if os.path.exists(cfg_path):
                                    is_target = False
                                    title_name = package 
                                    with open(cfg_path, 'r', encoding='utf-8', errors='ignore') as f:
                                        content = f.read()
                                        if f'base_container = "{base_container}"' in content or f"base_container = '{base_container}'" in content:
                                            is_target = True
                                            for line in content.splitlines():
                                                if line.strip().lower().startswith("title"):
                                                    title_name = line.split("=")[1].strip().replace('"', '')
                                                    break
                                    if is_target:
                                        found_data.append({
                                            "name": title_name, 
                                            "liv_path": os.path.join(search_root, fleet_folder),
                                            "root_path": os.path.join(self.community_path, package),
                                            "tags": ""
                                        })
                else:
                    sim_folder = ac_data["sim_folder"]
                    target_rel = os.path.join("SimObjects", "Airplanes", sim_folder, "liveries", "pmdg")
                    for package in os.listdir(self.community_path):
                        check_path = safe_path(os.path.join(self.community_path, package, target_rel))
                        if os.path.isdir(check_path):
                            for liv in os.listdir(check_path):
                                liv_path = os.path.join(check_path, liv)
                                if os.path.isdir(liv_path):
                                    d_name = os.path.basename(liv_path)
                                    tags_str = ""
                                    cfg = safe_path(os.path.join(liv_path, "livery.cfg"))
                                    if os.path.exists(cfg):
                                        with open(cfg, 'r', encoding='utf-8', errors='ignore') as f:
                                            for line in f:
                                                if "name" in line.lower() and "=" in line: 
                                                    d_name = line.split("=")[1].strip().replace('"', '')
                                                if "required_tags" in line.lower():
                                                    tags_str = line.split("=")[1].strip().lower()
                                    
                                    found_data.append({
                                        "name": d_name, 
                                        "liv_path": liv_path, 
                                        "root_path": os.path.join(self.community_path, package),
                                        "tags": tags_str
                                    })
        except: pass
        self.all_liveries_data = found_data; 
        self.after(0, lambda: self.render_grid(filter_text=self.search_text.get()))

    def render_grid(self, filter_text=""):
        for widget in self.scroll_frame.winfo_children(): widget.destroy()
        self.card_widgets = {} 
        self.scroll_frame.update_idletasks()
        
        ac_key = self.selected_aircraft.get()
        ac_data = AIRCRAFT_DB.get(ac_key, {})
        sel_variant = self.selected_variant.get()
        show_ssw = self.winglet_ssw_var.get()
        show_bw = self.winglet_bw_var.get()

        filtered = []
        for item in self.all_liveries_data:
            if filter_text.lower() not in item["name"].lower(): continue
            
            if ac_data.get("has_variants", False) and sel_variant != "All":
                required_tag_for_variant = ac_data["variant_map"].get(sel_variant)
                if required_tag_for_variant:
                    req_parts = [t.strip() for t in required_tag_for_variant.split(',')]
                    if not all(part in item["tags"] for part in req_parts):
                        continue

            if ac_data.get("has_winglets", False):
                is_ssw = "ssw_l" in item["tags"] or "ssw_r" in item["tags"]
                is_bw = "bw_l" in item["tags"] or "bw_r" in item["tags"]
                
                if is_ssw and not show_ssw: continue
                if is_bw and not show_bw: continue
            
            filtered.append(item)

        row, col = 0, 0
        self.card_image_labels = {} 
        for item in filtered:
            card, img_label = self.create_card_skeleton(item["name"], item["liv_path"], item["root_path"], row, col)
            self.card_image_labels[item["liv_path"]] = img_label
            self.card_widgets[item["liv_path"]] = card 
            col += 1
            if col >= 3: col = 0; row += 1
        self.lbl_stats.configure(text=f"{ac_key}: {len(filtered)} Liveries Found")
        
        if self.saved_scroll_pos > 0:
            self.scroll_frame.update_idletasks()
            self.scroll_frame._parent_canvas.yview_moveto(self.saved_scroll_pos)
            
        threading.Thread(target=self._background_image_loader, args=(filtered,), daemon=True).start()

    def create_card_skeleton(self, name, liv_path, root_path, r, c):
        card = ctk.CTkFrame(self.scroll_frame, fg_color=COLOR_CARD, corner_radius=12)
        card.grid(row=r, column=c, padx=10, pady=10, sticky="nsew"); card.grid_columnconfigure(0, weight=1)
        img_label = ctk.CTkLabel(card, text="Loading...", width=300, height=165, fg_color="transparent")
        img_label.grid(row=0, column=0, padx=10, pady=(10, 5))
        ctk.CTkLabel(card, text=name, font=("Roboto", 14, "bold"), wraplength=280).grid(row=1, column=0, padx=10, pady=(2, 10))
        ctk.CTkButton(card, text="🗑 Delete Livery", height=30, fg_color=COLOR_DANGER, hover_color="#B71C1C", command=lambda: self.delete_livery(liv_path, root_path, name)).grid(row=2, column=0, pady=(5, 10), padx=10, sticky="ew")
        return card, img_label

    def _background_image_loader(self, items):
        for item in items:
            path = item["liv_path"]
            if path in self.image_cache: self.after(0, lambda p=path, i=self.image_cache[path]: self._update_card_image(p, i)); continue
            img = self.load_thumbnail_optimized(path)
            if img: self.image_cache[path] = img; self.after(0, lambda p=path, i=img: self._update_card_image(p, i))
            else: self.after(0, lambda p=path: self._update_card_no_image(p))
            time.sleep(0.01)

    def _update_card_image(self, path, ctk_image):
        if path in self.card_image_labels:
            try: lbl = self.card_image_labels[path]; lbl.configure(image=ctk_image, text="")
            except: pass

    def _update_card_no_image(self, path):
        if path in self.card_image_labels:
            try: lbl = self.card_image_labels[path]; lbl.configure(text="[No Image]", image=None)
            except: pass

    def load_thumbnail_optimized(self, path):
        candidates = []
        for sub in ["thumbnail", "texture", "."]:
            for ext in ["jpg", "png", "jpeg"]:
                candidates.append(os.path.join(path, sub, f"thumbnail.{ext}"))
        try:
            for d in os.listdir(path):
                if d.lower().startswith("texture."):
                     for ext in ["jpg", "png", "jpeg"]:
                         candidates.append(os.path.join(path, d, f"thumbnail.{ext}"))
        except: pass

        for p in candidates:
            if os.path.exists(safe_path(p)):
                try:
                    with Image.open(safe_path(p)) as img_file:
                        img = img_file.convert("RGBA")
                        img = ImageOps.fit(img, (300, 165), method=Image.Resampling.LANCZOS)
                        mask = Image.new('L', (300, 165), 0); draw = ImageDraw.Draw(mask); draw.rounded_rectangle((0, 0, 300, 165), radius=15, fill=255)
                        img.putalpha(mask)
                        return ctk.CTkImage(light_image=img, dark_image=img, size=(300, 165))
                except: pass
        return None

    def delete_livery(self, liv, root, name):
        if self.processing_lock: return 
        if not messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete?\n\n{name}\n\nThis action cannot be undone.", parent=self): return
        
        self.processing_lock = True
        
        if liv in self.card_widgets:
            try: self.card_widgets[liv].grid_forget()
            except: pass
        
        if liv in self.image_cache: 
            del self.image_cache[liv]
        if liv in self.card_image_labels:
            del self.card_image_labels[liv]
            
        self.update() 
        
        def _run_delete_thread():
            try: 
                gc.collect() 
                time.sleep(0.5) 
                
                deleted = False
                target_path = safe_path(liv)
                
                if os.path.exists(target_path):
                    for _ in range(10): 
                        try:
                            for root_d, dirs, files in os.walk(target_path):
                                for momo in dirs: 
                                    try: os.chmod(os.path.join(root_d, momo), stat.S_IWRITE)
                                    except: pass
                                for momo in files: 
                                    try: os.chmod(os.path.join(root_d, momo), stat.S_IWRITE)
                                    except: pass
                            
                            shutil.rmtree(target_path, onerror=self._remove_readonly)
                            if not os.path.exists(target_path):
                                deleted = True
                                break
                        except Exception as e:
                            time.sleep(1.0)
                else:
                    deleted = True 

                if deleted:
                    sim_objects = os.path.join(root, "SimObjects", "Airplanes")
                    should_delete_root = False
                    
                    if not os.path.exists(sim_objects):
                        should_delete_root = True
                    else:
                        has_content = False
                        for r, d, f in os.walk(sim_objects):
                            lower_files = [x.lower() for x in f]
                            if "livery.cfg" in lower_files or "aircraft.cfg" in lower_files or "texture.cfg" in lower_files:
                                has_content = True
                                break
                        
                        if not has_content:
                            should_delete_root = True
                    
                    if should_delete_root:
                        try: shutil.rmtree(safe_path(root), onerror=self._remove_readonly)
                        except: pass
                    else:
                        self.run_layout_generator_safe_move(root)

            except Exception as e:
                print(f"THREAD ERROR: {e}")
            
            finally:
                self.after(0, self._finish_delete)
        
        threading.Thread(target=_run_delete_thread, daemon=True).start()

    def _finish_delete(self):
        self.processing_lock = False
        self.scan_liveries(keep_scroll=True)

    def _remove_readonly(self, func, path, excinfo):
        os.chmod(path, stat.S_IWRITE)
        func(path)

    def scan_ini_recursive(self, folder):
        ac = self.selected_aircraft.get()
        for root, _, files in os.walk(folder):
            if "options.ini" in [f.lower() for f in files]:
                self.process_options_ini(root, ac)

    def process_options_ini(self, installed_folder, ac_key):
        cfg_path = os.path.join(installed_folder, "livery.cfg")
        
        target_ini = None
        for f in os.listdir(installed_folder):
            if f.lower().endswith(".ini"):
                target_ini = os.path.join(installed_folder, f)
                break 
        
        if not os.path.exists(cfg_path) or not target_ini: return

        try:
            atc_id = "unknown_tail"
            with open(cfg_path, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    if "atc_id" in line.lower() and "=" in line:
                        raw_id = line.split("=")[1].strip()
                        atc_id = raw_id.replace('"', '').replace("'", "").strip()
                        break
            
            if atc_id:
                wasm_name = AIRCRAFT_DB[ac_key]["wasm"]
                if self.sim_version.get() == "MS_STORE":
                    base_path_str = rf"%localappdata%\Packages\Microsoft.Limitless_8wekyb3d8bbwe\LocalState\WASM\MSFS2024\{wasm_name}\work\Aircraft"
                else:
                    base_path_str = rf"%appdata%\Microsoft Flight Simulator 2024\WASM\MSFS2024\{wasm_name}\work\Aircraft"
                
                base = os.path.expandvars(base_path_str)
                os.makedirs(base, exist_ok=True)
                shutil.copy2(target_ini, os.path.join(base, f"{atc_id}.ini"))
        except: pass

    def process_ifly_ini(self, folder_path, ac_key):
        if not os.path.exists(folder_path): return

        wasm_name = AIRCRAFT_DB[ac_key]["wasm"]
        if self.sim_version.get() == "MS_STORE":
             base_path_str = rf"%localappdata%\Packages\Microsoft.Limitless_8wekyb3d8bbwe\LocalState\WASM\MSFS2020\{wasm_name}\work"
        else:
             base_path_str = rf"%appdata%\Microsoft Flight Simulator 2024\WASM\MSFS2020\{wasm_name}\work"
             
        base = os.path.expandvars(base_path_str)
        os.makedirs(base, exist_ok=True)
        
        try:
            for f in os.listdir(folder_path):
                full_path = os.path.join(folder_path, f)
                if os.path.isfile(full_path) and f.lower().endswith(".ini"):
                    shutil.copy2(full_path, os.path.join(base, f))
                    if DEBUG_MODE: print(f"iFly Config Found & Installed: {f}")
        except Exception as e:
            print(f"Error processing iFly INI: {e}")

    def install_standalone_ini(self, file_path, ac_key):
        filename = os.path.basename(file_path)
        ac_data = AIRCRAFT_DB[ac_key]
        wasm_name = ac_data["wasm"]
        
        if ac_data["type"] == "IFLY":
             base_path_str = rf"%localappdata%\Packages\Microsoft.Limitless_8wekyb3d8bbwe\LocalState\WASM\MSFS2020\{wasm_name}\work" if self.sim_version.get()=="MS_STORE" else rf"%appdata%\Microsoft Flight Simulator 2024\WASM\MSFS2020\{wasm_name}\work"
        else:
             base_path_str = rf"%localappdata%\Packages\Microsoft.Limitless_8wekyb3d8bbwe\LocalState\WASM\MSFS2024\{wasm_name}\work\Aircraft" if self.sim_version.get()=="MS_STORE" else rf"%appdata%\Microsoft Flight Simulator 2024\WASM\MSFS2024\{wasm_name}\work\Aircraft"

        base = os.path.expandvars(base_path_str)
        os.makedirs(base, exist_ok=True)
        shutil.copy2(file_path, os.path.join(base, filename))

class ConfigManager:
    @staticmethod
    def get_defaults():
        return {
            "community_path": "", 
            "sim_version": "MS_STORE", 
            "last_aircraft": "PMDG 737-800", 
            "last_run_version": "0.0.0",
            "addon_linker_mode": False
        }

    @staticmethod
    def load_config():
        if not os.path.exists(CONFIG_FILE):
            return ConfigManager.get_defaults()

        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f: 
                data = json.load(f)
                saved_ver = data.get("last_run_version", "0.0.0")
                buggy_versions = ["v1.0.5.1", "v1.0.5.0", "v1.0.4", "0.0.0"]
                if saved_ver in buggy_versions or saved_ver != CURRENT_VERSION:
                    if DEBUG_MODE: print("Versión antigua detectada. Purgando configuración corrupta.")
                    return ConfigManager.get_defaults()
                if "addon_linker_mode" not in data: data["addon_linker_mode"] = False
                return data

        except UnicodeDecodeError:
            print("Archivo de configuración corrupto (Encoding Error). Reseteando...")
            return ConfigManager.get_defaults()
            
        except json.JSONDecodeError:
            return ConfigManager.get_defaults()
            
        except Exception as e:
            print(f"Error cargando config: {e}")
            return ConfigManager.get_defaults()

    @staticmethod
    def save_config(data):
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f: 
                json.dump(data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"No se pudo guardar la config: {e}")

if __name__ == "__main__":
    app = PMDGManagerApp()
    app.mainloop()
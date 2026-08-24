import time
import os
import sys
import threading
import subprocess
import webbrowser
import shutil
import re
import requests
import ipaddress
import datetime
import tkinter as tk
from tkinter import scrolledtext, ttk
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, InvalidSessionIdException, WebDriverException

# --- Configuration ---
CACHE_FILE = "post_cache.txt"
VPN_IP_FILE = "vpn_ips.txt"

class RedditBotApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Reddit Auto-Commenter")
        self.root.geometry("700x650")
        self.root.minsize(600, 500)
        
        self.is_running = False
        self.is_logged_in = False
        self.bot_thread = None
        self.driver = None
        
        # Setup daily log filename based on current date (redditMM-DD.txt)
        current_date = datetime.datetime.now()
        self.daily_log_filename = f"reddit{current_date.strftime('%m-%d')}.txt"
        
        self.is_linux = sys.platform.startswith("linux")
        self.detect_os_and_theme()
        self.setup_ui()
        self.processed_posts = self.load_cache()
        
        self.log(f"Session started. Active log file: {self.daily_log_filename}")
        self.root.after(500, self.check_environment)

    def detect_os_and_theme(self):
        """Automatically detects OS and display server to set the best native theme and background."""
        self.style = ttk.Style(self.root)
        available_themes = self.style.theme_names()
        
        self.bg_color = "#f0f0f0"
        self.fg_color = "#000000"
        self.entry_bg = "#ffffff"
        self.border_color = "#cccccc"

        if sys.platform == "win32":
            if 'vista' in available_themes:
                self.style.theme_use('vista')
            elif 'winnative' in available_themes:
                self.style.theme_use('winnative')
        elif sys.platform == "darwin":
            if 'aqua' in available_themes:
                self.style.theme_use('aqua')
            self.bg_color = "#ececec"
        elif self.is_linux:
            self.bg_color = "#0f172a"
            self.fg_color = "#f8fafc"
            self.entry_bg = "#1e293b"
            self.border_color = "#334155"
            
            self.style.configure('TButton', font=('Helvetica', 10), padding=5, background="#1e293b", foreground=self.fg_color)
            self.style.map('TButton', background=[('active', '#334155')])
            self.style.configure('Action.TButton', font=('Helvetica', 10, 'bold'), padding=8, background="#2563eb", foreground="white")
            self.style.map('Action.TButton', background=[('active', '#3b82f6')])

        self.root.configure(bg=self.bg_color)

    # --- Custom Themed Dialogs ---
    def _center_toplevel(self, win, width=400, height=200):
        win.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - (width // 2)
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - (height // 2)
        win.geometry(f"{width}x{height}+{x}+{y}")
        win.transient(self.root)
        win.grab_set()

    def custom_messagebox(self, title, message, msg_type="info"):
        win = tk.Toplevel(self.root)
        win.title(title)
        win.configure(bg=self.bg_color)
        win.resizable(False, False)
        self._center_toplevel(win, 400, 150)

        color = self.fg_color
        if msg_type == "error": color = "#ef4444"
        elif msg_type == "warning": color = "#f59e0b"

        tk.Label(win, text=title, font=('Helvetica', 11, 'bold'), bg=self.bg_color, fg=color).pack(pady=(15, 5))
        tk.Label(win, text=message, bg=self.bg_color, fg=self.fg_color, wraplength=350, justify=tk.CENTER).pack(pady=(0, 15))
        
        ttk.Button(win, text="OK", command=win.destroy).pack(pady=5)
        self.root.wait_window(win)

    def custom_askyesno(self, title, message):
        win = tk.Toplevel(self.root)
        win.title(title)
        win.configure(bg=self.bg_color)
        win.resizable(False, False)
        self._center_toplevel(win, 450, 180)

        result = False
        def on_yes(): nonlocal result; result = True; win.destroy()
        def on_no(): win.destroy()

        tk.Label(win, text=title, font=('Helvetica', 11, 'bold'), bg=self.bg_color, fg=self.fg_color).pack(pady=(15, 5))
        tk.Label(win, text=message, bg=self.bg_color, fg=self.fg_color, wraplength=400, justify=tk.CENTER).pack(pady=(0, 15))
        
        btn_frame = tk.Frame(win, bg=self.bg_color)
        btn_frame.pack(fill=tk.X, padx=20)
        ttk.Button(btn_frame, text="Yes", command=on_yes).pack(side=tk.LEFT, expand=True, padx=5)
        ttk.Button(btn_frame, text="No", command=on_no).pack(side=tk.RIGHT, expand=True, padx=5)
        
        self.root.wait_window(win)
        return result

    def custom_askstring(self, title, prompt, show=None):
        win = tk.Toplevel(self.root)
        win.title(title)
        win.configure(bg=self.bg_color)
        win.resizable(False, False)
        self._center_toplevel(win, 400, 180)

        result = None
        def on_ok(event=None): nonlocal result; result = entry.get(); win.destroy()
        def on_cancel(): win.destroy()

        tk.Label(win, text=title, font=('Helvetica', 11, 'bold'), bg=self.bg_color, fg=self.fg_color).pack(pady=(15, 5))
        tk.Label(win, text=prompt, bg=self.bg_color, fg=self.fg_color, wraplength=350).pack(pady=(0, 10))
        
        entry = self.create_tk_entry(win, "")
        if show: entry.configure(show=show)
        entry.pack(fill=tk.X, padx=30, pady=5)
        entry.bind("<Return>", on_ok)
        entry.focus_set()

        btn_frame = tk.Frame(win, bg=self.bg_color)
        btn_frame.pack(fill=tk.X, padx=30, pady=10)
        ttk.Button(btn_frame, text="OK", command=on_ok).pack(side=tk.LEFT, expand=True, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=on_cancel).pack(side=tk.RIGHT, expand=True, padx=5)
        
        self.root.wait_window(win)
        return result

    def show_vpn_warning(self, current_ip):
        warning_win = tk.Toplevel(self.root)
        warning_win.title("VPN Required")
        warning_win.configure(bg=self.bg_color)
        warning_win.resizable(False, False)
        self._center_toplevel(warning_win, 450, 230)

        msg_frame = tk.Frame(warning_win, bg=self.bg_color)
        msg_frame.pack(expand=True, fill=tk.BOTH, padx=20, pady=20)

        tk.Label(msg_frame, text="VPN Connection Required", font=('Helvetica', 12, 'bold'), 
                 bg=self.bg_color, fg="#ef4444").pack(pady=(0, 10))

        msg = (f"Your current IP ({current_ip}) does NOT appear in major VPN datacenter lists.\n\n"
               "Please connect to your VPN to protect your identity before logging in or starting the bot.")
        tk.Label(msg_frame, text=msg, bg=self.bg_color, fg=self.fg_color, wraplength=400, justify=tk.CENTER).pack(pady=(0, 15))

        if sys.platform.startswith("linux"): dl_link = "https://protonvpn.com/download-linux"
        elif sys.platform == "darwin": dl_link = "https://protonvpn.com/download-macos"
        else: dl_link = "https://protonvpn.com/download-windows"
        
        btn_frame = tk.Frame(msg_frame, bg=self.bg_color)
        btn_frame.pack(fill=tk.X, pady=5)

        ttk.Button(btn_frame, text="Get ProtonVPN", command=lambda: webbrowser.open(dl_link)).pack(side=tk.LEFT, expand=True, padx=5)
        ttk.Button(btn_frame, text="I'll Connect It", command=warning_win.destroy).pack(side=tk.RIGHT, expand=True, padx=5)
        
        self.root.wait_window(warning_win)

    # --- VPN API Logic ---
    def fetch_vpn_ips(self):
        self.log("Fetching live server IPs from public mirrors...")
        sources = [
            'https://raw.githubusercontent.com/tn3w/ProtonVPN-IPs/master/protonvpn_ips.txt',
            'https://raw.githubusercontent.com/X4BNet/lists_vpn/main/output/vpn/ipv4.txt'
        ]
        combined_ips_and_cidrs = set()
        for url in sources:
            try:
                response = requests.get(url, timeout=15)
                response.raise_for_status()
                for line in response.text.splitlines():
                    clean_line = line.strip()
                    if clean_line and not clean_line.startswith('#'):
                        combined_ips_and_cidrs.add(clean_line)
                self.log(f"Fetched rules from {url.split('/')[-1]}")
            except Exception as e:
                self.log(f"Error fetching from {url}: {e}")
                
        if combined_ips_and_cidrs:
            try:
                with open(VPN_IP_FILE, 'w') as f:
                    for ip in combined_ips_and_cidrs:
                        f.write(f"{ip}\n")
                self.log(f"Successfully cached {len(combined_ips_and_cidrs)} VPN IP rules to {VPN_IP_FILE}")
            except Exception as e:
                self.log(f"Error writing to cache file: {e}")
        return combined_ips_and_cidrs

    def check_vpn_active(self):
        if not self.vpn_check_var.get():
            self.log("VPN Check is disabled. Proceeding...")
            return True

        vpn_rules = set()
        if os.path.exists(VPN_IP_FILE):
            with open(VPN_IP_FILE, "r") as f:
                vpn_rules = set(line.strip() for line in f if line.strip())

        if not vpn_rules:
            vpn_rules = self.fetch_vpn_ips()

        if not vpn_rules:
            self.custom_messagebox("Error", "Could not fetch VPN server lists. Cannot verify connection.", "error")
            return False

        self.log("Verifying your current IP address...")
        try:
            current_ip_str = requests.get('https://api.ipify.org?format=json', timeout=10).json().get('ip')
            current_ip_obj = ipaddress.ip_address(current_ip_str)
            is_secure = False
            for rule in vpn_rules:
                try:
                    if '/' in rule:
                        network = ipaddress.ip_network(rule, strict=False)
                        if current_ip_obj in network:
                            is_secure = True
                            break
                    else:
                        if current_ip_str == rule:
                            is_secure = True
                            break
                except ValueError:
                    continue
            
            if is_secure:
                self.log(f"VPN Verified! Connected securely via commercial IP: {current_ip_str}")
                return True
            else:
                self.log(f"CRITICAL: Unmasked or non-VPN IP detected ({current_ip_str}).")
                self.show_vpn_warning(current_ip_str)
                return False
        except Exception as e:
            self.log(f"Failed to verify IP address: {e}")
            self.custom_messagebox("Network Error", "Could not verify your IP address.", "error")
            return False

    def trigger_manual_vpn_update(self):
        threading.Thread(target=self.fetch_vpn_ips, daemon=True).start()

    # --- Time Parsing ---
    def parse_time_string(self, time_str):
        time_str = time_str.strip().lower().replace(" ", "")
        if not time_str: return 30
        if time_str.isdigit(): return int(time_str)

        total_seconds = 0
        matches = re.findall(r'(\d+)([dhms])', time_str)
        if not matches:
            self.log(f"Warning: Invalid time format '{time_str}'. Defaulting to 30s.")
            return 30

        for val, unit in matches:
            val = int(val)
            if unit == 'd': total_seconds += val * 86400
            elif unit == 'h': total_seconds += val * 3600
            elif unit == 'm': total_seconds += val * 60
            elif unit == 's': total_seconds += val
        return max(1, total_seconds)

    def format_time_string(self, total_seconds):
        if total_seconds == 0: return "0s"
        parts = []
        d = total_seconds // 86400; total_seconds %= 86400
        h = total_seconds // 3600; total_seconds %= 3600
        m = total_seconds // 60; s = total_seconds % 60
        if d: parts.append(f"{d}d")
        if h: parts.append(f"{h}h")
        if m: parts.append(f"{m}m")
        if s: parts.append(f"{s}s")
        return " ".join(parts)

    def is_npm_running(self):
        try:
            if self.is_linux or sys.platform == "darwin":
                ps_output = subprocess.check_output(['ps', '-A', '-o', 'comm']).decode().lower()
                processes = [line.strip() for line in ps_output.splitlines()]
                if 'node' in processes or 'npm' in processes or 'vite' in processes: return True
            else:
                ps_output = subprocess.check_output(['tasklist', '/NH', '/FO', 'CSV']).decode().lower()
                if '"node.exe"' in ps_output or '"npm.cmd"' in ps_output: return True
        except Exception as e:
            self.log(f"Process check failed: {e}")
        return False

    def check_environment(self):
        if self.is_npm_running():
            self.log("Detected 'npm' or 'node' running! Assuming Rosint is active.")
            return

        self.log("NPM/Rosint does NOT appear to be running.")
        do_install = False
        do_clone = False
        do_start = False
        sudo_pwd = None
        aur_helper_cmd = None

        if os.path.exists('/etc/arch-release'):
            self.log("Arch Linux detected. Checking for AUR helper...")
            aur_helper_cmd = shutil.which('yay') or shutil.which('paru')
            if aur_helper_cmd:
                sudo_pwd = self.custom_askstring("Sudo Required", f"{aur_helper_cmd} requires root privileges. Enter password:", show='*')
                if sudo_pwd: do_install = True

        if not os.path.exists("Rosint"):
            if self.custom_askyesno("Setup Rosint", "Rosint folder not found. Clone from GitHub and start it automatically?"):
                do_clone = True
                do_start = True
        else:
            do_start = True

        threading.Thread(target=self.bg_setup_tasks, args=(do_install, sudo_pwd, aur_helper_cmd, do_clone, do_start), daemon=True).start()

    def bg_setup_tasks(self, do_install, pwd, aur_helper, do_clone, do_start):
        if do_install and pwd and aur_helper:
            try:
                auth_process = subprocess.run(["sudo", "-S", "-v"], input=pwd + "\n", text=True, capture_output=True)
                if auth_process.returncode == 0:
                    subprocess.run([aur_helper, "-S", "git", "nodejs", "npm", "firefox", "geckodriver", "--needed", "--noconfirm"], check=True)
            except Exception as e:
                self.log(f"Installation error: {e}")

        if do_clone:
            try:
                subprocess.run(["git", "clone", "https://github.com/zuxu4n/Rosint.git"], check=True)
                subprocess.run(["npm", "install"], cwd="Rosint", shell=(sys.platform=="win32"), check=True)
            except Exception as e:
                self.log(f"Clone error: {e}")
                return

        if do_start:
            try:
                subprocess.Popen(["npm", "run", "dev"], cwd="Rosint", shell=(sys.platform=="win32"))
                self.root.after(0, lambda: self.custom_messagebox("Success", "Rosint server is booting up!"))
            except Exception as e:
                self.log(f"Start error: {e}")

    def create_tk_entry(self, parent, default_text=""):
        entry = tk.Entry(
            parent, font=('Helvetica', 10), bg=self.entry_bg, fg=self.fg_color, 
            insertbackground="white" if self.is_linux else "black", relief=tk.FLAT,
            highlightthickness=1, highlightbackground=self.border_color, highlightcolor="#2563eb"
        )
        entry.insert(0, default_text)
        return entry

    def setup_ui(self):
        main_container = tk.Frame(self.root, padx=15, pady=15, bg=self.bg_color)
        main_container.pack(fill=tk.BOTH, expand=True)

        settings_frame = tk.LabelFrame(main_container, text="Targeting & Action", font=('Helvetica', 10, 'bold'), 
                                       bg=self.bg_color, fg=self.fg_color, padx=15, pady=15, bd=1, relief=tk.SOLID)
        if self.is_linux: settings_frame.configure(highlightthickness=0, highlightbackground=self.border_color)
        settings_frame.pack(fill=tk.X, pady=(0, 15))
        settings_frame.columnconfigure(1, weight=1)

        tk.Label(settings_frame, text="Target User (u/):", bg=self.bg_color, fg=self.fg_color).grid(row=0, column=0, sticky=tk.W, pady=5, padx=(0, 10))
        self.username_entry = self.create_tk_entry(settings_frame, "")
        self.username_entry.grid(row=0, column=1, sticky=tk.EW, pady=5)

        tk.Label(settings_frame, text="Comment Text:", bg=self.bg_color, fg=self.fg_color).grid(row=1, column=0, sticky=tk.W, pady=5, padx=(0, 10))
        self.comment_entry = self.create_tk_entry(settings_frame, "This is an automated comment!")
        self.comment_entry.grid(row=1, column=1, sticky=tk.EW, pady=5)

        tk.Label(settings_frame, text="Scan Interval:", bg=self.bg_color, fg=self.fg_color).grid(row=2, column=0, sticky=tk.W, pady=5, padx=(0, 10))
        self.interval_entry = self.create_tk_entry(settings_frame, "30s")
        self.interval_entry.grid(row=2, column=1, sticky=tk.W, pady=5)

        vpn_frame = tk.LabelFrame(main_container, text="Network Security", font=('Helvetica', 10, 'bold'), 
                                  bg=self.bg_color, fg=self.fg_color, padx=15, pady=15, bd=1, relief=tk.SOLID)
        vpn_frame.pack(fill=tk.X, pady=(0, 15))

        self.vpn_check_var = tk.BooleanVar(value=True)
        self.vpn_checkbox = tk.Checkbutton(vpn_frame, text="Strict VPN IP Enforcement", variable=self.vpn_check_var, 
                                           bg=self.bg_color, fg=self.fg_color, activebackground=self.bg_color, 
                                           activeforeground=self.fg_color, selectcolor=self.entry_bg)
        self.vpn_checkbox.grid(row=0, column=0, sticky=tk.W, padx=(0, 15))

        self.update_vpn_btn = ttk.Button(vpn_frame, text="Fetch Latest VPN List", command=self.trigger_manual_vpn_update)
        self.update_vpn_btn.grid(row=0, column=1, sticky=tk.W)

        btn_frame = tk.Frame(main_container, bg=self.bg_color)
        btn_frame.pack(fill=tk.X, pady=(5, 15))
        btn_frame.columnconfigure((0,1,2), weight=1)
        
        self.login_btn = ttk.Button(btn_frame, text="1. Open Browser & Log In", command=self.manual_login, style='Action.TButton')
        self.login_btn.grid(row=0, column=0, sticky=tk.EW, padx=5)

        self.start_btn = ttk.Button(btn_frame, text="2. Start Bot", command=self.start_bot, state=tk.DISABLED, style='Action.TButton')
        self.start_btn.grid(row=0, column=1, sticky=tk.EW, padx=5)
        
        self.stop_btn = ttk.Button(btn_frame, text="3. Stop Bot", command=self.stop_bot, state=tk.DISABLED, style='Action.TButton')
        self.stop_btn.grid(row=0, column=2, sticky=tk.EW, padx=5)

        log_label_frame = tk.LabelFrame(main_container, text="Activity Log", font=('Helvetica', 10, 'bold'), 
                                        bg=self.bg_color, fg=self.fg_color, padx=5, pady=5, bd=1, relief=tk.SOLID)
        log_label_frame.pack(fill=tk.BOTH, expand=True)
        
        self.log_area = scrolledtext.ScrolledText(
            log_label_frame, state='disabled', wrap=tk.WORD, font=('Consolas', 10), 
            bg='#1e293b', fg='#4af626', insertbackground='white', bd=0, highlightthickness=0
        )
        self.log_area.pack(fill=tk.BOTH, expand=True)

    def log(self, message):
        timestamped_msg = f"[{time.strftime('%H:%M:%S')}] {message}"
        def _append_log():
            self.log_area.configure(state='normal')
            self.log_area.insert(tk.END, f"{timestamped_msg}\n")
            self.log_area.see(tk.END)
            self.log_area.configure(state='disabled')
        self.root.after(0, _append_log)
        
        try:
            with open(self.daily_log_filename, "a", encoding="utf-8") as f:
                f.write(f"{timestamped_msg}\n")
        except Exception as e:
            print(f"Error writing to daily log file: {e}")

    def load_cache(self):
        if not os.path.exists(CACHE_FILE): return set()
        with open(CACHE_FILE, "r") as file: return set(file.read().splitlines())

    def add_to_cache(self, reddit_url):
        with open(CACHE_FILE, "a") as file: file.write(f"{reddit_url}\n")

    def init_driver(self):
        try:
            if self.driver:
                try: self.driver.quit()
                except Exception: pass
            
            options = webdriver.FirefoxOptions()
            options.accept_insecure_certs = True
            options.set_preference("security.insecure_field_warning.contextual.enabled", False)
            options.set_preference("extensions.pocket.enabled", False)
            options.set_preference("browser.contentblocking.category", "standard")
            options.set_preference("signon.autofillForms", False)
            
            self.driver = webdriver.Firefox(options=options)
            return True
        except Exception as e:
            self.log(f"Failed to start/restart Firefox: {e}")
            return False

    def dismiss_popup_if_present(self):
        try:
            alert = WebDriverWait(self.driver, 2).until(EC.alert_is_present())
            alert.dismiss()
            return True
        except TimeoutException:
            pass
        return False

    def manual_login(self):
        if not self.check_vpn_active(): return
        self.log("Opening Firefox for manual login...")
        if self.init_driver():
            self.driver.get("https://www.reddit.com/login/")
            self.dismiss_popup_if_present()
            self.log("Waiting for user to log in manually...")
            self.start_btn.config(state=tk.NORMAL)
            self.login_btn.config(state=tk.DISABLED)
            self.is_logged_in = True 

    def start_bot(self):
        if not self.username_entry.get().strip():
            self.custom_messagebox("Missing Information", "Please enter a Target User before starting.", "warning")
            return
        if not self.is_logged_in or self.driver is None:
            self.custom_messagebox("Not Logged In", "Please click 'Open Browser & Log In' first.", "warning")
            return
        if not self.check_vpn_active(): return

        if not self.is_running:
            self.is_running = True
            self.start_btn.config(state=tk.DISABLED)
            self.stop_btn.config(state=tk.NORMAL)
            self.log("Starting automation loop...")
            self.bot_thread = threading.Thread(target=self.run_automation, daemon=True)
            self.bot_thread.start()

    def stop_bot(self):
        if self.is_running:
            self.is_running = False
            self.log("Stopping...")
            self.start_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.DISABLED)

    def smart_sleep(self, seconds):
        for _ in range(seconds):
            if not self.is_running: break
            time.sleep(1)

    def run_automation(self):
        try:
            while self.is_running:
                target_username = self.username_entry.get().strip()
                target_url = f"http://localhost:5173/?u={target_username}"
                comment_text = self.comment_entry.get()
                
                raw_interval = self.interval_entry.get()
                loop_interval_sec = self.parse_time_string(raw_interval)
                formatted_interval = self.format_time_string(loop_interval_sec)

                try:
                    _ = self.driver.current_url
                except (InvalidSessionIdException, WebDriverException, AttributeError):
                    self.log("Browser window lost connection. Re-initializing...")
                    if not self.init_driver():
                        self.smart_sleep(10)
                        continue
                    self.driver.get("https://www.reddit.com/login/")
                    self.dismiss_popup_if_present()

                self.log(f"Scanning {target_url}...")
                try:
                    self.driver.get(target_url)
                    self.dismiss_popup_if_present()
                except Exception as e:
                    self.log(f"Navigation error: {e}. Retrying...")
                    self.smart_sleep(10)
                    continue
                
                try:
                    reddit_link_element = WebDriverWait(self.driver, 15).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "a[href*='reddit.com']"))
                    )
                    reddit_url = reddit_link_element.get_attribute("href")
                    
                    # Convert to old.reddit.com to bypass modern layout shadow DOM bugs
                    reddit_url = reddit_url.replace("www.reddit.com", "old.reddit.com")
                    if "old.reddit.com" not in reddit_url and "reddit.com" in reddit_url:
                        reddit_url = reddit_url.replace("reddit.com", "old.reddit.com")
                    
                    if reddit_url in self.processed_posts:
                        self.log("Post already cached.")
                        self.smart_sleep(loop_interval_sec)
                        continue
                    
                    self.log(f"New post found. Opening via Classic Reddit: {reddit_url}")
                    self.driver.get(reddit_url)
                    self.dismiss_popup_if_present()
                    
                    self.log("Checking if post is open for comments...")
                    try:
                        # NEW FIX: Target only the top-level comment box inside the .commentarea 
                        # and require it to be fully VISIBLE, not just present in the DOM.
                        comment_box = WebDriverWait(self.driver, 10).until(
                            EC.visibility_of_element_located((By.CSS_SELECTOR, ".commentarea textarea[name='text']"))
                        )
                    except TimeoutException:
                        self.log("Post appears to be deleted, removed, or locked (textarea not found). Skipping...")
                        self.processed_posts.add(reddit_url)
                        self.add_to_cache(reddit_url)
                        self.smart_sleep(loop_interval_sec)
                        continue
                    
                    comment_box.clear() # Clear any pre-filled text just in case
                    comment_box.send_keys(comment_text)
                    
                    # NEW FIX: Target the specific save button associated with the top-level comment area
                    submit_btn = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, ".commentarea .usertext-buttons button[type='submit']"))
                    )
                    submit_btn.click()
                    
                    # Allow Reddit a brief moment to process, then check for error messages (rate limit, spam filters)
                    time.sleep(3)
                    
                    error_elements = self.driver.find_elements(By.CSS_SELECTOR, ".error, .usertext-edit .error")
                    if error_elements and any(el.is_displayed() for el in error_elements):
                        error_text = error_elements[0].text.strip()
                        self.log(f"Reddit rejected comment: {error_text}")
                    else:
                        self.log("Comment posted successfully!")
                    
                    self.processed_posts.add(reddit_url)
                    self.add_to_cache(reddit_url)

                except TimeoutException:
                    self.log("Could not find the Reddit link on localhost in time.")
                except NoSuchElementException as e:
                    self.log(f"Element not found: {e}")
                except Exception as e:
                    self.log(f"Unexpected error during scan loop: {e}")

                self.log(f"Waiting {formatted_interval} before next scan...")
                self.smart_sleep(loop_interval_sec)

        except Exception as e:
            self.log(f"Fatal WebDriver Error: {e}")
        finally:
            self.is_running = False
            self.start_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.DISABLED)
            self.log("Automation loop stopped.")

if __name__ == "__main__":
    root = tk.Tk()
    app = RedditBotApp(root)
    root.mainloop()
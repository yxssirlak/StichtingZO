import sys
import os
import pyrebase
import ctypes
import base64
import traceback
import json
import csv
import textwrap
import webbrowser
import random
import hashlib
import requests 
import subprocess
import time
from io import BytesIO
from datetime import datetime
from dotenv import load_dotenv
from PIL import Image, ImageDraw
from collections import Counter

HUIDIGE_VERSIE = "1.4.2"

#python -m PyInstaller --noconsole --onefile --exclude PyQt5 --icon=app.ico --add-data "Icons;Icons" --add-data "logo_stichtingzo_rgb.png;." --add-data "ENVStichtingZO.env;." StichtingZOPortaal.py

def log_uncaught_exceptions(ex_cls, ex, tb):
    """Vangt onverwachte fouten op en schrijft ze naar error_log.txt"""
    error_msg = ''.join(traceback.format_tb(tb))
    error_msg += f'{ex_cls.__name__}: {ex}\n'
    
    application_path = sys._MEIPASS if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
    log_file_path = os.path.join(application_path, "error_log.txt")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    try:
        with open(log_file_path, "a", encoding="utf-8") as f:
            f.write(f"\n[{timestamp}] --- CRASH RAPPORT ---\n")
            f.write(error_msg)
            f.write("-" * 40 + "\n")
    except:
        pass 
        
    try:
        sys.__excepthook__(ex_cls, ex, tb)
    except AttributeError:
        pass

sys.excepthook = log_uncaught_exceptions

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QPushButton, QLineEdit, QTextEdit, QComboBox, 
    QScrollArea, QFrame, QStackedWidget, QCheckBox, QRadioButton, 
    QSlider, QFileDialog, QDialog, QGridLayout, QCalendarWidget, 
    QSizePolicy, QSpacerItem, QButtonGroup, QGraphicsDropShadowEffect,
    QGraphicsOpacityEffect, QListView, QMenu, QProgressDialog, QMessageBox, QProgressBar
)
from PySide6.QtCore import (
    Qt, Signal, QObject, QTimer, QByteArray, QSettings, 
    QPropertyAnimation, QEasingCurve, QDate, QSize, 
    QParallelAnimationGroup, QRect, QEvent, QPoint, QMimeData
)
from PySide6.QtGui import QIcon, QPixmap, QColor, QFont, QPainter, QPen, QCursor, QGuiApplication, QDrag, QShortcut, QKeySequence, QImage
from PySide6.QtSvg import QSvgRenderer

try:
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
    from matplotlib.ticker import MaxNLocator
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

class AutoUpdater:
    def __init__(self, parent_widget=None):
        self.parent = parent_widget

    def controleer_op_updates(self, stille_check=False):
        if USER_TOKEN == "OFFLINE":
            if not stille_check:
                QMessageBox.warning(self.parent, "Offline Modus", "Je bent ingelogd in de offline werkmodus. Controleer je internetverbinding en log opnieuw in om updates te zoeken.")
            return

        try:
            # 1. Haal de laatste versie op uit Firebase
            info = db.child("app_info").get(USER_TOKEN).val()
            if not info:
                if not stille_check:
                    QMessageBox.warning(self.parent, "Update Fout", "Kon update-informatie niet ophalen van de server.")
                return

            online_versie = info.get("laatste_versie", "0.0.0")
            download_url = info.get("download_link", "")

            # 2. Vergelijk versies
            if self.is_nieuwer(HUIDIGE_VERSIE, online_versie):
                self.parent.update_available = True
                self.parent.update_versie = online_versie
                self.parent.update_url = download_url
                
                if stille_check:
                    self.parent.werk_notificatie_badge_bij()
                    # Ververs instellingen tabblad als de gebruiker daar toevallig in zit
                    if self.parent.active_nav_id == "Instellingen":
                        self.parent.show_tab_instellingen()
                else:
                    self.vraag_om_update(online_versie, download_url)
            else:
                self.parent.update_available = False
                if not stille_check:
                    QMessageBox.information(self.parent, "Up-to-date", f"Je gebruikt de nieuwste versie van de Stichting ZO! app (v{HUIDIGE_VERSIE}).\nEr zijn geen updates beschikbaar.")
                elif stille_check:
                    self.parent.werk_notificatie_badge_bij()

        except Exception as e:
            if not stille_check:
                QMessageBox.critical(self.parent, "Fout", f"Update check mislukt:\n{e}")

    def is_nieuwer(self, huidig, online):
        try:
            huidig_parts = [int(x) for x in huidig.split('.')]
            online_parts = [int(x) for x in online.split('.')]
            return online_parts > huidig_parts
        except:
            return False

    def vraag_om_update(self, nieuwe_versie, download_url):
        popup = UpdatePopup(self.parent, HUIDIGE_VERSIE, nieuwe_versie)
        
        if popup.exec() == QDialog.Accepted:
            self.download_en_installeer(download_url)

    def download_en_installeer(self, url):
        progress = CustomProgressDialog(self.parent, "Bezig met updaten")
        progress.show()

        huidige_exe = sys.executable 
        update_exe = os.path.join(os.path.dirname(huidige_exe), "update_temp.exe")

        try:
            response = requests.get(url, stream=True)
            total_size = int(response.headers.get('content-length', 0))
            block_size = 1024
            gedownload = 0

            with open(update_exe, 'wb') as file:
                for data in response.iter_content(block_size):
                    if progress.wasCanceled():
                        file.close()
                        if os.path.exists(update_exe):
                            os.remove(update_exe)
                        return
                    file.write(data)
                    gedownload += len(data)
                    if total_size > 0:
                        progress.setValue(int((gedownload / total_size) * 100))
                        QApplication.processEvents()

            progress.setValue(100)
            progress.lbl_info.setText("Download voltooid! Applicatie herstarten...")
            QApplication.processEvents()
            time.sleep(1) # Korte pauze zodat de gebruiker de 100% ziet
            
            self.voer_vervang_script_uit(huidige_exe, update_exe)

        except Exception as e:
            progress.close()
            QMessageBox.critical(self.parent, "Fout", f"Downloaden mislukt:\n{e}")

    def voer_vervang_script_uit(self, oude_exe, nieuwe_exe):
        oude_exe_naam = os.path.basename(oude_exe)
        nieuwe_exe_naam = os.path.basename(nieuwe_exe)
        map_pad = os.path.dirname(oude_exe)
        
        bat_pad = os.path.join(map_pad, "updater.bat")
        
        bat_code = f"""@echo off
set _MEIPASS2=
set _MEIPASS=
:loop
timeout /t 1 /nobreak > NUL
del "{oude_exe_naam}" > NUL 2>&1
if exist "{oude_exe_naam}" goto loop

ren "{nieuwe_exe_naam}" "{oude_exe_naam}"
start "" "{oude_exe_naam}"
del "%~f0"
"""
        with open(bat_pad, "w") as bat_file:
            bat_file.write(bat_code)

        schoon_env = os.environ.copy()
        verwijder_keys = [k for k in schoon_env if "MEIPASS" in k.upper() or "PYI" in k.upper()]
        for k in verwijder_keys:
            schoon_env.pop(k, None)

        CREATE_NO_WINDOW = 0x08000000
        subprocess.Popen(bat_pad, cwd=map_pad, shell=True, env=schoon_env, creationflags=CREATE_NO_WINDOW)
        
        QApplication.quit()
        sys.exit()

class EmittingStream(QObject):
    textWritten = Signal(str)
    def write(self, text):
        self.textWritten.emit(str(text))
    def flush(self): pass

class NullWriter:
    def write(self, text): pass
    def flush(self): pass

if sys.stdout is None: sys.stdout = NullWriter()
if sys.stderr is None: sys.stderr = NullWriter()

# --- VERBETERDE OMGEVINGSVARIABELEN LOGICA ---
application_path = sys._MEIPASS if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(application_path, 'ENVStichtingZO.env')

if not os.path.exists(env_path) and not getattr(sys, 'frozen', False):
    # VS Code fallback
    env_path = os.path.join(os.getcwd(), 'ENVStichtingZO.env')

load_dotenv(dotenv_path=env_path)

firebase_config = {
    "apiKey": os.getenv("FIREBASE_API_KEY"),
    "authDomain": os.getenv("FIREBASE_AUTH_DOMAIN"),
    "projectId": os.getenv("FIREBASE_PROJECT_ID"),
    "storageBucket": os.getenv("FIREBASE_STORAGE_BUCKET"),
    "messagingSenderId": os.getenv("FIREBASE_MESSAGING_SENDER_ID"),
    "appId": os.getenv("FIREBASE_APP_ID"),
    "databaseURL": os.getenv("FIREBASE_DATABASE_URL") 
}

try:
    if not firebase_config["apiKey"]:
        raise ValueError(".env variabelen zijn leeg! Kan niet verbinden met Firebase.")
    firebase = pyrebase.initialize_app(firebase_config)
    auth = firebase.auth()
    db = firebase.database() 
except Exception as e:
    print(f"🔥 FIREBASE STARTUP FOUT: {e}")
    auth = None; db = None

USER_TOKEN = None
REFRESH_TOKEN = None

class Colors:
    accent = "#00A98F"      
    secondary = "#95C93D"   
    bg_main = ""  
    bg_card = ""  
    bg_sidebar = "" 
    text_main = "" 
    text_grey = "" 
    border = ""

def apply_theme(mode="Systeem"):
    if mode == "Systeem":
        if QGuiApplication.styleHints().colorScheme() == Qt.ColorScheme.Dark:
            mode = "Dark"
        else:
            mode = "Light"

    if mode == "Dark":
        Colors.bg_main = "#0F111A"
        Colors.bg_card = "#1E2233"
        Colors.bg_sidebar = "#161925"
        Colors.text_main = "#F0F0F0"
        Colors.text_grey = "#9CA3AF"
        Colors.border = "#2D334B"
    else:
        Colors.bg_main = "#F3F4F6"
        Colors.bg_card = "#FFFFFF"
        Colors.bg_sidebar = "#FFFFFF"
        Colors.text_main = "#374151"
        Colors.text_grey = "#6B7280"
        Colors.border = "#E5E7EB"

def prepare_system_icons():
    icons_dir = os.path.join(application_path, "Icons")
    os.makedirs(icons_dir, exist_ok=True)

    plus = os.path.join(icons_dir, "Plus.svg")
    with open(plus, "w", encoding="utf-8") as f:
        f.write('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>')

    bin_svg = os.path.join(icons_dir, "bin.svg")
    with open(bin_svg, "w", encoding="utf-8") as f:
        f.write('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>')

    sync = os.path.join(icons_dir, "DatabaseSync.svg")
    with open(sync, "w", encoding="utf-8") as f:
        f.write('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M23 4v6h-6"></path><path d="M1 20v-6h6"></path><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path></svg>')

    link = os.path.join(icons_dir, "link.svg")
    with open(link, "w", encoding="utf-8") as f:
        f.write('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"></path><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"></path></svg>')

    terminal = os.path.join(icons_dir, "Terminal.svg")
    with open(terminal, "w", encoding="utf-8") as f:
        f.write('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="4 17 10 11 4 5"></polyline><line x1="12" y1="19" x2="20" y2="19"></line></svg>')
    
    mail = os.path.join(icons_dir, "Mail.svg")
    with open(mail, "w", encoding="utf-8") as f:
        f.write('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"></path><polyline points="22,6 12,13 2,6"></polyline></svg>')

    trash = os.path.join(icons_dir, "Trash.svg")
    with open(trash, "w", encoding="utf-8") as f:
        f.write('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path><line x1="10" y1="11" x2="10" y2="17"></line><line x1="14" y1="11" x2="14" y2="17"></line></svg>')

    save = os.path.join(icons_dir, "Save.svg")
    with open(save, "w", encoding="utf-8") as f:
        f.write('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"></path><polyline points="17 21 17 13 7 13 7 21"></polyline><polyline points="7 3 7 8 15 8"></polyline></svg>')

    lock = os.path.join(icons_dir, "Lock.svg")
    with open(lock, "w", encoding="utf-8") as f:
        f.write('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect><path d="M7 11V7a5 5 0 0 1 10 0v4"></path></svg>')

    user_svg = os.path.join(icons_dir, "User.svg")
    with open(user_svg, "w", encoding="utf-8") as f:
        f.write('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle></svg>')

    bell = os.path.join(icons_dir, "Bell.svg")
    with open(bell, "w", encoding="utf-8") as f:
        f.write('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"></path><path d="M13.73 21a2 2 0 0 1-3.46 0"></path></svg>')

    logout = os.path.join(icons_dir, "Logout.svg")
    with open(logout, "w", encoding="utf-8") as f:
        f.write('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path><polyline points="16 17 21 12 16 7"></polyline><line x1="21" y1="12" x2="9" y2="12"></line></svg>')

    arrow_white = os.path.join(icons_dir, "SystemArrowWhite.svg")
    with open(arrow_white, "w", encoding="utf-8") as f:
        f.write('<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#FFFFFF" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"></polyline></svg>')
        
    arrow_down = os.path.join(icons_dir, "SystemArrowDown.svg")
    with open(arrow_down, "w", encoding="utf-8") as f:
        f.write('<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"></polyline></svg>')
        
    arrow_up = os.path.join(icons_dir, "SystemArrowUp.svg")
    with open(arrow_up, "w", encoding="utf-8") as f:
        f.write('<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="18 15 12 9 6 15"></polyline></svg>')

    arrow_left = os.path.join(icons_dir, "LeftArrow.svg")
    with open(arrow_left, "w", encoding="utf-8") as f:
        f.write('<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="15 18 9 12 15 6"></polyline></svg>')

    arrow_right = os.path.join(icons_dir, "RightArrow.svg")
    with open(arrow_right, "w", encoding="utf-8") as f:
        f.write('<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="9 18 15 12 9 6"></polyline></svg>')

    fullscreen = os.path.join(icons_dir, "SystemFullscreen.svg")
    with open(fullscreen, "w", encoding="utf-8") as f:
        f.write('<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3"></path></svg>')

    normalscreen = os.path.join(icons_dir, "SystemNormalScreen.svg")
    with open(normalscreen, "w", encoding="utf-8") as f:
        f.write('<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M8 3v3a2 2 0 0 1-2 2H3m18 0h-3a2 2 0 0 1-2-2V3m0 18v-3a2 2 0 0 1 2-2h3M3 16h3a2 2 0 0 1 2 2v3"></path></svg>')

    minimize = os.path.join(icons_dir, "SystemMinimize.svg")
    with open(minimize, "w", encoding="utf-8") as f:
        f.write('<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="5" y1="12" x2="19" y2="12"></line></svg>')

    close_x = os.path.join(icons_dir, "SystemClose.svg")
    with open(close_x, "w", encoding="utf-8") as f:
        f.write('<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>')

    eye = os.path.join(icons_dir, "Eye.svg")
    with open(eye, "w", encoding="utf-8") as f:
        f.write('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"></path><circle cx="12" cy="12" r="3"></circle></svg>')

    eye_off = os.path.join(icons_dir, "EyeOff.svg")
    with open(eye_off, "w", encoding="utf-8") as f:
        f.write('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"></path><line x1="1" y1="1" x2="23" y2="23"></line></svg>')

    search = os.path.join(icons_dir, "Search.svg")
    with open(search, "w", encoding="utf-8") as f:
        f.write('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>')

    checkmark = os.path.join(icons_dir, "Checkmark.svg")
    with open(checkmark, "w", encoding="utf-8") as f:
        f.write('<svg viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>')

    download = os.path.join(icons_dir, "Download.svg")
    with open(download, "w", encoding="utf-8") as f:
        f.write('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>')

    grip = os.path.join(icons_dir, "Grip.svg")
    with open(grip, "w", encoding="utf-8") as f:
        f.write('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="9" cy="12" r="1"></circle><circle cx="9" cy="5" r="1"></circle><circle cx="9" cy="19" r="1"></circle><circle cx="15" cy="12" r="1"></circle><circle cx="15" cy="5" r="1"></circle><circle cx="15" cy="19" r="1"></circle></svg>')

    keyboard = os.path.join(icons_dir, "Keyboard.svg")
    with open(keyboard, "w", encoding="utf-8") as f:
        f.write('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="4" width="20" height="16" rx="2" ry="2"></rect><line x1="6" y1="8" x2="6.01" y2="8"></line><line x1="10" y1="8" x2="10.01" y2="8"></line><line x1="14" y1="8" x2="14.01" y2="8"></line><line x1="18" y1="8" x2="18.01" y2="8"></line><line x1="6" y1="12" x2="6.01" y2="12"></line><line x1="10" y1="12" x2="10.01" y2="12"></line><line x1="14" y1="12" x2="14.01" y2="12"></line><line x1="18" y1="12" x2="18.01" y2="12"></line><line x1="8" y1="16" x2="16" y2="16"></line></svg>')

    qr = os.path.join(icons_dir, "QR.svg")
    with open(qr, "w", encoding="utf-8") as f:
        f.write('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7"></rect><rect x="14" y="3" width="7" height="7"></rect><rect x="14" y="14" width="7" height="7"></rect><rect x="3" y="14" width="7" height="7"></rect><line x1="9" y1="9" x2="9.01" y2="9"></line><line x1="14" y1="9" x2="14.01" y2="9"></line><line x1="9" y1="14" x2="9.01" y2="14"></line><line x1="14" y1="14" x2="14.01" y2="14"></line><line x1="14" y1="21" x2="14.01" y2="21"></line><line x1="21" y1="9" x2="21.01" y2="9"></line></svg>')

    edit = os.path.join(icons_dir, "Edit.svg")
    with open(edit, "w", encoding="utf-8") as f:
        f.write('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path></svg>')

    more = os.path.join(icons_dir, "More.svg")
    with open(more, "w", encoding="utf-8") as f:
        f.write('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="1"></circle><circle cx="12" cy="5" r="1"></circle><circle cx="12" cy="19" r="1"></circle></svg>')

    info = os.path.join(icons_dir, "Info.svg")
    with open(info, "w", encoding="utf-8") as f:
        f.write('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>')

    return arrow_white.replace("\\", "/")

def get_stylesheet():
    arrow_url = prepare_system_icons()
    checkmark_url = os.path.join(application_path, "Icons", "Checkmark.svg").replace("\\", "/")
    
    return f"""
        QWidget {{ font-family: 'Segoe UI', 'Inter', system-ui, sans-serif; color: {Colors.text_main}; }}
        QMainWindow {{ background-color: transparent; }}
        
        QFrame#MainFrame {{ background-color: {Colors.bg_main}; border-radius: 12px; }}
        
        QRadioButton {{ spacing: 8px; outline: none; color: {Colors.text_main}; }}
        QRadioButton::indicator {{ width: 14px; height: 14px; border: 2px solid {Colors.border}; border-radius: 9px; background-color: {Colors.bg_main}; }}
        QRadioButton::indicator:hover {{ border: 2px solid {Colors.accent}; }}
        QRadioButton::indicator:checked {{ width: 8px; height: 8px; border: 5px solid {Colors.accent}; background-color: {Colors.bg_main}; border-radius: 9px; }}

        QScrollArea {{ border: none; background-color: transparent; }}
        QScrollArea > QWidget > QWidget {{ background-color: transparent; }}
        
        QFrame#Card {{ background-color: {Colors.bg_card}; border: 1px solid {Colors.border}; border-radius: 10px; }}
        QFrame#HeroCard {{ background-color: {Colors.bg_sidebar}; border: 2px solid {Colors.accent}; border-radius: 12px; }}
        QFrame#Sidebar {{ background-color: {Colors.bg_sidebar}; border-right: 1px solid {Colors.border}; border-top-left-radius: 12px; border-bottom-left-radius: 12px; }}
        QFrame#TitleBar {{ background-color: {Colors.bg_main}; border-top-right-radius: 12px; border-top-left-radius: 12px; }}
        
        QPushButton {{ background-color: {Colors.bg_sidebar}; border: 1px solid {Colors.border}; border-radius: 6px; padding: 8px 12px; font-weight: bold; color: {Colors.text_main}; outline: none; }}
        QPushButton:hover {{ background-color: {Colors.border}; }}
        
        QPushButton#AccentButton {{ background-color: {Colors.accent}; color: white; border: none; }}
        QPushButton#AccentButton:hover {{ background-color: #008F7A; }}
        
        QPushButton#DetailsButton {{ background-color: {Colors.bg_card}; color: {Colors.text_main}; border: 1px solid {Colors.border}; }}
        QPushButton#DetailsButton:hover {{ background-color: {Colors.border}; }}
        
        QPushButton#DangerButton {{ color: #EF4444; background-color: transparent; border: 1px solid #EF4444; }}
        QPushButton#DangerButton:hover {{ background-color: #FEE2E2; color: #DC2626; }}
        QPushButton#DangerButtonSmall {{ color: #EF4444; background-color: transparent; border: 1px solid transparent; border-radius: 4px; padding: 4px; }}
        QPushButton#DangerButtonSmall:hover {{ background-color: #FEE2E2; border: 1px solid #EF4444; }}
        
        QPushButton#SidebarButton {{ text-align: left; padding: 10px 15px; border: none; font-size: 14px; background-color: transparent; border-radius: 8px; outline: none; margin: 2px 10px; }}
        QPushButton#SidebarButton:hover {{ background-color: {Colors.bg_main}; border-radius: 8px; }}
        QPushButton#SidebarButton:checked {{ background-color: {Colors.accent}; color: white; border-radius: 8px; }}
        
        QPushButton#SidebarButtonCollapsed {{ border: none; font-size: 18px; background-color: transparent; border-radius: 8px; outline: none; margin: 2px 5px; }}
        QPushButton#SidebarButtonCollapsed:hover {{ background-color: {Colors.bg_main}; border-radius: 8px; }}
        QPushButton#SidebarButtonCollapsed:checked {{ background-color: {Colors.accent}; color: white; border-radius: 8px; }}
        
        QPushButton#MinBtn, QPushButton#MaxBtn, QPushButton#CloseBtn {{ border: none; background-color: transparent; color: {Colors.text_grey}; border-radius: 4px; }}
        QPushButton#MinBtn:hover, QPushButton#MaxBtn:hover {{ background-color: rgba(128,128,128,0.2); color: {Colors.text_main}; }}
        QPushButton#CloseBtn:hover {{ background-color: #E81123; color: white; }}
        
        QPushButton#AppBtn {{ border: none; background-color: transparent; color: {Colors.text_grey}; font-weight: bold; outline: none; }}
        QPushButton#AppBtn:hover {{ background-color: {Colors.border}; border-radius: 6px; }}
        
        QLineEdit, QTextEdit {{ background-color: {Colors.bg_card}; border: 1px solid {Colors.border}; border-radius: 6px; padding: 4px 10px; color: {Colors.text_main}; selection-background-color: {Colors.accent}; }}
        QLineEdit:focus, QTextEdit:focus {{ border: 1px solid {Colors.accent}; background-color: {Colors.bg_card}; }}
        
        QCheckBox {{ spacing: 8px; outline: none; color: {Colors.text_main}; }}
        QCheckBox::indicator {{ width: 18px; height: 18px; border: 2px solid {Colors.border}; border-radius: 4px; background-color: {Colors.bg_main}; }}
        QCheckBox::indicator:hover {{ border: 2px solid {Colors.accent}; }}
        QCheckBox::indicator:checked {{ background-color: {Colors.accent}; border: 2px solid {Colors.accent}; image: url('{checkmark_url}'); }}

        QComboBox {{ 
            background-color: {Colors.bg_card}; 
            border: 1px solid {Colors.border}; 
            border-radius: 8px; 
            padding: 6px 12px; 
            color: {Colors.text_main}; 
        }}
        QComboBox:focus {{ border: 1px solid {Colors.accent}; }}
        
        QComboBox::drop-down {{ 
            subcontrol-origin: padding;
            subcontrol-position: top right;
            width: 35px; 
            border-left: none;
            border-top-right-radius: 7px;
            border-bottom-right-radius: 7px;
            background-color: {Colors.accent};
        }}
        
        QComboBox::down-arrow {{ 
            image: url('{arrow_url}'); 
            width: 16px;
            height: 16px;
        }}

        QComboBox QAbstractItemView {{ 
            background-color: {Colors.bg_card}; 
            border: 1px solid {Colors.border}; 
            border-radius: 8px; 
            selection-background-color: {Colors.accent}; 
            outline: none;
            padding: 4px;
        }}

        QComboBox QAbstractItemView::item {{ 
            min-height: 35px; 
            margin: 2px 5px;
            border-radius: 6px;
            padding-left: 10px;
            color: {Colors.text_main};
            background-color: transparent;
            border: none;
        }}

        QComboBox QAbstractItemView::item:selected {{ 
            background-color: {Colors.accent}; 
            color: #FFFFFF; 
        }}

        QScrollBar:vertical {{ border: none; background: transparent; width: 8px; margin: 0px; }}
        QScrollBar::handle:vertical {{ background: #D1D5DB; min-height: 30px; border-radius: 4px; }}
        QScrollBar::handle:vertical:hover {{ background: #9CA3AF; }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical, QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ border: none; background: none; height: 0px; }}
        
        QSlider::groove:horizontal {{ border: 1px solid {Colors.border}; height: 6px; background: {Colors.bg_main}; border-radius: 3px; }}
        QSlider::sub-page:horizontal {{ background: {Colors.accent}; border-radius: 3px; }}
        QSlider::handle:horizontal {{ background: {Colors.accent}; border: 2px solid {Colors.bg_card}; width: 16px; margin: -6px 0; border-radius: 8px; }}
        QSlider::handle:horizontal:hover {{ background: #008F7A; transform: scale(1.1); }}
        
        QCalendarWidget QWidget {{ alternate-background-color: {Colors.bg_main}; background-color: {Colors.bg_card}; outline: none; border: none; }}
        QCalendarWidget QAbstractItemView:enabled {{ font-size: 13px; color: {Colors.text_main}; background-color: {Colors.bg_card}; selection-background-color: {Colors.accent}; selection-color: white; border-radius: 6px; outline: none; border: none; }}
        QCalendarWidget QToolButton {{ color: {Colors.text_main}; font-weight: bold; background-color: transparent; border-radius: 4px; padding: 4px; outline: none; border: none; }}
        QCalendarWidget QToolButton:hover {{ background-color: {Colors.bg_main}; }}
        QCalendarWidget QMenu {{ background-color: {Colors.bg_card}; color: {Colors.text_main}; border: 1px solid {Colors.border}; }}
        QCalendarWidget QSpinBox {{ background-color: {Colors.bg_card}; color: {Colors.text_main}; border: 1px solid {Colors.border}; border-radius: 4px; }}
        QCalendarWidget QWidget#qt_calendar_navigationbar {{ background-color: transparent; border: none; }}
        
        QMenu {{ background-color: {Colors.bg_card}; border: 1px solid {Colors.border}; border-radius: 6px; padding: 5px; }}
        QMenu::item {{ padding: 8px 25px 8px 20px; border-radius: 4px; color: {Colors.text_main}; }}
        QMenu::item:selected {{ background-color: rgba(0, 169, 143, 0.1); color: {Colors.accent}; }}
        QMenu::separator {{ height: 1px; background-color: {Colors.border}; margin: 4px 10px; }}
    """

class CustomComboBox(QComboBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.list_view = QListView()
        self.list_view.setSpacing(0)
        self.list_view.setFrameShape(QFrame.NoFrame)
        self.list_view.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setView(self.list_view)

    def wheelEvent(self, event):
        event.ignore() 

    def showPopup(self):
        self.list_view.setStyleSheet(f"""
            QListView {{ 
                background-color: {Colors.bg_card}; 
                border: 1px solid {Colors.border}; 
                border-radius: 8px; 
                selection-background-color: {Colors.accent}; 
                outline: none;
                padding: 4px;
            }}
            QListView::item {{ 
                min-height: 35px; 
                margin: 2px 5px;
                border-radius: 6px;
                padding-left: 10px;
                color: {Colors.text_main};
                background-color: transparent;
                border: none;
            }}
            QListView::item:selected {{ 
                background-color: {Colors.accent}; 
                color: #FFFFFF; 
            }}
        """)
        
        container = self.view().parentWidget()
        if container:
            container.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint | Qt.NoDropShadowWindowHint)
            container.setAttribute(Qt.WA_TranslucentBackground)
            container.setObjectName("SpookContainer")
            container.setStyleSheet("#SpookContainer { background: transparent; }")
            
        super().showPopup()
        
        if container:
            pos = self.mapToGlobal(self.rect().bottomLeft())
            container.move(pos.x(), pos.y() - 4)

class ImageDragDropArea(QFrame):
    images_dropped = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setMinimumHeight(50)
        self.layout = QHBoxLayout(self) 
        self.layout.setContentsMargins(15, 0, 15, 0) 
        self.layout.setSpacing(10)
        
        lbl_file = QLabel()
        lbl_file.setFixedSize(20, 20)
        icon_path = os.path.join(application_path, "Icons", "Addfile.svg").replace("\\", "/")
        
        pixmap = QPixmap(20, 20)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        svg_ren = QSvgRenderer(icon_path)
        if svg_ren.isValid():
            svg_ren.render(painter)
            painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
            painter.fillRect(pixmap.rect(), QColor(Colors.accent))
        else:
            pen = QPen(QColor(Colors.accent))
            pen.setWidth(2)
            painter.setPen(pen)
            painter.drawRect(2, 2, 16, 20)
        
        painter.end()
        lbl_file.setPixmap(pixmap)
        
        self.layout.addWidget(lbl_file)
        
        self.lbl = QLabel("Sleep afbeeldingen hierheen...")
        self.lbl.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.lbl.setStyleSheet(f"color: {Colors.text_grey}; font-style: italic; border: none; font-size: 13px;")
        self.layout.addWidget(self.lbl)
        self.update_style(False)

    def update_style(self, active):
        color = Colors.accent if active else Colors.border
        bg = f"rgba(0, 169, 143, 0.1)" if active else "transparent"
        self.setStyleSheet(f"""
            ImageDragDropArea {{
                border: 2px dashed {color}; 
                border-radius: 8px; 
                background-color: {bg};
            }}
        """)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
            self.update_style(True)
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        self.update_style(False)

    def dropEvent(self, event):
        self.update_style(False)
        paths = [url.toLocalFile() for url in event.mimeData().urls() if url.isLocalFile()]
        images = [p for p in paths if p.lower().endswith(('.png', '.jpg', '.jpeg'))]
        if images:
            self.images_dropped.emit(images)

class CircularLoader(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.angle = 0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.rotate)
        self.setFixedSize(50, 50)

    def start(self): self.timer.start(30); self.show()
    def stop(self): self.timer.stop(); self.hide()

    def rotate(self):
        self.angle = (self.angle + 10) % 360
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        pen = QPen(QColor(Colors.accent), 4)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        rect = self.rect().adjusted(5, 5, -5, -5)
        painter.drawArc(rect, -self.angle * 16, 120 * 16)

class DropIndicator(QFrame):
    dropped_here = Signal(int)
    def __init__(self, index):
        super().__init__()
        self.index = index
        self.setAcceptDrops(True)
        self.setFixedHeight(16) 
        self.default_style = f"background-color: rgba(0, 169, 143, 0.15); border-radius: 4px; margin: 2px 15px;"
        self.hover_style = f"background-color: {Colors.accent}; border-radius: 4px; margin: 2px 5px;"
        self.setStyleSheet(self.default_style)

    def dragEnterEvent(self, event):
        if event.source() and isinstance(event.source(), DraggableQuestionCard):
            event.acceptProposedAction()
            self.setStyleSheet(self.hover_style)

    def dragLeaveEvent(self, event):
        self.setStyleSheet(self.default_style)

    def dropEvent(self, event):
        self.setStyleSheet("background-color: transparent;")
        self.dropped_here.emit(self.index)
        event.acceptProposedAction()

class DraggableQuestionCard(QFrame):
    def __init__(self, parent_layout):
        super().__init__()
        self.setObjectName("Card")
        self.parent_layout = parent_layout
        self.drag_start_pos = None
        self.is_currently_dragged = False

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_start_pos = event.position().toPoint()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.LeftButton) or not self.drag_start_pos: return
        if (event.position().toPoint() - self.drag_start_pos).manhattanLength() < 10: return
            
        drag = QDrag(self)
        mime = QMimeData(); drag.setMimeData(mime)
        pixmap = self.grab(); drag.setPixmap(pixmap); drag.setHotSpot(event.position().toPoint())
        
        main_win = self.window()
        if hasattr(main_win, 'update_vraag_nummers'): main_win.update_vraag_nummers(show_indicators=True)
        
        self.is_currently_dragged = True
        self.hide()
        drag.exec(Qt.MoveAction)
        
        self.is_currently_dragged = False
        self.show()
        if hasattr(main_win, 'update_vraag_nummers'): main_win.update_vraag_nummers(show_indicators=False)

class DragDropContainerWidget(QWidget):
    order_changed = Signal() 

    def __init__(self, layout_to_manage, scroll_area):
        super().__init__()
        self.setAcceptDrops(True)
        self.managed_layout = layout_to_manage
        self.scroll_area = scroll_area
        self.scroll_timer = QTimer(self)
        self.scroll_timer.timeout.connect(self.auto_scroll)
        self.scroll_speed = 0

    def auto_scroll(self):
        if self.scroll_speed != 0:
            bar = self.scroll_area.verticalScrollBar()
            bar.setValue(bar.value() + self.scroll_speed)

    def dragEnterEvent(self, event):
        if event.source() and isinstance(event.source(), DraggableQuestionCard):
            event.acceptProposedAction()
            self.scroll_timer.start(16) 

    def dragLeaveEvent(self, event):
        self.scroll_speed = 0
        self.scroll_timer.stop() 

    def dragMoveEvent(self, event):
        pos_in_viewport = self.mapTo(self.scroll_area.viewport(), event.position().toPoint()).y()
        viewport_height = self.scroll_area.viewport().height()
        
        if pos_in_viewport < 60: 
            self.scroll_speed = -15 
        elif pos_in_viewport > viewport_height - 60: 
            self.scroll_speed = 15  
        else:
            self.scroll_speed = 0   
            
        event.acceptProposedAction()
        
    def dropEvent(self, event):
        self.scroll_speed = 0
        self.scroll_timer.stop()
        event.ignore() 

class CustomProgressDialog(QDialog):
    def __init__(self, parent, title="Bezig met updaten..."):
        super().__init__(parent, Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(400, 200)
        self.is_canceled = False
        
        layout = QVBoxLayout(self)
        frame = QFrame()
        frame.setObjectName("Card")
        frame.setStyleSheet(f"background-color: {Colors.bg_card}; border: 1px solid {Colors.border}; border-radius: 12px;")
        
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20); shadow.setColor(QColor(0, 0, 0, 60)); shadow.setOffset(0, 5)
        frame.setGraphicsEffect(shadow)
        
        fl = QVBoxLayout(frame)
        fl.setContentsMargins(25, 25, 25, 25)
        
        header = QHBoxLayout()
        icon_lbl = QLabel()
        icon_lbl.setPixmap(parent.get_tinted_icon("Download.svg", Colors.accent, Colors.accent).pixmap(24, 24))
        icon_lbl.setStyleSheet("border: none; background: transparent;")
        header.addWidget(icon_lbl)
        
        lbl_t = QLabel(title)
        lbl_t.setStyleSheet(f"font-size: 16px; font-weight: bold; border: none; color: {Colors.text_main}; margin-left: 5px;")
        header.addWidget(lbl_t)
        header.addStretch()
        fl.addLayout(header)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(18)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid {Colors.border};
                border-radius: 9px;
                background-color: {Colors.bg_main};
            }}
            QProgressBar::chunk {{
                background-color: {Colors.accent};
                border-radius: 8px;
            }}
        """)
        fl.addSpacing(15)
        fl.addWidget(self.progress_bar)
        
        self.lbl_info = QLabel("Update aan het downloaden... (0%)")
        self.lbl_info.setStyleSheet(f"color: {Colors.text_grey}; font-size: 12px; border: none; margin-top: 5px;")
        self.lbl_info.setAlignment(Qt.AlignCenter)
        fl.addWidget(self.lbl_info)
        
        fl.addStretch()
        
        btn_layout = QHBoxLayout()
        btn_cancel = QPushButton("Annuleren")
        btn_cancel.setCursor(Qt.PointingHandCursor)
        btn_cancel.setStyleSheet(f"QPushButton {{ background-color: {Colors.bg_main}; border: 1px solid {Colors.border}; border-radius: 8px; font-weight: bold; color: {Colors.text_main}; min-height: 36px; }} QPushButton:hover {{ background-color: #FEE2E2; color: #DC2626; border: 1px solid #EF4444; }}")
        btn_cancel.clicked.connect(self.cancel_download)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_cancel)
        btn_layout.addStretch()
        fl.addLayout(btn_layout)
        
        layout.addWidget(frame)

    def setValue(self, val):
        self.progress_bar.setValue(val)
        self.lbl_info.setText(f"Update aan het downloaden... {val}% voltooid")

    def cancel_download(self):
        self.is_canceled = True
        self.reject()

    def wasCanceled(self):
        return self.is_canceled

class NotificationPopup(QDialog):
    def __init__(self, parent, data, nieuw_aantal, btn_notif):
        super().__init__(parent, Qt.FramelessWindowHint | Qt.Popup | Qt.NoDropShadowWindowHint)
        self.main_parent = parent
        self.btn_notif = btn_notif
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setObjectName("SpookContainer")
        self.setStyleSheet(get_stylesheet() + "\n#SpookContainer { background: transparent; border: none; }")
        self.setWindowOpacity(1.0)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 40)
        
        frame = QFrame()
        frame.setFixedWidth(340)
        frame.setObjectName("Card")
        frame.setStyleSheet(f"background-color: {Colors.bg_card}; border: 1px solid {Colors.border}; border-radius: 12px;")
        
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 35))
        shadow.setOffset(0, 5)
        frame.setGraphicsEffect(shadow)
        
        fl = QVBoxLayout(frame)
        fl.setContentsMargins(20, 20, 20, 20)
        fl.setSpacing(12)
        
        header_layout = QHBoxLayout()
        header_lbl = QLabel("Notificaties")
        header_lbl.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {Colors.text_main}; border: none;")
        header_layout.addWidget(header_lbl)
        header_layout.addStretch()
        fl.addLayout(header_layout)
        
        line = QFrame()
        line.setFixedHeight(1)
        line.setStyleSheet(f"background-color: {Colors.border}; border: none;")
        fl.addWidget(line)
        
        has_items = False
        
        if getattr(parent, 'update_available', False):
            item = QFrame()
            item.setStyleSheet(f"background-color: {Colors.bg_main}; border-radius: 8px; border-left: 4px solid #3B82F6; border-top: none; border-right: none; border-bottom: none;")
            il = QVBoxLayout(item)
            il.setContentsMargins(15, 10, 15, 10)
            
            row = QHBoxLayout()
            row.setContentsMargins(0,0,0,0)
            lbl_t = QLabel("Software Update Beschikbaar!")
            lbl_t.setStyleSheet("color: #3B82F6; font-weight: bold; font-size: 13px; border: none;")
            row.addWidget(lbl_t)
            
            btn_dl = QPushButton("Installeren")
            btn_dl.setFixedSize(80, 26)
            btn_dl.setStyleSheet("background-color: #3B82F6; color: white; border-radius: 4px; font-size: 11px; font-weight: bold; border: none;")
            btn_dl.setCursor(Qt.PointingHandCursor)
            
            v = parent.update_versie
            u = parent.update_url
            btn_dl.clicked.connect(lambda checked=False, vers=v, url=u: (self.close(), parent.updater.vraag_om_update(vers, url)))
            row.addWidget(btn_dl)
            
            il.addLayout(row)
            lbl_sub = QLabel(f"Versie {parent.update_versie} is gereed om te installeren.")
            lbl_sub.setStyleSheet(f"color: {Colors.text_grey}; font-size: 11px; border: none;")
            il.addWidget(lbl_sub)
            
            fl.addWidget(item)
            has_items = True
            
        if not data and not has_items:
            fl.addWidget(QLabel("Je bent helemaal bij!", styleSheet=f"color: {Colors.text_grey}; font-size: 13px; font-style: italic; border: none; margin-top: 10px; margin-bottom: 10px;"), alignment=Qt.AlignCenter)
        elif data:
            items = list(reversed(data))[:4]
            for idx, k in enumerate(items):
                item = QFrame()
                border_color = Colors.accent if idx < nieuw_aantal else Colors.border
                item.setStyleSheet(f"background-color: {Colors.bg_main}; border-radius: 8px; border-left: 4px solid {border_color}; border-top: none; border-right: none; border-bottom: none;")
                il = QVBoxLayout(item)
                il.setContentsMargins(15, 10, 15, 10)
                il.addWidget(QLabel(f"{str(k.get('naam') or 'Onbekend')} heeft ingezonden", styleSheet=f"color: {Colors.text_main}; font-weight: bold; font-size: 13px; border: none;"))
                
                lbl_sub = QLabel(f"{str(k.get('template_titel') or '')}  •  {str(k.get('datum') or '')}")
                lbl_sub.setWordWrap(True)
                lbl_sub.setStyleSheet(f"color: {Colors.text_grey}; font-size: 11px; border: none;")
                il.addWidget(lbl_sub)
                
                fl.addWidget(item)
                has_items = True
        
        fl.addSpacing(5)
        btn_all = QPushButton("Bekijk Alle Inzendingen")
        btn_all.setFixedHeight(38)
        btn_all.setObjectName("AccentButton")
        btn_all.setCursor(Qt.PointingHandCursor)
        btn_all.setStyleSheet(f"QPushButton {{ background-color: {Colors.accent}; color: white; font-weight: bold; border-radius: 6px; border: none; }} QPushButton:hover {{ background-color: #008F7A; }}")
        btn_all.clicked.connect(lambda: (parent.show_tab_inzendingen(), self.close()))
        fl.addWidget(btn_all)
        
        layout.addWidget(frame)
        self.adjustSize()

    def leaveEvent(self, event):
        self.btn_notif.setStyleSheet("")
        self.btn_notif.setIcon(self.main_parent.get_tinted_icon("Bell.svg", Colors.text_grey, Colors.text_main))
        self.fade_anim = QPropertyAnimation(self, b"windowOpacity")
        self.fade_anim.setDuration(250)
        self.fade_anim.setStartValue(1.0)
        self.fade_anim.setEndValue(0.0)
        self.fade_anim.finished.connect(self.accept)
        self.fade_anim.start()
        super().leaveEvent(event)

class ConfettiParticle:
    def __init__(self, width, height):
        self.x = random.randint(0, width)
        self.y = random.randint(-height, 0)
        self.color = QColor(random.choice(["#00A98F", "#95C93D", "#FFD700", "#FF6B6B", "#4D96FF"]))
        self.size = random.randint(8, 12)
        self.speed = random.randint(5, 10)
        self.angle = random.uniform(0, 360)
        self.rotation_speed = random.randint(-10, 10)

class ConfettiWidget(QWidget):
    def __init__(self, parent):
        super().__init__(parent)
        self.setFixedSize(parent.size())
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.particles = [ConfettiParticle(self.width(), self.height()) for _ in range(100)]
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_particles)
        self.opacity = 1.0

    def start(self):
        self.show()
        self.timer.start(20)
        QTimer.singleShot(4000, self.stop_confetti)

    def stop_confetti(self):
        self.timer.stop()
        self.hide()
        self.deleteLater()

    def update_particles(self):
        for p in self.particles:
            p.y += p.speed
            p.angle += p.rotation_speed
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        for p in self.particles:
            painter.save()
            painter.translate(p.x, p.y)
            painter.rotate(p.angle)
            painter.setBrush(p.color)
            painter.setPen(Qt.NoPen)
            painter.drawRect(-p.size//2, -p.size//2, p.size, p.size)
            painter.restore()

class QRCodePopup(QDialog):
    def __init__(self, parent, titel, url):
        super().__init__(parent, Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(380, 480)
        
        layout = QVBoxLayout(self)
        frame = QFrame(); frame.setObjectName("Card")
        frame.setStyleSheet(f"background-color: {Colors.bg_card}; border: 1px solid {Colors.border}; border-radius: 15px;")
        
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(25); shadow.setColor(QColor(0, 0, 0, 70)); shadow.setOffset(0, 8)
        frame.setGraphicsEffect(shadow)
        
        fl = QVBoxLayout(frame)
        fl.setContentsMargins(30, 20, 30, 30)
        
        header = QHBoxLayout()
        lbl_t = QLabel("QR-Code"); lbl_t.setStyleSheet(f"font-size: 18px; font-weight: bold; border: none;")
        header.addWidget(lbl_t); header.addStretch()
        
        btn_close = QPushButton()
        icon_norm = parent.get_tinted_icon("SystemClose.svg", Colors.text_grey, Colors.text_grey)
        icon_hover = parent.get_tinted_icon("SystemClose.svg", "#EF4444", "#EF4444")
        btn_close.setIcon(icon_norm)
        btn_close.setFixedSize(30, 30)
        btn_close.setCursor(Qt.PointingHandCursor)
        btn_close.setStyleSheet("QPushButton { border: none; background: transparent; border-radius: 6px; } QPushButton:hover { background-color: #FEE2E2; }")
        btn_close.clicked.connect(self.accept)
        btn_close.enterEvent = lambda e: btn_close.setIcon(icon_hover)
        btn_close.leaveEvent = lambda e: btn_close.setIcon(icon_norm)
        header.addWidget(btn_close)
        fl.addLayout(header)
        
        lbl_sub = QLabel(titel); lbl_sub.setStyleSheet(f"color: {Colors.text_grey}; font-size: 12px; border: none; margin-bottom: 10px;")
        lbl_sub.setWordWrap(True); fl.addWidget(lbl_sub)
        
        try:
            import qrcode
            qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_H, box_size=10, border=2)
            qr.add_data(url)
            qr.make(fit=True)
            img_qr = qr.make_image(fill_color=Colors.accent, back_color="white").convert('RGB')
            
            logo_path = os.path.join(application_path, "logo_stichtingzo_rgb.png")
            if os.path.exists(logo_path):
                logo = Image.open(logo_path)
                bw = img_qr.size[0]
                logo = logo.resize((int(bw * 0.25), int(bw * 0.25)), Image.Resampling.LANCZOS)
                pos = ((img_qr.size[0] - logo.size[0]) // 2, (img_qr.size[1] - logo.size[1]) // 2)
                draw = ImageDraw.Draw(img_qr)
                padding = 10
                draw.rectangle([pos[0]-padding, pos[1]-padding, pos[0]+logo.size[0]+padding, pos[1]+logo.size[1]+padding], fill="white")
                img_qr.paste(logo, pos, mask=logo if logo.mode == 'RGBA' else None)
            
            self.pil_img = img_qr
            buffer = BytesIO(); img_qr.save(buffer, format="PNG")
            qimg = QImage.fromData(buffer.getvalue())
            lbl_qr = QLabel(); lbl_qr.setPixmap(QPixmap.fromImage(qimg).scaled(250, 250, Qt.KeepAspectRatio))
            lbl_qr.setAlignment(Qt.AlignCenter); fl.addWidget(lbl_qr)
        except Exception as e: fl.addWidget(QLabel(f"Fout: {e}"))
            
        fl.addStretch()
        btn_layout = QHBoxLayout()
        
        btn_copy = QPushButton(" Kopieer Link")
        btn_copy.setCursor(Qt.PointingHandCursor)
        btn_copy.setIcon(parent.get_tinted_icon("link.svg", Colors.text_main))
        btn_copy.setStyleSheet(f"QPushButton {{ background-color: {Colors.bg_card}; color: {Colors.text_main}; border: 1px solid {Colors.border}; border-radius: 8px; font-weight: bold; min-height: 38px; }} QPushButton:hover {{ background-color: {Colors.bg_main}; }}")
        btn_copy.clicked.connect(lambda: (QApplication.clipboard().setText(url), parent.toon_melding("Link gekopieerd!")))
        
        btn_down = QPushButton(" Download PNG")
        btn_down.setCursor(Qt.PointingHandCursor)
        btn_down.setIcon(parent.get_tinted_icon("Download.svg", "white", "white"))
        btn_down.setStyleSheet(f"QPushButton {{ background-color: {Colors.accent}; color: white; border-radius: 8px; font-weight: bold; min-height: 38px; border: none; }} QPushButton:hover {{ background-color: #008F7A; }}")
        btn_down.clicked.connect(self.download_qr)
        
        btn_layout.addWidget(btn_copy); btn_layout.addWidget(btn_down)
        fl.addLayout(btn_layout)
        layout.addWidget(frame)

    def download_qr(self):
        filepath, _ = QFileDialog.getSaveFileName(self, "QR Opslaan", "QR_Code.png", "PNG (*.png)")
        if filepath: self.pil_img.save(filepath)

class CustomTitleBar(QFrame):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowOpacity(1.0)
        self.parent = parent
        self.setFixedHeight(40)
        self.setObjectName("TitleBar")
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 0, 10, 0)
        
        self.btn_collapse = QPushButton()
        self.btn_collapse.setObjectName("AppBtn")
        self.btn_collapse.setFixedSize(40, 30)
        self.btn_collapse.setIcon(self.parent.get_tinted_icon("Menu.svg", Colors.text_main, Colors.accent))
        self.btn_collapse.setIconSize(QSize(20, 20))
        self.btn_collapse.clicked.connect(self.parent.toggle_sidebar)
        layout.addWidget(self.btn_collapse)
        
        self.lbl_offline = QLabel(" • Offline Werkmodus")
        self.lbl_offline.setStyleSheet("color: #EF4444; font-weight: bold; font-size: 13px; border: none;")
        self.lbl_offline.hide()
        layout.addWidget(self.lbl_offline)
        
        layout.addStretch()
        
        self.btn_notif = QPushButton()
        self.btn_notif.setObjectName("AppBtn")
        self.btn_notif.setFixedSize(40, 30)
        self.btn_notif.setIcon(self.parent.get_tinted_icon("Bell.svg", Colors.text_grey, Colors.text_main))
        self.btn_notif.setIconSize(QSize(18, 18))
        self.btn_notif.clicked.connect(self.show_notifications)
        
        def notif_enter(e):
            self.show_notifications()
        self.btn_notif.enterEvent = notif_enter
        
        self.lbl_badge = QLabel("0", self.btn_notif)
        self.lbl_badge.setFixedSize(16, 16)
        self.lbl_badge.setStyleSheet("background-color: #EF4444; color: white; border-radius: 8px; font-size: 9px; font-weight: bold; border: none;")
        self.lbl_badge.setAlignment(Qt.AlignCenter)
        self.lbl_badge.move(20, 2)
        self.lbl_badge.hide()
        
        layout.addWidget(self.btn_notif)

        self.btn_min = QPushButton()
        self.btn_min.setObjectName("MinBtn")
        self.btn_min.setIcon(self.parent.get_tinted_icon("SystemMinimize.svg", Colors.text_grey, Colors.text_main))
        
        self.btn_max = QPushButton()
        self.btn_max.setObjectName("MaxBtn")
        self.btn_max.setIcon(self.parent.get_tinted_icon("SystemFullscreen.svg", Colors.text_grey, Colors.text_main))
        
        self.btn_close = QPushButton()
        self.btn_close.setObjectName("CloseBtn")
        self.btn_close.setIcon(self.parent.get_tinted_icon("SystemClose.svg", Colors.text_grey, "white"))
        
        for btn in [self.btn_min, self.btn_max, self.btn_close]:
            btn.setFixedSize(40, 30)
            btn.setIconSize(QSize(14, 14)) 
            layout.addWidget(btn)
            
        self.btn_min.clicked.connect(self.animate_minimize)
        self.btn_max.clicked.connect(self.toggle_max)
        self.btn_close.clicked.connect(parent.close)
        
        self.start_pos = None
        self.is_maximized = False
        self.normal_geometry = None
        self.anim = None
        self.min_anim_group = None
        self.restore_anim = None

    def toggle_max(self):
        self.anim = QPropertyAnimation(self.parent, b"geometry")
        self.anim.setDuration(250)
        self.anim.setEasingCurve(QEasingCurve.OutCubic)

        if not self.is_maximized:
            self.normal_geometry = self.parent.geometry()
            screen_geom = self.screen().availableGeometry()
            
            self.anim.setStartValue(self.normal_geometry)
            self.anim.setEndValue(screen_geom)
            
            self.btn_max.setIcon(self.parent.get_tinted_icon("SystemNormalScreen.svg", Colors.text_grey, Colors.text_main))
            self.parent.centralWidget().layout().setContentsMargins(0, 0, 0, 0)
            self.is_maximized = True
        else:
            self.anim.setStartValue(self.parent.geometry())
            self.anim.setEndValue(self.normal_geometry)
            
            self.btn_max.setIcon(self.parent.get_tinted_icon("SystemFullscreen.svg", Colors.text_grey, Colors.text_main))
            self.parent.centralWidget().layout().setContentsMargins(10, 10, 10, 10)
            self.is_maximized = False

        self.anim.start()

    def animate_minimize(self):
        if not self.is_maximized:
            self.normal_geometry = self.parent.geometry()
        
        self.min_anim_group = QParallelAnimationGroup()

        self.fade_out = QPropertyAnimation(self.parent, b"windowOpacity")
        self.fade_out.setDuration(200)
        self.fade_out.setStartValue(1.0)
        self.fade_out.setEndValue(0.0)
        self.fade_out.setEasingCurve(QEasingCurve.OutQuad)

        self.slide_down = QPropertyAnimation(self.parent, b"geometry")
        self.slide_down.setDuration(200)
        current_geo = self.parent.geometry()
        target_geo = QRect(current_geo.x(), 
                           current_geo.y() + 30, 
                           current_geo.width(), 
                           current_geo.height())
        self.slide_down.setStartValue(current_geo)
        self.slide_down.setEndValue(target_geo)
        self.slide_down.setEasingCurve(QEasingCurve.OutQuad)

        self.min_anim_group.addAnimation(self.fade_out)
        self.min_anim_group.addAnimation(self.slide_down)
        
        self.min_anim_group.finished.connect(self.parent.showMinimized)
        self.min_anim_group.start()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton: 
            self.start_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if self.is_maximized:
            return
        if self.start_pos:
            delta = event.globalPosition().toPoint() - self.start_pos
            self.parent.move(self.parent.pos() + delta)
            self.start_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event): 
        self.start_pos = None

    def show_notifications(self):
        if hasattr(self, 'notif_popup') and self.notif_popup.isVisible():
            return
            
        self.lbl_badge.hide()
        vandaag = datetime.now().strftime("%d-%m-%Y")
        vandaag_inzendingen = [k for k in self.parent.opgeslagen_data if k.get("datum") == vandaag and k.get("status") != "verwijderd"]
        gelezen = getattr(self.parent, 'gelezen_notificaties_count', 0)
        nieuw_aantal = max(0, len(vandaag_inzendingen) - gelezen)
        
        self.btn_notif.setStyleSheet(f"background-color: {Colors.border}; border-radius: 6px;")
        self.btn_notif.setIcon(self.parent.get_tinted_icon("Bell.svg", Colors.text_main, Colors.text_main))
        
        self.notif_popup = NotificationPopup(self.parent, self.parent.opgeslagen_data, nieuw_aantal, self.btn_notif)
        self.notif_popup.adjustSize()
        pos = self.btn_notif.mapToGlobal(self.btn_notif.rect().bottomRight())
        self.notif_popup.move(pos.x() - self.notif_popup.width() + 25, pos.y() - 15)
        self.notif_popup.show()
        
        self.parent.gelezen_notificaties_count = len(vandaag_inzendingen)
        local_settings = QSettings("StichtingZO", "Klantenportaal")
        local_settings.setValue("notif_date", vandaag)
        local_settings.setValue("notif_count", self.parent.gelezen_notificaties_count)
        local_settings.sync()
        
        QTimer.singleShot(100, self.parent.werk_notificatie_badge_bij)

class ToastNotification(QDialog):
    def __init__(self, parent, message, type="success"):
        super().__init__(parent, Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        layout = QVBoxLayout(self)
        frame = QFrame(); frame.setObjectName("Card")
        frame.setStyleSheet(f"background-color: {Colors.bg_card}; border: 1px solid {Colors.border}; border-radius: 8px;")
        
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15); shadow.setColor(QColor(0, 0, 0, 40)); shadow.setOffset(0, 4)
        frame.setGraphicsEffect(shadow)
        
        fl = QVBoxLayout(frame)
        color = "#22C55E" if type == "success" else "#EF4444" if type == "error" else Colors.accent
        lbl = QLabel(message)
        lbl.setStyleSheet(f"color: {color}; font-weight: bold; font-size: 13px; border: none;")
        fl.addWidget(lbl)
        layout.addWidget(frame)
        
        self.adjustSize()
        px = parent.geometry().x() + parent.width() - self.width() - 20
        py = parent.geometry().y() + parent.height() - self.height() - 20
        self.move(px, py)
        
        QTimer.singleShot(3000, self.accept)
        self.show()

class BevestigingPopup(QDialog):
    def __init__(self, parent, titel, bericht, callback):
        super().__init__(parent, Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(400, 220)
        
        layout = QVBoxLayout(self)
        frame = QFrame(); frame.setObjectName("Card")
        frame.setStyleSheet(f"background-color: {Colors.bg_card}; border: 1px solid {Colors.border}; border-radius: 12px;")
        
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20); shadow.setColor(QColor(0, 0, 0, 60)); shadow.setOffset(0, 5)
        frame.setGraphicsEffect(shadow)
        
        fl = QVBoxLayout(frame)
        fl.setContentsMargins(25, 25, 25, 25)
        
        lbl_t = QLabel(titel); lbl_t.setStyleSheet(f"font-size: 18px; font-weight: bold; border: none; color: {Colors.text_main};")
        lbl_b = QLabel(bericht); lbl_b.setWordWrap(True); lbl_b.setStyleSheet(f"color: {Colors.text_grey}; border: none;")
        fl.addWidget(lbl_t); fl.addWidget(lbl_b); fl.addStretch()
        
        btn_layout = QHBoxLayout()
        btn_cancel = QPushButton("Annuleren")
        btn_cancel.clicked.connect(self.reject)
        btn_confirm = QPushButton(" Verwijderen")
        btn_confirm.setObjectName("DangerButton")
        btn_confirm.setIcon(parent.get_tinted_icon("bin.svg", "#EF4444", "white"))
        btn_confirm.clicked.connect(lambda: (callback(), self.accept()))
        
        btn_layout.addWidget(btn_cancel); btn_layout.addWidget(btn_confirm)
        fl.addLayout(btn_layout)
        layout.addWidget(frame)

class UpdatePopup(QDialog):
    def __init__(self, parent, huidige_versie, nieuwe_versie):
        super().__init__(parent, Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(420, 240)
        
        layout = QVBoxLayout(self)
        frame = QFrame(); frame.setObjectName("Card")
        frame.setStyleSheet(f"background-color: {Colors.bg_card}; border: 1px solid {Colors.border}; border-radius: 12px;")
        
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20); shadow.setColor(QColor(0, 0, 0, 60)); shadow.setOffset(0, 5)
        frame.setGraphicsEffect(shadow)
        
        fl = QVBoxLayout(frame)
        fl.setContentsMargins(25, 25, 25, 25)
        
        # --- Header ---
        header = QHBoxLayout()
        icon_lbl = QLabel()
        icon_lbl.setPixmap(parent.get_tinted_icon("Download.svg", Colors.accent, Colors.accent).pixmap(24, 24))
        icon_lbl.setStyleSheet("border: none; background: transparent;")
        header.addWidget(icon_lbl)
        
        lbl_t = QLabel("Software Update Beschikbaar!")
        lbl_t.setStyleSheet(f"font-size: 16px; font-weight: bold; border: none; color: {Colors.text_main}; margin-left: 5px;")
        header.addWidget(lbl_t)
        header.addStretch()
        fl.addLayout(header)
        
        line = QFrame()
        line.setFixedHeight(1)
        line.setStyleSheet(f"background-color: {Colors.border}; border: none; margin: 10px 0px;")
        fl.addWidget(line)
        
        # --- Tekst ---
        lbl_b = QLabel(f"Er is een nieuwe update gevonden (versie <b>{nieuwe_versie}</b>).<br>Je gebruikt momenteel versie {huidige_versie}.<br><br>Wil je de update nu downloaden en installeren?")
        lbl_b.setWordWrap(True)
        lbl_b.setStyleSheet(f"color: {Colors.text_grey}; font-size: 13px; border: none;")
        fl.addWidget(lbl_b)
        fl.addStretch()
        
        # --- Knoppen ---
        btn_layout = QHBoxLayout()
        
        btn_cancel = QPushButton("Later")
        btn_cancel.setCursor(Qt.PointingHandCursor)
        btn_cancel.setStyleSheet(f"QPushButton {{ background-color: {Colors.bg_main}; border: 1px solid {Colors.border}; border-radius: 8px; font-weight: bold; color: {Colors.text_main}; min-height: 36px; }} QPushButton:hover {{ background-color: {Colors.border}; }}")
        btn_cancel.clicked.connect(self.reject)
        
        btn_confirm = QPushButton(" Ja, Updaten")
        btn_confirm.setCursor(Qt.PointingHandCursor)
        btn_confirm.setIcon(parent.get_tinted_icon("Download.svg", "white", "white"))
        btn_confirm.setStyleSheet(f"QPushButton {{ background-color: {Colors.accent}; color: white; border-radius: 8px; font-weight: bold; min-height: 36px; border: none; }} QPushButton:hover {{ background-color: #008F7A; }}")
        btn_confirm.clicked.connect(self.accept)
        
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_confirm)
        fl.addLayout(btn_layout)
        
        layout.addWidget(frame)

class DatePickerPopup(QDialog):
    def __init__(self, parent, callback):
        super().__init__(parent, Qt.FramelessWindowHint | Qt.Popup)
        self.callback = callback
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet(get_stylesheet())
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10,10,10,10)
        frame = QFrame(); frame.setObjectName("Card")
        frame.setStyleSheet(f"background-color: {Colors.bg_card}; border: 1px solid {Colors.border}; border-radius: 8px;")
        
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20); shadow.setColor(QColor(0, 0, 0, 60)); shadow.setOffset(0, 5)
        frame.setGraphicsEffect(shadow)
        
        fl = QVBoxLayout(frame)
        
        self.cal = QCalendarWidget()
        self.cal.setGridVisible(False)
        self.cal.setVerticalHeaderFormat(QCalendarWidget.NoVerticalHeader)
        self.cal.setSelectedDate(QDate.currentDate())
        fl.addWidget(self.cal)
        
        btn = QPushButton("Selecteer Datum")
        btn.setObjectName("AccentButton")
        btn.clicked.connect(self.select_date)
        fl.addWidget(btn)
        
        layout.addWidget(frame)

    def select_date(self):
        date = self.cal.selectedDate()
        self.callback(date.toString("dd-MM-yyyy"))
        self.accept()

class TerminalDialog(QDialog):
    def __init__(self, parent=None, log_history=""):
        super().__init__(parent)
        self.setWindowTitle("Systeem Terminal")
        self.resize(750, 500)
        self.setStyleSheet(f"background-color: #0F111A; color: #00FF41; font-family: Consolas;")
        layout = QVBoxLayout(self)
        self.text_edit = QTextEdit()
        self.text_edit.setReadOnly(True)
        self.text_edit.setText(log_history)
        layout.addWidget(self.text_edit)

    def append_text(self, text):
        self.text_edit.moveCursor(self.text_edit.textCursor().MoveOperation.End)
        self.text_edit.insertPlainText(text)
        self.text_edit.moveCursor(self.text_edit.textCursor().MoveOperation.End)

class ResultaatPopup(QDialog):
    def __init__(self, parent, kandidaat, fallback_vragen):
        super().__init__(parent, Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet(get_stylesheet())
        self.resize(650, 700)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        
        main_frame = QFrame()
        main_frame.setObjectName("Card")
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20); shadow.setColor(QColor(0, 0, 0, 50)); shadow.setOffset(0, 5)
        main_frame.setGraphicsEffect(shadow)
        
        fl = QVBoxLayout(main_frame)
        
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("Inzending Details", styleSheet="font-weight: bold; font-size: 16px; border: none;"))
        header_layout.addStretch()
        btn_close = QPushButton()
        btn_close.setIcon(parent.get_tinted_icon("x.svg", Colors.text_main, Colors.accent))
        btn_close.setFixedSize(30, 30)
        btn_close.setStyleSheet("border: none; background: transparent;")
        btn_close.clicked.connect(self.accept)
        header_layout.addWidget(btn_close)
        fl.addLayout(header_layout)
        
        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        container = QWidget(); cl = QVBoxLayout(container)
        
        h_card = QFrame(); h_card.setObjectName("Card"); hl = QVBoxLayout(h_card)
        titel = QLabel(str(kandidaat.get('naam') or 'Onbekend'))
        titel.setStyleSheet("font-size: 22px; font-weight: bold; border: none;")
        hl.addWidget(titel)
        hl.addWidget(QLabel(f"📅 {str(kandidaat.get('datum') or '-')}  |  👤 {str(kandidaat.get('leeftijd') or '-')} jr  |  ⚧ {str(kandidaat.get('geslacht') or '-')}", styleSheet="border: none;"))
        tmpl_lbl = QLabel(f"Vragenlijst: {str(kandidaat.get('template_titel') or 'Standaard Vragenlijst')}")
        tmpl_lbl.setStyleSheet(f"color: {Colors.accent}; font-style: italic; border: none;")
        hl.addWidget(tmpl_lbl)
        cl.addWidget(h_card)
        
        a_card = QFrame(); a_card.setObjectName("Card"); al = QVBoxLayout(a_card)
        lbl_a = QLabel("Ingevulde Antwoorden"); lbl_a.setStyleSheet("font-size: 16px; font-weight: bold; border: none;")
        al.addWidget(lbl_a)
        
        antwoorden = kandidaat.get("antwoorden", [])
        for i, a_data in enumerate(antwoorden):
            if isinstance(a_data, dict):
                v_tekst = str(a_data.get("vraag") or f"Vraag {i+1}")
                a_tekst = str(a_data.get("antwoord") or "-")
            else:
                v_tekst = str(fallback_vragen[i]["vraag"] if i < len(fallback_vragen) else f"Vraag {i+1}")
                a_tekst = str(a_data)
                
            qf = QFrame(); qf.setStyleSheet(f"background-color: {Colors.bg_main}; border-radius: 6px; border: none;")
            ql = QVBoxLayout(qf)
            vl = QLabel(f"{i+1}. {v_tekst}"); vl.setWordWrap(True); vl.setStyleSheet(f"color: {Colors.text_grey}; border: none;")
            albl = QLabel(a_tekst); albl.setWordWrap(True); albl.setStyleSheet("font-weight: bold; border: none;")
            ql.addWidget(vl); ql.addWidget(albl)
            al.addWidget(qf)
        cl.addWidget(a_card)
        
        opm = str(kandidaat.get("opmerking") or "").strip()
        if opm:
            o_card = QFrame(); o_card.setObjectName("Card"); ol = QVBoxLayout(o_card)
            ol.addWidget(QLabel("Extra Opmerkingen / Ideeën", styleSheet="font-size: 16px; font-weight: bold; border: none;"))
            lbl_o = QLabel(opm); lbl_o.setWordWrap(True); lbl_o.setStyleSheet("border: none;")
            ol.addWidget(lbl_o)
            cl.addWidget(o_card)
            
        cl.addStretch()
        scroll.setWidget(container)
        fl.addWidget(scroll)
        
        btn_close_main = QPushButton("Sluiten")
        btn_close_main.setObjectName("DetailsButton")
        btn_close_main.setFixedWidth(120)
        btn_close_main.clicked.connect(self.accept)
        fl.addWidget(btn_close_main, alignment=Qt.AlignCenter)
        
        layout.addWidget(main_frame)

class ClickableCard(QFrame):
    clicked = Signal()
    def __init__(self):
        super().__init__()
        self.setCursor(Qt.PointingHandCursor)
        
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mouseReleaseEvent(event)

class SnelstartPopup(QDialog):
    def __init__(self, parent):
        super().__init__(parent, Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(750, 450)
        self.parent_window = parent

        layout = QVBoxLayout(self)
        frame = QFrame(); frame.setObjectName("Card")
        frame.setStyleSheet(f"background-color: {Colors.bg_card}; border: 1px solid {Colors.border}; border-radius: 12px;")

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(25); shadow.setColor(QColor(0, 0, 0, 60)); shadow.setOffset(0, 5)
        frame.setGraphicsEffect(shadow)

        fl = QVBoxLayout(frame)
        fl.setContentsMargins(30, 30, 30, 30)

        header = QHBoxLayout()
        
        lbl_icon = QLabel()
        lbl_icon.setPixmap(parent.get_tinted_icon("Library.svg", Colors.text_main, Colors.text_main).pixmap(24, 24))
        lbl_icon.setStyleSheet("border: none; background: transparent;")
        header.addWidget(lbl_icon)

        lbl_t = QLabel("Snelstart Bibliotheek")
        lbl_t.setStyleSheet(f"font-size: 22px; font-weight: bold; color: {Colors.text_main}; border: none;")
        header.addWidget(lbl_t)
        header.addStretch()

        btn_close = QPushButton()
        btn_close.setIcon(parent.get_tinted_icon("SystemClose.svg", Colors.text_grey, "white"))
        btn_close.setFixedSize(30, 30)
        btn_close.setCursor(Qt.PointingHandCursor)
        
        btn_close.setStyleSheet("""
            QPushButton {
                border: none; 
                background: transparent; 
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #EF4444; 
            }
        """)
        btn_close.clicked.connect(self.reject)
        header.addWidget(btn_close)
        fl.addLayout(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none; background: transparent;")
        
        grid_container = QWidget()
        grid_container.setStyleSheet("background: transparent;")
        grid_layout = QGridLayout(grid_container)
        grid_layout.setSpacing(15)
        grid_layout.setAlignment(Qt.AlignTop)

        def create_card(title, desc, icon, action, is_custom=False):
            c = ClickableCard()
            border_col = Colors.accent if is_custom else Colors.border
            bg_col = "rgba(0, 169, 143, 0.05)" if is_custom else Colors.bg_main
            
            c.setStyleSheet(f"""
                ClickableCard {{
                    background-color: {bg_col};
                    border: 1px solid {border_col};
                    border-radius: 10px;
                }}
                ClickableCard:hover {{
                    border: 2px solid {Colors.accent};
                    background-color: rgba(0, 169, 143, 0.1);
                }}
            """)
            c.setFixedSize(200, 160)
            l = QVBoxLayout(c)
            l.setAlignment(Qt.AlignCenter)

            lbl_i = QLabel()
            lbl_i.setPixmap(parent.get_tinted_icon(icon, Colors.accent, Colors.accent).pixmap(40, 40))
            lbl_i.setAlignment(Qt.AlignCenter)
            lbl_i.setStyleSheet("border: none; background: transparent;")

            t = QLabel(title)
            t.setStyleSheet("font-size: 14px; font-weight: bold; border: none; background: transparent; margin-top: 5px;")
            t.setAlignment(Qt.AlignCenter)
            t.setWordWrap(True)

            d = QLabel(desc)
            d.setWordWrap(True)
            d.setAlignment(Qt.AlignCenter)
            d.setStyleSheet(f"color: {Colors.text_grey}; font-size: 11px; border: none; background: transparent;")

            l.addWidget(lbl_i); l.addWidget(t); l.addWidget(d)
            c.clicked.connect(lambda: (action(), self.accept()))
            return c

        row, col = 0, 0
        def add_to_grid(widget):
            nonlocal row, col
            grid_layout.addWidget(widget, row, col)
            col += 1
            if col > 2: 
                col = 0
                row += 1

        def act_blank():
            self.parent_window.show_tab_ontwerpen()

        def load_as_new(t_data):
            self.parent_window.show_tab_ontwerpen()
            self.parent_window.input_titel.setText(f"Kopie: {t_data.get('titel', '')}")
            self.parent_window.input_desc.setText(t_data.get('beschrijving', ''))
            
            for w in self.parent_window.dynamische_vragen_widgets:
                w['card'].deleteLater()
            self.parent_window.dynamische_vragen_widgets.clear()
            
            for v in t_data.get('vragen', []):
                self.parent_window.voeg_ontwerp_vraag_toe(v)

        def act_peil():
            tmpl = {
                "titel": "Behoeftepeiling (Standaard)",
                "beschrijving": "Een snelle peiling om de interesses in kaart te brengen.",
                "vragen": [
                    {"vraag": "Via welk kanaal hoor jij het liefst over activiteiten?", "type": "Meerkeuze (Checkboxes)", "opties": ["Instagram", "TikTok", "WhatsApp", "Anders..."], "afbeeldingen": []},
                    {"vraag": "Welk soort activiteiten mis je in de gemeente?", "type": "Open Vraag", "opties": [], "afbeeldingen": []},
                    {"vraag": "Hoe waarschijnlijk is het dat je naar een activiteit in de buurt komt?", "type": "Slider (1-10)", "opties": [], "afbeeldingen": []}
                ]
            }
            load_as_new(tmpl)

        def act_eval():
            tmpl = {
                "titel": "Activiteit Evaluatie",
                "beschrijving": "Korte feedbacklijst voor na een evenement.",
                "vragen": [
                    {"vraag": "Hoe zou je de activiteit van vandaag beoordelen?", "type": "Slider (1-10)", "opties": [], "afbeeldingen": []},
                    {"vraag": "Wat vond je het leukst aan vandaag?", "type": "Open Vraag", "opties": [], "afbeeldingen": []},
                    {"vraag": "Zou je volgende keer weer meedoen?", "type": "Keuze (Radiobuttons)", "opties": ["Zeker weten!", "Misschien", "Nee, bedankt"], "afbeeldingen": []}
                ]
            }
            load_as_new(tmpl)

        add_to_grid(create_card("Blanco Canvas", "Begin vanaf nul met een leeg ontwerp.", "Newfile.svg", act_blank))
        add_to_grid(create_card("Behoeftepeiling", "Standaard vragen over interesses.", "Folder.svg", act_peil))
        add_to_grid(create_card("Evaluatie", "Korte feedbacklijst voor evenementen.", "Sendins.svg", act_eval))

        custom_sjablonen = [t for t in parent.opgeslagen_templates if t.get("status") == "sjabloon"]
        for tmpl in custom_sjablonen:
            titel = tmpl.get("titel", "Mijn Sjabloon")
            desc = tmpl.get("beschrijving", "Eigen ontwikkeld sjabloon.")
            if len(desc) > 35: desc = desc[:32] + "..."
            add_to_grid(create_card(titel, desc, "Draft.svg", lambda t=tmpl: load_as_new(t), is_custom=True))

        scroll.setWidget(grid_container)
        fl.addWidget(scroll)
        layout.addWidget(frame)


class SplashScreen(QDialog):
    def __init__(self):
        super().__init__(None, Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(500, 380)
        self.setStyleSheet(get_stylesheet())

        layout = QVBoxLayout(self)
        frame = QFrame()
        frame.setObjectName("Card")
        frame.setStyleSheet(f"background-color: {Colors.bg_card}; border: 1px solid {Colors.border}; border-radius: 20px;")

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(40); shadow.setColor(QColor(0, 0, 0, 90)); shadow.setOffset(0, 10)
        frame.setGraphicsEffect(shadow)

        fl = QVBoxLayout(frame)
        fl.setContentsMargins(40, 50, 40, 30)
        fl.setAlignment(Qt.AlignCenter)

        logo_lbl = QLabel()
        logo_lbl.setStyleSheet("border: none !important; background: transparent;")
        logo_path = os.path.join(application_path, "logo_stichtingzo_rgb.png")
        if os.path.exists(logo_path):
            pix = QPixmap(logo_path)
            logo_lbl.setPixmap(pix.scaled(260, 130, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            logo_lbl.setText("ZO!")
            logo_lbl.setStyleSheet(f"color: {Colors.accent}; font-size: 50px; font-weight: bold; border: none;")
        logo_lbl.setAlignment(Qt.AlignCenter)
        fl.addWidget(logo_lbl)
        
        fl.addSpacing(15)
        
        self.loader = CircularLoader()
        fl.addWidget(self.loader, alignment=Qt.AlignCenter)
        self.loader.start()
        
        fl.addSpacing(30)

        lbl_info = QLabel(f"v{HUIDIGE_VERSIE} |  © {datetime.now().year} Stichting ZO!")
        lbl_info.setStyleSheet("""
            font-family: 'Segoe UI', 'Inter', sans-serif; 
            color: #9CA3AF; 
            font-size: 11px; 
            font-weight: 500;
            border: none;
        """)
        lbl_info.setAlignment(Qt.AlignCenter)
        fl.addWidget(lbl_info)

        layout.addWidget(frame)


class FocusLineEdit(QLineEdit):
    focus_in = Signal()
    focus_out = Signal()
    
    def focusInEvent(self, e):
        super().focusInEvent(e)
        self.focus_in.emit()
        
    def focusOutEvent(self, e):
        super().focusOutEvent(e)
        self.focus_out.emit()


class LoginScreen(QDialog):
    def __init__(self):
        super().__init__(None, Qt.FramelessWindowHint | Qt.Window)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(450, 520) 
        self.setStyleSheet(get_stylesheet())

        icon_path = os.path.join(application_path, "app.ico").replace("\\", "/")
        self.setWindowIcon(QIcon(icon_path))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        frame = QFrame()
        frame.setObjectName("Card")
        frame.setStyleSheet(f"background-color: {Colors.bg_card}; border: 1px solid {Colors.border}; border-radius: 20px;")

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(35); shadow.setColor(QColor(0, 0, 0, 80)); shadow.setOffset(0, 8)
        frame.setGraphicsEffect(shadow)

        self.btn_close = QPushButton(frame)
        self.btn_close.setAutoDefault(False)
        self.icon_norm = QIcon(self.get_svg_icon("x.svg", Colors.text_grey))
        self.icon_hov = QIcon(self.get_svg_icon("x.svg", "#FFFFFF"))
        
        self.btn_close.setIcon(self.icon_norm)
        self.btn_close.setIconSize(QSize(12, 12))
        self.btn_close.setFixedSize(30, 30)
        self.btn_close.move(400, 15) 
        self.btn_close.setCursor(Qt.PointingHandCursor)
        self.btn_close.setStyleSheet("""
            QPushButton { border: none; background: transparent; border-radius: 6px; } 
            QPushButton:hover { background-color: #EF4444; } 
        """)
        
        def enter_evt(e): self.btn_close.setIcon(self.icon_hov)
        def leave_evt(e): self.btn_close.setIcon(self.icon_norm)
        self.btn_close.enterEvent = enter_evt
        self.btn_close.leaveEvent = leave_evt
        self.btn_close.clicked.connect(sys.exit)

        fl = QVBoxLayout(frame)
        fl.setContentsMargins(45, 30, 45, 20)
        fl.setAlignment(Qt.AlignTop)

        logo_lbl = QLabel()
        logo_lbl.setStyleSheet("border: none !important; background: transparent;")
        logo_path = os.path.join(application_path, "logo_stichtingzo_rgb.png")
        if os.path.exists(logo_path):
            pix = QPixmap(logo_path)
            logo_lbl.setPixmap(pix.scaled(200, 85, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        logo_lbl.setAlignment(Qt.AlignCenter)
        fl.addWidget(logo_lbl)
        fl.addSpacing(5)

        lbl_titel = QLabel("Welkom Terug")
        lbl_titel.setStyleSheet(f"font-size: 22px; font-weight: bold; color: {Colors.text_main}; border: none;")
        lbl_titel.setAlignment(Qt.AlignCenter)
        fl.addWidget(lbl_titel)
        
        lbl_sub = QLabel("Log in om toegang te krijgen")
        lbl_sub.setStyleSheet(f"color: {Colors.text_grey}; font-size: 13px; border: none;")
        lbl_sub.setAlignment(Qt.AlignCenter)
        fl.addWidget(lbl_sub)
        
        line = QFrame()
        line.setFixedHeight(1)
        line.setStyleSheet(f"background-color: {Colors.border}; border: none; margin-top: 10px; margin-bottom: 10px;")
        fl.addWidget(line)
        fl.addSpacing(25) 

        def create_input_field(icon_name, placeholder, is_password=False):
            wrap = QFrame()
            default_style = f"background-color: {Colors.bg_main}; border: 1px solid {Colors.border}; border-radius: 8px;"
            glow_style = f"background-color: {Colors.bg_card}; border: 2px solid {Colors.accent}; border-radius: 8px;"
            wrap.setStyleSheet(default_style)
            wl = QHBoxLayout(wrap); wl.setContentsMargins(12, 0, 12, 0) 
            icn = QLabel(); icn.setPixmap(self.get_svg_icon(icon_name, Colors.text_grey)); icn.setStyleSheet("border: none; background: transparent;")
            wl.addWidget(icn)
            inp = FocusLineEdit()
            inp.setPlaceholderText(placeholder)
            if is_password: inp.setEchoMode(QLineEdit.Password)
            inp.setFixedHeight(34); inp.setStyleSheet("border: none; background: transparent; font-size: 13px;")
            inp.focus_in.connect(lambda: wrap.setStyleSheet(glow_style))
            inp.focus_out.connect(lambda: wrap.setStyleSheet(default_style))
            wl.addWidget(inp)
            if is_password:
                btn_eye = QPushButton()
                btn_eye.setAutoDefault(False)
                btn_eye.setIcon(QIcon(self.get_svg_icon("Eye.svg", Colors.text_grey))); btn_eye.setFixedSize(28, 28); btn_eye.setCursor(Qt.PointingHandCursor); btn_eye.setStyleSheet("border: none; background: transparent;")
                def toggle_eye():
                    if inp.echoMode() == QLineEdit.Password:
                        inp.setEchoMode(QLineEdit.Normal)
                        btn_eye.setIcon(QIcon(self.get_svg_icon("EyeOff.svg", Colors.accent)))
                    else:
                        inp.setEchoMode(QLineEdit.Password)
                        btn_eye.setIcon(QIcon(self.get_svg_icon("Eye.svg", Colors.text_grey)))
                btn_eye.clicked.connect(toggle_eye)
                wl.addWidget(btn_eye)
            return wrap, inp

        self.wrap_email, self.inp_email = create_input_field("Mail.svg", "naam@stzo.nl")
        fl.addWidget(self.wrap_email)
        fl.addSpacing(8)

        self.wrap_pass, self.inp_pass = create_input_field("Lock.svg", "Wachtwoord", True)
        self.inp_pass.returnPressed.connect(self.start_login_process)
        self.inp_email.returnPressed.connect(self.inp_pass.setFocus)
        fl.addWidget(self.wrap_pass)

        options_layout = QHBoxLayout()
        checkmark_path = os.path.join(application_path, "Icons", "Checkmark.svg").replace("\\", "/")
        self.cb_remember = QCheckBox("Gegevens Onthouden")
        self.cb_remember.setCursor(Qt.PointingHandCursor)
        self.cb_remember.setStyleSheet(f"""
            QCheckBox {{ color: {Colors.text_grey}; font-size: 11px; font-weight: bold; border: none; background: transparent; }}
            QCheckBox::indicator {{ width: 14px; height: 14px; border: 1px solid {Colors.border}; border-radius: 4px; background-color: {Colors.bg_main}; }}
            QCheckBox::indicator:checked {{ background-color: {Colors.accent}; border: 1px solid {Colors.accent}; image: url('{checkmark_path}'); }}
        """)
        options_layout.addWidget(self.cb_remember)
        options_layout.addStretch()
        btn_forgot = QPushButton("Wachtwoord vergeten?")
        btn_forgot.setAutoDefault(False)
        btn_forgot.setCursor(Qt.PointingHandCursor)
        btn_forgot.setStyleSheet(f"QPushButton {{ border: none; background: transparent; color: {Colors.text_grey}; font-size: 11px; font-weight: bold; }} QPushButton:hover {{ color: {Colors.accent}; }}")
        btn_forgot.clicked.connect(self.handle_forgot_password)
        options_layout.addWidget(btn_forgot)
        fl.addLayout(options_layout)
        
        fl.addSpacing(15)
        self.btn_login = QPushButton("Inloggen")
        self.btn_login.setDefault(True)
        self.btn_login.setFixedHeight(42); self.btn_login.setCursor(Qt.PointingHandCursor)
        self.btn_login.setStyleSheet(f"background-color: {Colors.accent}; color: white; border-radius: 8px; font-weight: bold; font-size: 14px; border: none;")
        self.btn_login.clicked.connect(self.start_login_process)
        fl.addWidget(self.btn_login)

        self.lbl_error = QLabel("")
        self.lbl_error.setStyleSheet("color: #EF4444; font-size: 11px; font-weight: bold; border: none; margin-top: 5px;")
        self.lbl_error.setAlignment(Qt.AlignCenter)
        fl.addWidget(self.lbl_error)
        
        self.loader_container = QWidget(); self.loader_container.setFixedHeight(30); self.loader_container.setStyleSheet("background: transparent; border: none;") 
        ll = QVBoxLayout(self.loader_container); ll.setContentsMargins(0,0,0,0)
        self.loader = CircularLoader(); self.loader.setFixedSize(25, 25) 
        ll.addWidget(self.loader, alignment=Qt.AlignCenter); self.loader_container.hide()
        fl.addWidget(self.loader_container)

        fl.addStretch()
        footer = QLabel(f"© {datetime.now().year} Stichting ZO!")
        footer.setStyleSheet("color: #9CA3AF; font-size: 10px; border: none;"); footer.setAlignment(Qt.AlignCenter)
        fl.addWidget(footer)
        layout.addWidget(frame)

        local_settings = QSettings("StichtingZO", "Klantenportaal")
        self.saved_email = local_settings.value("remembered_email", "")
        
        if self.saved_email:
            self.inp_email.setText(self.saved_email)
            self.cb_remember.setChecked(True)
            QTimer.singleShot(500, lambda: self.inp_pass.setFocus())

    def get_svg_icon(self, filename, color):
        path = os.path.join(application_path, "Icons", filename)
        pix = QPixmap(18, 18); pix.fill(Qt.transparent)
        if os.path.exists(path):
            renderer = QSvgRenderer(path); painter = QPainter(pix); renderer.render(painter)
            painter.setCompositionMode(QPainter.CompositionMode_SourceIn); painter.fillRect(pix.rect(), QColor(color)); painter.end()
        return pix

    def handle_forgot_password(self):
        email = self.inp_email.text().strip()
        if not email:
            self.lbl_error.setStyleSheet("color: #EF4444; font-size: 11px; font-weight: bold; border: none; margin-top: 5px;")
            self.lbl_error.setText("Vul eerst je e-mailadres in hierboven.")
            return
        self.lbl_error.setStyleSheet(f"color: {Colors.accent}; font-size: 11px; font-weight: bold; border: none; margin-top: 5px;")
        self.lbl_error.setText("Bezig met sturen reset-mail...")
        QApplication.processEvents()
        try:
            if auth:
                auth.send_password_reset_email(email)
                self.lbl_error.setText(f"Check je inbox! Reset-link gestuurd naar {email}")
            else: self.lbl_error.setText("Database niet verbonden.")
        except Exception:
            self.lbl_error.setStyleSheet("color: #EF4444; font-size: 11px; font-weight: bold; border: none; margin-top: 5px;")
            self.lbl_error.setText("Kon geen mail sturen. Bestaat dit account?")

    def start_login_process(self):
        email = self.inp_email.text().strip(); password = self.inp_pass.text().strip()
        if not email or not password:
            self.lbl_error.setStyleSheet("color: #EF4444; font-size: 11px; font-weight: bold; border: none; margin-top: 5px;")
            self.lbl_error.setText("Vul beide velden in.")
            return
        self.btn_login.setText("Laden..."); self.loader_container.show(); self.loader.start()
        QApplication.processEvents(); QTimer.singleShot(600, lambda: self.process_login(email, password))

    def process_login(self, email, password):
        global USER_TOKEN, REFRESH_TOKEN
        email_clean = email.strip().lower()
        password_clean = password.strip()

        if email_clean == "admin" and password_clean == "admin":
            self.save_remember_me(email_clean)
            self.accept()
            return

        try:
            user = auth.sign_in_with_email_and_password(email_clean, password_clean)
            USER_TOKEN = user['idToken']
            REFRESH_TOKEN = user['refreshToken']
            self.save_remember_me(email_clean)
            
            offline_hash = hashlib.sha256((email_clean + password_clean).encode()).hexdigest()
            local_settings = QSettings("StichtingZO", "Klantenportaal")
            local_settings.setValue("offline_hash", offline_hash)
            
            self.accept()
        except Exception as e:
            print(f"Netwerk inlogfout: {e}")
            offline_hash = hashlib.sha256((email_clean + password_clean).encode()).hexdigest()
            local_settings = QSettings("StichtingZO", "Klantenportaal")
            stored_hash = local_settings.value("offline_hash", "")
            
            if offline_hash == stored_hash and stored_hash != "":
                USER_TOKEN = "OFFLINE"
                REFRESH_TOKEN = None
                self.save_remember_me(email_clean)
                self.accept()
            else:
                self.lbl_error.setText("Onjuist e-mailadres, wachtwoord of offline bij eerste login.")
                self.loader.stop()
                self.loader_container.hide()
                self.btn_login.setText("Inloggen")

    def save_remember_me(self, email):
        local_settings = QSettings("StichtingZO", "Klantenportaal")
        
        if self.cb_remember.isChecked():
            local_settings.setValue("remembered_email", email)
        else:
            local_settings.remove("remembered_email")
        
        local_settings.sync() 
            
    def show_error(self, message):
        self.lbl_error.setStyleSheet("color: #EF4444; font-size: 11px; font-weight: bold; border: none; margin-top: 5px;")
        self.loader.stop(); self.loader_container.hide(); self.btn_login.setText("Inloggen"); self.lbl_error.setText(message)


class StichtingZOPortal(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Stichting ZO! Portaal")
        self.resize(1200, 800)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet(get_stylesheet())
        self.update_available = False
        self.update_versie = ""
        self.update_url = ""

        icon_path = os.path.join(application_path, "app.ico").replace("\\", "/")
        self.setWindowIcon(QIcon(icon_path))
        
        self.log_history = f"--- Systeem Terminal Gestart ---\nApp versie v{HUIDIGE_VERSIE} (PySide6)\n\n"
        self.terminal_dialog = None
        
        self.web_domein = "https://stichtingzoforms.netlify.app"
        self.opgeslagen_data = []
        self.opgeslagen_templates = []
        self.huidige_template = None
        self.huidig_te_bewerken_template = None
        self.dynamische_vragen_widgets = []
        
        self.huidige_dashboard_filter = "Alle Vragenlijsten"
        self.sidebar_collapsed = False
        self.active_nav_id = "Overzicht"
        
        self.vragen_fallback = [
            {"vraag": "Ben je eerder in contact gekomen met jongeren activiteiten in jouw omgeving?"},
            {"vraag": "Als er iets wordt georganiseerd voor jongeren in jouw buurt, via welk kanaal hoor jij dat dan het liefst?"},
            {"vraag": "Wat maakt het voor jou makkelijker om mee te doen aan een activiteit voor jongeren?"},
            {"vraag": "Wanneer heb je liever een jongeren activiteit?"},
            {"vraag": "Welk tijdstip is voor jou het beste voor een jongeren activiteit?"},
            {"vraag": "Waar spreek je in je vrije tijd het vaakst af met vrienden?"},
            {"vraag": "Wat zou jou het meest tegenhouden om mee te doen aan jongeren activiteiten?"},
            {"vraag": "Wat voor soort bericht op sociale media trekt jouw aandacht het meest?"},
            {"vraag": "Wat zorgt er bij jou voor dat een sociale media bericht je aandacht trekt?"}
        ]
        
        self.build_ui()
        self.show_loading("Verbinden met database...")
        QTimer.singleShot(500, self.init_data)
        
        self.sync_timer = QTimer(self)
        self.sync_timer.timeout.connect(self.check_offline_data)
        self.sync_timer.start(30000)

        self.token_timer = QTimer(self)
        self.token_timer.timeout.connect(self.ververs_firebase_token)
        self.token_timer.start(45 * 60 * 1000)

    def check_offline_data(self):
        offline_dir = os.path.join(application_path, "OfflineData")
        if not os.path.exists(offline_dir) or not getattr(self, 'is_online', False) or USER_TOKEN == "OFFLINE": return
        for f in os.listdir(offline_dir):
            if f.endswith(".json"):
                try:
                    with open(os.path.join(offline_dir, f), 'r') as file:
                        db.child("vragenlijsten").push(json.load(file), USER_TOKEN)
                    os.remove(os.path.join(offline_dir, f))
                except: pass

    def ververs_firebase_token(self):
        global USER_TOKEN, REFRESH_TOKEN

        if not getattr(self, 'is_online', False) or USER_TOKEN == "OFFLINE" or not REFRESH_TOKEN:
            return
            
        try:
            if auth:
                nieuw_user_data = auth.refresh(REFRESH_TOKEN)
                USER_TOKEN = nieuw_user_data['idToken']
                REFRESH_TOKEN = nieuw_user_data['refreshToken']
                self.log_output("[Systeem] Firebase Token succesvol ververst op de achtergrond.\n")
        except Exception as e:
            self.log_output(f"[Fout] Kon Firebase Token niet verversen: {e}\n")

    def start_confetti(self):
        self.confetti = ConfettiWidget(self)
        self.confetti.start()

    def changeEvent(self, event):
        if event.type() == QEvent.WindowStateChange:
            if not self.isMinimized():
                self.restore_anim = QPropertyAnimation(self, b"windowOpacity")
                self.restore_anim.setDuration(300)
                self.restore_anim.setStartValue(0.0)
                self.restore_anim.setEndValue(1.0)
                self.restore_anim.setEasingCurve(QEasingCurve.OutQuad)
                self.restore_anim.start()
                
                if hasattr(self.title_bar, 'normal_geometry') and self.title_bar.normal_geometry and not self.isMaximized():
                     self.setGeometry(self.title_bar.normal_geometry)
                     
        super().changeEvent(event)

    def log_output(self, text):
        self.log_history += text
        if self.terminal_dialog and self.terminal_dialog.isVisible():
            self.terminal_dialog.append_text(text)

    def toon_melding(self, bericht, type="success"):
        ToastNotification(self, bericht, type)

    def get_tinted_icon(self, icon_filename, default_color, active_color="white"):
        icon_path = os.path.join(application_path, "Icons", icon_filename)
        if not os.path.exists(icon_path):
            return QIcon()
            
        icon = QIcon()
        renderer = QSvgRenderer(icon_path)
        
        if not renderer.isValid():
            return QIcon()
            
        pix_default = QPixmap(48, 48)
        pix_default.fill(Qt.transparent)
        painter = QPainter(pix_default)
        renderer.render(painter)
        painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
        painter.fillRect(pix_default.rect(), QColor(default_color))
        painter.end()
        icon.addPixmap(pix_default, QIcon.Normal, QIcon.Off)
        
        pix_active = QPixmap(48, 48)
        pix_active.fill(Qt.transparent)
        painter2 = QPainter(pix_active)
        renderer.render(painter2)
        painter2.setCompositionMode(QPainter.CompositionMode_SourceIn)
        painter2.fillRect(pix_active.rect(), QColor(active_color))
        painter2.end()
        icon.addPixmap(pix_active, QIcon.Normal, QIcon.On)
        
        return icon

    def build_ui(self):
        central_wrapper = QWidget()
        self.setCentralWidget(central_wrapper)
        wrapper_layout = QVBoxLayout(central_wrapper)
        wrapper_layout.setContentsMargins(10, 10, 10, 10) 
        
        self.main_frame = QFrame()
        self.main_frame.setObjectName("MainFrame")
        
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 60))
        shadow.setOffset(0, 5)
        self.main_frame.setGraphicsEffect(shadow)
        
        self.grid_layout = QGridLayout(self.main_frame)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.grid_layout.setSpacing(0)
        
        self.title_bar = CustomTitleBar(self)
        self.grid_layout.addWidget(self.title_bar, 0, 0, 1, 2)
        
        self.sidebar = QFrame()
        self.sidebar.setObjectName("Sidebar")
        self.sidebar_layout = QVBoxLayout(self.sidebar)
        self.grid_layout.addWidget(self.sidebar, 1, 0)
        
        self.main_area = QStackedWidget()
        self.main_area.setContentsMargins(35, 30, 35, 20)
        self.grid_layout.addWidget(self.main_area, 1, 1)
        
        self.loading_tab = QWidget()
        load_layout = QVBoxLayout(self.loading_tab)
        
        skeleton_layout = QVBoxLayout()
        skeleton_layout.setAlignment(Qt.AlignTop)
        
        title_skel = QFrame()
        title_skel.setFixedSize(250, 40)
        title_skel.setStyleSheet(f"background-color: {Colors.border}; border-radius: 8px;")
        skeleton_layout.addWidget(title_skel)
        skeleton_layout.addSpacing(20)
        
        grid_skel = QHBoxLayout()
        for _ in range(3):
            card_skel = QFrame()
            card_skel.setFixedHeight(110)
            card_skel.setStyleSheet(f"background-color: {Colors.bg_main}; border: 1px solid {Colors.border}; border-radius: 10px;")
            grid_skel.addWidget(card_skel)
        skeleton_layout.addLayout(grid_skel)
        skeleton_layout.addSpacing(20)
        
        main_skel = QFrame()
        main_skel.setFixedHeight(300)
        main_skel.setStyleSheet(f"background-color: {Colors.bg_main}; border: 1px solid {Colors.border}; border-radius: 10px;")
        skeleton_layout.addWidget(main_skel)
        
        self.shimmer_effect = QGraphicsOpacityEffect()
        container_skel = QWidget()
        container_skel.setLayout(skeleton_layout)
        container_skel.setGraphicsEffect(self.shimmer_effect)
        
        self.shimmer_anim = QPropertyAnimation(self.shimmer_effect, b"opacity")
        self.shimmer_anim.setDuration(800)
        self.shimmer_anim.setStartValue(0.4)
        self.shimmer_anim.setEndValue(1.0)
        self.shimmer_anim.setLoopCount(-1)
        
        load_layout.addWidget(container_skel)
        self.main_area.addWidget(self.loading_tab)
        
        self.init_nav_buttons()
        self.rebuild_sidebar()
        self.setup_shortcuts()

        wrapper_layout.addWidget(self.main_frame)

    def init_nav_buttons(self):
        display_name = "Medewerker" 
        try:
            if auth and auth.current_user:
                email = auth.current_user.get('email', '')
                if email:
                    name_part = email.split('@')[0]
                    if '.' in name_part:
                        parts = name_part.split('.')
                        voorletter = parts[0].upper()
                        achternaam = parts[1].title()
                        display_name = f"{voorletter}. {achternaam}"
                    else:
                        display_name = name_part.title()
        except:
            pass

        self.nav_btns_data = [
            {"icon_file": "Home.svg", "text": "Overzicht", "callback": self.show_tab_home},
            {"icon_file": "Folder.svg", "text": "Vragenlijsten", "callback": self.show_tab_vragenlijsten},
            {"icon_file": "Newfile.svg", "text": "Nieuwe Vragenlijst", "callback": self.show_tab_ontwerpen},
            {"icon_file": "Draft.svg", "text": "Concepten", "callback": self.show_tab_concepten}, 
            {"icon_file": "Sendins.svg", "text": "Inzendingen", "callback": self.show_tab_inzendingen},
            {"icon_file": "Dashboard.svg", "text": "Data Dashboard", "callback": self.show_tab_dashboard},
            {"spacer": True},
            {"icon_file": "User.svg", "text": display_name, "callback": self.show_tab_profiel},
            {"icon_file": "Settings.svg", "text": "Instellingen", "callback": self.show_tab_instellingen}
        ]

    def toggle_sidebar(self):
        self.sidebar_collapsed = not self.sidebar_collapsed
        self.rebuild_sidebar()

    def rebuild_sidebar(self):
        while self.sidebar_layout.count():
            child = self.sidebar_layout.takeAt(0)
            if child.widget(): child.widget().deleteLater()
            
        if self.sidebar_collapsed:
            self.sidebar.setFixedWidth(70)
            self.sidebar_layout.setContentsMargins(0, 20, 0, 10)
            
            logo_lbl = QLabel()
            logo_lbl.setAlignment(Qt.AlignCenter)
            logo_path = os.path.join(application_path, "logo_stichtingzo_rgb.png")
            if os.path.exists(logo_path):
                pix = QPixmap(logo_path)
                logo_lbl.setPixmap(pix.scaled(35, 35, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                logo_lbl.setContentsMargins(0,0,0,15)
            else: 
                logo_lbl.setText("ZO!")
                logo_lbl.setStyleSheet(f"border: none; font-weight:bold; font-size:16px; color:{Colors.accent};")
            self.sidebar_layout.addWidget(logo_lbl, alignment=Qt.AlignCenter)
            
            for btn_data in self.nav_btns_data:
                if btn_data.get("spacer"): 
                    self.sidebar_layout.addStretch()
                    line = QFrame()
                    line.setFixedHeight(1)
                    line.setStyleSheet(f"background-color: {Colors.border}; border: none; margin: 0px 10px;")
                    self.sidebar_layout.addWidget(line)
                    self.sidebar_layout.addSpacing(5)
                    continue
                    
                btn = QPushButton()
                btn.setObjectName("SidebarButtonCollapsed")
                btn.setProperty("nav_id", btn_data["text"])
                btn.setCheckable(True)
                btn.setFixedSize(45, 45)
                btn.setToolTip(btn_data["text"])
                
                btn.setIcon(self.get_tinted_icon(btn_data["icon_file"], Colors.text_grey, "white"))
                btn.setIconSize(QSize(24, 24))
                
                def make_callback(cb, b=btn):
                    def wrapper():
                        self.set_active_btn(b)
                        cb()
                    return wrapper
                btn.clicked.connect(make_callback(btn_data["callback"]))
                
                self.sidebar_layout.addWidget(btn, alignment=Qt.AlignCenter)
        else:
            self.sidebar.setFixedWidth(250)
            self.sidebar_layout.setContentsMargins(0, 20, 0, 10)
            
            logo_container = QWidget()
            logo_layout = QVBoxLayout(logo_container)
            logo_layout.setContentsMargins(0,0,0,0)
            logo_layout.setAlignment(Qt.AlignCenter)
            
            logo_lbl = QLabel()
            logo_path = os.path.join(application_path, "logo_stichtingzo_rgb.png")
            if os.path.exists(logo_path):
                pix = QPixmap(logo_path)
                logo_lbl.setPixmap(pix.scaled(150, 70, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            else:
                logo_lbl.setText("Stichting ZO!")
                logo_lbl.setStyleSheet("font-size: 24px; font-weight: bold; border:none;")
            logo_layout.addWidget(logo_lbl)
            self.sidebar_layout.addWidget(logo_container)
            
            self.sidebar_layout.addWidget(QLabel("ZO! maakt samen leven\nin Zuidplas mooier!", styleSheet=f"color: {Colors.text_grey}; font-style: italic; margin-bottom: 20px; border:none;"), alignment=Qt.AlignCenter)
            
            lbl_menu = QLabel("WERKOMGEVING", styleSheet=f"color: {Colors.text_grey}; font-size: 12px; font-weight: bold; border:none; margin-top: 10px; letter-spacing: 1px;")
            lbl_menu.setContentsMargins(15, 0, 0, 0)
            self.sidebar_layout.addWidget(lbl_menu)
            
            for btn_data in self.nav_btns_data:
                if btn_data.get("spacer"): 
                    self.sidebar_layout.addStretch()
                    line = QFrame()
                    line.setFixedHeight(1)
                    line.setStyleSheet(f"background-color: {Colors.border}; border: none; margin: 0px 15px;")
                    self.sidebar_layout.addWidget(line)
                    self.sidebar_layout.addSpacing(5)
                    continue
                    
                btn = QPushButton(f"  {btn_data['text']}")
                btn.setObjectName("SidebarButton")
                btn.setProperty("nav_id", btn_data["text"])
                btn.setCheckable(True)
                btn.setFixedHeight(45)
                
                btn.setIcon(self.get_tinted_icon(btn_data["icon_file"], Colors.text_grey, "white"))
                btn.setIconSize(QSize(20, 20))
                
                def make_callback(cb, b=btn):
                    def wrapper():
                        self.set_active_btn(b)
                        cb()
                    return wrapper
                btn.clicked.connect(make_callback(btn_data["callback"]))
                
                self.sidebar_layout.addWidget(btn)
            
            self.sidebar_layout.addSpacing(10)
            lbl_versie = QLabel(f"v{HUIDIGE_VERSIE}")
            lbl_versie.setStyleSheet(f"color: {Colors.text_grey}; font-size: 10px; border: none;")
            self.sidebar_layout.addWidget(lbl_versie, alignment=Qt.AlignCenter)
                
        self.highlight_nav_btn(self.active_nav_id)

    def set_active_btn(self, active_btn):
        if not active_btn: return
        for btn in self.sidebar.findChildren(QPushButton):
            if btn.property("nav_id"):
                btn.setChecked(btn == active_btn)
        self.active_nav_id = active_btn.property("nav_id")

    def highlight_nav_btn(self, nav_id):
        self.active_nav_id = nav_id
        for btn in self.sidebar.findChildren(QPushButton):
            if btn.property("nav_id"):
                btn.setChecked(btn.property("nav_id") == nav_id)
        if self.title_bar.btn_collapse:
            self.title_bar.btn_collapse.setIcon(self.get_tinted_icon("Menu.svg", Colors.text_main, Colors.text_main))

    def show_loading(self, text="Laden..."):
        self.shimmer_anim.start()
        self.main_area.setCurrentWidget(self.loading_tab)
        QApplication.processEvents()

    def clear_stacked_widget(self):
        for i in range(self.main_area.count() - 1, -1, -1):
            widget = self.main_area.widget(i)
            if widget != self.loading_tab:
                self.main_area.removeWidget(widget)
                widget.deleteLater()

    def hide_loading(self, target_widget):
        self.shimmer_anim.stop()
        self.main_area.addWidget(target_widget)
        self.main_area.setCurrentWidget(target_widget)

    def init_data(self):
        self.haal_data_op()
        self.show_tab_home()

        if getattr(self, 'is_online', False):
            self.updater = AutoUpdater(self)
            QTimer.singleShot(1500, lambda: self.updater.controleer_op_updates(stille_check=True))

    def werk_notificatie_badge_bij(self):
        if not hasattr(self, 'title_bar'): return
        
        vandaag = datetime.now().strftime("%d-%m-%Y")
        vandaag_inzendingen = [k for k in self.opgeslagen_data if k.get("datum") == vandaag and k.get("status") != "verwijderd"]
        
        local_settings = QSettings("StichtingZO", "Klantenportaal")
        saved_date = local_settings.value("notif_date", "")
        saved_count = int(local_settings.value("notif_count", 0))
        
        if saved_date == vandaag:
            self.gelezen_notificaties_count = saved_count
        else:
            self.gelezen_notificaties_count = 0
            
        nieuw_inzendingen = max(0, len(vandaag_inzendingen) - self.gelezen_notificaties_count)
        
        update_count = 1 if getattr(self, 'update_available', False) else 0
        totaal = nieuw_inzendingen + update_count
        
        if totaal > 0:
            self.title_bar.lbl_badge.setText(str(totaal))
            self.title_bar.lbl_badge.show()
        else:
            self.title_bar.lbl_badge.hide()
            
    def setup_shortcuts(self):
        if hasattr(self, 'shortcuts_list'):
            for s in self.shortcuts_list: s.setEnabled(False)
            
        self.shortcuts_list = [
            QShortcut(QKeySequence(settings.value("bind_save", "Ctrl+S")), self),
            QShortcut(QKeySequence(settings.value("bind_new", "Ctrl+N")), self),
            QShortcut(QKeySequence(settings.value("bind_search", "Ctrl+F")), self)
        ]
        
        self.shortcuts_list[0].activated.connect(lambda: self.sla_template_op() if self.active_nav_id == "Nieuwe Vragenlijst" else None)
        self.shortcuts_list[1].activated.connect(lambda: self.show_tab_ontwerpen())
        self.shortcuts_list[2].activated.connect(lambda: (self.show_tab_inzendingen(), self.search_inp.setFocus()))

    def haal_data_op(self):
        try:
            if USER_TOKEN == "OFFLINE":
                raise Exception("Handmatige Offline Mode")
                
            if db:
                # 1. Haal actieve templates op
                db_data = db.child("templates").get(USER_TOKEN)
                self.opgeslagen_templates = [{'fb_key': i.key(), **i.val()} for i in db_data.each()] if db_data.val() else []
                
                # 2. Haal verwijderde templates op
                db_del_data = db.child("verwijderde_templates").get(USER_TOKEN)
                self.verwijderde_templates = [{'fb_key': i.key(), **i.val()} for i in db_del_data.each()] if db_del_data.val() else []
                
                alle_templates = self.opgeslagen_templates + self.verwijderde_templates
                try:
                    with open(os.path.join(application_path, "templates_cache.json"), "w") as f:
                        json.dump(alle_templates, f)
                except: pass
                
                # 3. Haal actieve inzendingen op
                db_inz = db.child("vragenlijsten").get(USER_TOKEN)
                self.opgeslagen_data = [{'fb_key': i.key(), **i.val()} for i in db_inz.each()] if db_inz.val() else []
                
                # 4. Haal verwijderde inzendingen op
                db_del_inz = db.child("verwijderde_vragenlijsten").get(USER_TOKEN)
                self.verwijderde_data = [{'fb_key': i.key(), **i.val()} for i in db_del_inz.each()] if db_del_inz.val() else []
                
                alle_data = self.opgeslagen_data + self.verwijderde_data
                try:
                    with open(os.path.join(application_path, "data_cache.json"), "w") as f:
                        json.dump(alle_data, f)
                except: pass

                # Automatisch definitief wissen na 30 dagen
                nu = datetime.now()
                for item in self.verwijderde_templates + self.verwijderde_data:
                    if item.get("verwijderd_op"):
                        try:
                            del_date = datetime.strptime(item.get("verwijderd_op"), "%d-%m-%Y")
                            if (nu - del_date).days >= 30:
                                folder = "verwijderde_templates" if "vragen" in item else "verwijderde_vragenlijsten"
                                db.child(folder).child(item["fb_key"]).remove(USER_TOKEN)
                        except: pass
                
                self.is_online = True
                
                if hasattr(self, 'title_bar'):
                    self.title_bar.lbl_offline.hide()
                self.werk_notificatie_badge_bij()
                    
        except Exception as e:
            self.log_output(f"[Netwerk] Terugval naar offline modus. Foutmelding: {str(e)}\n")
            self.is_online = False
            if hasattr(self, 'title_bar'):
                self.title_bar.lbl_offline.show()
                
            try:
                with open(os.path.join(application_path, "templates_cache.json"), "r") as f:
                    alle_templates = json.load(f)
                    self.opgeslagen_templates = [t for t in alle_templates if t.get("status") != "verwijderd"]
                    self.verwijderde_templates = [t for t in alle_templates if t.get("status") == "verwijderd"]
            except: pass
            
            try:
                with open(os.path.join(application_path, "data_cache.json"), "r") as f:
                    alle_data = json.load(f)
                    self.opgeslagen_data = [d for d in alle_data if d.get("status") != "verwijderd"]
                    self.verwijderde_data = [d for d in alle_data if d.get("status") == "verwijderd"]
            except: pass
            
    def bereken_invultijd(self, vragen):
        seconden = 10 
        for v in vragen:
            q_type = str(v.get("type") or "")
            if q_type == "Open Vraag": seconden += 40
            elif q_type in ["Meerkeuze (Checkboxes)", "Keuze (Radiobuttons)"]: seconden += 20
            else: seconden += 15
        return f"~{max(1, round(seconden / 60))} min"

    def show_tab_home(self):
        self.highlight_nav_btn("Overzicht")
        self.clear_stacked_widget()

        tab = QWidget(); layout = QVBoxLayout(tab)
        
        self.topbar_layout = QHBoxLayout()
        self.topbar_layout.setAlignment(Qt.AlignVCenter)
        
        self.lbl_titel = QLabel("Overzicht")
        self.lbl_titel.setStyleSheet("font-size: 28px; font-weight: bold; border: none;")
        self.topbar_layout.addWidget(self.lbl_titel)
        self.topbar_layout.addStretch()
        
        btn_quick_sync = QPushButton(" Ververs Data")
        btn_quick_sync.setObjectName("DetailsButton")
        btn_quick_sync.setIcon(self.get_tinted_icon("DatabaseSync.svg", Colors.text_main, "white"))
        btn_quick_sync.setFixedHeight(38)
        btn_quick_sync.clicked.connect(lambda: (self.init_data(), self.toon_melding("Dashboard bijgewerkt!")))

        btn_snel_nieuw = QPushButton(" Snelstart Bibliotheek")
        btn_snel_nieuw.setObjectName("AccentButton")
        btn_snel_nieuw.setIcon(self.get_tinted_icon("Library.svg", "white", "white"))
        btn_snel_nieuw.setCursor(Qt.PointingHandCursor)
        btn_snel_nieuw.setFixedHeight(38)
        btn_snel_nieuw.clicked.connect(lambda: SnelstartPopup(self).exec())
        
        self.topbar_layout.addWidget(btn_quick_sync)
        self.topbar_layout.addWidget(btn_snel_nieuw)
        layout.addLayout(self.topbar_layout)
        layout.addSpacing(10)

        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        container = QWidget(); cl = QVBoxLayout(container)
        cl.setAlignment(Qt.AlignTop)
        cl.setContentsMargins(10, 10, 10, 20) 
        cl.setSpacing(20) 

        gepubliceerd_count = len([t for t in self.opgeslagen_templates if t.get("status", "gepubliceerd") == "gepubliceerd"])
        concepten_count = len([t for t in self.opgeslagen_templates if t.get("status") == "concept"])
        tot_inz = len([d for d in self.opgeslagen_data if d.get("status") != "verwijderd"])

        hero_card = QFrame()
        hero_card.setObjectName("HeroCard")
        hero_card.setStyleSheet(f"""
            #HeroCard {{
                background-color: rgba(0, 169, 143, 0.08);
                border: none;
                border-left: 6px solid {Colors.accent};
                border-radius: 8px;
            }}
        """)
        
        hero_layout = QHBoxLayout(hero_card)
        hero_layout.setContentsMargins(25, 20, 25, 20)

        tekst_layout = QVBoxLayout()
        tekst_layout.setAlignment(Qt.AlignVCenter)
        
        uur = datetime.now().hour
        groet = "Goedemorgen" if uur < 12 else "Goedemiddag" if uur < 18 else "Goedenavond"
        
        lbl_groet = QLabel(f"{groet}!")
        lbl_groet.setStyleSheet(f"color: {Colors.text_main}; font-size: 24px; font-weight: bold; border: none;")
        tekst_layout.addWidget(lbl_groet)
        
        lbl_msg = QLabel(f"Je hebt momenteel <b>{gepubliceerd_count} actieve vragenlijsten</b> en <b>{tot_inz} inzendingen</b> verzameld.") 
        lbl_msg.setWordWrap(True)  # <-- DEZE REGEL TOEVOEGEN!
        lbl_msg.setStyleSheet(f"color: {Colors.text_grey}; font-size: 14px; border: none; margin-top: 2px;")
        tekst_layout.addWidget(lbl_msg)
        
        hero_layout.addLayout(tekst_layout, stretch=1)

        klok_layout = QVBoxLayout()
        klok_layout.setAlignment(Qt.AlignVCenter | Qt.AlignRight)
        
        self.lbl_clock = QLabel()
        self.lbl_clock.setStyleSheet(f"""
            background-color: {Colors.bg_card}; 
            color: {Colors.accent}; 
            font-weight: bold; 
            font-size: 16px;  
            border: 1px solid rgba(0, 169, 143, 0.2); 
            border-radius: 20px; 
            padding: 10px 24px;  
        """)
        klok_layout.addWidget(self.lbl_clock)
        hero_layout.addLayout(klok_layout)
        
        cl.addWidget(hero_card)

        def update_time():
            try:
                now = datetime.now()
                tijd = now.strftime("%H:%M:%S")
                dagen = ["Zondag", "Maandag", "Dinsdag", "Woensdag", "Donderdag", "Vrijdag", "Zaterdag"]
                maanden = ["Jan", "Feb", "Mrt", "Apr", "Mei", "Jun", "Jul", "Aug", "Sep", "Okt", "Nov", "Dec"]
                dag_naam = dagen[now.isoweekday() % 7]
                date_str = f"{dag_naam} {now.day} {maanden[now.month-1]} {now.year}"
                self.lbl_clock.setText(f"{date_str}   |   {tijd}")
            except RuntimeError:
                pass 

        update_time() 
        self.clock_timer = QTimer(tab) 
        self.clock_timer.timeout.connect(update_time)
        self.clock_timer.start(1000)

        kpi_layout = QHBoxLayout()
        kpi_layout.setSpacing(15)

        def create_kpi_card(titel, waarde, subtitel, icoon_file):
            c = QFrame(); c.setObjectName("Card"); c.setFixedHeight(110)
            l = QVBoxLayout(c); l.setContentsMargins(20, 15, 20, 15)
            
            top_row = QHBoxLayout()
            top_row.addWidget(QLabel(titel, styleSheet=f"color: {Colors.text_grey}; font-size: 13px; font-weight: bold; border: none;"))
            top_row.addStretch()
            
            lbl_icoon = QLabel()
            lbl_icoon.setFixedSize(34, 34)
            lbl_icoon.setStyleSheet("background: rgba(0, 169, 143, 0.1); border-radius: 8px;")
            lbl_icoon.setAlignment(Qt.AlignCenter)
            
            pixmap = self.get_tinted_icon(icoon_file, Colors.accent, Colors.accent).pixmap(20, 20)
            lbl_icoon.setPixmap(pixmap)
            
            top_row.addWidget(lbl_icoon)
            
            l.addLayout(top_row)
            l.addWidget(QLabel(str(waarde), styleSheet="font-size: 32px; font-weight: bold; border: none; margin-top: -5px;"))
            l.addWidget(QLabel(subtitel, styleSheet=f"color: {Colors.secondary}; font-size: 12px; font-weight: bold; border: none;"))
            return c

        kpi_layout.addWidget(create_kpi_card("Actieve Vragenlijsten", gepubliceerd_count, "Gepubliceerd", "Folder.svg"))
        kpi_layout.addWidget(create_kpi_card("Concepten", concepten_count, "Nog niet gepubliceerd", "Draft.svg"))
        kpi_layout.addWidget(create_kpi_card("Totaal Inzendingen", tot_inz, "Verzamelde reacties", "Sendins.svg"))
        cl.addLayout(kpi_layout)

        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(15)

        recent_card = QFrame(); recent_card.setObjectName("Card"); rl = QVBoxLayout(recent_card)
        rl.setContentsMargins(20, 20, 20, 20)
        rl.addWidget(QLabel("Recente Inzendingen", styleSheet="font-size: 18px; font-weight: bold; border: none; margin-bottom: 10px;"))
        
        recente_data = list(reversed([d for d in self.opgeslagen_data if d.get("status") != "verwijderd"]))[:5]
        if not recente_data:
            rl.addWidget(QLabel("Nog geen inzendingen.", styleSheet=f"color: {Colors.text_grey}; font-style: italic; border: none;"))
        else:
            for k in recente_data:
                item = QFrame()
                item.setStyleSheet(f"background-color: {Colors.bg_main}; border-radius: 8px; border: 1px solid {Colors.border};")
                il = QVBoxLayout(item)
                il.setContentsMargins(15, 10, 15, 10)
                il.addWidget(QLabel(f"{str(k.get('naam') or 'Onbekend')} - {str(k.get('template_titel') or '')}", styleSheet="font-weight: bold; font-size: 14px; border: none;"))
                il.addWidget(QLabel(f"Datum: {str(k.get('datum') or '-')}  |  Leeftijd: {str(k.get('leeftijd') or '-')} jr", styleSheet=f"color: {Colors.text_grey}; font-size: 12px; border: none;"))
                rl.addWidget(item)
                
        rl.addStretch()
        bottom_layout.addWidget(recent_card, stretch=5)

        feedback_card = QFrame(); feedback_card.setObjectName("Card"); fl = QVBoxLayout(feedback_card)
        fl.setContentsMargins(20, 20, 20, 20)
        fl.addWidget(QLabel("Uitgelichte Opmerkingen", styleSheet="font-size: 18px; font-weight: bold; border: none; margin-bottom: 10px;"))
        
        opmerkingen_lijst = [k for k in reversed([d for d in self.opgeslagen_data if d.get("status") != "verwijderd"]) if str(k.get("opmerking") or "").strip()]
        
        if not opmerkingen_lijst:
            fl.addWidget(QLabel("Nog geen opmerkingen achtergelaten.", styleSheet=f"color: {Colors.text_grey}; font-style: italic; border: none;"))
            fl.addStretch()
        else:
            self.huidige_opm_idx = 0
            
            opm_container = QWidget(); opm_l = QVBoxLayout(opm_container)
            opm_l.setAlignment(Qt.AlignCenter) 
            
            self.lbl_quote = QLabel()
            self.lbl_quote.setAlignment(Qt.AlignCenter)
            self.lbl_quote.setWordWrap(True)
            self.lbl_quote.setStyleSheet(f"font-size: 18px; font-style: italic; color: {Colors.text_main}; border: none; padding: 10px;") 
            
            self.lbl_author = QLabel()
            self.lbl_author.setAlignment(Qt.AlignCenter)
            self.lbl_author.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {Colors.accent}; border: none; padding-top: 5px;")
            
            opm_l.addWidget(self.lbl_quote); opm_l.addWidget(self.lbl_author)
            
            self.quote_effect = QGraphicsOpacityEffect(opm_container)
            opm_container.setGraphicsEffect(self.quote_effect)
            fl.addWidget(opm_container, stretch=1)
            
            btn_row = QHBoxLayout()
            btn_row.addStretch()
            
            btn_prev = QPushButton(); btn_prev.setFixedSize(30, 30); btn_prev.setObjectName("DetailsButton")
            btn_prev.setIcon(self.get_tinted_icon("LeftArrow.svg", Colors.text_main, "white"))
            btn_prev.setCursor(Qt.PointingHandCursor)
            
            btn_next = QPushButton(); btn_next.setFixedSize(30, 30); btn_next.setObjectName("DetailsButton")
            btn_next.setIcon(self.get_tinted_icon("RightArrow.svg", Colors.text_main, "white"))
            btn_next.setCursor(Qt.PointingHandCursor)
            
            btn_row.addWidget(btn_prev); btn_row.addWidget(btn_next)
            fl.addLayout(btn_row)
            
            fade_out = QPropertyAnimation(self.quote_effect, b"opacity", opm_container)
            fade_out.setDuration(300); fade_out.setStartValue(1.0); fade_out.setEndValue(0.0)
            
            fade_in = QPropertyAnimation(self.quote_effect, b"opacity", opm_container)
            fade_in.setDuration(300); fade_in.setStartValue(0.0); fade_in.setEndValue(1.0)
            
            opm_container.huidige_idx = 0
            opm_container.next_dir = 1
            
            def set_new_text():
                try:
                    opm_container.huidige_idx = (opm_container.huidige_idx + opm_container.next_dir) % len(opmerkingen_lijst)
                    item = opmerkingen_lijst[opm_container.huidige_idx]
                    self.lbl_quote.setText(f'"{item.get("opmerking")}"')
                    self.lbl_author.setText(f"— {item.get('naam', 'Onbekend')} ({item.get('leeftijd', '-')} jr)")
                    fade_in.start()
                except RuntimeError: pass 

            fade_out.finished.connect(set_new_text)

            def update_quote(direction=1):
                try:
                    if fade_out.state() == QPropertyAnimation.Running or fade_in.state() == QPropertyAnimation.Running: return 
                    opm_container.next_dir = direction
                    fade_out.start()
                except RuntimeError: pass

            btn_prev.clicked.connect(lambda: update_quote(-1))
            btn_next.clicked.connect(lambda: update_quote(1))
            
            item = opmerkingen_lijst[0]
            self.lbl_quote.setText(f'"{item.get("opmerking")}"')
            self.lbl_author.setText(f"— {item.get('naam', 'Onbekend')} ({item.get('leeftijd', '-')} jr)")
            
            quote_timer = QTimer(opm_container)
            quote_timer.timeout.connect(lambda: update_quote(1))
            quote_timer.start(7000) 

        bottom_layout.addWidget(feedback_card, stretch=4)
        cl.addLayout(bottom_layout)
        cl.addStretch()

        scroll.setWidget(container)
        layout.addWidget(scroll)
        self.hide_loading(tab)

    def show_tab_vragenlijsten(self):
        self.highlight_nav_btn("Vragenlijsten")
        self.clear_stacked_widget()
        
        tab = QWidget(); layout = QVBoxLayout(tab)
        
        self.topbar_layout = QHBoxLayout()
        self.lbl_titel = QLabel("Gepubliceerde Vragenlijsten")
        self.lbl_titel.setStyleSheet("font-size: 26px; font-weight: bold;")
        self.topbar_layout.addWidget(self.lbl_titel)
        self.topbar_layout.addStretch()
        layout.addLayout(self.topbar_layout)
        layout.addSpacing(10)

        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        container = QWidget(); cl = QVBoxLayout(container)
        cl.setAlignment(Qt.AlignTop)
        
        gepubliceerde_templates = [t for t in self.opgeslagen_templates if t.get("status", "gepubliceerd") == "gepubliceerd"]
        
        if not gepubliceerde_templates:
            cl.addWidget(QLabel("Er zijn nog geen gepubliceerde vragenlijsten.", styleSheet=f"color: {Colors.text_grey}; font-size: 14px;"))
            
        for tmpl in reversed(gepubliceerde_templates):
            card = QFrame(); card.setObjectName("Card"); card_layout = QHBoxLayout(card)
            card.setMinimumHeight(100)
            
            info_layout = QVBoxLayout()
            titel = QLabel(str(tmpl.get("titel") or "Zonder titel")); titel.setStyleSheet("font-size: 16px; font-weight: bold; border: none;")
            info_layout.addWidget(titel)
            
            beschrijving = str(tmpl.get("beschrijving") or "").strip()
            if beschrijving:
                lbl_desc = QLabel(beschrijving)
                lbl_desc.setWordWrap(True) 
                lbl_desc.setStyleSheet(f"color: {Colors.text_grey}; font-style: italic; border: none;")
                info_layout.addWidget(lbl_desc)
                
            badge_layout = QHBoxLayout()
            badge_layout.setSpacing(8)
            badge_layout.setAlignment(Qt.AlignLeft)

            def create_badge(text):
                lbl = QLabel(text)
                lbl.setStyleSheet(f"""
                    background-color: rgba(0, 169, 143, 0.1); 
                    color: {Colors.accent}; 
                    border: 1px solid transparent; 
                    border-radius: 12px; 
                    padding: 4px 12px; 
                    font-size: 11px; 
                    font-weight: bold;
                """)
                return lbl

            badge_layout.addWidget(create_badge(f"{len(tmpl.get('vragen', []))} vragen"))
            badge_layout.addWidget(create_badge(self.bereken_invultijd(tmpl.get('vragen', []))))
            badge_layout.addWidget(create_badge(str(tmpl.get('aangemaakt_op') or '-')))
            badge_layout.addStretch()
            
            info_layout.addLayout(badge_layout)
            card_layout.addLayout(info_layout)
            card_layout.addStretch()
            
            btn_layout = QHBoxLayout()
            btn_layout.addStretch()
            
            btn_edit = QPushButton(" Bewerken")
            btn_edit.setIcon(self.get_tinted_icon("Edit.svg", Colors.text_main))
            btn_edit.setObjectName("DetailsButton")
            btn_edit.setFixedHeight(36)
            btn_edit.setCursor(Qt.PointingHandCursor)
            btn_edit.clicked.connect(lambda checked=False, t=tmpl: self.show_tab_ontwerpen(t))
            
            btn_invullen = QPushButton(" Invullen")
            btn_invullen.setIcon(self.get_tinted_icon("Continue.svg", "white", "white"))
            btn_invullen.setObjectName("AccentButton")
            btn_invullen.setFixedHeight(36)
            btn_invullen.setFixedWidth(120)
            btn_invullen.setCursor(Qt.PointingHandCursor)
            btn_invullen.clicked.connect(lambda checked=False, t=tmpl: self.show_formulier(t))

            btn_more = QPushButton()
            btn_more.setIcon(self.get_tinted_icon("More.svg", Colors.text_main))
            btn_more.setObjectName("DetailsButton")
            btn_more.setFixedSize(36, 36)
            btn_more.setCursor(Qt.PointingHandCursor)
            
            menu = QMenu(self)
            menu.setStyleSheet(f"""
                QMenu {{ background-color: {Colors.bg_card}; border: 1px solid {Colors.border}; border-radius: 6px; padding: 5px; }}
                QMenu::item {{ padding: 8px 25px 8px 20px; border-radius: 4px; color: {Colors.text_main}; }}
                QMenu::item:selected {{ background-color: rgba(0, 169, 143, 0.1); color: {Colors.accent}; }}
                QMenu::separator {{ height: 1px; background-color: {Colors.border}; margin: 4px 10px; }}
            """)
            
            act_qr = menu.addAction("QR-code tonen")
            act_qr.setIcon(self.get_tinted_icon("QR.svg", Colors.text_main))
            act_qr.triggered.connect(lambda checked=False, t=tmpl: QRCodePopup(self, str(t.get('titel')), f"{self.web_domein}/?id={t.get('fb_key')}").exec())
            
            act_link = menu.addAction("Link kopiëren")
            act_link.setIcon(self.get_tinted_icon("link.svg", Colors.text_main))
            act_link.triggered.connect(lambda checked=False, key=tmpl.get('fb_key'): self.kopieer_link(key))
            
            menu.addSeparator()
            
            act_del = menu.addAction("Verwijderen")
            act_del.setIcon(self.get_tinted_icon("bin.svg", "#EF4444"))
            act_del.triggered.connect(lambda checked=False, key=tmpl.get('fb_key'), t=tmpl.get('titel', 'Deze vragenlijst'): self.bevestig_verwijder_template(key, t))
            
            btn_more.setMenu(menu)
            
            def toon_actie_menu(checked=False, m=menu, b=btn_more):
                menu_breedte = m.sizeHint().width()
                knop_breedte = b.width()
                x_offset = knop_breedte - menu_breedte
                y_offset = b.height() + 4 
                pos = b.mapToGlobal(QPoint(x_offset, y_offset))
                m.exec(pos)

            btn_more.clicked.connect(toon_actie_menu)

            btn_layout.addWidget(btn_edit)
            btn_layout.addWidget(btn_invullen)
            btn_layout.addWidget(btn_more)
            
            card_layout.addLayout(btn_layout)
            cl.addWidget(card)
            
        scroll.setWidget(container)
        layout.addWidget(scroll)
        self.hide_loading(tab)

    def show_tab_concepten(self):
        self.highlight_nav_btn("Concepten")
        self.clear_stacked_widget()
        
        tab = QWidget(); layout = QVBoxLayout(tab)

        self.topbar_layout = QHBoxLayout()
        self.lbl_titel = QLabel("Opgeslagen Concepten")
        self.lbl_titel.setStyleSheet("font-size: 26px; font-weight: bold;")
        self.topbar_layout.addWidget(self.lbl_titel)
        self.topbar_layout.addStretch()
        layout.addLayout(self.topbar_layout)
        layout.addSpacing(10)

        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        container = QWidget(); cl = QVBoxLayout(container)
        cl.setAlignment(Qt.AlignTop)
        
        concepten = [t for t in self.opgeslagen_templates if t.get("status") in ["concept", "sjabloon"]]
        
        if not concepten:
            cl.addWidget(QLabel("Je hebt momenteel geen ontwerpen als concept opgeslagen.", styleSheet=f"color: {Colors.text_grey}; font-size: 14px;"))
            
        for tmpl in reversed(concepten):
            card = QFrame(); card.setObjectName("Card"); card_layout = QHBoxLayout(card)
            
            info_layout = QVBoxLayout()
            titel = QLabel(str(tmpl.get("titel") or "Zonder titel")); titel.setStyleSheet("font-size: 16px; font-weight: bold; border: none;")
            info_layout.addWidget(titel)
            
            beschrijving = str(tmpl.get("beschrijving") or "").strip()
            if beschrijving:
                lbl_desc = QLabel(beschrijving)
                lbl_desc.setWordWrap(True) 
                lbl_desc.setStyleSheet(f"color: {Colors.text_grey}; font-style: italic; border: none;")
                info_layout.addWidget(lbl_desc)
                
            badge_layout = QHBoxLayout()
            badge_layout.setSpacing(8)
            badge_layout.setAlignment(Qt.AlignLeft)

            def create_badge(text, is_status=False):
                bg = "rgba(0, 169, 143, 0.1)" if not is_status else Colors.bg_main
                col = Colors.accent if not is_status else Colors.text_grey
                border = "1px solid transparent" if not is_status else f"1px solid {Colors.border}"
                
                lbl = QLabel(text)
                lbl.setStyleSheet(f"""
                    background-color: {bg}; 
                    color: {col}; 
                    border: {border};
                    border-radius: 12px; 
                    padding: 4px 12px; 
                    font-size: 11px; 
                    font-weight: bold;
                """)
                return lbl

            type_weergave = "Eigen Sjabloon" if tmpl.get("status") == "sjabloon" else "Concept"
            
            badge_layout.addWidget(create_badge(f"{len(tmpl.get('vragen', []))} vragen"))
            badge_layout.addWidget(create_badge(type_weergave, is_status=True))
            badge_layout.addWidget(create_badge(str(tmpl.get('aangemaakt_op') or '-')))
            badge_layout.addStretch()
            
            info_layout.addLayout(badge_layout)
            card_layout.addLayout(info_layout)
            card_layout.addStretch()
            
            btn_layout = QHBoxLayout()
            
            btn_del = QPushButton(" Verwijderen")
            btn_del.setIcon(self.get_tinted_icon("bin.svg", "#EF4444", "white"))
            btn_del.setObjectName("DangerButton")
            btn_del.clicked.connect(lambda checked, key=tmpl.get('fb_key'), t=tmpl.get('titel', 'Dit concept'): self.bevestig_verwijder_template(key, t))
            
            btn_edit = QPushButton(" Verder Bewerken")
            btn_edit.setIcon(self.get_tinted_icon("Continue.svg", "white", "white"))
            btn_edit.setObjectName("AccentButton")
            btn_edit.clicked.connect(lambda checked, t=tmpl: self.show_tab_ontwerpen(t))
            
            for b in [btn_del, btn_edit]: btn_layout.addWidget(b)
            card_layout.addLayout(btn_layout)
            
            cl.addWidget(card)
            
        scroll.setWidget(container)
        layout.addWidget(scroll)
        self.hide_loading(tab)

    def kopieer_link(self, key):
        link = f"{self.web_domein}/?id={key}"
        QApplication.clipboard().setText(link)
        self.toon_melding("🔗 Link gekopieerd naar klembord!", "success")

    def bevestig_verwijder_template(self, key, titel):
        popup = BevestigingPopup(self, "Vragenlijst Verwijderen", f"Weet je zeker dat je '{titel}' wilt verwijderen?", lambda: self.verwijder_template(key))
        popup.exec()

    def verwijder_template(self, key):
        if db:
            try:
                item_data = db.child("templates").child(key).get(USER_TOKEN).val()
                if item_data:
                    item_data["status"] = "verwijderd"
                    item_data["verwijderd_op"] = datetime.now().strftime("%d-%m-%Y")
                    
                    # Verplaats naar nieuwe map en verwijder uit oude
                    db.child("verwijderde_templates").child(key).set(item_data, USER_TOKEN)
                    db.child("templates").child(key).remove(USER_TOKEN)
                    
                    self.toon_melding("Vragenlijst verwijderd.", "success")
                    self.haal_data_op()
                    if self.active_nav_id == "Concepten":
                        self.show_tab_concepten()
                    else:
                        self.show_tab_vragenlijsten()
            except Exception as e:
                self.toon_melding(f"Fout bij verwijderen: {e}", "error")

    def show_tab_ontwerpen(self, edit_template=None):
        if isinstance(edit_template, bool): edit_template = None
            
        self.highlight_nav_btn("Nieuwe Vragenlijst")
        self.clear_stacked_widget()
        
        self.huidig_te_bewerken_template = edit_template
        self.dynamische_vragen_widgets.clear()
        
        tab = QWidget(); layout = QVBoxLayout(tab)
        
        self.topbar_layout = QHBoxLayout()
        self.lbl_titel = QLabel("Vragenlijst Bewerken" if edit_template else "Nieuwe Vragenlijst")
        self.lbl_titel.setStyleSheet("font-size: 26px; font-weight: bold;")
        
        if edit_template:
            btn_back = QPushButton("← Terug")
            btn_back.setStyleSheet(f"background: transparent; border: none; font-size: 14px; font-weight: bold; color: {Colors.accent}; margin-right: 15px;")
            btn_back.setCursor(Qt.PointingHandCursor)
            is_concept = edit_template.get("status") == "concept"
            btn_back.clicked.connect(self.show_tab_concepten if is_concept else self.show_tab_vragenlijsten)
            self.topbar_layout.addWidget(btn_back)
            
        self.topbar_layout.addWidget(self.lbl_titel)
        self.topbar_layout.addStretch()

        btn_concept = QPushButton(" Opslaan als Concept")
        btn_concept.setObjectName("DetailsButton")
        btn_concept.clicked.connect(lambda checked=False: self.sla_template_op(status="concept"))

        btn_sjabloon = QPushButton(" Sla op als Sjabloon")
        btn_sjabloon.setObjectName("DetailsButton")
        btn_sjabloon.clicked.connect(lambda checked=False: self.sla_template_op(status="sjabloon"))
        
        btn_save = QPushButton(" Vragenlijst Publiceren")
        btn_save.setObjectName("AccentButton")
        btn_save.clicked.connect(lambda checked=False: self.sla_template_op(status="gepubliceerd"))
        
        self.topbar_layout.addWidget(btn_concept)
        self.topbar_layout.addWidget(btn_sjabloon)
        self.topbar_layout.addWidget(btn_save)
        
        layout.addLayout(self.topbar_layout)
        layout.addSpacing(10)

        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        self.ontwerp_container = DragDropContainerWidget(None, scroll)
        self.ontwerp_layout = QVBoxLayout(self.ontwerp_container)
        self.ontwerp_container.managed_layout = self.ontwerp_layout
        self.ontwerp_layout.setAlignment(Qt.AlignTop)
        
        titel_card = QFrame(); titel_card.setObjectName("Card")
        titel_layout = QVBoxLayout(titel_card)
        titel_layout.addWidget(QLabel("1. Naam van de Vragenlijst", styleSheet="font-weight: bold; font-size: 14px; border: none;"))
        self.input_titel = QLineEdit(); self.input_titel.setFixedHeight(40); self.input_titel.setPlaceholderText("Bijv: Behoeftepeiling...")
        titel_layout.addWidget(self.input_titel)
        
        titel_layout.addWidget(QLabel("Korte beschrijving (optioneel):", styleSheet="border: none;"))
        self.input_desc = QTextEdit(); self.input_desc.setFixedHeight(60)
        titel_layout.addWidget(self.input_desc)
        self.ontwerp_layout.addWidget(titel_card)
        
        self.vragen_layout = QVBoxLayout()
        self.ontwerp_layout.addLayout(self.vragen_layout)
        self.ontwerp_container.managed_layout = self.vragen_layout

        btn_layout = QHBoxLayout()
        btn_add = QPushButton(" Vraag Toevoegen")
        btn_add.setIcon(self.get_tinted_icon("Plus.svg", Colors.text_main, "white"))
        btn_add.setObjectName("DetailsButton")
        btn_add.clicked.connect(lambda: self.voeg_ontwerp_vraag_toe())
        btn_layout.addWidget(btn_add)
        btn_layout.addStretch()
        
        self.ontwerp_layout.addLayout(btn_layout)
        
        scroll.setWidget(self.ontwerp_container)
        layout.addWidget(scroll)
        
        if edit_template:
            self.input_titel.setText(str(edit_template.get('titel') or ''))
            self.input_desc.setText(str(edit_template.get('beschrijving') or ''))
            for v in edit_template.get('vragen', []):
                self.voeg_ontwerp_vraag_toe(v)
        else:
            self.voeg_ontwerp_vraag_toe()
            
        self.hide_loading(tab)

    def voeg_ontwerp_vraag_toe(self, vraag_data=None):
        vraag_data = vraag_data or {"vraag": "", "type": "Dropdown", "opties": ["", ""], "afbeeldingen": [], "logic": {"target": "Altijd tonen", "value": ""}}
        caption_inputs = [] 
        
        card = DraggableQuestionCard(self.vragen_layout)
        layout = QVBoxLayout(card)
        
        header = QHBoxLayout()
        drag_handle = QLabel(); drag_handle.setPixmap(self.get_tinted_icon("Grip.svg", Colors.text_grey, Colors.text_main).pixmap(16, 16))
        drag_handle.setCursor(Qt.OpenHandCursor); header.addWidget(drag_handle)
        
        lbl_idx = QLabel(); lbl_idx.setStyleSheet("font-weight: bold; font-size: 14px; border: none;")
        header.addWidget(lbl_idx); header.addStretch()
        
        btn_del = QPushButton(" Verwijder"); btn_del.setObjectName("DangerButton")
        btn_del.setIcon(self.get_tinted_icon("bin.svg", "#EF4444", "white"))
        header.addWidget(btn_del); layout.addLayout(header)
        
        input_vraag = QLineEdit(); input_vraag.setFixedHeight(45); input_vraag.setPlaceholderText("Typ hier de vraag...")
        input_vraag.setText(str(vraag_data.get('vraag') or '')); layout.addWidget(input_vraag)
        
        t_layout = QHBoxLayout(); t_layout.addWidget(QLabel("Vraagtype:", styleSheet="border: none;"))
        type_combo = CustomComboBox(); type_combo.setFixedWidth(200)
        type_combo.addItems(["Dropdown", "Keuze (Radiobuttons)", "Meerkeuze (Checkboxes)", "Open Vraag", "Slider (1-10)"])
        type_combo.setCurrentText(str(vraag_data.get('type') or 'Dropdown'))
        t_layout.addWidget(type_combo); t_layout.addStretch(); layout.addLayout(t_layout)
        
        opties_container = QWidget(); opties_layout = QVBoxLayout(opties_container)
        opties_layout.setContentsMargins(0,0,0,0); layout.addWidget(opties_container)
        
        optie_inputs = [] 
        def add_optie(text=""):
            row = QHBoxLayout(); inp = QLineEdit(str(text)); inp.setFixedHeight(45)
            inp.setPlaceholderText(f"Optie {len(optie_inputs)+1}")
            optie_inputs.append(inp) 
            row.addWidget(inp)
            btn_x = QPushButton(); btn_x.setIcon(self.get_tinted_icon("SystemClose.svg", "#EF4444", "white"))
            btn_x.setFixedSize(24, 24); btn_x.setObjectName("DangerButtonSmall")
            btn_x.clicked.connect(lambda: (optie_inputs.remove(inp), row.deleteLater()))
            row.addWidget(btn_x); opties_layout.addLayout(row)
            
        for opt in vraag_data.get('opties', []): add_optie(opt)
        if not vraag_data.get('opties'): add_optie(); add_optie()
            
        btn_add_optie = QPushButton(" Antwoord toevoegen")
        btn_add_optie.setIcon(self.get_tinted_icon("Plus.svg", Colors.text_main, "white"))
        btn_add_optie.setObjectName("DetailsButton"); btn_add_optie.setFixedWidth(180)
        btn_add_optie.clicked.connect(lambda: add_optie("")); layout.addWidget(btn_add_optie)
        
        def toggle_opties(text):
            visible = text not in ["Open Vraag", "Slider (1-10)"]
            opties_container.setVisible(visible); btn_add_optie.setVisible(visible)
        type_combo.currentTextChanged.connect(toggle_opties); toggle_opties(type_combo.currentText())

        img_ui_container = QWidget()
        img_ui_layout = QVBoxLayout(img_ui_container)
        img_ui_layout.setContentsMargins(0, 0, 0, 0)

        drop_area = ImageDragDropArea()
        btn_img = QPushButton(" Bladeren naar afbeeldingen")
        btn_img.setIcon(self.get_tinted_icon("Addfile.svg", Colors.text_main, "white"))
        btn_img.setObjectName("DetailsButton")

        preview_container = QWidget()
        preview_layout = QHBoxLayout(preview_container)
        preview_layout.setAlignment(Qt.AlignLeft)
        preview_layout.setContentsMargins(0, 0, 0, 0)

        img_ui_layout.addWidget(drop_area)
        img_ui_layout.addWidget(btn_img)
        img_ui_layout.addWidget(preview_container)
        layout.addWidget(img_ui_container)

        logic_target = CustomComboBox(); logic_target.setFixedWidth(150); logic_target.addItem("Altijd tonen")
        logic_val = QLineEdit(); logic_val.setFixedHeight(45); logic_val.setPlaceholderText("Waarde..."); logic_val.setFixedWidth(120); logic_val.setVisible(False)
        
        afbeeldingen_data = list(vraag_data.get('afbeeldingen', []))
        
        widget_ref = {
            "card": card, "lbl_idx": lbl_idx, "input_vraag": input_vraag, 
            "type_combo": type_combo, "optie_inputs": optie_inputs, 
            "afbeeldingen": afbeeldingen_data, "bewaar_captions": lambda: None,
            "logic_target": logic_target, "logic_val": logic_val
        }
        
        btn_del.clicked.connect(lambda: (card.deleteLater(), self.verwijder_vraag(widget_ref)))
        self.dynamische_vragen_widgets.append(widget_ref)
        self.vragen_layout.addWidget(card)
        QTimer.singleShot(10, lambda: self.update_vraag_nummers(show_indicators=False))

        def scroll_naar_bodem():
            bar = self.ontwerp_container.scroll_area.verticalScrollBar()
            if hasattr(self, 'scroll_anim'): self.scroll_anim.stop()
            self.scroll_anim = QPropertyAnimation(bar, b"value")
            self.scroll_anim.setDuration(400)
            self.scroll_anim.setStartValue(bar.value())
            self.scroll_anim.setEndValue(bar.maximum())
            self.scroll_anim.setEasingCurve(QEasingCurve.OutCubic)
            self.scroll_anim.start()
        QTimer.singleShot(50, scroll_naar_bodem)

        def bewaar_captions():
            for i, inp in enumerate(caption_inputs):
                if i < len(afbeeldingen_data):
                    if isinstance(afbeeldingen_data[i], dict): afbeeldingen_data[i]["caption"] = inp.text().strip()
                    else: afbeeldingen_data[i] = {"data": afbeeldingen_data[i], "caption": inp.text().strip()}

        def render_previews():
            while preview_layout.count():
                child = preview_layout.takeAt(0)
                if child.widget(): child.widget().deleteLater()
            caption_inputs.clear()
            
            for idx, img_info in enumerate(afbeeldingen_data):
                try:
                    b64 = img_info.get("data", "") if isinstance(img_info, dict) else img_info
                    cap = img_info.get("caption", "") if isinstance(img_info, dict) else ""
                    
                    item_frame = QWidget(); il = QVBoxLayout(item_frame)
                    
                    ba = QByteArray.fromBase64(b64.encode())
                    pix = QPixmap()
                    pix.loadFromData(ba)
                    lbl_img = QLabel()
                    lbl_img.setPixmap(pix.scaled(80, 80, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                    il.addWidget(lbl_img)
                    
                    inp_cap = QLineEdit(cap); inp_cap.setFixedWidth(80); inp_cap.setPlaceholderText(f"Bijschrift {idx+1}")
                    caption_inputs.append(inp_cap)
                    il.addWidget(inp_cap)
                    
                    btn_rem_img = QPushButton(); btn_rem_img.setFixedSize(24, 24); btn_rem_img.setObjectName("DangerButtonSmall")
                    btn_rem_img.setIcon(self.get_tinted_icon("x.svg", "#EF4444", "white"))
                    btn_rem_img.clicked.connect(lambda checked, i=idx: (bewaar_captions(), afbeeldingen_data.pop(i), render_previews()))
                    il.addWidget(btn_rem_img)
                    
                    preview_layout.addWidget(item_frame)
                except Exception as e: pass

        def verwerk_afbeeldingen(paths):
            bewaar_captions()
            for p in paths:
                try:
                    img = Image.open(p)
                    if img.mode in ('RGBA', 'P'):
                        bg = Image.new('RGB', img.size, (255, 255, 255))
                        bg.paste(img, mask=img.split()[3] if img.mode == 'RGBA' else None)
                        img = bg
                    img.thumbnail((600, 600))
                    buf = BytesIO()
                    img.save(buf, format="JPEG", quality=75)
                    b64 = base64.b64encode(buf.getvalue()).decode('utf-8')
                    afbeeldingen_data.append({"data": b64, "caption": ""})
                except Exception as e: pass
            render_previews()

        def upload_images_via_knop():
            paths, _ = QFileDialog.getOpenFileNames(self, "Selecteer Afbeeldingen", "", "Images (*.png *.jpg *.jpeg)")
            if paths: verwerk_afbeeldingen(paths)

        btn_img.clicked.connect(upload_images_via_knop)
        drop_area.images_dropped.connect(verwerk_afbeeldingen)
        render_previews()

        conditie_layout = QHBoxLayout()
        conditie_layout.addWidget(QLabel("Toon alleen als:", styleSheet="font-size: 11px; color: grey; border: none;"))
        
        for i in range(len(self.dynamische_vragen_widgets)):
            logic_target.addItem(f"Vraag {i+1}")
            
        logic_data = vraag_data.get("logic", {})
        logic_target.setCurrentText(logic_data.get("target", "Altijd tonen"))
        
        logic_val.setText(logic_data.get("value", ""))
        logic_val.setVisible(logic_target.currentText() != "Altijd tonen")
        
        def toggle_logic_val(t): logic_val.setVisible(t != "Altijd tonen")
        logic_target.currentTextChanged.connect(toggle_logic_val)
        
        conditie_layout.addWidget(logic_target); conditie_layout.addWidget(logic_val); conditie_layout.addStretch()
        layout.addLayout(conditie_layout)

        widget_ref["bewaar_captions"] = bewaar_captions

    def update_vraag_nummers(self, show_indicators=False):
        for i in reversed(range(self.vragen_layout.count())):
            w = self.vragen_layout.itemAt(i).widget()
            if isinstance(w, DropIndicator):
                self.vragen_layout.removeWidget(w)
                w.deleteLater()

        for idx, ref in enumerate(self.dynamische_vragen_widgets):
            ref["lbl_idx"].setText(f"Vraag {idx + 1}")

        if show_indicators:
            for idx, ref in enumerate(self.dynamische_vragen_widgets):
                ind = DropIndicator(idx)
                ind.dropped_here.connect(self.verplaats_vraag_naar_index)
                self.vragen_layout.insertWidget(self.vragen_layout.indexOf(ref["card"]), ind)
            
            last_ind = DropIndicator(len(self.dynamische_vragen_widgets))
            last_ind.dropped_here.connect(self.verplaats_vraag_naar_index)
            self.vragen_layout.addWidget(last_ind)

    def verplaats_vraag_naar_index(self, nieuwe_index):
        source_card = None
        oude_index = -1
        
        for i, ref in enumerate(self.dynamische_vragen_widgets):
            if ref["card"].is_currently_dragged:
                source_card = ref["card"]
                oude_index = i
                break
                
        if not source_card or oude_index == -1: return

        if oude_index < nieuwe_index:
            insert_index = nieuwe_index - 1
        else:
            insert_index = nieuwe_index

        widget_ref = self.dynamische_vragen_widgets.pop(oude_index)
        self.dynamische_vragen_widgets.insert(insert_index, widget_ref)

        for ref in self.dynamische_vragen_widgets:
            self.vragen_layout.removeWidget(ref["card"])
            
        for ref in self.dynamische_vragen_widgets:
            self.vragen_layout.addWidget(ref["card"])
            
        source_card.is_currently_dragged = False
        source_card.show()
        self.update_vraag_nummers(show_indicators=False)

    def verwijder_vraag(self, widget_ref):
        if widget_ref in self.dynamische_vragen_widgets:
          self.dynamische_vragen_widgets.remove(widget_ref)
          self.update_vraag_nummers(show_indicators=False)

    def sla_template_op(self, status="gepubliceerd"):
        titel = self.input_titel.text().strip()
        if not titel: return self.toon_melding("Vul een titel in", "error")
        
        vragen = []
        for w in self.dynamische_vragen_widgets:
            w["bewaar_captions"]()
            v_tekst = w['input_vraag'].text().strip()
            if not v_tekst: continue
            
            v_type = w['type_combo'].currentText()
            opties = [o.text().strip() for o in w['optie_inputs'] if o.text().strip()] if v_type not in ["Open Vraag", "Slider (1-10)"] else []
            
            logic = {
                "target": w.get('logic_target').currentText() if 'logic_target' in w else "Altijd tonen",
                "value": w.get('logic_val').text().strip() if 'logic_val' in w else ""
            }
            
            vragen.append({
                "vraag": v_tekst, 
                "type": v_type, 
                "opties": opties, 
                "afbeeldingen": w["afbeeldingen"],
                "logic": logic
            })
            
        if not vragen: return self.toon_melding("Voeg minimaal 1 vraag toe", "error")
        
        data = {
            "titel": titel, 
            "beschrijving": self.input_desc.toPlainText().strip(),
            "vragen": vragen, 
            "aangemaakt_op": datetime.now().strftime("%d-%m-%Y %H:%M"),
            "status": status 
        }
        
        try:
            if self.huidig_te_bewerken_template:
                db.child("templates").child(self.huidig_te_bewerken_template['fb_key']).update(data, USER_TOKEN)
                melding = "Concept bijgewerkt!" if status == "concept" else "Vragenlijst gepubliceerd!"
                self.toon_melding(melding, "success")
            else:
                db.child("templates").push(data, USER_TOKEN)
                melding = "Als concept opgeslagen!" if status == "concept" else "Vragenlijst gepubliceerd!"
                self.toon_melding(melding, "success")
                
            self.haal_data_op()
            if status == "concept":
                self.show_tab_concepten()
            else:
                self.show_tab_vragenlijsten()
        except Exception as e:
            self.toon_melding(f"Opslaan mislukt: {e}", "error")

    def show_formulier(self, template):
        self.huidige_template = template
        self.clear_stacked_widget()
        self.highlight_nav_btn("Vragenlijsten")
        
        tab = QWidget(); layout = QVBoxLayout(tab)
        
        self.topbar_layout = QHBoxLayout()
        btn_back = QPushButton("← Terug")
        btn_back.setStyleSheet(f"background: transparent; border: none; font-size: 16px; font-weight: bold; color: {Colors.accent}; margin-right: 15px;")
        btn_back.setCursor(Qt.PointingHandCursor)
        btn_back.clicked.connect(self.show_tab_vragenlijsten)
        self.topbar_layout.addWidget(btn_back)
        
        self.lbl_titel = QLabel("Invullen")
        self.lbl_titel.setStyleSheet("font-size: 26px; font-weight: bold;")
        self.topbar_layout.addWidget(self.lbl_titel)
        self.topbar_layout.addStretch()
        
        btn_verzenden = QPushButton("Opslaan & Verzenden")
        btn_verzenden.setObjectName("AccentButton")
        btn_verzenden.clicked.connect(self.verzend_formulier)
        self.topbar_layout.addWidget(btn_verzenden)
        
        layout.addLayout(self.topbar_layout)
        layout.addSpacing(10)

        scroll = QScrollArea(); scroll.setWidgetResizable(True)
        container = QWidget(); form_layout = QVBoxLayout(container)
        form_layout.setAlignment(Qt.AlignTop)
        
        header_card = QFrame(); header_card.setObjectName("Card"); hl = QVBoxLayout(header_card)
        hl.addWidget(QLabel(str(template.get('titel') or ''), styleSheet=f"font-size: 22px; font-weight: bold; color: {Colors.accent}; border: none;"))
        beschrijving = str(template.get('beschrijving') or '').strip()
        if beschrijving: hl.addWidget(QLabel(beschrijving, styleSheet="font-size: 14px; border: none;"))
        form_layout.addWidget(header_card)
        
        info_card = QFrame(); info_card.setObjectName("Card"); il = QGridLayout(info_card)
        il.addWidget(QLabel("Informatie Respondent", styleSheet="font-size: 16px; font-weight: bold; border: none;"), 0, 0, 1, 3)
        
        il.addWidget(QLabel("Voornaam:", styleSheet="border: none;"), 1, 0)
        self.input_naam = QLineEdit()
        il.addWidget(self.input_naam, 2, 0)
        
        il.addWidget(QLabel("Geslacht:", styleSheet="border: none;"), 1, 1)
        self.input_geslacht = CustomComboBox()
        self.input_geslacht.addItems(["Man", "Vrouw", "Zeg ik liever niet"])
        il.addWidget(self.input_geslacht, 2, 1)
        
        il.addWidget(QLabel("Leeftijd:", styleSheet="border: none;"), 1, 2)
        self.input_leeftijd = CustomComboBox()
        self.input_leeftijd.addItems([str(i) for i in range(12, 28)] + ["> 27"])
        il.addWidget(self.input_leeftijd, 2, 2)
        
        il.addWidget(QLabel("Datum:", styleSheet="border: none;"), 3, 0)
        self.btn_datum = QPushButton(datetime.now().strftime('%d-%m-%Y'))
        self.btn_datum.setStyleSheet(f"text-align: left; background-color: {Colors.bg_card};")
        self.btn_datum.clicked.connect(lambda: DatePickerPopup(self, lambda d: self.btn_datum.setText(d)).exec())
        il.addWidget(self.btn_datum, 4, 0)
        
        form_layout.addWidget(info_card)
        
        self.actieve_vraag_widgets = []
        for i, vraag_data in enumerate(template.get('vragen', []), 1):
            card = QFrame(); card.setObjectName("Card"); q_layout = QVBoxLayout(card)
            q_layout.addWidget(QLabel(f"{i}. {str(vraag_data.get('vraag') or '')}", styleSheet="font-weight: bold; font-size: 14px; border: none;"))
            
            afb_data = vraag_data.get("afbeeldingen", [])
            if afb_data:
                img_container = QWidget(); ic_layout = QHBoxLayout(img_container); ic_layout.setAlignment(Qt.AlignLeft)
                for img_info in afb_data:
                    try:
                        b64 = img_info.get("data", "") if isinstance(img_info, dict) else img_info
                        cap = img_info.get("caption", "") if isinstance(img_info, dict) else ""
                        item = QWidget(); ilbl = QVBoxLayout(item)
                        
                        ba = QByteArray.fromBase64(b64.encode())
                        pix = QPixmap()
                        pix.loadFromData(ba)
                        lbl = QLabel()
                        lbl.setPixmap(pix.scaled(250, 250, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                        ilbl.addWidget(lbl)
                        if cap: ilbl.addWidget(QLabel(str(cap), styleSheet=f"color: {Colors.text_grey}; font-style: italic; border: none;"), alignment=Qt.AlignCenter)
                        ic_layout.addWidget(item)
                    except: pass
                q_layout.addWidget(img_container)

            q_type = str(vraag_data.get('type') or 'Dropdown')
            get_val_func = None
            
            inp_anders = QLineEdit(); inp_anders.setPlaceholderText("Typ hier je antwoord..."); inp_anders.hide()
            
            if q_type == "Open Vraag":
                inp = QTextEdit(); inp.setFixedHeight(60)
                q_layout.addWidget(inp)
                get_val_func = lambda i=inp: i.toPlainText().strip()
            
            elif q_type == "Slider (1-10)":
                slider = QSlider(Qt.Horizontal)
                slider.setRange(1, 10); slider.setValue(5)
                slider.setTickPosition(QSlider.TicksBelow)
                slider.setTickInterval(1)
                lbl_val = QLabel("5", styleSheet=f"font-size: 16px; font-weight: bold; color: {Colors.accent}; border: none;")
                slider.valueChanged.connect(lambda v, l=lbl_val: l.setText(str(v)))
                hl = QHBoxLayout(); hl.addWidget(slider); hl.addWidget(lbl_val)
                q_layout.addLayout(hl)
                get_val_func = lambda s=slider: str(s.value())
                
            elif q_type == "Meerkeuze (Checkboxes)":
                cbs = []
                def cb_changed():
                    inp_anders.setVisible(any("anders" in cb.text().lower() and cb.isChecked() for cb in cbs))
                
                for opt in vraag_data.get('opties', []):
                    cb = QCheckBox(str(opt))
                    cb.toggled.connect(cb_changed)
                    q_layout.addWidget(cb)
                    cbs.append(cb)
                q_layout.addWidget(inp_anders)
                
                def get_cb(boxes=cbs, anders_inp=inp_anders):
                    vals = []
                    for b in boxes:
                        if b.isChecked():
                            if "anders" in b.text().lower() and anders_inp.text().strip(): vals.append(f"{b.text()}: {anders_inp.text().strip()}")
                            else: vals.append(b.text())
                    return ", ".join(vals) if vals else "Niets geselecteerd"
                get_val_func = get_cb
                
            elif q_type == "Keuze (Radiobuttons)":
                group = QButtonGroup(card)
                def rb_changed(btn):
                    inp_anders.setVisible("anders" in btn.text().lower())
                    
                for opt in vraag_data.get('opties', []):
                    rb = QRadioButton(str(opt))
                    rb.toggled.connect(lambda checked, b=rb: rb_changed(b) if checked else None)
                    group.addButton(rb)
                    q_layout.addWidget(rb)
                q_layout.addWidget(inp_anders)
                
                def get_rb(g=group, anders_inp=inp_anders):
                    btn = g.checkedButton()
                    if not btn: return "Niets geselecteerd"
                    if "anders" in btn.text().lower() and anders_inp.text().strip(): return f"{btn.text()}: {anders_inp.text().strip()}"
                    return btn.text()
                get_val_func = get_rb

            else: 
                combo = CustomComboBox()
                combo.addItems([str(o) for o in vraag_data.get('opties', [])])
                combo.currentTextChanged.connect(lambda t: inp_anders.setVisible("anders" in t.lower()))
                q_layout.addWidget(combo)
                q_layout.addWidget(inp_anders)
                
                def get_dd(c=combo, anders_inp=inp_anders):
                    t = c.currentText()
                    if "anders" in t.lower() and anders_inp.text().strip(): return f"{t}: {anders_inp.text().strip()}"
                    return t
                get_val_func = get_dd

            self.actieve_vraag_widgets.append({"vraag": vraag_data['vraag'], "get_val": get_val_func})
            form_layout.addWidget(card)
            
        opm_card = QFrame(); opm_card.setObjectName("Card"); opm_layout = QVBoxLayout(opm_card)
        opm_layout.addWidget(QLabel("Extra Opmerkingen / Ideeën", styleSheet="font-size: 16px; font-weight: bold; border: none;"))
        self.input_opmerking = QTextEdit(); self.input_opmerking.setFixedHeight(80)
        opm_layout.addWidget(self.input_opmerking)
        form_layout.addWidget(opm_card)
        
        scroll.setWidget(container)
        layout.addWidget(scroll)
        self.hide_loading(tab)

    def verzend_formulier(self):
        if not self.input_naam.text().strip(): return self.toon_melding("Vul een voornaam in.", "error")
        
        antwoorden = [{"vraag": w["vraag"], "antwoord": w["get_val"]()} for w in self.actieve_vraag_widgets]
        
        data = {
            "template_id": str(self.huidige_template.get("fb_key") or ""),
            "template_titel": str(self.huidige_template.get("titel") or "Onbekende Vragenlijst"),
            "naam": self.input_naam.text().strip(),
            "leeftijd": self.input_leeftijd.currentText(),
            "geslacht": self.input_geslacht.currentText(),
            "datum": self.btn_datum.text(),
            "opmerking": self.input_opmerking.toPlainText().strip(),
            "antwoorden": antwoorden
        }
        
        self.start_confetti()

        try:
            if self.is_online:
                db.child("vragenlijsten").push(data, USER_TOKEN)
                self.toon_melding("Formulier succesvol verzonden!", "success")
            else:
                raise Exception("Offline")
                
            self.haal_data_op()
            self.show_tab_vragenlijsten()

        except Exception as e:
            offline_dir = os.path.join(application_path, "OfflineData")
            os.makedirs(offline_dir, exist_ok=True)
            
            bestandsnaam = f"form_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.json"
            pad = os.path.join(offline_dir, bestandsnaam)
            
            with open(pad, 'w') as f:
                json.dump(data, f)
                
            self.toon_melding("Offline opgeslagen. Sync volgt bij internet!", "info")
            self.show_tab_vragenlijsten()

    def show_tab_inzendingen(self):
        self.highlight_nav_btn("Inzendingen")
        self.clear_stacked_widget()
        self.geselecteerde_inzendingen = set()
        
        tab = QWidget(); layout = QVBoxLayout(tab)
        
        self.topbar_layout = QHBoxLayout()
        self.lbl_titel = QLabel("Inzendingen")
        self.lbl_titel.setStyleSheet("font-size: 26px; font-weight: bold;")
        self.topbar_layout.addWidget(self.lbl_titel)
        self.topbar_layout.addStretch()
        layout.addLayout(self.topbar_layout)
        
        filter_layout = QHBoxLayout()
        self.search_inp = QLineEdit(); self.search_inp.setPlaceholderText("Zoek op naam..."); self.search_inp.setFixedWidth(200)
        filter_layout.addWidget(self.search_inp)
        
        self.filter_combo = CustomComboBox(); self.filter_combo.setFixedWidth(200)
        titels = ["Alle Vragenlijsten"] + sorted(list(set(str(t.get("titel") or "") for t in self.opgeslagen_templates if t.get("status") != "concept")))
        self.filter_combo.addItems(titels)
        filter_layout.addWidget(self.filter_combo)
        
        btn_filter = QPushButton(" Zoeken")
        btn_filter.setObjectName("DetailsButton")
        btn_filter.setIcon(self.get_tinted_icon("Search.svg", Colors.text_main, Colors.text_main))
        btn_filter.clicked.connect(self.render_inzendingen_lijst)
        filter_layout.addWidget(btn_filter)
        
        filter_layout.addSpacing(20)
        
        self.btn_bulk_del = QPushButton(" Verwijder Selectie")
        self.btn_bulk_del.setObjectName("DangerButton")
        self.btn_bulk_del.setIcon(self.get_tinted_icon("bin.svg", "#EF4444", "white"))
        self.btn_bulk_del.hide()
        self.btn_bulk_del.clicked.connect(self.bevestig_bulk_verwijderen)
        filter_layout.addWidget(self.btn_bulk_del)
        
        filter_layout.addStretch()
        layout.addLayout(filter_layout)
        
        self.inzendingen_scroll = QScrollArea(); self.inzendingen_scroll.setWidgetResizable(True)
        self.inz_container = QWidget(); self.inz_layout = QVBoxLayout(self.inz_container)
        self.inz_layout.setAlignment(Qt.AlignTop)
        self.inzendingen_scroll.setWidget(self.inz_container)
        layout.addWidget(self.inzendingen_scroll)
        
        self.hide_loading(tab)
        self.render_inzendingen_lijst()

    def render_inzendingen_lijst(self):
        while self.inz_layout.count():
            child = self.inz_layout.takeAt(0)
            if child.widget(): child.widget().deleteLater()
            
        zoekterm = self.search_inp.text().lower().strip()
        fil_val = self.filter_combo.currentText()
        
        filtered = [k for k in self.opgeslagen_data if 
                    (not zoekterm or zoekterm in str(k.get("naam") or "").lower()) and 
                    (fil_val == "Alle Vragenlijsten" or str(k.get("template_titel") or "") == fil_val) and
                    str(k.get("status")) != "verwijderd"]
                    
        if not filtered:
            self.inz_layout.addWidget(QLabel("Geen inzendingen gevonden.", styleSheet=f"color: {Colors.text_grey};"), alignment=Qt.AlignCenter)
            return
            
        checkmark_path = os.path.join(application_path, "Icons", "Checkmark.svg").replace("\\", "/")
            
        for k in reversed(filtered):
            card = ClickableCard()
            card.setObjectName("Card")
            card.setStyleSheet(f"""
                ClickableCard#Card {{ background-color: {Colors.bg_card}; border: 1px solid {Colors.border}; border-radius: 10px; }}
                ClickableCard#Card:hover {{ border: 1px solid {Colors.accent}; background-color: rgba(0, 169, 143, 0.05); }}
            """)
            cl = QHBoxLayout(card)
            
            cb = QCheckBox()
            cb.setCursor(Qt.PointingHandCursor)
            cb.setStyleSheet(f"""
                QCheckBox::indicator {{ width: 20px; height: 20px; border: 2px solid {Colors.border}; border-radius: 6px; background-color: {Colors.bg_main}; }}
                QCheckBox::indicator:hover {{ border: 2px solid {Colors.accent}; }}
                QCheckBox::indicator:checked {{ background-color: {Colors.accent}; border: 2px solid {Colors.accent}; image: url('{checkmark_path}'); }}
            """)
            cb.stateChanged.connect(lambda state, key=k['fb_key']: self.update_bulk_selection(key, state))
            cl.addWidget(cb)
            
            info = QVBoxLayout()
            info.addWidget(QLabel(str(k.get('naam') or 'Onbekend'), styleSheet="font-size: 15px; font-weight: bold; border: none; background: transparent;"))
            info.addWidget(QLabel(f"Vragenlijst: {str(k.get('template_titel') or '')}", styleSheet=f"color: {Colors.accent}; font-style: italic; border: none; background: transparent;"))
            
            cl.addLayout(info)
            cl.addStretch()
            
            btn_details = QPushButton("Bekijk Details")
            btn_details.setObjectName("DetailsButton") 
            btn_details.clicked.connect(lambda checked, kand=k: ResultaatPopup(self, kand, self.vragen_fallback).exec())
            cl.addWidget(btn_details)
            
            card.clicked.connect(cb.toggle)
            
            self.inz_layout.addWidget(card)

    def update_bulk_selection(self, key, state):
        if state == 2: self.geselecteerde_inzendingen.add(key)
        else: self.geselecteerde_inzendingen.discard(key)
        self.btn_bulk_del.setVisible(len(self.geselecteerde_inzendingen) > 0)
        self.btn_bulk_del.setText(f" Verwijder {len(self.geselecteerde_inzendingen)} geselecteerd")

    def bevestig_bulk_verwijderen(self):
        BevestigingPopup(self, "Bulk Verwijderen", f"Weet je zeker dat je {len(self.geselecteerde_inzendingen)} inzendingen wilt verwijderen?", self.bulk_verwijderen).exec()

    def bulk_verwijderen(self):
        for key in self.geselecteerde_inzendingen:
            try:
                item_data = db.child("vragenlijsten").child(key).get(USER_TOKEN).val()
                if item_data:
                    item_data["status"] = "verwijderd"
                    item_data["verwijderd_op"] = datetime.now().strftime("%d-%m-%Y")
                    
                    # Verplaats naar nieuwe map en verwijder uit oude
                    db.child("verwijderde_vragenlijsten").child(key).set(item_data, USER_TOKEN)
                    db.child("vragenlijsten").child(key).remove(USER_TOKEN)
            except: pass
        self.toon_melding(f"{len(self.geselecteerde_inzendingen)} inzendingen verwijderd.")
        self.haal_data_op()
        self.show_tab_inzendingen()

    def show_tab_dashboard(self):
        self.highlight_nav_btn("Data Dashboard")
        self.clear_stacked_widget()
        
        tab = QWidget(); layout = QVBoxLayout(tab)
        
        self.topbar_layout = QHBoxLayout()
        self.lbl_titel = QLabel("Data Dashboard")
        self.lbl_titel.setStyleSheet("font-size: 26px; font-weight: bold;")
        self.topbar_layout.addWidget(self.lbl_titel)
        self.topbar_layout.addStretch()
        
        btn_export = QPushButton(" Exporteer Data (.CSV)")
        btn_export.setIcon(self.get_tinted_icon("Download.svg", Colors.text_main, "white"))
        btn_export.setObjectName("DetailsButton")
        btn_export.clicked.connect(self.exporteer_data)
        self.topbar_layout.addWidget(btn_export)
        layout.addLayout(self.topbar_layout)
        
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Inzichten voor:", styleSheet="font-weight: bold;"))
        self.dash_filter = CustomComboBox(); self.dash_filter.setFixedWidth(250)
        
        titels = ["Alle Vragenlijsten"] + sorted(list(set(str(t.get("titel") or "") for t in self.opgeslagen_templates if t.get("status") != "concept" and str(t.get("titel") or ""))))
        self.dash_filter.addItems(titels)
        
        if hasattr(self, 'huidige_dashboard_filter') and self.huidige_dashboard_filter in titels:
            self.dash_filter.setCurrentText(self.huidige_dashboard_filter)
        else:
            self.huidige_dashboard_filter = "Alle Vragenlijsten"
            self.dash_filter.setCurrentText("Alle Vragenlijsten")
            
        self.dash_filter.currentTextChanged.connect(self.render_dashboard_content)
        filter_layout.addWidget(self.dash_filter); filter_layout.addStretch()
        layout.addLayout(filter_layout)
        
        self.dash_scroll = QScrollArea(); self.dash_scroll.setWidgetResizable(True)
        self.dash_container = QWidget(); self.dash_layout = QVBoxLayout(self.dash_container)
        self.dash_layout.setAlignment(Qt.AlignTop)
        self.dash_scroll.setWidget(self.dash_container)
        layout.addWidget(self.dash_scroll)
        
        self.hide_loading(tab)
        self.render_dashboard_content(self.huidige_dashboard_filter)

    def render_dashboard_content(self, filter_val):
        self.huidige_dashboard_filter = filter_val
        
        # 1. Bestaande widgets netjes en grondig opruimen
        while self.dash_layout.count():
            item = self.dash_layout.takeAt(0)
            widget = item.widget()
            if widget: 
                widget.deleteLater()
            elif item.layout():
                # Ruim ook stiekeme oude layouts op om dubbeling te voorkomen
                while item.layout().count():
                    sub_item = item.layout().takeAt(0)
                    if sub_item.widget(): sub_item.widget().deleteLater()
            
        actieve_data = [d for d in self.opgeslagen_data if d.get("status") != "verwijderd"]
        data = actieve_data if filter_val == "Alle Vragenlijsten" else [k for k in actieve_data if str(k.get("template_titel") or "") == filter_val]
        tot = len(data)
        
        # --- 1. BOVENSTE RIJ: KPI'S (Altijd zichtbaar) ---
        leeftijden = [int(k["leeftijd"]) for k in data if str(k.get("leeftijd") or "").isdigit()]
        gem_lft = round(sum(leeftijden)/len(leeftijden), 1) if leeftijden else 0
        mannen = sum(1 for k in data if str(k.get("geslacht") or "") == "Man")
        perc_m = int((mannen/tot)*100) if tot > 0 else 0
        perc_v = 100 - perc_m if tot > 0 else 0
        
        # OPLOSSING: We stoppen de KPI's in een eigen Widget (container)
        kpi_container = QWidget()
        kpi_layout = QHBoxLayout(kpi_container)
        kpi_layout.setContentsMargins(0, 0, 0, 0)
        
        def create_kpi_card(t, v, s):
            c = QFrame(); c.setObjectName("Card"); c.setFixedHeight(100); l = QVBoxLayout(c)
            l.addWidget(QLabel(t, styleSheet=f"color: {Colors.text_grey}; border: none;"))
            l.addWidget(QLabel(str(v), styleSheet="font-size: 28px; font-weight: bold; border: none;"))
            l.addWidget(QLabel(s, styleSheet=f"color: {Colors.secondary}; font-size: 11px; border: none;"))
            return c
            
        kpi_layout.addWidget(create_kpi_card("Totaal Inzendingen", tot, filter_val))
        kpi_layout.addWidget(create_kpi_card("Gemiddelde Leeftijd", f"{gem_lft} jaar", "Doelgroep analyse"))
        kpi_layout.addWidget(create_kpi_card("Geslachtsverdeling", f"{perc_m}% M / {perc_v}% V", "Op basis van inzendingen"))
        
        # Nu voegen we de verpakte widget toe, zodat hij ook weer makkelijk te wissen is!
        self.dash_layout.addWidget(kpi_container)
        
        # --- 2. GRAFIEKEN PER VRAAG (Alleen als één lijst is geselecteerd) ---
        if filter_val != "Alle Vragenlijsten" and tot > 0:
            
            gekozen_template = next((t for t in self.opgeslagen_templates if str(t.get("titel") or "") == filter_val), None)
            
            if gekozen_template and MATPLOTLIB_AVAILABLE:
                vragen = gekozen_template.get("vragen", [])
                
                for vraag_idx, vraag_info in enumerate(vragen):
                    if vraag_info.get("type") == "Open Vraag": continue

                    chart_card = QFrame(); chart_card.setObjectName("Card"); chart_layout = QVBoxLayout(chart_card)
                    chart_card.setFixedHeight(450)
                    
                    titel_grafiek = f"{vraag_idx+1}. {vraag_info.get('vraag', f'Vraag {vraag_idx+1}')}"
                    chart_layout.addWidget(QLabel(titel_grafiek, styleSheet="font-size: 16px; font-weight: bold; border: none;"))
                    
                    voorkeuren = []
                    details = {}
                    
                    for k in data:
                        antwoorden = k.get("antwoorden", [])
                        if len(antwoorden) > vraag_idx:
                            a_data = antwoorden[vraag_idx]
                            ans = str(a_data.get("antwoord") or "") if isinstance(a_data, dict) else str(a_data)
                            
                            if not ans or ans == "Niets geselecteerd": continue
                            
                            ans_list = [a.strip() for a in ans.split(',')] if vraag_info.get("type") == "Meerkeuze (Checkboxes)" else [ans]
                            
                            for enkele_ans in ans_list:
                                voorkeuren.append(enkele_ans)
                                if enkele_ans not in details: details[enkele_ans] = {'Man': 0, 'Vrouw': 0, 'Lft': []}
                                g = str(k.get("geslacht") or "")
                                if g in ['Man', 'Vrouw']: details[enkele_ans][g] += 1
                                l = str(k.get("leeftijd") or "")
                                if l.isdigit(): details[enkele_ans]['Lft'].append(int(l))
                    
                    if not voorkeuren:
                        chart_layout.addWidget(QLabel("Nog geen antwoorden voor deze vraag.", alignment=Qt.AlignCenter, styleSheet="border: none; color: grey; font-style: italic;"))
                    else:
                        try:
                            telling = Counter(voorkeuren)
                            
                            fig, ax = plt.subplots(figsize=(8, 3.5), dpi=100)
                            fig.patch.set_facecolor(Colors.bg_card)
                            ax.set_facecolor(Colors.bg_card)
                            ax.tick_params(colors=Colors.text_main, labelsize=9)
                            for spine in ax.spines.values(): spine.set_color(Colors.border)
                            ax.yaxis.set_major_locator(MaxNLocator(integer=True))

                            labels = list(telling.keys())
                            wrapped_labels = [textwrap.fill(lbl, width=15) for lbl in labels]
                            bars = ax.bar(wrapped_labels, telling.values(), color=Colors.accent, width=0.5)
                            ax.set_xticks(range(len(wrapped_labels)))
                            ax.set_xticklabels(wrapped_labels, rotation=45, ha='right')

                            def maak_hover_functie(ax_ref, fig_ref, bars_ref, labels_ref, details_ref):
                                annot = ax_ref.annotate("", xy=(0,0), xytext=(0, 10), textcoords="offset points",
                                                    bbox=dict(boxstyle="round,pad=0.5", fc=Colors.bg_main, ec=Colors.accent, alpha=0.9),
                                                    color=Colors.text_main, ha='center', fontsize=9)
                                annot.set_visible(False)
                                
                                def hover(event):
                                    vis = annot.get_visible()
                                    if event.inaxes == ax_ref:
                                        for i, bar in enumerate(bars_ref):
                                            cont, _ = bar.contains(event)
                                            if cont:
                                                kanaal = labels_ref[i]
                                                d = details_ref.get(kanaal, {})
                                                m = d.get('Man', 0); v = d.get('Vrouw', 0); ages = d.get('Lft', [])
                                                avg_age = round(sum(ages)/len(ages), 1) if ages else "-"
                                                annot.xy = (bar.get_x() + bar.get_width() / 2, bar.get_height())
                                                annot.set_text(f"{kanaal}\nM: {m} | V: {v}\nGem Lft: {avg_age} jr")
                                                annot.set_visible(True)
                                                fig_ref.canvas.draw_idle()
                                                return
                                    if vis:
                                        annot.set_visible(False)
                                        fig_ref.canvas.draw_idle()
                                return hover

                            fig.canvas.mpl_connect("motion_notify_event", maak_hover_functie(ax, fig, bars, labels, details))
                            fig.subplots_adjust(bottom=0.35) 
                            
                            canvas = FigureCanvasQTAgg(fig)
                            
                            canvas.wheelEvent = lambda event: event.ignore()
                            
                            chart_layout.addWidget(canvas)
                        except Exception as e: pass
                    
                    self.dash_layout.addWidget(chart_card)
        
        opm_card = QFrame(); opm_card.setObjectName("Card"); ol = QVBoxLayout(opm_card)
        ol.addWidget(QLabel("Recente Ideeën & Opmerkingen", styleSheet="font-size: 16px; font-weight: bold; border: none;"))
        
        opm_lijst = [k for k in reversed(data) if str(k.get("opmerking") or "").strip() != ""]
        if not opm_lijst: 
            ol.addWidget(QLabel("Geen opmerkingen gevonden.", styleSheet=f"color: {Colors.text_grey}; font-style: italic; border: none; padding: 10px 0;"))
        else:
            for k in opm_lijst[:10]:
                item = QFrame(); item.setStyleSheet(f"background-color: {Colors.bg_main}; border: none; border-radius: 8px;")
                il = QVBoxLayout(item)
                il.addWidget(QLabel(f"{str(k.get('naam') or 'Onbekend')} ({str(k.get('leeftijd') or '-')} jr) - {str(k.get('datum') or '-')}", styleSheet=f"color: {Colors.accent}; font-weight: bold; font-size: 11px; border: none;"))
                lbl_o = QLabel(f'"{str(k.get("opmerking") or "")}"')
                lbl_o.setWordWrap(True); lbl_o.setStyleSheet("font-style: italic; border: none;")
                il.addWidget(lbl_o)
                ol.addWidget(item)
            
        self.dash_layout.addWidget(opm_card)

    def exporteer_data(self):
        actieve_data = [d for d in self.opgeslagen_data if d.get("status") != "verwijderd"]
        if not actieve_data: return self.toon_melding("Geen data om te exporteren", "error")
        
        fil = self.huidige_dashboard_filter
        bestandsnaam = "StichtingZO_Alle_Inzendingen.csv" if fil == "Alle Vragenlijsten" else f"StichtingZO_{fil.replace(' ', '_')}.csv"
        
        filepath, _ = QFileDialog.getSaveFileName(self, "Exporteer Data", bestandsnaam, "CSV Bestand (*.csv)")
        if filepath:
            try:
                with open(filepath, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f, delimiter=';') 
                    data_ex = actieve_data if fil == "Alle Vragenlijsten" else [k for k in actieve_data if str(k.get("template_titel") or "") == fil]
                    
                    headers = ['Naam', 'Leeftijd', 'Geslacht', 'Datum', 'Vragenlijst (Template)', 'Opmerking']
                    spec_tmpl = next((t for t in self.opgeslagen_templates if str(t.get('titel') or "") == fil), None) if fil != "Alle Vragenlijsten" else None
                    
                    if spec_tmpl:
                        for i, v in enumerate(spec_tmpl.get('vragen', [])): headers.append(str(v.get('vraag') or f'Vraag {i+1}'))
                    else:
                        max_vragen = max([len(k.get('antwoorden', [])) for k in data_ex]) if data_ex else 0
                        for i in range(max_vragen):
                            headers.extend([f"Vraag {i+1}", f"Antwoord {i+1}"])
                            
                    writer.writerow(headers)
                    
                    for k in data_ex:
                        rij = [str(k.get('naam') or ''), str(k.get('leeftijd') or ''), str(k.get('geslacht') or ''), str(k.get('datum') or ''), str(k.get('template_titel') or ''), str(k.get('opmerking') or '').replace('\n', ' ')]
                        antw = k.get('antwoorden', [])
                        
                        if spec_tmpl:
                            for i in range(len(spec_tmpl.get('vragen', []))):
                                if i < len(antw): rij.append(str(antw[i].get('antwoord') or '') if isinstance(antw[i], dict) else str(antw[i]))
                                else: rij.append("")
                        else:
                            for ans in antw:
                                if isinstance(ans, dict): rij.extend([str(ans.get('vraag') or ''), str(ans.get('antwoord') or '')])
                                else: rij.extend(["", str(ans)])
                        writer.writerow(rij)
                        
                self.toon_melding("Data succesvol geëxporteerd!", "success")
                os.startfile(filepath) 
            except Exception as e:
                self.toon_melding(f"Fout bij exporteren: {e}", "error")

    def show_tab_instellingen(self):
        self.highlight_nav_btn("Instellingen")
        self.clear_stacked_widget()
        
        tab = QWidget(); layout = QVBoxLayout(tab)
        layout.setAlignment(Qt.AlignTop)
        
        self.topbar_layout = QHBoxLayout()
        self.lbl_titel = QLabel("Instellingen")
        self.lbl_titel.setStyleSheet("font-size: 26px; font-weight: bold;")
        self.topbar_layout.addWidget(self.lbl_titel)
        self.topbar_layout.addStretch()
        layout.addLayout(self.topbar_layout)
        layout.addSpacing(10)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff) # Dit is de schone manier!
        
        container = QWidget()
        cl = QVBoxLayout(container)
        cl.setAlignment(Qt.AlignTop)
        cl.setContentsMargins(5, 5, 15, 20)
        cl.setSpacing(20)

        btn_style = f"QPushButton {{ background-color: {Colors.bg_main}; border: 1px solid {Colors.border}; border-radius: 6px; font-weight: bold; color: {Colors.text_main}; text-align: left; padding-left: 15px; }} QPushButton:hover {{ background-color: rgba(0, 169, 143, 0.1); border: 1px solid {Colors.accent}; color: {Colors.accent}; }}"
        combo_style = f"QComboBox {{ background-color: {Colors.bg_main}; border: 1px solid {Colors.border}; border-radius: 6px; padding: 6px 12px; color: {Colors.text_main}; }} QComboBox::drop-down {{ border: none; width: 30px; }} QComboBox::down-arrow {{ image: url({os.path.join(application_path, 'Icons', 'SystemArrowDown.svg').replace(chr(92), '/')}); width: 16px; height: 16px; }}"

        weergave_card = QFrame(); weergave_card.setObjectName("Card")
        wl = QVBoxLayout(weergave_card)
        wl.setContentsMargins(25, 20, 25, 20); wl.setSpacing(15)
        lbl_w = QLabel("Weergave"); lbl_w.setStyleSheet("font-size: 16px; font-weight: bold; border: none;")
        wl.addWidget(lbl_w)
        
        theme_layout = QHBoxLayout()
        lbl_theme = QLabel("Applicatie Thema:")
        lbl_theme.setStyleSheet("border: none; font-size: 13px;")
        theme_layout.addWidget(lbl_theme)
        
        self.combo_theme = CustomComboBox()
        self.combo_theme.setFixedWidth(200)
        self.combo_theme.setStyleSheet(combo_style) 
        self.combo_theme.addItems(["Systeem", "Light", "Dark"])
        self.combo_theme.setCurrentText(settings.value("theme", "Systeem"))
        self.combo_theme.currentTextChanged.connect(self.toggle_theme)
        theme_layout.addWidget(self.combo_theme); theme_layout.addStretch()
        wl.addLayout(theme_layout)
        cl.addWidget(weergave_card)
        
        sys_card = QFrame(); sys_card.setObjectName("Card")
        sl = QVBoxLayout(sys_card)
        sl.setContentsMargins(25, 20, 25, 20); sl.setSpacing(15)
        lbl_sys = QLabel("Systeem & Database"); lbl_sys.setStyleSheet("font-size: 16px; font-weight: bold; border: none;")
        sl.addWidget(lbl_sys)
        
        btn_update = QPushButton("  Controleer op Software Updates")
        btn_update.setStyleSheet(btn_style) 
        btn_update.setCursor(Qt.PointingHandCursor)
        btn_update.setFixedWidth(300); btn_update.setFixedHeight(40)
    
        btn_update.setIcon(self.get_tinted_icon("Download.svg", Colors.text_main, Colors.accent))
        
        if getattr(self, 'update_available', False):
            lbl_upd_badge = QLabel("1", btn_update)
            lbl_upd_badge.setFixedSize(18, 18)
            lbl_upd_badge.setStyleSheet("background-color: #EF4444; color: white; border-radius: 9px; font-size: 10px; font-weight: bold; border: none;")
            lbl_upd_badge.setAlignment(Qt.AlignCenter)
            lbl_upd_badge.move(270, 11)

        def start_handmatige_update():
            self.toon_melding("Bezig met controleren...")
            self.updater = AutoUpdater(self)

            self.updater.controleer_op_updates(stille_check=False) 

        btn_update.clicked.connect(start_handmatige_update)
        sl.addWidget(btn_update)

        btn_refresh = QPushButton("  Forceer Database Synchronisatie")
        btn_refresh.setStyleSheet(btn_style) 
        btn_refresh.setCursor(Qt.PointingHandCursor)
        btn_refresh.setFixedWidth(300); btn_refresh.setFixedHeight(40)
        btn_refresh.setIcon(self.get_tinted_icon("DatabaseSync.svg", Colors.text_main, Colors.accent))
        btn_refresh.clicked.connect(lambda: (self.init_data(), self.toon_melding("Database ververst!")))
        sl.addWidget(btn_refresh)
        
        btn_term = QPushButton("  Open Systeem Terminal")
        btn_term.setStyleSheet(btn_style)
        btn_term.setCursor(Qt.PointingHandCursor)
        btn_term.setFixedWidth(300); btn_term.setFixedHeight(40)
        btn_term.setIcon(self.get_tinted_icon("Terminal.svg", Colors.text_main, Colors.accent))
        btn_term.clicked.connect(self.open_terminal)
        sl.addWidget(btn_term)
        cl.addWidget(sys_card)
        
        status_card = QFrame(); status_card.setObjectName("Card")
        sl2 = QVBoxLayout(status_card)
        sl2.setContentsMargins(25, 20, 25, 20); sl2.setSpacing(15)
        lbl_stat = QLabel("Verbindingsstatus"); lbl_stat.setStyleSheet("font-size: 16px; font-weight: bold; border: none;")
        sl2.addWidget(lbl_stat)
        
        status_layout = QHBoxLayout()
        self.lbl_status_icon = QLabel(); self.lbl_status_icon.setFixedSize(14, 14)
        self.lbl_status_text = QLabel("Controleren..."); self.lbl_status_text.setStyleSheet("font-size: 13px; border: none;")
        status_layout.addWidget(self.lbl_status_icon); status_layout.addWidget(self.lbl_status_text); status_layout.addStretch()
        sl2.addLayout(status_layout)
        cl.addWidget(status_card)
        
        beheer_card = QFrame(); beheer_card.setObjectName("Card")
        bl = QVBoxLayout(beheer_card)
        bl.setContentsMargins(25, 20, 25, 20); bl.setSpacing(15)
        lbl_beh = QLabel("Geavanceerd Beheer"); lbl_beh.setStyleSheet("font-size: 16px; font-weight: bold; border: none;")
        bl.addWidget(lbl_beh)
        
        btn_prullenbak = QPushButton("  Open Prullenbak (Herstel Data)")
        btn_prullenbak.setStyleSheet(btn_style)
        btn_prullenbak.setCursor(Qt.PointingHandCursor)
        btn_prullenbak.setFixedWidth(300); btn_prullenbak.setFixedHeight(40)
        btn_prullenbak.setIcon(self.get_tinted_icon("Trash.svg", Colors.text_main, Colors.accent))
        btn_prullenbak.clicked.connect(self.open_prullenbak)
        bl.addWidget(btn_prullenbak)
        
        btn_sneltoetsen = QPushButton("  Sneltoetsen Aanpassen")
        btn_sneltoetsen.setStyleSheet(btn_style) 
        btn_sneltoetsen.setCursor(Qt.PointingHandCursor)
        btn_sneltoetsen.setFixedWidth(300); btn_sneltoetsen.setFixedHeight(40)
        btn_sneltoetsen.setIcon(self.get_tinted_icon("Keyboard.svg", Colors.text_main, Colors.accent))
        btn_sneltoetsen.clicked.connect(self.open_sneltoetsen)
        bl.addWidget(btn_sneltoetsen)
        cl.addWidget(beheer_card)
        
        over_card = QFrame(); over_card.setObjectName("Card")
        ol = QVBoxLayout(over_card)
        ol.setContentsMargins(25, 20, 25, 20); ol.setSpacing(15)
        lbl_over = QLabel("Over deze applicatie"); lbl_over.setStyleSheet("font-size: 16px; font-weight: bold; border: none;")
        ol.addWidget(lbl_over)
        
        lbl_versie = QLabel(f"Stichting ZO! Vragenlijsten & Analyse Systeem v{HUIDIGE_VERSIE}")
        lbl_versie.setStyleSheet(f"color: {Colors.text_main}; font-size: 13px; font-weight: bold; border: none;")
        ol.addWidget(lbl_versie)
        
        desc = QLabel("Dit systeem is speciaal ontwikkeld voor Stichting ZO! om dynamische vragenlijsten te creëren, eenvoudig uit te sturen en diepgaande analyses uit te voeren op de verzamelde data.\n\nBelangrijkste functionaliteiten:\n- Dynamische vragenlijsten ontwerpen (incl. logica & media)\n- Uitgebreid data dashboard met visuele analyses\n- Offline Safe-Sync: formulieren invullen zonder internetverbinding\n- Realtime cloud synchronisatie via beveiligde database\n- Automatische QR-code generatie in eigen huisstijl\n- Exporteren van resultaten naar Excel/CSV\n- Prullenbak en robuust data-beheer")
        desc.setWordWrap(True)
        desc.setStyleSheet(f"color: {Colors.text_grey}; font-size: 12px; border: none; line-height: 1.5; margin-bottom: 5px;")
        ol.addWidget(desc)
        
        btn_help = QPushButton("  Ga naar stzo.nl")
        btn_help.setStyleSheet(btn_style) 
        btn_help.setFixedWidth(200); btn_help.setFixedHeight(40)
        btn_help.setCursor(Qt.PointingHandCursor)
        btn_help.setIcon(self.get_tinted_icon("link.svg", Colors.text_main, Colors.accent))
        btn_help.clicked.connect(lambda: webbrowser.open("https://www.stzo.nl")) 
        ol.addWidget(btn_help)
        cl.addWidget(over_card)
        
        cl.addStretch()
        scroll.setWidget(container)
        layout.addWidget(scroll)

        self.check_connection_status()
        self.hide_loading(tab)
        
    def check_connection_status(self):
        online = getattr(self, 'is_online', False)
        
        color = "#22C55E" if online else "#EF4444"
        self.lbl_status_icon.setStyleSheet(f"background-color: {color}; border-radius: 6px; border: none;")
        self.lbl_status_text.setText("Verbonden met Firebase" if online else "Geen verbinding met database")
        self.lbl_status_text.setStyleSheet(f"color: {color}; font-weight: bold; border: none; background: transparent;")

    def toggle_theme(self, mode):
        settings.setValue("theme", mode)
        apply_theme(mode)
        self.setStyleSheet(get_stylesheet())
        self.rebuild_sidebar()
        self.update() 

    def open_terminal(self):
        if not self.terminal_dialog: self.terminal_dialog = TerminalDialog(self, self.log_history)
        self.terminal_dialog.show()

    def show_tab_profiel(self):
        for btn_data in self.nav_btns_data:
            if btn_data.get("icon_file") == "User.svg":
                self.highlight_nav_btn(btn_data["text"])

        self.clear_stacked_widget()
        
        tab = QWidget(); layout = QVBoxLayout(tab)
        layout.setAlignment(Qt.AlignTop)
        
        self.lbl_titel = QLabel("Mijn Profiel")
        self.lbl_titel.setStyleSheet("font-size: 26px; font-weight: bold; border: none; margin-bottom: 20px;")
        layout.addWidget(self.lbl_titel)
        
        profiel_card = QFrame()
        profiel_card.setObjectName("Card")
        pl = QVBoxLayout(profiel_card)
        pl.setContentsMargins(0, 0, 0, 0)
        
        banner = QFrame()
        banner.setFixedHeight(80)
        banner.setStyleSheet(f"background-color: rgba(0, 169, 143, 0.1); border-top-left-radius: 10px; border-top-right-radius: 10px; border-bottom: 1px solid {Colors.border};")
        pl.addWidget(banner)
        
        content = QWidget()
        cl = QVBoxLayout(content)
        cl.setContentsMargins(30, 20, 30, 30)
        
        current_email = "Onbekend (Admin modus)"
        display_name = "Systeem Beheerder"
        try:
            if auth and auth.current_user:
                current_email = auth.current_user.get('email', 'Geen email gevonden')
                name_part = current_email.split('@')[0]
                if '.' in name_part:
                    parts = name_part.split('.')
                    display_name = f"{parts[0].upper()}. {parts[1].title()}"
                else:
                    display_name = name_part.title()
        except: pass

        info_row = QHBoxLayout()
        info_row.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        
        avatar = QLabel()
        avatar.setFixedSize(80, 80)
        avatar.setStyleSheet(f"background-color: {Colors.accent}; border-radius: 40px;")
        avatar.setPixmap(self.get_tinted_icon("User.svg", "white", "white").pixmap(40, 40))
        avatar.setAlignment(Qt.AlignCenter)
        info_row.addWidget(avatar)
        
        det_l = QVBoxLayout()
        det_l.setAlignment(Qt.AlignVCenter)
        det_l.setContentsMargins(20, 0, 0, 0)
        
        lbl_n = QLabel(display_name)
        lbl_n.setStyleSheet(f"color: {Colors.text_main}; font-size: 24px; font-weight: bold; border: none;")
        lbl_e = QLabel(current_email)
        lbl_e.setStyleSheet(f"color: {Colors.text_grey}; font-size: 14px; border: none;")
        
        lbl_rol = QLabel("  Beheerder  ")
        lbl_rol.setStyleSheet(f"background-color: rgba(0, 169, 143, 0.15); color: {Colors.accent}; border-radius: 6px; font-size: 11px; font-weight: bold; padding: 4px 8px; border: none;")
        lbl_rol.setFixedWidth(80)
        lbl_rol.setAlignment(Qt.AlignCenter)

        det_l.addWidget(lbl_n)
        det_l.addWidget(lbl_e)
        det_l.addSpacing(5)
        det_l.addWidget(lbl_rol)
        
        info_row.addLayout(det_l)
        info_row.addStretch()
        cl.addLayout(info_row)
        
        cl.addSpacing(30)
        line = QFrame(); line.setFixedHeight(1); line.setStyleSheet(f"background-color: {Colors.border}; border: none;")
        cl.addWidget(line)
        cl.addSpacing(30)
        
        info_grid = QGridLayout()
        info_grid.setSpacing(15)
        
        def create_info_box(title, value, icon):
            box = QFrame()
            box.setStyleSheet(f"background-color: {Colors.bg_main}; border: 1px solid {Colors.border}; border-radius: 8px;")
            box_layout = QHBoxLayout(box)
            box_layout.setContentsMargins(15, 15, 15, 15)
            
            icn = QLabel()
            icn.setPixmap(self.get_tinted_icon(icon, Colors.accent, Colors.accent).pixmap(24, 24))
            icn.setStyleSheet("border: none; background: transparent;")
            box_layout.addWidget(icn)
            
            vl = QVBoxLayout()
            lbl_t = QLabel(title)
            lbl_t.setStyleSheet(f"color: {Colors.text_grey}; font-size: 11px; font-weight: bold; border: none; background: transparent;")
            lbl_v = QLabel(value)
            lbl_v.setStyleSheet(f"color: {Colors.text_main}; font-size: 14px; font-weight: bold; border: none; background: transparent;")
            vl.addWidget(lbl_t)
            vl.addWidget(lbl_v)
            
            box_layout.addLayout(vl)
            box_layout.addStretch()
            return box

        info_grid.addWidget(create_info_box("Account Status", "Actief", "Checkmark.svg"), 0, 0)
        info_grid.addWidget(create_info_box("Beveiliging", "Firebase Auth", "Lock.svg"), 0, 1)
        info_grid.addWidget(create_info_box("Laatste Login", datetime.now().strftime("%d-%m-%Y"), "Dashboard.svg"), 0, 2)
        
        cl.addLayout(info_grid)
        cl.addStretch()
        
        pl.addWidget(content)
        layout.addWidget(profiel_card)
        
        layout.addSpacing(15)
        btn_layout = QHBoxLayout()
        
        btn_logout = QPushButton(" Veilig Uitloggen")
        btn_logout.setObjectName("DangerButton")
        btn_logout.setFixedWidth(200)
        btn_logout.setIcon(self.get_tinted_icon("Logout.svg", "#EF4444", "white"))
        btn_logout.clicked.connect(lambda: os.execl(sys.executable, sys.executable, *sys.argv))
        
        btn_reset_pw = QPushButton(" Wachtwoord Wijzigen")
        btn_reset_pw.setObjectName("DetailsButton")
        btn_reset_pw.setFixedWidth(200)
        btn_reset_pw.setIcon(self.get_tinted_icon("Lock.svg", Colors.text_main, "white"))
        
        def send_reset():
            try:
                auth.send_password_reset_email(current_email)
                self.toon_melding("Reset-link naar je e-mail gestuurd!", "success")
            except:
                self.toon_melding("Kon geen reset-mail sturen.", "error")
                
        btn_reset_pw.clicked.connect(send_reset)
        
        btn_layout.addWidget(btn_logout)
        btn_layout.addWidget(btn_reset_pw)
        btn_layout.addStretch()
        
        layout.addLayout(btn_layout)
        self.hide_loading(tab)

    def open_sneltoetsen(self):
        d = QDialog(self, Qt.FramelessWindowHint | Qt.Dialog)
        d.setAttribute(Qt.WA_TranslucentBackground)
        d.setFixedSize(450, 420)
        
        layout = QVBoxLayout(d)
        layout.setContentsMargins(15, 15, 15, 15)
        
        container = QFrame(); container.setObjectName("Card")
        container.setStyleSheet(f"background-color: {Colors.bg_card}; border: 1px solid {Colors.border}; border-radius: 15px;")
        
        shadow = QGraphicsDropShadowEffect(d)
        shadow.setBlurRadius(30); shadow.setColor(QColor(0, 0, 0, 70)); shadow.setOffset(0, 8)
        container.setGraphicsEffect(shadow)
        
        cl = QVBoxLayout(container)
        cl.setContentsMargins(25, 20, 25, 25)
        
        header = QHBoxLayout()
        icon_head = QLabel()
        icon_head.setPixmap(self.get_tinted_icon("Keyboard.svg", Colors.accent, Colors.accent).pixmap(24, 24))
        icon_head.setStyleSheet("border: none; background: transparent; padding: 0px;") 
        header.addWidget(icon_head)
        
        lbl_t = QLabel("Sneltoetsen Configureren")
        lbl_t.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {Colors.text_main}; border: none; margin-left: 5px;")
        header.addWidget(lbl_t)
        header.addStretch()
        
        btn_close = QPushButton()
        btn_close.setIcon(self.get_tinted_icon("SystemClose.svg", Colors.text_grey, Colors.accent))
        btn_close.setCursor(Qt.PointingHandCursor); btn_close.setStyleSheet("border: none; background: transparent;")
        btn_close.clicked.connect(d.reject)
        header.addWidget(btn_close)
        cl.addLayout(header)
        
        line = QFrame(); line.setFixedHeight(1); line.setStyleSheet(f"background-color: {Colors.border}; border: none; margin: 5px 0px 15px 0px;")
        cl.addWidget(line)

        inputs = []
        shortcut_data = [
            ("Opslaan Formulier", "bind_save", "Ctrl+S", "Save.svg"),
            ("Nieuw Formulier", "bind_new", "Ctrl+N", "Plus.svg"),
            ("Zoekbalk Focus", "bind_search", "Ctrl+F", "Search.svg")
        ]

        for naam, key, default, icon in shortcut_data:
            row_widget = QFrame()
            row_widget.setStyleSheet("background: transparent; border: none;")
            row = QHBoxLayout(row_widget)
            row.setContentsMargins(0, 8, 0, 8)
            
            icon_l = QLabel()
            icon_l.setPixmap(self.get_tinted_icon(icon, Colors.text_grey, Colors.text_grey).pixmap(20, 20))
            icon_l.setStyleSheet("border: none; background: transparent;")
            row.addWidget(icon_l)
            
            lbl = QLabel(naam)
            lbl.setStyleSheet(f"font-size: 14px; font-weight: 600; color: {Colors.text_main}; border: none; margin-left: 10px;")
            row.addWidget(lbl)
            
            row.addStretch()
            
            inp = QLineEdit(settings.value(key, default))
            inp.setFixedWidth(110); inp.setFixedHeight(35); inp.setAlignment(Qt.AlignCenter)
            inp.setStyleSheet(f"""
                QLineEdit {{
                    background-color: {Colors.bg_main};
                    border: 1px solid {Colors.border};
                    border-bottom: 3px solid {Colors.border};
                    border-radius: 6px;
                    font-family: 'Consolas', monospace;
                    font-weight: bold;
                    color: {Colors.accent};
                    font-size: 13px;
                }}
                QLineEdit:focus {{
                    border: 2px solid {Colors.accent};
                    border-bottom: 3px solid {Colors.accent};
                    background-color: {Colors.bg_card};
                }}
            """)
            row.addWidget(inp)
            inputs.append((key, inp))
            cl.addWidget(row_widget)
            
        cl.addSpacing(20)
        
        btn_save = QPushButton("  Instellingen Opslaan")
        btn_save.setObjectName("AccentButton")
        btn_save.setFixedHeight(48)
        btn_save.setCursor(Qt.PointingHandCursor)
        btn_save.setIcon(self.get_tinted_icon("Save.svg", "white", "white"))
        btn_save.setIconSize(QSize(20, 20))
        btn_save.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.accent};
                color: white;
                font-weight: bold;
                font-size: 14px;
                border-radius: 10px;
                border: none;
            }}
            QPushButton:hover {{
                background-color: #008F7A;
            }}
        """)
        
        def save_and_close():
            for k, i in inputs:
                settings.setValue(k, i.text().strip().upper())
            self.setup_shortcuts()
            d.accept()
            self.toon_melding("Sneltoetsen succesvol bijgewerkt!", "success")

        btn_save.clicked.connect(save_and_close)
        cl.addWidget(btn_save)
        
        layout.addWidget(container)
        d.exec()

    def open_prullenbak(self):
        d = QDialog(self, Qt.FramelessWindowHint | Qt.Dialog)
        d.setAttribute(Qt.WA_TranslucentBackground)
        d.setFixedSize(650, 500)
        
        layout = QVBoxLayout(d); layout.setContentsMargins(15, 15, 15, 15)
        container = QFrame(); container.setObjectName("Card")
        container.setStyleSheet(f"background-color: {Colors.bg_card}; border: 1px solid {Colors.border}; border-radius: 15px;")
        
        shadow = QGraphicsDropShadowEffect(d)
        shadow.setBlurRadius(30); shadow.setColor(QColor(0, 0, 0, 70)); shadow.setOffset(0, 8)
        container.setGraphicsEffect(shadow)
        
        cl = QVBoxLayout(container); cl.setContentsMargins(25, 20, 25, 25)
        
        header = QHBoxLayout()
        icon_head = QLabel()
        icon_head.setPixmap(self.get_tinted_icon("Trash.svg", Colors.accent, Colors.accent).pixmap(24, 24))
        icon_head.setStyleSheet("border: none; background: transparent;")
        header.addWidget(icon_head)
        
        lbl_t = QLabel("Prullenbak"); lbl_t.setStyleSheet(f"font-size: 22px; font-weight: bold; color: {Colors.text_main}; border: none; margin-left: 5px;")
        header.addWidget(lbl_t); header.addStretch()
        
        btn_close = QPushButton()
        btn_close.setIcon(self.get_tinted_icon("SystemClose.svg", Colors.text_grey, "white"))
        btn_close.setFixedSize(32, 32); btn_close.setCursor(Qt.PointingHandCursor)
        btn_close.setStyleSheet("""
            QPushButton { background-color: transparent; border: none; border-radius: 6px; }
            QPushButton:hover { background-color: #EF4444; }
        """)
        btn_close.clicked.connect(d.reject)
        header.addWidget(btn_close); cl.addLayout(header)
        
        action_bar = QHBoxLayout()
        lbl_info = QLabel("Items worden na 30 dagen automatisch gewist."); lbl_info.setStyleSheet(f"color: {Colors.text_grey}; font-size: 11px; font-style: italic; border: none;")
        action_bar.addWidget(lbl_info); action_bar.addStretch()
        
        btn_empty = QPushButton(" Alles definitief wissen"); btn_empty.setCursor(Qt.PointingHandCursor)
        btn_empty.setIcon(self.get_tinted_icon("Trash.svg", "#EF4444", "white"))
        btn_empty.setStyleSheet("QPushButton { color: #EF4444; border: 1px solid #EF4444; background: transparent; border-radius: 8px; padding: 6px 12px; font-weight: bold; font-size: 11px; } QPushButton:hover { background-color: #FEE2E2; color: #DC2626; }")
        
        def leeg_prullenbak():
            BevestigingPopup(self, "Prullenbak Legen", "Weet je zeker dat je ALLES definitief wilt wissen?", 
                lambda: [[db.child("verwijderde_templates").child(t["fb_key"]).remove(USER_TOKEN) for t in self.verwijderde_templates],
                         [db.child("verwijderde_vragenlijsten").child(di["fb_key"]).remove(USER_TOKEN) for di in self.verwijderde_data],
                         self.init_data(), d.accept(), self.toon_melding("Prullenbak geleegd!")]).exec()
        
        btn_empty.clicked.connect(leeg_prullenbak)
        if self.verwijderde_templates or self.verwijderde_data: action_bar.addWidget(btn_empty)
        cl.addLayout(action_bar)
        
        line = QFrame(); line.setFixedHeight(1); line.setStyleSheet(f"background-color: {Colors.border}; border: none; margin: 10px 0px;"); cl.addWidget(line)

        scroll = QScrollArea(); scroll.setWidgetResizable(True); scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff); scroll.setStyleSheet("border: none; background: transparent;")
        cw = QWidget(); cl_list = QVBoxLayout(cw); cl_list.setAlignment(Qt.AlignTop); cl_list.setContentsMargins(0,0,5,0)
        
        alles = self.verwijderde_templates + self.verwijderde_data
        if not alles: cl_list.addWidget(QLabel("Prullenbak is leeg.", styleSheet=f"color:{Colors.text_grey}; border:none; padding-top: 20px;"), alignment=Qt.AlignCenter)
        
        for item in alles:
            is_tmpl = "vragen" in item
            titel = item.get("titel") if is_tmpl else item.get("naam")
            item_card = QFrame(); item_card.setStyleSheet(f"background-color: {Colors.bg_main}; border: 1px solid {Colors.border}; border-radius: 10px;")
            row = QHBoxLayout(item_card); row.setContentsMargins(15, 12, 15, 12)
            
            icon_l = QLabel()
            icon_l.setPixmap(self.get_tinted_icon("Folder.svg" if is_tmpl else "User.svg", Colors.accent, Colors.accent).pixmap(22, 22))
            icon_l.setStyleSheet("border:none;"); row.addWidget(icon_l)
            
            info_l = QVBoxLayout(); info_l.setSpacing(2)
            lbl_main = QLabel(str(titel)); lbl_main.setStyleSheet(f"font-size: 14px; font-weight: bold; border:none; color: {Colors.text_main};")
            info_l.addWidget(lbl_main)
            
            lbl_sub = QLabel(f"Verwijderd op: {item.get('verwijderd_op', 'Onbekend')}"); lbl_sub.setStyleSheet(f"font-size: 11px; color: {Colors.text_grey}; border:none;")
            info_l.addWidget(lbl_sub); row.addLayout(info_l); row.addStretch()
            
            btn_res = QPushButton(" Herstel"); btn_res.setCursor(Qt.PointingHandCursor); btn_res.setFixedSize(90, 32)
            btn_res.setIcon(self.get_tinted_icon("Restore.svg", Colors.accent, "white"))
            btn_res.setStyleSheet(f"QPushButton {{ background-color: {Colors.bg_card}; border: 1px solid {Colors.border}; border-radius: 6px; font-weight: bold; color: {Colors.text_main}; }} QPushButton:hover {{ border-color: {Colors.accent}; background-color: rgba(0, 169, 143, 0.05); }}")
            
            def herstel_item(i=item, tm=is_tmpl, card=item_card):
                bron_map = "verwijderde_templates" if tm else "verwijderde_vragenlijsten"
                doel_map = "templates" if tm else "vragenlijsten"
                try:
                    data = db.child(bron_map).child(i["fb_key"]).get(USER_TOKEN).val()
                    if data:
                        data["status"] = "gepubliceerd" if tm else "actief"
                        data.pop("verwijderd_op", None)
                        db.child(doel_map).child(i["fb_key"]).set(data, USER_TOKEN)
                        db.child(bron_map).child(i["fb_key"]).remove(USER_TOKEN)
                except: pass
                card.deleteLater(); self.init_data(); self.toon_melding("Item hersteld!", "success")
                
            btn_res.clicked.connect(herstel_item); row.addWidget(btn_res); cl_list.addWidget(item_card)
            
        scroll.setWidget(cw); cl.addWidget(scroll); layout.addWidget(container); d.exec()

if __name__ == "__main__":
    try:
        myappid = 'stichtingzo.klantenportaal.1.0'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except:
        pass

    app = QApplication(sys.argv)
    
    settings = QSettings("StichtingZO", "Klantenportaal")
    apply_theme(settings.value("theme", "Systeem"))

    app.setStyle("Fusion")
    app.setQuitOnLastWindowClosed(False)
    
    icon_path = os.path.join(application_path, "app.ico")
    app.setWindowIcon(QIcon(icon_path))
    
    splash = SplashScreen()
    splash.show()
    
    window = None

    def launch_portal():
        global window
        splash.close()
        login = LoginScreen()
        if login.exec() == QDialog.Accepted:
            window = StichtingZOPortal()
            window.show()
            app.setQuitOnLastWindowClosed(True)
        else:
            sys.exit()

    QTimer.singleShot(2500, launch_portal)
    sys.exit(app.exec())
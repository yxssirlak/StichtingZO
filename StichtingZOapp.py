# === IMPORTS ===
import customtkinter as ctk
from PIL import Image, ImageTk
import os
import sys
import pyrebase
import ctypes
import json
import calendar
import csv
import textwrap
import base64
import traceback  
from io import BytesIO
from datetime import datetime
from tkinter import filedialog
from dotenv import load_dotenv

try:
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.ticker import MaxNLocator
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False


# === SYSTEEM LOGGER ===
class OutputRedirector:
    def __init__(self):
        self.log_text = "--- Stichting ZO! Systeem Terminal Gestart ---\nApp versie 1.3.5\n\n"
        self.terminal_widget = None
        self.original_stdout = sys.stdout
        self.original_stderr = sys.stderr

    def write(self, text):
        self.log_text += text
        self.original_stdout.write(text)
        
        if self.terminal_widget and self.terminal_widget.winfo_exists():
            self.terminal_widget.after(0, self._update_widget, text)
            
    def _update_widget(self, text):
        try:
            self.terminal_widget.configure(state="normal")
            self.terminal_widget.insert("end", text)
            self.terminal_widget.see("end")
            self.terminal_widget.configure(state="disabled")
        except:
            pass

    def flush(self):
        self.original_stdout.flush()

sys_logger = OutputRedirector()
sys.stdout = sys_logger
sys.stderr = sys_logger


# === BASIS CONFIGURATIE & FIREBASE ===
try:
    myappid = 'stichtingzo.klantenportaal.1.0' 
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
except Exception:
    pass

ctk.set_appearance_mode("system")

current_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(current_dir, 'ENVStichtingZO.env')
load_dotenv(dotenv_path=env_path)

application_path = sys._MEIPASS if getattr(sys, 'frozen', False) else current_dir

APP_FONT = "Inter"

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
    firebase = pyrebase.initialize_app(firebase_config)
    auth = firebase.auth()
    db = firebase.database() 
    print("Database succesvol verbonden!")
except Exception as e:
    auth = None
    db = None
    print(f"Firebase initialisatie fout: {e}")

class Colors:
    accent = "#00A98F"      
    secondary = "#95C93D"   
    bg_main = ("#F4F6F8", "#0F111A")  
    bg_card = ("#FFFFFF", "#1E2233")  
    bg_sidebar = ("#FFFFFF", "#161925") 
    text_main = ("#1F2937", "#FFFFFF") 
    text_grey = ("#6B7280", "#8B949E") 
    border = ("#D1D5DB", "#2D334B")


# === HULPFUNCTIES & KLEINE WIDGETS ===
def versnel_scroll_snelheid(scroll_frame, multiplier=2):
    try:
        scroll_frame._scrollbar.grid_forget()
        scroll_frame._scrollbar.configure(width=0)
        
        canvas = scroll_frame._parent_canvas
        original_yview = canvas.yview
        def nieuwe_yview(*args):
            if len(args) == 3 and args[0] == 'scroll' and args[2] == 'units':
                try:
                    original_yview('scroll', int(args[1]) * multiplier, 'units')
                except:
                    original_yview(*args)
            else:
                original_yview(*args)
        canvas.yview = nieuwe_yview
    except Exception:
        pass

class CircularProgressbar(ctk.CTkCanvas):
    def __init__(self, parent, width=50, height=50, color=Colors.accent, bg_color=Colors.bg_main):
        mode = ctk.get_appearance_mode()
        bg = bg_color[1] if mode == "Dark" else bg_color[0]
        super().__init__(parent, width=width, height=height, bg=bg, highlightthickness=0)
        self.color = color
        self.angle = 0
        self.is_running = False
        self.arc = self.create_arc(5, 5, width-5, height-5, start=0, extent=100, outline=self.color, width=4, style="arc")

    def start(self):
        self.is_running = True
        self._animate()

    def stop(self):
        self.is_running = False

    def _animate(self):
        if not self.is_running:
            return
        self.angle = (self.angle - 15) % 360
        self.itemconfig(self.arc, start=self.angle)
        self.after(25, self._animate)


# === POPUP: DATUM KIEZER ===
class ModernDatePicker(ctk.CTkToplevel):
    def __init__(self, parent, callback_fn, font):
        super().__init__(parent)
        self.callback = callback_fn
        self.font = font
        self.overrideredirect(True) 
        self.configure(fg_color=Colors.bg_card)
        
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - 140
        y = parent.winfo_y() + (parent.winfo_height() // 2) - 175
        self.geometry(f"280x350+{x}+{y}")
        self.grab_set() 
        
        self.current_date = datetime.now()
        self.maanden = ["Januari", "Februari", "Maart", "April", "Mei", "Juni", "Juli", "Augustus", "September", "Oktober", "November", "December"]
        
        self.setup_ui()
        self.render_calendar()

    def setup_ui(self):
        self.border_frame = ctk.CTkFrame(self, fg_color=Colors.bg_card, border_width=2, border_color=Colors.accent, corner_radius=10)
        self.border_frame.pack(fill="both", expand=True)

        self.header = ctk.CTkFrame(self.border_frame, fg_color=Colors.bg_card)
        self.header.pack(fill="x", pady=(15, 5), padx=15)
        
        ctk.CTkButton(self.header, text="<", width=30, fg_color=Colors.bg_main, text_color=Colors.text_main, hover_color=Colors.border, command=self.prev_month).pack(side="left")
        self.lbl_month = ctk.CTkLabel(self.header, text="", font=(self.font, 14, "bold"), text_color=Colors.text_main)
        self.lbl_month.pack(side="left", expand=True)
        ctk.CTkButton(self.header, text=">", width=30, fg_color=Colors.bg_main, text_color=Colors.text_main, hover_color=Colors.border, command=self.next_month).pack(side="right")
        
        self.grid_frame = ctk.CTkFrame(self.border_frame, fg_color=Colors.bg_card)
        self.grid_frame.pack(fill="both", expand=True, padx=15, pady=0)
        
        dagen = ["Ma", "Di", "Wo", "Do", "Vr", "Za", "Zo"]
        for i, dag in enumerate(dagen):
            ctk.CTkLabel(self.grid_frame, text=dag, font=(self.font, 12, "bold"), text_color=Colors.text_grey).grid(row=0, column=i, padx=5, pady=5)

        btn_annuleer = ctk.CTkButton(self.border_frame, text="Annuleren", font=(self.font, 13), height=35, fg_color=Colors.bg_card, text_color=Colors.text_grey, hover_color=Colors.bg_main, command=self.destroy)
        btn_annuleer.pack(pady=(5, 15))

    def prev_month(self):
        m = self.current_date.month - 1
        y = self.current_date.year
        if m == 0: 
            m = 12
            y -= 1
        self.current_date = self.current_date.replace(month=m, year=y)
        self.render_calendar()

    def next_month(self):
        m = self.current_date.month + 1
        y = self.current_date.year
        if m == 13: 
            m = 1
            y += 1
        self.current_date = self.current_date.replace(month=m, year=y)
        self.render_calendar()

    def render_calendar(self):
        for widget in self.grid_frame.winfo_children():
            if int(widget.grid_info()["row"]) > 0: 
                widget.destroy()
            
        self.lbl_month.configure(text=f"{self.maanden[self.current_date.month-1]} {self.current_date.year}")
        
        cal = calendar.monthcalendar(self.current_date.year, self.current_date.month)
        today = datetime.now()
        
        for row_idx, week in enumerate(cal, start=1):
            for col_idx, day in enumerate(week):
                if day != 0:
                    btn = ctk.CTkButton(self.grid_frame, text=str(day), width=32, height=32, fg_color=Colors.bg_card, text_color=Colors.text_main, hover_color=Colors.border, command=lambda d=day: self.select_date(d))
                    btn.grid(row=row_idx, column=col_idx, padx=2, pady=2)
                    
                    if day == today.day and self.current_date.month == today.month and self.current_date.year == today.year:
                        btn.configure(fg_color=Colors.accent, text_color="white", hover_color=Colors.accent)

    def select_date(self, day):
        formatted_date = f"{day:02d}-{self.current_date.month:02d}-{self.current_date.year}"
        self.callback(formatted_date)
        self.destroy()


# === POPUP: TOAST MELDING ===
class ToastNotification(ctk.CTkToplevel):
    def __init__(self, parent, boodschap, soort="success"):
        super().__init__(parent)
        self.overrideredirect(True) 
        self.attributes("-topmost", True) 

        trans_color = "#000001"
        self.configure(fg_color=trans_color)
        try:
            self.attributes("-transparentcolor", trans_color)
        except:
            pass

        if soort == "success":
            txt_kleur = "#22C55E"
        elif soort == "error":
            txt_kleur = "#EF4444"
        else:
            txt_kleur = Colors.accent

        self.frame = ctk.CTkFrame(self, fg_color=Colors.bg_card, bg_color=trans_color, corner_radius=10, border_width=1, border_color=Colors.border)
        self.frame.pack(fill="both", expand=True)

        lbl = ctk.CTkLabel(self.frame, text=boodschap, font=(APP_FONT, 12, "bold"), text_color=txt_kleur)
        lbl.pack(padx=20, pady=2)

        self.update_idletasks()
        w = self.winfo_reqwidth()
        h = self.winfo_reqheight()

        x = parent.winfo_x() + parent.winfo_width() - w - 260
        y = parent.winfo_y() + parent.winfo_height() - h - 50
        self.geometry(f"{w}x{h}+{x}+{y}")

        self.after(3000, self.destroy)
        

# === POPUP: BEVESTIGING DIALOOG ===
class BevestigingPopup(ctk.CTkToplevel):
    def __init__(self, parent, titel, bericht, confirm_callback):
        super().__init__(parent)
        self.title(titel)
        self.geometry("400x200")
        self.configure(fg_color=Colors.bg_card)
        self.overrideredirect(True) 

        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - 200
        y = parent.winfo_y() + (parent.winfo_height() // 2) - 100
        self.geometry(f"+{x}+{y}")
        
        self.attributes("-topmost", True)
        self.grab_set() 

        self.border_frame = ctk.CTkFrame(self, fg_color=Colors.bg_card, border_width=2, border_color=Colors.border, corner_radius=10)
        self.border_frame.pack(fill="both", expand=True)

        lbl_titel = ctk.CTkLabel(self.border_frame, text=titel, font=(APP_FONT, 18, "bold"), text_color=Colors.text_main)
        lbl_titel.pack(pady=(20, 10))

        lbl_bericht = ctk.CTkLabel(self.border_frame, text=bericht, font=(APP_FONT, 14), text_color=Colors.text_grey, wraplength=350)
        lbl_bericht.pack(pady=(0, 20))

        btn_frame = ctk.CTkFrame(self.border_frame, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=10)

        def on_cancel():
            self.grab_release()
            self.destroy()

        btn_cancel = ctk.CTkButton(btn_frame, text="Annuleren", fg_color=Colors.bg_main, text_color=Colors.text_main, hover_color=Colors.border, command=on_cancel)
        btn_cancel.pack(side="left", expand=True, padx=10)

        def on_confirm():
            self.grab_release()     
            self.withdraw()         
            self.update_idletasks() 
            confirm_callback()      
            self.after(100, self.destroy) 

        btn_confirm = ctk.CTkButton(btn_frame, text="Verwijderen", fg_color="#EF4444", text_color="white", hover_color="#DC2626", command=on_confirm)
        btn_confirm.pack(side="right", expand=True, padx=10)


# === POPUP: TERMINAL WIDGET ===
class TerminalPopup(ctk.CTkToplevel):
    def __init__(self, parent, font):
        super().__init__(parent)
        self.title("Systeem Terminal")
        self.geometry("750x500")
        self.configure(fg_color=Colors.bg_main)
        self.overrideredirect(True) 

        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - 375
        y = parent.winfo_y() + (parent.winfo_height() // 2) - 250
        self.geometry(f"+{x}+{y}")
        self.grab_set()

        drag_bar = ctk.CTkFrame(self, height=40, corner_radius=0, fg_color=Colors.bg_main)
        drag_bar.pack(fill="x", padx=10, pady=(5, 0))
        drag_bar.bind("<ButtonPress-1>", self.start_move)
        drag_bar.bind("<B1-Motion>", self.do_move)
        
        lbl_titel = ctk.CTkLabel(drag_bar, text="Systeem Terminal (Logs & Errors)", font=(font, 14, "bold"), text_color=Colors.text_main)
        lbl_titel.place(relx=0.02, rely=0.5, anchor="w")

        close_btn = ctk.CTkButton(drag_bar, text="✕", width=30, height=30, corner_radius=10, fg_color=Colors.bg_main, text_color=Colors.text_grey, hover_color=("#E5E5E5", "#E81123"), font=(font, 14, "bold"), command=self.sluiten)
        close_btn.place(relx=1.0, rely=0.5, anchor="e", x=-5)

        self.textbox = ctk.CTkTextbox(self, fg_color="#0F111A", text_color="#00FF41", font=("Consolas", 13), border_width=1, border_color=Colors.border, corner_radius=8)
        self.textbox.pack(fill="both", expand=True, padx=20, pady=(10, 20))
        
        self.textbox.insert("1.0", sys_logger.log_text)
        self.textbox.configure(state="disabled")
        self.textbox.see("end")

        sys_logger.terminal_widget = self.textbox

    def sluiten(self):
        sys_logger.terminal_widget = None
        self.destroy()

    def start_move(self, event):
        self._start_x, self._start_y = event.x_root, event.y_root
        self._win_x, self._win_y = self.winfo_x(), self.winfo_y()

    def do_move(self, event):
        self.geometry(f"+{self._win_x + (event.x_root - self._start_x)}+{self._win_y + (event.y_root - self._start_y)}")


# === POPUP: INZENDING DETAILS ===
class ResultaatPopup(ctk.CTkToplevel):
    def __init__(self, parent, kandidaat, font, oude_vragenlijst_fallback):
        super().__init__(parent)
        self.title("Resultaat Details")
        self.geometry("650x750")
        self.configure(fg_color=Colors.bg_main)
        
        self.overrideredirect(True)

        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - 325
        y = parent.winfo_y() + (parent.winfo_height() // 2) - 375
        self.geometry(f"+{x}+{y}")
        self.grab_set() 

        drag_bar = ctk.CTkFrame(self, height=40, corner_radius=0, fg_color=Colors.bg_main)
        drag_bar.pack(fill="x", padx=10, pady=(5, 0))
        drag_bar.bind("<ButtonPress-1>", self.start_move)
        drag_bar.bind("<B1-Motion>", self.do_move)
        
        close_btn = ctk.CTkButton(drag_bar, text="✕", width=30, height=30, corner_radius=10, fg_color=Colors.bg_main, text_color=Colors.text_grey, hover_color=("#E5E5E5", "#E81123"), font=(font, 14, "bold"), command=self.destroy)
        close_btn.place(relx=1.0, rely=0.5, anchor="e", x=-5)

        scroll = ctk.CTkScrollableFrame(self, fg_color=Colors.bg_main)
        scroll.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        versnel_scroll_snelheid(scroll) 

        header = ctk.CTkFrame(scroll, fg_color=Colors.bg_card, corner_radius=10, border_width=1, border_color=Colors.border)
        header.pack(fill="x", pady=(0, 15))
        
        ctk.CTkLabel(header, text=kandidaat.get("naam", "Onbekend"), font=(font, 22, "bold"), text_color=Colors.text_main).pack(anchor="w", padx=20, pady=(20, 5))
        
        info_text = f"📅 Datum: {kandidaat.get('datum', '-')}  |  👤 Leeftijd: {kandidaat.get('leeftijd', '-')}  |  ⚧ Geslacht: {kandidaat.get('geslacht', '-')}"
        ctk.CTkLabel(header, text=info_text, font=(font, 14), text_color=Colors.text_grey).pack(anchor="w", padx=20, pady=(0, 5))
        
        tmpl_text = f"Vragenlijst: {kandidaat.get('template_titel', 'Standaard Vragenlijst')}"
        ctk.CTkLabel(header, text=tmpl_text, font=(font, 12, "italic"), text_color=Colors.accent).pack(anchor="w", padx=20, pady=(0, 20))

        vragen_card = ctk.CTkFrame(scroll, fg_color=Colors.bg_card, corner_radius=10, border_width=1, border_color=Colors.border)
        vragen_card.pack(fill="x", pady=10)
        
        ctk.CTkLabel(vragen_card, text="Ingevulde Antwoorden", font=(font, 16, "bold"), text_color=Colors.text_main).pack(anchor="w", padx=20, pady=(15, 10))
        
        antwoorden = kandidaat.get("antwoorden", [])
        for i, antwoord_data in enumerate(antwoorden):
            if isinstance(antwoord_data, dict):
                vraag_tekst = antwoord_data.get("vraag", f"Vraag {i+1}")
                antwoord = antwoord_data.get("antwoord", "Geen antwoord")
            else:
                vraag_tekst = oude_vragenlijst_fallback[i]["vraag"] if i < len(oude_vragenlijst_fallback) else f"Vraag {i+1}"
                antwoord = str(antwoord_data)
            
            q_frame = ctk.CTkFrame(vragen_card, fg_color=Colors.bg_card)
            q_frame.pack(fill="x", padx=20, pady=5)
            ctk.CTkLabel(q_frame, text=f"{i+1}. {vraag_tekst}", font=(font, 13), text_color=Colors.text_grey, wraplength=550, justify="left").pack(anchor="w")
            ctk.CTkLabel(q_frame, text=antwoord, font=(font, 14, "bold"), text_color=Colors.text_main, wraplength=550, justify="left").pack(anchor="w", pady=(0, 10))

        opmerking = kandidaat.get("opmerking", "").strip()
        if opmerking:
            opm_card = ctk.CTkFrame(scroll, fg_color=Colors.bg_card, corner_radius=10, border_width=1, border_color=Colors.border)
            opm_card.pack(fill="x", pady=10)
            ctk.CTkLabel(opm_card, text="Extra Opmerkingen / Ideeën", font=(font, 16, "bold"), text_color=Colors.text_main).pack(anchor="w", padx=20, pady=(15, 5))
            ctk.CTkLabel(opm_card, text=opmerking, font=(font, 14), text_color=Colors.text_main, wraplength=550, justify="left").pack(anchor="w", padx=20, pady=(0, 20))

        ctk.CTkButton(scroll, text="Sluiten", font=(font, 14, "bold"), fg_color=Colors.bg_sidebar, border_width=1, border_color=Colors.border, text_color=Colors.text_main, hover_color=Colors.border, command=self.destroy).pack(pady=20)

    def start_move(self, event):
        self._start_x, self._start_y = event.x_root, event.y_root
        self._win_x, self._win_y = self.winfo_x(), self.winfo_y()

    def do_move(self, event):
        self.geometry(f"+{self._win_x + (event.x_root - self._start_x)}+{self._win_y + (event.y_root - self._start_y)}")


# === HOOFDAPPLICATIE SCHERM ===
class StichtingZOPortal(ctk.CTk):
    
    # === INITIALISATIE ===
    def __init__(self):
        super().__init__()
        
        self.report_callback_exception = self.handle_tk_exception

        self.w, self.h = 1150, 750 
        self.font = APP_FONT  
        
        self.dropdown_kwargs = {
            "state": "readonly",
            "fg_color": Colors.bg_main,
            "border_color": Colors.border,
            "button_color": Colors.accent,
            "button_hover_color": "#008F7A",
            "dropdown_fg_color": ("#E2E5EA", "#13151E"), 
            "dropdown_hover_color": Colors.accent,
            "dropdown_text_color": Colors.text_main,
            "text_color": Colors.text_main,
            "font": (self.font, 13)
        }
        
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
        
        self.opgeslagen_data = []
        self.opgeslagen_templates = []
        self.huidige_template = None
        self.huidig_te_bewerken_template = None
        self.huidige_dashboard_filter = "Alle Vragenlijsten"
        
        self.web_domein = "https://stichtingzoforms.netlify.app"

        self.overrideredirect(True)
        self.attributes("-transparentcolor", "#000001")
        self.configure(fg_color="#000001")
        
        try:
            png_path = os.path.join(application_path, "logo_stichtingzo_rgb.png")
            ico_path = os.path.join(application_path, "logo_stichtingzo_icon.ico")
            
            if os.path.exists(png_path):
                if not os.path.exists(ico_path):
                    img = Image.open(png_path).convert("RGBA")
                    target_size = 256
                    aspect_ratio = img.width / img.height
                    if img.width > img.height:
                        new_w, new_h = target_size, int(target_size / aspect_ratio)
                    else:
                        new_h, new_w = target_size, int(target_size * aspect_ratio)
                        
                    try:
                        resample_filter = Image.Resampling.LANCZOS
                    except AttributeError:
                        resample_filter = Image.LANCZOS
                        
                    img_resized = img.resize((new_w, new_h), resample_filter)
                    square_img = Image.new("RGBA", (target_size, target_size), (0, 0, 0, 0))
                    square_img.paste(img_resized, ((target_size - new_w) // 2, (target_size - new_h) // 2), img_resized)
                    square_img.save(ico_path, format="ICO", sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
                
                self.iconbitmap(ico_path)
        except Exception:
            pass

        self.withdraw()
        self._set_initial_position()
        self._load_all_assets()

        self.main_container = ctk.CTkFrame(self, corner_radius=0, border_width=0, fg_color=Colors.bg_main)
        self.main_container.pack(fill="both", expand=True)

        self.start_splash()
        self.update()
        self.show_in_taskbar()

    def handle_tk_exception(self, exc, val, tb):
        err_msg = str(val)
        if "bad window path name" in err_msg or "invalid command name" in err_msg:
            return 
        print("Exception in Tkinter callback", file=sys.stderr)
        traceback.print_exception(exc, val, tb, file=sys.stderr)

    def toon_melding(self, boodschap, soort="success"):
        if hasattr(self, "huidige_toast") and self.huidige_toast.winfo_exists():
            self.huidige_toast.destroy()
        
        self.huidige_toast = ToastNotification(self, boodschap, soort)

    def apply_focus_highlight(self, widget):
        def focus_in(event=None):
            if widget.winfo_exists():
                try: widget.configure(border_color=Colors.accent)
                except: pass
            
        def focus_out(event=None):
            if widget.winfo_exists():
                try: widget.configure(border_color=Colors.border)
                except: pass
            
        if hasattr(widget, "_entry"):
            widget._entry.bind("<FocusIn>", lambda e: self.after(10, focus_in), add="+")
            widget._entry.bind("<FocusOut>", lambda e: self.after(10, focus_out), add="+")
        elif hasattr(widget, "_textbox"):
            widget._textbox.bind("<FocusIn>", lambda e: self.after(10, focus_in), add="+")
            widget._textbox.bind("<FocusOut>", lambda e: self.after(10, focus_out), add="+")

    def _set_initial_position(self):
        self.geometry(f"{self.w}x{self.h}")

    def _load_image(self, filename, size, light_filename=None):
        try:
            full_path = os.path.join(application_path, filename)
            if not os.path.exists(full_path): return None
            if light_filename:
                light_path = os.path.join(application_path, light_filename)
                return ctk.CTkImage(light_image=Image.open(light_path), dark_image=Image.open(full_path), size=size)
            return ctk.CTkImage(Image.open(full_path), size=size)
        except Exception: return None

    def _load_all_assets(self):
        self.logo_img = self._load_image("logo_stichtingzo_rgb.png", (150, 70), "logo_stichtingzo_rgb.png")
        self.splash_logo_img = self._load_image("logo_stichtingzo_rgb.png", (300, 140))


    # === VENSTER BEHEER ===
    def start_move(self, event):
        self._start_x, self._start_y = event.x_root, event.y_root
        self._win_x, self._win_y = self.winfo_x(), self.winfo_y()

    def do_move(self, event):
        self.geometry(f"+{self._win_x + (event.x_root - self._start_x)}+{self._win_y + (event.y_root - self._start_y)}")

    def stop_move(self, event):
        pass 

    def minimize_app(self):
        try:
            hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
            ctypes.windll.user32.ShowWindow(hwnd, 6) 
        except:
            self.iconify()

    def toggle_maximize(self):
        if not getattr(self, 'is_maximized', False):
            self.normal_geom = self.geometry()
            try:
                self.state('zoomed')
            except:
                pass 
            self.is_maximized = True
        else:
            try:
                self.state('normal')
            except:
                pass
            self.geometry(getattr(self, 'normal_geom', f"{self.w}x{self.h}"))
            self.is_maximized = False

    def create_drag_bar(self, parent_frame, add_close_btn=False, bg_col=Colors.bg_main):
        drag_bar = ctk.CTkFrame(parent_frame, height=30, corner_radius=0, fg_color=bg_col)
        drag_bar.place(relx=0, rely=0, relwidth=1)
        drag_bar.bind("<ButtonPress-1>", self.start_move)
        drag_bar.bind("<B1-Motion>", self.do_move)
        drag_bar.bind("<ButtonRelease-1>", self.stop_move)
        drag_bar.bind("<Double-1>", lambda e: self.toggle_maximize())
        
        if add_close_btn:
            ctk.CTkButton(drag_bar, text="—", width=35, height=30, corner_radius=8, fg_color=bg_col, text_color=Colors.text_grey, hover_color=("#E5E5E5", "#333333"), command=self.minimize_app).place(relx=1.0, rely=0.5, anchor="e", x=-95)
            ctk.CTkButton(drag_bar, text="◻", width=35, height=30, corner_radius=8, fg_color=bg_col, text_color=Colors.text_grey, hover_color=("#E5E5E5", "#333333"), font=(self.font, 15), command=self.toggle_maximize).place(relx=1.0, rely=0.5, anchor="e", x=-55)
            ctk.CTkButton(drag_bar, text="✕", width=35, height=30, corner_radius=8, fg_color=bg_col, text_color=Colors.text_grey, hover_color=("#E5E5E5", "#E81123"), command=self.close_app).place(relx=1.0, rely=0.5, anchor="e", x=-15)
        return drag_bar

    def close_app(self):
        self.withdraw() 
        import os
        os._exit(0)      

    def show_in_taskbar(self):
        self.update_idletasks() 
        GWL_EXSTYLE = -20; WS_EX_APPWINDOW = 0x00040000
        hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
        style = ctypes.windll.user32.GetWindowLongPtrW(hwnd, GWL_EXSTYLE)
        ctypes.windll.user32.SetWindowLongPtrW(hwnd, GWL_EXSTYLE, style | WS_EX_APPWINDOW)
        self.withdraw()
        
        def forceer_midden():
            self.deiconify() 
            self.update()    
            
            screen_w = self.winfo_screenwidth()
            screen_h = self.winfo_screenheight()
            
            x = int((screen_w / 2) - (self.w / 2))
            y = int((screen_h / 2) - (self.h / 2))
            
            self.geometry(f"{self.w}x{self.h}+{x}+{y}")
            
        self.after(10, forceer_midden)

    def start_splash(self):
        self.splash_frame = ctk.CTkFrame(self.main_container, corner_radius=0, fg_color=Colors.bg_main)
        self.splash_frame.place(relx=0, rely=0, relwidth=1, relheight=1)
        
        if self.splash_logo_img:
            self.splash_logo_lbl = ctk.CTkLabel(self.splash_frame, text="", image=self.splash_logo_img)
            self.splash_motto = ctk.CTkLabel(self.splash_frame, text="ZO! maakt samen leven in Zuidplas mooier!", font=(self.font, 15, "italic"), text_color=Colors.text_grey)
            
            self.splash_spinner = CircularProgressbar(self.splash_frame, width=40, height=40, color=Colors.accent, bg_color=Colors.bg_main)
            
            huidig_jaar = datetime.now().year
            self.splash_footer = ctk.CTkLabel(self.splash_frame, text=f"Versie 1.3.5  |  © {huidig_jaar} Stichting ZO!", font=(self.font, 11), text_color=Colors.text_grey)

            self.after(400, lambda: self.splash_logo_lbl.place(relx=0.5, rely=0.42, anchor="center"))
            self.after(400, lambda: self.splash_motto.place(relx=0.5, rely=0.55, anchor="center"))
            
            def show_extras():
                self.splash_spinner.place(relx=0.5, rely=0.65, anchor="center")
                self.splash_spinner.start()
                self.splash_footer.place(relx=0.5, rely=0.95, anchor="center")
                
            self.after(800, show_extras)
            self.after(3000, self.end_splash)
        else:
            self.after(10, self.end_splash)

    def end_splash(self):
        if hasattr(self, 'splash_spinner'):
            self.splash_spinner.stop()
        self.splash_frame.destroy()
        self.build_ui_layout() 


    # === DATABASE FUNCTIES ===
    def haal_data_op_uit_database(self):
        try:
            if db:
                db_data = db.child("vragenlijsten").get()
                self.opgeslagen_data = []
                if db_data.val(): 
                    for item in db_data.each():
                        data = item.val()
                        data['fb_key'] = item.key()
                        self.opgeslagen_data.append(data)
        except Exception as e:
            print(f"Kan data niet ophalen: {e}")

    def haal_templates_op_uit_database(self):
        try:
            if db:
                db_data = db.child("templates").get()
                self.opgeslagen_templates = []
                if db_data.val():
                    for item in db_data.each():
                        data = item.val()
                        data['fb_key'] = item.key()
                        self.opgeslagen_templates.append(data)
        except Exception as e:
            print(f"Kan templates niet ophalen: {e}")


    # === HOOFD LAYOUT & NAVIGATIE ===
    def build_ui_layout(self):
        for widget in self.main_container.winfo_children(): widget.destroy()

        self.sidebar = ctk.CTkFrame(self.main_container, width=250, corner_radius=0, fg_color=Colors.bg_sidebar)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        if self.logo_img: ctk.CTkLabel(self.sidebar, text="", image=self.logo_img).pack(pady=(40, 0))
        
        ctk.CTkLabel(self.sidebar, text="ZO! maakt samen leven\nin Zuidplas mooier!", font=(self.font, 11, "italic"), text_color=Colors.text_grey).pack(pady=(5, 20), padx=20) 
        ctk.CTkLabel(self.sidebar, text="BEHOEFTEPEILING", font=(self.font, 12, "bold"), text_color=Colors.text_grey).pack(anchor="w", padx=20, pady=(10, 5))

        btn_cfg = {"anchor": "w", "height": 40, "font": (self.font, 14, "bold"), "hover_color": ("#F0F2F5", "#2B2B2B")}
        
        self.btn_tab_vragenlijsten = ctk.CTkButton(self.sidebar, text="Vragenlijsten", fg_color=Colors.bg_sidebar, text_color=Colors.text_main, command=self.show_tab_vragenlijsten, **btn_cfg)
        self.btn_tab_vragenlijsten.pack(fill="x", padx=15, pady=5)
        
        self.btn_tab_ontwerpen = ctk.CTkButton(self.sidebar, text="Nieuwe Vragenlijst", fg_color=Colors.bg_sidebar, text_color=Colors.text_main, command=self.show_tab_ontwerpen, **btn_cfg)
        self.btn_tab_ontwerpen.pack(fill="x", padx=15, pady=5)
        
        self.btn_tab_inzendingen = ctk.CTkButton(self.sidebar, text="Inzendingen", fg_color=Colors.bg_sidebar, text_color=Colors.text_main, command=self.show_tab_inzendingen, **btn_cfg)
        self.btn_tab_inzendingen.pack(fill="x", padx=15, pady=5)
        
        self.btn_tab_dashboard = ctk.CTkButton(self.sidebar, text="Data Dashboard", fg_color=Colors.bg_sidebar, text_color=Colors.text_main, command=self.show_tab_dashboard, **btn_cfg)
        self.btn_tab_dashboard.pack(fill="x", padx=15, pady=5)

        self.btn_tab_instellingen = ctk.CTkButton(self.sidebar, text="Instellingen", fg_color=Colors.bg_sidebar, text_color=Colors.text_main, command=self.show_tab_instellingen, **btn_cfg)
        self.btn_tab_instellingen.pack(side="bottom", fill="x", padx=15, pady=20)

        self.content_area = ctk.CTkFrame(self.main_container, fg_color=Colors.bg_main, corner_radius=0)
        self.content_area.pack(side="right", fill="both", expand=True)

        self.content_area.columnconfigure(0, weight=1)
        self.content_area.rowconfigure(0, weight=0) 
        self.content_area.rowconfigure(1, weight=1) 

        self.topbar = ctk.CTkFrame(self.content_area, fg_color="transparent")
        self.topbar.grid(row=0, column=0, sticky="ew", padx=35, pady=(30, 5)) 
        
        self.topbar_title = ctk.CTkLabel(self.topbar, text="", font=(self.font, 26, "bold"), text_color=Colors.text_main)
        self.topbar_title.pack(side="left")
        
        self.topbar_action = ctk.CTkFrame(self.topbar, fg_color="transparent")
        self.topbar_action.pack(side="right")

        self.view_frame = ctk.CTkFrame(self.content_area, fg_color="transparent")
        self.view_frame.grid(row=1, column=0, sticky="nsew")

        self.frames = {}
        for naam in ["loading", "vragenlijsten", "ontwerpen", "inzendingen", "dashboard", "instellingen"]:
            self.frames[naam] = ctk.CTkFrame(self.view_frame, fg_color="transparent")
            
        self.is_built = {"vragenlijsten": False, "ontwerpen": False, "inzendingen": False, "dashboard": False, "instellingen": False}
        self.needs_refresh = {"inzendingen": True, "dashboard": True, "vragenlijsten": True}

        self.drag_bar_links = self.create_drag_bar(self.sidebar, bg_col=Colors.bg_sidebar)
        self.drag_bar_rechts = self.create_drag_bar(self.content_area, add_close_btn=True, bg_col=Colors.bg_main)
        
        self.show_tab_vragenlijsten()

    def _highlight_button(self, active_button):
        for btn in [self.btn_tab_vragenlijsten, self.btn_tab_ontwerpen, self.btn_tab_inzendingen, self.btn_tab_dashboard, self.btn_tab_instellingen]:
            btn.configure(fg_color=Colors.accent, text_color="white") if btn == active_button else btn.configure(fg_color=Colors.bg_sidebar, text_color=Colors.text_main)

    def _switch_to(self, target_name):
        self.focus_set() 
        for w in self.topbar_action.winfo_children(): 
            w.destroy()
            
        for name, frame in self.frames.items():
            if name == target_name:
                frame.pack(fill="both", expand=True)
            else:
                frame.pack_forget()
                
        if target_name == "dashboard" and self.is_built["dashboard"]:
            btn_export = ctk.CTkButton(self.topbar_action, text="📥 Exporteer Data (.CSV)", font=(self.font, 12, "bold"), fg_color=Colors.bg_sidebar, text_color=Colors.text_main, border_width=1, border_color=Colors.border, hover_color=Colors.border, command=self.exporteer_naar_csv)
            btn_export.pack(side="right", pady=(5,0))

        if hasattr(self, 'topbar'): self.topbar.lift()
        if hasattr(self, 'drag_bar_rechts'): self.drag_bar_rechts.lift()
        if hasattr(self, 'drag_bar_links'): self.drag_bar_links.lift()

    def _show_loading_and_build(self, target_name, build_func, message="Laden..."):
        self.focus_set() 
        if getattr(self, '_is_loading', False) and getattr(self, '_current_target', '') == target_name:
            return 
            
        self._is_loading = True
        self._current_target = target_name
        
        self._switch_to("loading")
        
        if hasattr(self, 'huidige_spinner') and self.huidige_spinner:
            self.huidige_spinner.stop()
            
        for w in self.frames["loading"].winfo_children(): 
            w.destroy()
            
        self.huidige_spinner = CircularProgressbar(self.frames["loading"], width=45, height=45, color=Colors.accent, bg_color=Colors.bg_main)
        self.huidige_spinner.place(relx=0.5, rely=0.45, anchor="center")
        self.huidige_spinner.start()
        
        lbl = ctk.CTkLabel(self.frames["loading"], text=message, font=(self.font, 16, "bold"), text_color=Colors.text_grey)
        lbl.place(relx=0.5, rely=0.53, anchor="center")
        
        if hasattr(self, '_build_task') and self._build_task is not None:
            self.after_cancel(self._build_task)
            
        self._build_task = self.after(100, lambda: self._execute_build(target_name, build_func))

    def _execute_build(self, target_name, build_func):
        self.update()
        build_func()
        
        self.is_built[target_name] = True
        self._switch_to(target_name)
        
        self._is_loading = False
        
        if hasattr(self, 'huidige_spinner') and self.huidige_spinner:
            self.huidige_spinner.stop()

    def bereken_invultijd(self, vragen):
        seconden = 10 
        for v in vragen:
            q_type = v.get("type", "")
            if q_type == "Open Vraag":
                seconden += 40
            elif q_type in ["Meerkeuze (Checkboxes)", "Keuze (Radiobuttons)"]:
                seconden += 20
            else:
                seconden += 15
        
        minuten = max(1, round(seconden / 60))
        return f"~{minuten} min"


    # === TAB NAVIGATIE ===
    def show_tab_vragenlijsten(self):
        self._highlight_button(self.btn_tab_vragenlijsten)
        self.topbar_title.configure(text="Vragenlijsten")
        if self.needs_refresh["vragenlijsten"] or not self.is_built["vragenlijsten"]:
            self._show_loading_and_build("vragenlijsten", self._build_template_kies_scherm, "Laden...")
            self.needs_refresh["vragenlijsten"] = False
        else:
            self._switch_to("vragenlijsten")

    def show_tab_ontwerpen(self):
        self._highlight_button(self.btn_tab_ontwerpen)
        self.huidig_te_bewerken_template = None 
        self.topbar_title.configure(text="Nieuwe Vragenlijst Ontwerpen")
        self._show_loading_and_build("ontwerpen", self._build_vragenlijst_maken_ui, "Laden...")

    def _open_template_editor(self, template):
        self.huidig_te_bewerken_template = template
        self.topbar_title.configure(text="Vragenlijst Bewerken")
        self._highlight_button(self.btn_tab_ontwerpen)
        self._show_loading_and_build("ontwerpen", self._build_vragenlijst_maken_ui, "Laden...")

    def show_tab_inzendingen(self):
        self._highlight_button(self.btn_tab_inzendingen)
        self.topbar_title.configure(text="Inzendingen")
        if self.needs_refresh["inzendingen"] or not self.is_built["inzendingen"]:
            self._show_loading_and_build("inzendingen", self._build_opgeslagen_vragenlijsten, "Laden...")
            self.needs_refresh["inzendingen"] = False
        else:
            self._switch_to("inzendingen")

    def show_tab_dashboard(self):
        self._highlight_button(self.btn_tab_dashboard)
        self.topbar_title.configure(text="Data Dashboard")
        if self.needs_refresh["dashboard"] or not self.is_built["dashboard"]:
            self._show_loading_and_build("dashboard", self._build_dashboard, "Grafieken berekenen...")
            self.needs_refresh["dashboard"] = False
        else:
            self._switch_to("dashboard")

    def show_tab_instellingen(self):
        self._highlight_button(self.btn_tab_instellingen)
        self.topbar_title.configure(text="Instellingen")
        if not self.is_built["instellingen"]:
            self._show_loading_and_build("instellingen", self._build_settings, "Laden...")
        else:
            self._switch_to("instellingen")


    # === VRAAG VERPLAATSEN HULP ===
    def verplaats_vraag_invoer(self, card_widget, richting):
        self.focus_set()

        huidige_index = -1
        for i, item in enumerate(self.dynamische_vragen_widgets):
            if item["card"] == card_widget:
                huidige_index = i
                break

        if huidige_index == -1: return

        nieuwe_index = huidige_index + richting
        
        if nieuwe_index < 0 or nieuwe_index >= len(self.dynamische_vragen_widgets):
            return 

        self.dynamische_vragen_widgets[huidige_index], self.dynamische_vragen_widgets[nieuwe_index] = \
            self.dynamische_vragen_widgets[nieuwe_index], self.dynamische_vragen_widgets[huidige_index]

        for item in self.dynamische_vragen_widgets:
            item["card"].pack_forget()

        for i, item in enumerate(self.dynamische_vragen_widgets, 1):
            item["card"].pack(fill="x", pady=5)
            item["label"].configure(text=f"Vraag {i}")


    # === TAB: ONTWERPEN / BEWERKEN ===
    def _build_vragenlijst_maken_ui(self):
        self.focus_set() 
        for w in self.frames["ontwerpen"].winfo_children(): w.destroy()

        scroll_area = ctk.CTkScrollableFrame(self.frames["ontwerpen"], fg_color="transparent") 
        scroll_area.pack(fill="both", expand=True, padx=30, pady=(5, 15))
        versnel_scroll_snelheid(scroll_area)

        if self.huidig_te_bewerken_template:
            nav_bar = ctk.CTkFrame(scroll_area, fg_color="transparent")
            nav_bar.pack(fill="x", pady=(0, 10))
            ctk.CTkButton(nav_bar, text="← Terug naar overzicht", fg_color=Colors.bg_sidebar, text_color=Colors.text_main, border_width=1, border_color=Colors.border, hover_color=Colors.border, command=self.show_tab_vragenlijsten).pack(side="left")

        titel_card = ctk.CTkFrame(scroll_area, fg_color=Colors.bg_card, corner_radius=10, border_width=1, border_color=Colors.border)
        titel_card.pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(titel_card, text="1. Naam van de Vragenlijst", font=(self.font, 16, "bold"), text_color=Colors.text_main).pack(anchor="w", padx=20, pady=(15, 5))
        self.entry_template_titel = ctk.CTkEntry(titel_card, placeholder_text="Bijv: Behoeftepeiling Zomeractiviteiten...", height=40)
        self.entry_template_titel.pack(fill="x", padx=20, pady=(0, 10))
        self.apply_focus_highlight(self.entry_template_titel)

        ctk.CTkLabel(titel_card, text="Korte beschrijving (optioneel):", font=(self.font, 12), text_color=Colors.text_grey).pack(anchor="w", padx=20, pady=(0, 5))
        self.entry_template_beschrijving = ctk.CTkTextbox(titel_card, height=60, fg_color=Colors.bg_main, border_width=1, border_color=Colors.border, text_color=Colors.text_main, font=(self.font, 13))
        self.entry_template_beschrijving.pack(fill="x", padx=20, pady=(0, 20))
        self.apply_focus_highlight(self.entry_template_beschrijving)

        self.vragen_container = ctk.CTkFrame(scroll_area, fg_color="transparent")
        self.vragen_container.pack(fill="x", pady=0)
        
        self.dynamische_vragen_widgets = []

        bottom_frame = ctk.CTkFrame(scroll_area, fg_color="transparent")
        bottom_frame.pack(fill="x", pady=20)
        
        ctk.CTkButton(bottom_frame, text="+ Vraag Toevoegen", font=(self.font, 14, "bold"), fg_color=Colors.bg_sidebar, text_color=Colors.text_main, border_width=1, border_color=Colors.border, hover_color=Colors.border, height=45, command=lambda: self.voeg_vraag_invoer_toe()).pack(side="left")
        
        ctk.CTkButton(bottom_frame, text="Vragenlijst Opslaan", font=(self.font, 14, "bold"), fg_color=Colors.accent, text_color="white", height=45, command=self.sla_template_op).pack(side="right")

        if self.huidig_te_bewerken_template:
            self.entry_template_titel.insert(0, self.huidig_te_bewerken_template.get('titel', ''))
            beschrijving = self.huidig_te_bewerken_template.get('beschrijving', '')
            if beschrijving:
                self.entry_template_beschrijving.insert("1.0", beschrijving)
                
            for v in self.huidig_te_bewerken_template.get('vragen', []):
                opties_data = v.get('opties', [])
                type_str = v.get('type', 'Dropdown') 
                afb_data = v.get('afbeeldingen', [])
                self.voeg_vraag_invoer_toe(v.get('vraag', ''), opties_data, type_str, afb_data)
        else:
            self.voeg_vraag_invoer_toe()

    def voeg_vraag_invoer_toe(self, def_vraag="", def_opties=None, def_type="Dropdown", def_afbeeldingen=None):
        is_new = False
        if def_opties is None: 
            def_opties = ["", ""] 
            is_new = True
        elif isinstance(def_opties, str): 
            def_opties = [o.strip() for o in def_opties.split(",")]

        vraag_nummer = len(self.dynamische_vragen_widgets) + 1
        
        q_card = ctk.CTkFrame(self.vragen_container, fg_color=Colors.bg_card, corner_radius=10, border_width=1, border_color=Colors.border)
        q_card.pack(fill="x", pady=5)
        
        header_frame = ctk.CTkFrame(q_card, fg_color="transparent")
        header_frame.pack(fill="x", padx=20, pady=(15, 5))
        
        lbl_titel = ctk.CTkLabel(header_frame, text=f"Vraag {vraag_nummer}", font=(self.font, 14, "bold"), text_color=Colors.text_main)
        lbl_titel.pack(side="left")
        
        btn_del_q = ctk.CTkButton(header_frame, text="✕ Verwijder", width=30, fg_color="transparent", text_color="#EF4444", hover_color=("#FFCDD2", "#4A1C1C"), command=lambda: self.verwijder_vraag_invoer(q_card))
        btn_del_q.pack(side="right")

        btn_down = ctk.CTkButton(header_frame, text="⬇ Omlaag", width=30, fg_color="transparent", text_color=Colors.text_grey, hover_color=Colors.border, command=lambda: self.verplaats_vraag_invoer(q_card, 1))
        btn_down.pack(side="right", padx=(0, 5))

        btn_up = ctk.CTkButton(header_frame, text="⬆ Omhoog", width=30, fg_color="transparent", text_color=Colors.text_grey, hover_color=Colors.border, command=lambda: self.verplaats_vraag_invoer(q_card, -1))
        btn_up.pack(side="right", padx=(0, 5))

        type_frame = ctk.CTkFrame(q_card, fg_color="transparent")
        type_frame.pack(fill="x", padx=20, pady=(0, 10))
        ctk.CTkLabel(type_frame, text="Vraagtype:", font=(self.font, 12), text_color=Colors.text_grey).pack(side="left", padx=(0,10))
        
        type_var = ctk.StringVar(value=def_type)
        
        opties_frame = ctk.CTkFrame(q_card, fg_color="transparent") 
        opties_lijst_container = ctk.CTkFrame(opties_frame, fg_color="transparent")
        opties_lijst_container.pack(fill="x", pady=(5, 5))
        
        optie_entries = [] 

        def voeg_optie_invoer_toe(val=""):
            row = ctk.CTkFrame(opties_lijst_container, fg_color="transparent")
            row.pack(fill="x", pady=2)
            idx = len(optie_entries) + 1
            e = ctk.CTkEntry(row, height=30, placeholder_text=f"Optie {idx}")
            e.pack(side="left", fill="x", expand=True, padx=(0, 5))
            self.apply_focus_highlight(e)
            
            if val and val != f"Optie {idx}": 
                if is_new and val.startswith("Optie "):
                    pass 
                else:
                    e.insert(0, val)
            optie_entries.append(e)

            def wis_rij():
                self.focus_set() 
                def safe_destroy():
                    try:
                        if e in optie_entries: optie_entries.remove(e)
                        e.destroy()
                        btn_del_opt.destroy()
                        row.destroy()
                    except: pass
                self.after(50, safe_destroy)

            btn_del_opt = ctk.CTkButton(row, text="✕", width=30, fg_color="transparent", text_color="#EF4444", hover_color=("#FFCDD2", "#4A1C1C"), command=wis_rij)
            btn_del_opt.pack(side="right")

        for o in def_opties:
            voeg_optie_invoer_toe(o)

        btn_add_optie = ctk.CTkButton(opties_frame, text="+ Antwoord toevoegen", font=(self.font, 12, "bold"), fg_color=Colors.accent, text_color="white", border_width=1, border_color=Colors.border, hover_color=Colors.border, command=voeg_optie_invoer_toe)
        btn_add_optie.pack(anchor="w", pady=(5, 10))

        def update_visibility(val):
            if val in ["Open Vraag", "Slider (1-10)"]:
                opties_frame.pack_forget()
            else:
                opties_frame.pack(fill="x", padx=20, pady=(0, 20))
                
        type_menu = ctk.CTkComboBox(type_frame, variable=type_var, values=["Dropdown", "Keuze (Radiobuttons)", "Meerkeuze (Checkboxes)", "Open Vraag", "Slider (1-10)"], width=200, command=update_visibility, **self.dropdown_kwargs)
        type_menu.pack(side="left")
        
        entry_vraag = ctk.CTkEntry(q_card, placeholder_text="Typ hier de vraag...", height=35)
        entry_vraag.pack(fill="x", padx=20, pady=(0, 10))
        self.apply_focus_highlight(entry_vraag)
        if def_vraag: entry_vraag.insert(0, def_vraag)

        afbeelding_container = ctk.CTkFrame(q_card, fg_color="transparent")
        afbeelding_container.pack(fill="x", padx=20, pady=(0, 10))

        btn_img = ctk.CTkButton(afbeelding_container, text="🖼 + Afbeelding(en) toevoegen", font=(self.font, 12, "bold"), fg_color=Colors.accent, text_color="white", border_width=1, border_color=Colors.border, hover_color=Colors.border, command=lambda: voeg_afbeelding_toe())
        btn_img.pack(anchor="w", pady=(0, 0))

        afbeeldingen_lijst = list(def_afbeeldingen) if def_afbeeldingen else []
        caption_entries = [] 
        img_preview_frame = ctk.CTkFrame(afbeelding_container, fg_color="transparent")

        def bewaar_captions():
            for i, entry in enumerate(caption_entries):
                if i < len(afbeeldingen_lijst):
                    if isinstance(afbeeldingen_lijst[i], dict):
                        afbeeldingen_lijst[i]["caption"] = entry.get().strip()
                    else:
                        afbeeldingen_lijst[i] = {"data": afbeeldingen_lijst[i], "caption": entry.get().strip()}

        def render_previews():
            for w in img_preview_frame.winfo_children(): w.destroy()
            caption_entries.clear() 
            
            if len(afbeeldingen_lijst) == 0:
                img_preview_frame.pack_forget()
            else:
                img_preview_frame.pack(fill="x", pady=(10, 0))
                for idx, img_info in enumerate(afbeeldingen_lijst):
                    try:
                        if isinstance(img_info, dict):
                            b64_data = img_info.get("data", "")
                            caption = img_info.get("caption", "")
                        else:
                            b64_data = img_info
                            caption = ""

                        img_data = base64.b64decode(b64_data)
                        img = Image.open(BytesIO(img_data))
                        img.thumbnail((70, 70))
                        ctk_img = ctk.CTkImage(img, size=(img.width, img.height))
                        
                        f = ctk.CTkFrame(img_preview_frame, fg_color="transparent")
                        f.pack(side="left", padx=(0, 10))
                        ctk.CTkLabel(f, text="", image=ctk_img).pack()
                        
                        entry_cap = ctk.CTkEntry(f, width=80, height=24, font=(self.font, 11), placeholder_text=f"Afb {idx+1}", fg_color=Colors.bg_main, border_color=Colors.border)
                        entry_cap.pack(pady=(5, 2))
                        if caption: entry_cap.insert(0, caption)
                        caption_entries.append(entry_cap)
                        self.apply_focus_highlight(entry_cap)

                        ctk.CTkButton(f, text="✕", width=25, height=25, font=(self.font, 10), fg_color="#EF4444", hover_color="#DC2626", command=lambda i=idx: wis_img(i)).pack(pady=(2,0))
                    except Exception: pass

        def wis_img(index):
            self.focus_set()
            bewaar_captions() 
            afbeeldingen_lijst.pop(index)
            render_previews()

        def voeg_afbeelding_toe():
            bewaar_captions() 
            filepaths = filedialog.askopenfilenames(filetypes=[("Afbeeldingen", "*.png;*.jpg;*.jpeg")])
            for path in filepaths:
                try:
                    img = Image.open(path)
                    if img.mode in ('RGBA', 'P'):
                        background = Image.new('RGB', img.size, (255, 255, 255))
                        background.paste(img, mask=img.split()[3] if img.mode == 'RGBA' else None)
                        img = background
                    img.thumbnail((600, 600)) 
                    buffer = BytesIO()
                    img.save(buffer, format="JPEG", quality=75)
                    b64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
                    
                    afbeeldingen_lijst.append({"data": b64, "caption": ""})
                except Exception as e:
                    print(f"Fout bij laden afbeelding: {e}")
            render_previews()

        render_previews() 
        update_visibility(def_type)
        
        self.dynamische_vragen_widgets.append({
            "card": q_card,
            "label": lbl_titel,
            "type_var": type_var,
            "vraag": entry_vraag,
            "opties_lijst": optie_entries,
            "afbeeldingen": afbeeldingen_lijst,
            "bewaar_afb_captions": bewaar_captions 
        })

    def verwijder_vraag_invoer(self, card_widget):
        self.focus_set() 
        def safe_destroy():
            try:
                for item in self.dynamische_vragen_widgets:
                    if item["card"] == card_widget:
                        self.dynamische_vragen_widgets.remove(item)
                        card_widget.destroy()
                        break
                        
                for i, item in enumerate(self.dynamische_vragen_widgets, 1):
                    item["label"].configure(text=f"Vraag {i}")
            except: pass
        self.after(50, safe_destroy)

    def sla_template_op(self):
        titel = self.entry_template_titel.get().strip()
        beschrijving = self.entry_template_beschrijving.get("1.0", "end-1c").strip()
        
        if not titel:
            self.toon_melding("× Vul a.u.b. een titel in.", "error")
            return

        opgeslagen_vragen = []
        for widget_dict in self.dynamische_vragen_widgets:
            if "bewaar_afb_captions" in widget_dict:
                widget_dict["bewaar_afb_captions"]()

            vraag_tekst = widget_dict["vraag"].get().strip()
            type_val = widget_dict["type_var"].get()
            
            if not vraag_tekst: continue 
            
            opties_lijst = []
            if type_val in ["Dropdown", "Keuze (Radiobuttons)", "Meerkeuze (Checkboxes)"]:
                for opt_entry in widget_dict["opties_lijst"]:
                    val = opt_entry.get().strip()
                    if val: opties_lijst.append(val)

            opgeslagen_vragen.append({
                "vraag": vraag_tekst,
                "type": type_val,
                "opties": opties_lijst,
                "afbeeldingen": widget_dict["afbeeldingen"]
            })

        if len(opgeslagen_vragen) == 0:
            self.toon_melding("× Voeg minimaal 1 geldige vraag toe.", "error")
            return

        nieuwe_template = {
            "titel": titel,
            "beschrijving": beschrijving,
            "vragen": opgeslagen_vragen,
            "aangemaakt_op": datetime.now().strftime("%d-%m-%Y %H:%M")
        }

        try:
            if db:
                if self.huidig_te_bewerken_template and 'fb_key' in self.huidig_te_bewerken_template:
                    fb_key = self.huidig_te_bewerken_template['fb_key']
                    nieuwe_template['aangemaakt_op'] = self.huidig_te_bewerken_template.get('aangemaakt_op', nieuwe_template['aangemaakt_op'])
                    db.child("templates").child(fb_key).update(nieuwe_template)
                    self.toon_melding("✓ Vragenlijst succesvol bijgewerkt!", "success")
                else:
                    db.child("templates").push(nieuwe_template)
                    self.toon_melding("✓ Vragenlijst succesvol opgeslagen!", "success")
                    self.entry_template_titel.delete(0, 'end')
                    self.entry_template_beschrijving.delete("1.0", "end")
                    self.focus_set() 
                    for w in self.vragen_container.winfo_children(): w.destroy()
                    self.dynamische_vragen_widgets.clear()
                    self.voeg_vraag_invoer_toe()
                
                self.needs_refresh["vragenlijsten"] = True 
                self.needs_refresh["dashboard"] = True
                self.needs_refresh["inzendingen"] = True
            else:
                self.toon_melding("× Geen database verbinding.", "error")
        except Exception as e:
            self.toon_melding(f"× Opslaan mislukt: {e}", "error")


    # === TAB: OVERZICHT VRAGENLIJSTEN ===
    def _build_template_kies_scherm(self):
        self.haal_templates_op_uit_database()
        self.focus_set() 
        for w in self.frames["vragenlijsten"].winfo_children(): w.destroy()
        
        scroll_area = ctk.CTkScrollableFrame(self.frames["vragenlijsten"], fg_color="transparent") 
        scroll_area.pack(fill="both", expand=True, padx=30, pady=(5, 15))
        versnel_scroll_snelheid(scroll_area)

        ctk.CTkLabel(scroll_area, text="Kies een Vragenlijst", font=(self.font, 20, "bold"), text_color=Colors.text_main).pack(anchor="w", pady=(0, 20))

        if len(self.opgeslagen_templates) == 0:
            ctk.CTkLabel(scroll_area, text="Er zijn nog geen vragenlijsten gemaakt.\nGa naar 'Nieuwe Vragenlijst' om er eentje te ontwerpen.", font=(self.font, 14), text_color=Colors.text_grey, justify="left").pack(anchor="w", pady=20)
            return

        for tmpl in reversed(self.opgeslagen_templates):
            card = ctk.CTkFrame(scroll_area, fg_color=Colors.bg_card, corner_radius=10, border_width=1, border_color=Colors.border)
            card.pack(fill="x", pady=5)
            
            btn_frame = ctk.CTkFrame(card, fg_color=Colors.bg_card)
            btn_frame.pack(side="right", padx=15)
            
            def kopieer_link(key):
                link = f"{self.web_domein}/?id={key}"
                self.clipboard_clear()
                self.clipboard_append(link)
                self.update()
                self.toon_melding("🔗 Link gekopieerd naar klembord!", "info")
                
            ctk.CTkButton(btn_frame, text="🔗 Link", fg_color=Colors.bg_sidebar, text_color=Colors.accent, border_width=1, border_color=Colors.accent, hover_color=Colors.bg_main, width=90, command=lambda k=tmpl.get('fb_key'): kopieer_link(k)).pack(side="left", padx=(0, 5))
            ctk.CTkButton(btn_frame, text="🗑 Verwijderen", fg_color=Colors.bg_card, text_color="#EF4444", hover_color=("#FFCDD2", "#4A1C1C"), width=100, command=lambda k=tmpl.get('fb_key'), t=tmpl.get('titel', 'Deze vragenlijst'): self.bevestig_verwijder_template(k, t)).pack(side="left", padx=(0, 5))
            ctk.CTkButton(btn_frame, text="Bewerken", fg_color=Colors.bg_sidebar, text_color=Colors.text_main, border_width=1, border_color=Colors.border, hover_color=Colors.border, width=100, command=lambda t=tmpl: self._open_template_editor(t)).pack(side="left", padx=(0, 5))
            ctk.CTkButton(btn_frame, text="Invullen", fg_color=Colors.accent, text_color="white", font=(self.font, 13, "bold"), width=100, command=lambda t=tmpl: self._build_formulier(t)).pack(side="left", padx=(0, 0))

            info = ctk.CTkFrame(card, fg_color=Colors.bg_card)
            info.pack(side="left", fill="x", expand=True, padx=20, pady=15)
            
            ctk.CTkLabel(info, text=tmpl.get("titel", "Zonder titel"), font=(self.font, 16, "bold"), text_color=Colors.text_main).pack(anchor="w")
            
            beschrijving = tmpl.get("beschrijving", "").strip()
            if beschrijving:
                nette_beschrijving = textwrap.fill(beschrijving, width=75)
                ctk.CTkLabel(info, text=nette_beschrijving, font=(self.font, 12, "italic"), text_color=Colors.text_main, justify="left").pack(anchor="w", pady=(0, 2))
            
            aantal = len(tmpl.get('vragen', []))
            invultijd = self.bereken_invultijd(tmpl.get('vragen', []))
            
            ctk.CTkLabel(info, text=f"Aantal vragen: {aantal} | ⏱️ {invultijd} | Aangemaakt: {tmpl.get('aangemaakt_op', '-')}", font=(self.font, 12), text_color=Colors.text_grey).pack(anchor="w")

    def bevestig_verwijder_template(self, firebase_key, titel):
        def voer_verwijderen_uit():
            self.verwijder_template(firebase_key)
        BevestigingPopup(self, "Vragenlijst Verwijderen", f"Weet je zeker dat je '{titel}' wilt verwijderen?\nDit kan niet ongedaan worden gemaakt.", voer_verwijderen_uit)

    def verwijder_template(self, firebase_key):
        if db:
            try:
                db.child("templates").child(firebase_key).remove()
                self.toon_melding("🗑 Vragenlijst succesvol verwijderd.", "info")
                self.needs_refresh["vragenlijsten"] = True
                self.needs_refresh["dashboard"] = True
                self.needs_refresh["inzendingen"] = True
                self.show_tab_vragenlijsten() 
            except Exception as e:
                self.toon_melding(f"× Verwijderen mislukt: {e}", "error")


    # === TAB: INVULLEN FORMULIER ===
    def _build_formulier(self, template):
        self.huidige_template = template
        self.focus_set() 
        for w in self.frames["vragenlijsten"].winfo_children(): w.destroy()
        
        scroll_area = ctk.CTkScrollableFrame(self.frames["vragenlijsten"], fg_color="transparent") 
        scroll_area.pack(fill="both", expand=True, padx=30, pady=(5, 15))
        versnel_scroll_snelheid(scroll_area)

        nav_bar = ctk.CTkFrame(scroll_area, fg_color="transparent")
        nav_bar.pack(fill="x", pady=(0, 10))
        ctk.CTkButton(nav_bar, text="← Terug naar overzicht", fg_color=Colors.bg_sidebar, text_color=Colors.text_main, border_width=1, border_color=Colors.border, hover_color=Colors.border, command=self._build_template_kies_scherm).pack(side="left")

        beschrijving = template.get("beschrijving", "").strip()
        header_card = ctk.CTkFrame(scroll_area, fg_color=Colors.bg_card, corner_radius=10, border_width=1, border_color=Colors.border)
        header_card.pack(fill="x", pady=(0, 10))
        
        ctk.CTkLabel(header_card, text=template.get('titel', 'Onbekende Vragenlijst'), font=(self.font, 22, "bold"), text_color=Colors.accent).pack(anchor="w", padx=20, pady=(15, 5 if beschrijving else 15))
        
        if beschrijving:
            ctk.CTkLabel(header_card, text=beschrijving, font=(self.font, 14), text_color=Colors.text_main, justify="left", wraplength=900).pack(anchor="w", padx=20, pady=(0, 20))

        info_card = ctk.CTkFrame(scroll_area, fg_color=Colors.bg_card, corner_radius=10, border_width=1, border_color=Colors.border)
        info_card.pack(fill="x", pady=10)
        ctk.CTkLabel(info_card, text="Informatie Respondent", font=(self.font, 16, "bold"), text_color=Colors.text_main).pack(anchor="w", padx=20, pady=(15, 10))
        
        row1_frame = ctk.CTkFrame(info_card, fg_color=Colors.bg_card)
        row1_frame.pack(fill="x", padx=20, pady=(0, 15))
        
        naam_frame = ctk.CTkFrame(row1_frame, fg_color=Colors.bg_card)
        naam_frame.pack(side="left", padx=(0, 15))
        ctk.CTkLabel(naam_frame, text="Voornaam (of Alias)", font=(self.font, 12), text_color=Colors.text_grey).pack(anchor="w", pady=(0, 2))
        self.entry_naam = ctk.CTkEntry(naam_frame, placeholder_text="Vul voornaam in", height=35, width=200)
        self.entry_naam.pack()
        self.apply_focus_highlight(self.entry_naam)

        geslacht_frame = ctk.CTkFrame(row1_frame, fg_color=Colors.bg_card)
        geslacht_frame.pack(side="left", padx=(0, 15))
        ctk.CTkLabel(geslacht_frame, text="Geslacht", font=(self.font, 12), text_color=Colors.text_grey).pack(anchor="w", pady=(0, 2))
        self.menu_geslacht = ctk.CTkComboBox(geslacht_frame, values=["Man", "Vrouw", "Zeg ik liever niet"], height=35, width=150, **self.dropdown_kwargs)
        self.menu_geslacht.pack()
        self.menu_geslacht.set("Man")

        leeftijd_frame = ctk.CTkFrame(row1_frame, fg_color=Colors.bg_card)
        leeftijd_frame.pack(side="left")
        ctk.CTkLabel(leeftijd_frame, text="Leeftijd", font=(self.font, 12), text_color=Colors.text_grey).pack(anchor="w", pady=(0, 2))
        leeftijden = [str(i) for i in range(12, 28)] + ["> 27"]
        self.menu_leeftijd = ctk.CTkComboBox(leeftijd_frame, values=leeftijden, height=35, width=80, **self.dropdown_kwargs)
        self.menu_leeftijd.pack()
        self.menu_leeftijd.set("12")

        row2_frame = ctk.CTkFrame(info_card, fg_color=Colors.bg_card)
        row2_frame.pack(fill="x", padx=20, pady=(0, 20))
        
        datum_frame = ctk.CTkFrame(row2_frame, fg_color=Colors.bg_card)
        datum_frame.pack(side="left")
        ctk.CTkLabel(datum_frame, text="Datum van afname", font=(self.font, 12), text_color=Colors.text_grey).pack(anchor="w", pady=(0, 2))
        
        self.geselecteerde_datum = datetime.now().strftime("%d-%m-%Y")
        self.btn_datum = ctk.CTkButton(datum_frame, text=f"📅 {self.geselecteerde_datum}", height=35, width=150, font=(self.font, 13), fg_color=Colors.bg_sidebar, border_color=Colors.border, border_width=1, text_color=Colors.text_main, hover_color=Colors.border, anchor="w", command=self.open_datepicker)
        self.btn_datum.pack()

        vragen_card = ctk.CTkFrame(scroll_area, fg_color=Colors.bg_card, corner_radius=10, border_width=1, border_color=Colors.border)
        vragen_card.pack(fill="x", pady=10)
        ctk.CTkLabel(vragen_card, text="Vragenlijst Vragen", font=(self.font, 16, "bold"), text_color=Colors.text_main).pack(anchor="w", padx=20, pady=(15, 10))

        self.vraag_widgets = [] 
        
        for i, vraag_data in enumerate(template.get("vragen", []), 1):
            q_frame = ctk.CTkFrame(vragen_card, fg_color=Colors.bg_card)
            q_frame.pack(fill="x", padx=20, pady=10)
            ctk.CTkLabel(q_frame, text=f"{i}. {vraag_data['vraag']}", font=(self.font, 14), text_color=Colors.text_main).pack(anchor="w")
            
            afbeeldingen = vraag_data.get("afbeeldingen", [])
            if afbeeldingen:
                img_container = ctk.CTkFrame(q_frame, fg_color="transparent")
                img_container.pack(fill="x", pady=(10, 10))
                for idx, img_info in enumerate(afbeeldingen):
                    try:
                        if isinstance(img_info, dict):
                            b64_data = img_info.get("data", "")
                            caption = img_info.get("caption", "") or f"Afbeelding {idx+1}"
                        else:
                            b64_data = img_info
                            caption = f"Afbeelding {idx+1}"

                        img_data = base64.b64decode(b64_data)
                        img = Image.open(BytesIO(img_data))
                        img.thumbnail((250, 250))
                        ctk_img = ctk.CTkImage(img, size=(img.width, img.height))
                        
                        item = ctk.CTkFrame(img_container, fg_color="transparent")
                        item.pack(side="left", padx=(0, 15))
                        ctk.CTkLabel(item, text="", image=ctk_img).pack()
                        ctk.CTkLabel(item, text=caption, font=(self.font, 11, "italic"), text_color=Colors.text_grey).pack(pady=(5,0))
                    except:
                        pass

            q_type = vraag_data.get("type", "Dropdown")
            get_waarde_functie = None

            if q_type == "Open Vraag":
                entry = ctk.CTkTextbox(q_frame, height=80, fg_color=Colors.bg_main, border_width=1, border_color=Colors.border, text_color=Colors.text_main)
                entry.pack(fill="x", pady=(5, 10))
                self.apply_focus_highlight(entry)
                get_waarde_functie = lambda e=entry: e.get("1.0", "end-1c").strip()

            elif q_type == "Slider (1-10)":
                num_frame = ctk.CTkFrame(q_frame, fg_color="transparent")
                num_frame.pack(fill="x", padx=10, pady=(10, 0))

                num_labels = []
                for j in range(1, 11):
                    lbl = ctk.CTkLabel(num_frame, text=str(j), font=(self.font, 12, "bold"), text_color=Colors.text_grey)
                    lbl.pack(side="left", expand=True)
                    num_labels.append(lbl)

                slider = ctk.CTkSlider(q_frame, from_=1, to=10, number_of_steps=9, button_color=Colors.accent, progress_color=Colors.accent)
                slider.pack(fill="x", padx=15, pady=(5, 15))
                slider.set(5)
                
                def update_slider_ui(val, lbls=num_labels):
                    v = int(val)
                    for idx, l in enumerate(lbls):
                        if idx + 1 == v:
                            l.configure(text_color=Colors.accent, font=(self.font, 16, "bold"))
                        else:
                            l.configure(text_color=Colors.text_grey, font=(self.font, 12, "bold"))
                            
                slider.configure(command=update_slider_ui)
                update_slider_ui(5) 
                
                get_waarde_functie = lambda s=slider: str(int(s.get()))

            elif q_type == "Meerkeuze (Checkboxes)":
                entry_anders = ctk.CTkEntry(q_frame, placeholder_text="Typ hier je antwoord...", width=300, height=35)
                self.apply_focus_highlight(entry_anders)
                checkboxes = []
                
                def on_cb_change(e=entry_anders, cbs=checkboxes):
                    toon_anders = any("anders" in v.get().lower() for v in cbs if v.get())
                    if toon_anders:
                        e.pack(anchor="w", pady=(5, 10))
                    else:
                        e.pack_forget()

                for optie in vraag_data.get('opties', []):
                    var = ctk.StringVar(value="")
                    cb = ctk.CTkCheckBox(q_frame, text=optie, variable=var, onvalue=optie, offvalue="", fg_color=Colors.accent, hover_color=Colors.secondary, command=on_cb_change)
                    cb.pack(anchor="w", pady=(5, 0))
                    checkboxes.append(var)
                
                ctk.CTkFrame(q_frame, fg_color="transparent", height=5).pack()

                def get_checkbox_vals(cbs=checkboxes, e_anders=entry_anders):
                    vals = [v.get() for v in cbs if v.get()]
                    if not vals: return "Niets geselecteerd"
                    final_vals = []
                    for val in vals:
                        if "anders" in val.lower():
                            eigen_tekst = e_anders.get().strip()
                            final_vals.append(f"{val}: {eigen_tekst}" if eigen_tekst else f"{val}: (Niets ingevuld)")
                        else:
                            final_vals.append(val)
                    return ", ".join(final_vals)
                    
                get_waarde_functie = get_checkbox_vals

            elif q_type == "Keuze (Radiobuttons)":
                entry_anders = ctk.CTkEntry(q_frame, placeholder_text="Typ hier je antwoord...", width=300, height=35)
                self.apply_focus_highlight(entry_anders)
                radio_var = ctk.StringVar(value="")
                
                def on_radio_change(e=entry_anders, r_var=radio_var):
                    if "anders" in r_var.get().lower():
                        e.pack(anchor="w", pady=(5, 10))
                    else:
                        e.pack_forget()

                for optie in vraag_data.get('opties', []):
                    rb = ctk.CTkRadioButton(q_frame, text=optie, variable=radio_var, value=optie, fg_color=Colors.accent, hover_color=Colors.secondary, command=on_radio_change)
                    rb.pack(anchor="w", pady=(5, 0))
                
                ctk.CTkFrame(q_frame, fg_color="transparent", height=5).pack()
                
                def get_radio_val(r_var=radio_var, e_anders=entry_anders):
                    val = r_var.get()
                    if not val: return "Niets geselecteerd"
                    if "anders" in val.lower():
                        eigen_tekst = e_anders.get().strip()
                        return f"{val}: {eigen_tekst}" if eigen_tekst else f"{val}: (Niets ingevuld)"
                    return val
                
                get_waarde_functie = get_radio_val

            else: 
                entry_anders = ctk.CTkEntry(q_frame, placeholder_text="Typ hier je antwoord...", width=300, height=35)
                self.apply_focus_highlight(entry_anders)
                menu_var = ctk.StringVar()
                
                def on_change(waarde, e=entry_anders):
                    if "anders" in waarde.lower():
                        e.pack(anchor="w", pady=(5, 10)) 
                    else:
                        e.pack_forget() 

                menu = ctk.CTkComboBox(q_frame, values=vraag_data.get('opties', []), variable=menu_var, width=300, command=on_change, **self.dropdown_kwargs)
                menu.pack(anchor="w", pady=(5, 10))
                
                if len(vraag_data.get('opties', [])) > 0:
                    menu.set(vraag_data['opties'][0]) 

                def get_dropdown_val(m_var=menu_var, e_anders=entry_anders):
                    val = m_var.get()
                    if "anders" in val.lower():
                        eigen_tekst = e_anders.get().strip()
                        return f"{val}: {eigen_tekst}" if eigen_tekst else f"{val}: (Niets ingevuld)"
                    return val
                get_waarde_functie = get_dropdown_val

            self.vraag_widgets.append({
                "vraag_tekst": vraag_data['vraag'],
                "get_waarde_functie": get_waarde_functie
            })

        opm_card = ctk.CTkFrame(scroll_area, fg_color=Colors.bg_card, corner_radius=10, border_width=1, border_color=Colors.border)
        opm_card.pack(fill="x", pady=10)
        ctk.CTkLabel(opm_card, text="Extra Opmerkingen / Ideeën", font=(self.font, 16, "bold"), text_color=Colors.text_main).pack(anchor="w", padx=20, pady=(15, 5))
        ctk.CTkLabel(opm_card, text="Wat mis je nog of wat wil je graag aan ons kwijt?", font=(self.font, 12), text_color=Colors.text_grey).pack(anchor="w", padx=20, pady=(0, 10))
        
        self.entry_opmerking = ctk.CTkTextbox(opm_card, height=100, fg_color=Colors.bg_main, border_width=1, border_color=Colors.border, text_color=Colors.text_main, font=(self.font, 13))
        self.entry_opmerking.pack(fill="x", padx=20, pady=(0, 20))
        self.apply_focus_highlight(self.entry_opmerking)

        bottom_frame = ctk.CTkFrame(scroll_area, fg_color="transparent")
        bottom_frame.pack(fill="x", pady=20)

        btn_save = ctk.CTkButton(bottom_frame, text="Opslaan & Verzenden", font=(self.font, 14, "bold"), fg_color=Colors.accent, text_color="white", height=45, command=self.sla_vragenlijst_op)
        btn_save.pack(side="right")

    def open_datepicker(self):
        def set_date(date_str):
            self.geselecteerde_datum = date_str
            self.btn_datum.configure(text=f"📅 {date_str}")
        ModernDatePicker(self, set_date, self.font)

    def sla_vragenlijst_op(self):
        naam = self.entry_naam.get().strip()
        leeftijd = self.menu_leeftijd.get()
        geslacht = self.menu_geslacht.get()
        datum = self.geselecteerde_datum
        opmerking = self.entry_opmerking.get("1.0", "end-1c").strip()
        
        if not naam:
            self.toon_melding("× Vul a.u.b. de voornaam in.", "error")
            return

        gekozen_antwoorden = []
        for widget_dict in self.vraag_widgets:
            vraag_tekst = widget_dict["vraag_tekst"]
            antwoord_waarde = widget_dict["get_waarde_functie"]() 
                
            gekozen_antwoorden.append({
                "vraag": vraag_tekst,
                "antwoord": antwoord_waarde
            })
        
        nieuwe_invoer = {
            "template_id": self.huidige_template.get("fb_key", ""),
            "template_titel": self.huidige_template.get("titel", "Onbekende Vragenlijst"),
            "naam": naam,
            "leeftijd": leeftijd,
            "geslacht": geslacht,
            "datum": datum,
            "opmerking": opmerking,
            "antwoorden": gekozen_antwoorden 
        }

        try:
            if db:
                db.child("vragenlijsten").push(nieuwe_invoer)
                self.toon_melding("✓ Vragenlijst succesvol verzonden!", "success")
                self.needs_refresh["inzendingen"] = True
                self.needs_refresh["dashboard"] = True
                self.show_tab_vragenlijsten() 
            else:
                self.toon_melding("× Geen database verbinding.", "error")
        except Exception as e:
            self.toon_melding(f"× Opslaan mislukt: {e}", "error")


    # === TAB: INZENDINGEN OVERZICHT ===
    def _build_opgeslagen_vragenlijsten(self):
        self.haal_data_op_uit_database() 
        self.haal_templates_op_uit_database() 
        self.focus_set() 
        for w in self.frames["inzendingen"].winfo_children(): w.destroy()

        unieke_titels = set(t.get("titel") for t in self.opgeslagen_templates if t.get("titel"))
        filter_opties = ["Alle Vragenlijsten"] + sorted(list(unieke_titels))

        top_controls = ctk.CTkFrame(self.frames["inzendingen"], fg_color="transparent")
        top_controls.pack(fill="x", padx=35, pady=(0, 10))
        
        self.entry_zoek = ctk.CTkEntry(top_controls, placeholder_text="Zoek op voornaam...", height=35, width=250)
        self.entry_zoek.pack(side="left")
        self.apply_focus_highlight(self.entry_zoek)
        
        self.menu_filter = ctk.CTkComboBox(top_controls, values=filter_opties, height=35, width=250, command=self._filter_inzendingen_lijst, **self.dropdown_kwargs)
        self.menu_filter.pack(side="left", padx=10)
        self.menu_filter.set("Alle Vragenlijsten")
        
        ctk.CTkButton(top_controls, text="Zoeken / Filteren", fg_color=Colors.bg_sidebar, border_width=1, border_color=Colors.border, text_color=Colors.text_main, hover_color=Colors.border, width=120, command=self._filter_inzendingen_lijst).pack(side="left", padx=(0, 10))

        self.inzendingen_scroll = ctk.CTkScrollableFrame(self.frames["inzendingen"], fg_color="transparent") 
        self.inzendingen_scroll.pack(fill="both", expand=True, padx=30, pady=(5, 15))
        versnel_scroll_snelheid(self.inzendingen_scroll) 
        
        self._filter_inzendingen_lijst()

    def _filter_inzendingen_lijst(self, *args):
        self.focus_set() 
        for w in self.inzendingen_scroll.winfo_children(): 
            w.destroy()

        zoekterm = self.entry_zoek.get().lower().strip()
        gekozen_filter = self.menu_filter.get()

        gefilterde_data = []
        for kand in self.opgeslagen_data:
            naam = kand.get("naam", "").lower()
            titel = kand.get("template_titel", "Standaard Vragenlijst")
            
            if zoekterm and zoekterm not in naam:
                continue
            if gekozen_filter != "Alle Vragenlijsten" and titel != gekozen_filter:
                continue
            gefilterde_data.append(kand)

        if len(gefilterde_data) == 0:
            ctk.CTkLabel(self.inzendingen_scroll, text="Geen inzendingen gevonden voor deze selectie.", font=(self.font, 14), text_color=Colors.text_grey).pack(pady=40)
            return

        for kandidaat in reversed(gefilterde_data):
            card = ctk.CTkFrame(self.inzendingen_scroll, fg_color=Colors.bg_card, corner_radius=10, border_width=1, border_color=Colors.border)
            card.pack(fill="x", pady=5)
            
            info = ctk.CTkFrame(card, fg_color=Colors.bg_card)
            info.pack(side="left", fill="x", expand=True, padx=20, pady=15)
            
            ctk.CTkLabel(info, text=kandidaat.get("naam", "Onbekend"), font=(self.font, 15, "bold"), text_color=Colors.text_main).pack(anchor="w")
            
            tmpl_titel = kandidaat.get("template_titel", "Standaard Vragenlijst")
            ctk.CTkLabel(info, text=f"Vragenlijst: {tmpl_titel}", font=(self.font, 12, "italic"), text_color=Colors.accent).pack(anchor="w")

            heeft_opmerking = "Ja" if kandidaat.get("opmerking", "").strip() else "Nee"
            ctk.CTkLabel(info, text=f"Datum: {kandidaat.get('datum', '-')} | Leeftijd: {kandidaat.get('leeftijd', '-')} | Extra Opmerking: {heeft_opmerking}", font=(self.font, 12), text_color=Colors.text_grey).pack(anchor="w")

            btn_frame = ctk.CTkFrame(card, fg_color=Colors.bg_card)
            btn_frame.pack(side="right", padx=15)

            ctk.CTkButton(btn_frame, text="🗑 Verwijder", fg_color=Colors.bg_card, text_color="#EF4444", hover_color=("#FFCDD2", "#4A1C1C"), width=100, command=lambda k=kandidaat['fb_key'], n=kandidaat.get('naam', 'Onbekend'): self.bevestig_verwijder_inzending(k, n)).pack(side="left", padx=(0, 5))
            ctk.CTkButton(btn_frame, text="Bekijk Details", fg_color=Colors.bg_sidebar, text_color=Colors.text_main, border_width=1, border_color=Colors.border, hover_color=Colors.border, width=130, command=lambda k=kandidaat: ResultaatPopup(self, k, self.font, self.vragen_fallback)).pack(side="left")

    def bevestig_verwijder_inzending(self, firebase_key, naam):
        def voer_verwijderen_uit():
            self.verwijder_inzending(firebase_key)
        BevestigingPopup(self, "Inzending Verwijderen", f"Weet je zeker dat je de inzending van '{naam}' wilt verwijderen?", voer_verwijderen_uit)

    def verwijder_inzending(self, firebase_key):
        if db:
            try:
                db.child("vragenlijsten").child(firebase_key).remove()
                self.toon_melding("🗑 Inzending succesvol verwijderd.", "info")
                self.needs_refresh["inzendingen"] = True
                self.needs_refresh["dashboard"] = True
                self.show_tab_inzendingen() 
            except Exception as e:
                self.toon_melding(f"× Verwijderen mislukt: {e}", "error")


    # === TAB: DATA DASHBOARD ===
    def _build_dashboard(self):
        self.haal_data_op_uit_database()
        self.haal_templates_op_uit_database()
        self.focus_set() 
        for w in self.frames["dashboard"].winfo_children(): w.destroy()

        unieke_titels = set(t.get("titel") for t in self.opgeslagen_templates if t.get("titel"))
        filter_opties = ["Alle Vragenlijsten"] + sorted(list(unieke_titels))

        top_controls = ctk.CTkFrame(self.frames["dashboard"], fg_color="transparent")
        top_controls.pack(fill="x", padx=35, pady=(0, 10))
        ctk.CTkLabel(top_controls, text="Inzichten voor:", font=(self.font, 14, "bold"), text_color=Colors.text_main).pack(side="left")
        
        self.menu_dashboard_filter = ctk.CTkComboBox(top_controls, values=filter_opties, height=35, width=250, command=self._render_dashboard_content, **self.dropdown_kwargs)
        self.menu_dashboard_filter.pack(side="left", padx=10)
        self.menu_dashboard_filter.set(self.huidige_dashboard_filter if self.huidige_dashboard_filter in filter_opties else "Alle Vragenlijsten")

        self.dashboard_scroll = ctk.CTkScrollableFrame(self.frames["dashboard"], fg_color="transparent") 
        self.dashboard_scroll.pack(fill="both", expand=True, padx=30, pady=(5, 15))
        versnel_scroll_snelheid(self.dashboard_scroll)

        self._render_dashboard_content(self.menu_dashboard_filter.get())

    def _render_dashboard_content(self, filter_val=None):
        if filter_val is None:
            filter_val = self.menu_dashboard_filter.get()
            
        self.huidige_dashboard_filter = filter_val
        
        self.focus_set() 
        for w in self.dashboard_scroll.winfo_children(): 
            w.destroy()

        data_to_show = self.opgeslagen_data if filter_val == "Alle Vragenlijsten" else [k for k in self.opgeslagen_data if k.get("template_titel", "Standaard Vragenlijst") == filter_val]

        totaal_ingevuld = len(data_to_show)
        gemiddelde_leeftijd = 0
        perc_man = 0
        perc_vrouw = 0
        
        if totaal_ingevuld > 0:
            leeftijden = [int(k["leeftijd"]) for k in data_to_show if str(k.get("leeftijd")).isdigit()]
            if leeftijden: gemiddelde_leeftijd = round(sum(leeftijden) / len(leeftijden), 1)
                
            mannen = sum(1 for k in data_to_show if k.get("geslacht") == "Man")
            vrouwen = sum(1 for k in data_to_show if k.get("geslacht") == "Vrouw")
            
            perc_man = int((mannen / totaal_ingevuld) * 100)
            perc_vrouw = int((vrouwen / totaal_ingevuld) * 100)

        stats_frame = ctk.CTkFrame(self.dashboard_scroll, fg_color="transparent")
        stats_frame.pack(fill="x", pady=(0, 20))
        stats_frame.columnconfigure((0, 1, 2), weight=1)

        def create_stat_card(parent, col, title, value, subtitle):
            card = ctk.CTkFrame(parent, fg_color=Colors.bg_card, corner_radius=10, border_width=1, border_color=Colors.border, height=100)
            card.grid(row=0, column=col, sticky="nsew", padx=5)
            card.pack_propagate(False)
            ctk.CTkLabel(card, text=title, font=(self.font, 13), text_color=Colors.text_grey).pack(anchor="w", padx=15, pady=(15, 0))
            ctk.CTkLabel(card, text=str(value), font=(self.font, 28, "bold"), text_color=Colors.text_main).pack(anchor="w", padx=15)
            ctk.CTkLabel(card, text=subtitle, font=(self.font, 11), text_color=Colors.secondary).pack(anchor="w", padx=15)

        create_stat_card(stats_frame, 0, "Totaal Inzendingen", totaal_ingevuld, filter_val)
        create_stat_card(stats_frame, 1, "Gemiddelde Leeftijd", f"{gemiddelde_leeftijd} jaar", "Doelgroep analyse")
        create_stat_card(stats_frame, 2, "Geslachtsverdeling", f"{perc_man}% M / {perc_vrouw}% V", "Op basis van inzendingen")

        chart_card = ctk.CTkFrame(self.dashboard_scroll, fg_color=Colors.bg_card, corner_radius=10, border_width=1, border_color=Colors.border, height=450)
        chart_card.pack(fill="x", padx=5, pady=(0, 20))
        chart_card.pack_propagate(False)
        
        vraag_index_grafiek = 1 
        titel_grafiek_vraag = f"Antwoordverdeling (Vraag {vraag_index_grafiek+1})"
        voorkeuren = []
        details = {}
        
        for k in data_to_show:
            antwoorden = k.get("antwoorden", [])
            if len(antwoorden) > vraag_index_grafiek:
                ans_data = antwoorden[vraag_index_grafiek]
                if isinstance(ans_data, dict):
                    titel_grafiek_vraag = ans_data.get("vraag", titel_grafiek_vraag)
                    ans = ans_data.get("antwoord", "")
                else:
                    ans = str(ans_data)
                
                voorkeuren.append(ans)
                if ans not in details:
                    details[ans] = {'Man': 0, 'Vrouw': 0, 'Leeftijden': []}
                
                geslacht = k.get("geslacht", "")
                if geslacht in ['Man', 'Vrouw']:
                    details[ans][geslacht] += 1
                
                l = str(k.get("leeftijd", ""))
                if l.isdigit():
                    details[ans]['Leeftijden'].append(int(l))
                    
        ctk.CTkLabel(chart_card, text=titel_grafiek_vraag, font=(self.font, 16, "bold"), text_color=Colors.text_main).pack(anchor="w", padx=20, pady=(15, 5))
        
        if totaal_ingevuld == 0 or len(voorkeuren) == 0:
             ctk.CTkLabel(chart_card, text="Nog geen data beschikbaar om een grafiek te tonen.", text_color=Colors.text_grey).pack(pady=50)
        elif MATPLOTLIB_AVAILABLE:
            try:
                from collections import Counter
                telling = Counter(voorkeuren)
                
                bg_color = Colors.bg_card[1] if ctk.get_appearance_mode() == "Dark" else Colors.bg_card[0]
                text_color = "white" if ctk.get_appearance_mode() == "Dark" else "black"
                
                fig, ax = plt.subplots(figsize=(8, 3.5), dpi=100)
                fig.patch.set_facecolor(bg_color)
                ax.set_facecolor(bg_color)
                ax.tick_params(colors=text_color, labelsize=9)
                for spine in ax.spines.values(): spine.set_color(Colors.border[1] if ctk.get_appearance_mode() == "Dark" else Colors.border[0])

                ax.yaxis.set_major_locator(MaxNLocator(integer=True))

                full_labels = list(telling.keys())
                wrapped_labels = [textwrap.fill(label, width=15) for label in full_labels]
                
                bars = ax.bar(wrapped_labels, telling.values(), color=Colors.accent, width=0.5)
                
                ax.set_xticks(range(len(wrapped_labels)))
                ax.set_xticklabels(wrapped_labels, rotation=45, ha='right')

                annot = ax.annotate("", xy=(0,0), xytext=(0, 10), textcoords="offset points",
                                    bbox=dict(boxstyle="round,pad=0.5", fc=Colors.bg_main[1] if ctk.get_appearance_mode() == "Dark" else Colors.bg_main[0], ec=Colors.accent, alpha=0.9),
                                    color=text_color, ha='center', fontsize=9)
                annot.set_visible(False)

                def hover(event):
                    vis = annot.get_visible()
                    if event.inaxes == ax:
                        for i, bar in enumerate(bars):
                            cont, ind = bar.contains(event)
                            if cont:
                                kanaal = full_labels[i]
                                d = details.get(kanaal, {})
                                m = d.get('Man', 0)
                                v = d.get('Vrouw', 0)
                                ages = d.get('Leeftijden', [])
                                avg_age = round(sum(ages)/len(ages), 1) if ages else "-"
                                
                                tooltip_tekst = f"{kanaal}\nMannen: {m} | Vrouwen: {v}\nGem. Leeftijd: {avg_age} jr"
                                
                                annot.xy = (bar.get_x() + bar.get_width() / 2, bar.get_height())
                                annot.set_text(tooltip_tekst)
                                annot.set_visible(True)
                                fig.canvas.draw_idle()
                                return
                    if vis:
                        annot.set_visible(False)
                        fig.canvas.draw_idle()

                fig.canvas.mpl_connect("motion_notify_event", hover)
                
                fig.subplots_adjust(bottom=0.35) 
                
                canvas = FigureCanvasTkAgg(fig, master=chart_card)
                canvas.draw()
                canvas.get_tk_widget().pack(fill="both", expand=True, padx=20, pady=(0, 15))
            except Exception as e:
                ctk.CTkLabel(chart_card, text=f"Fout bij laden grafiek: {e}", text_color="#EF4444").pack(pady=50)

        opm_card = ctk.CTkFrame(self.dashboard_scroll, fg_color=Colors.bg_card, corner_radius=10, border_width=1, border_color=Colors.border)
        opm_card.pack(fill="x", padx=5)
        
        ctk.CTkLabel(opm_card, text="Recente Ideeën & Opmerkingen", font=(self.font, 16, "bold"), text_color=Colors.text_main).pack(anchor="w", padx=20, pady=(15, 5))
        
        opmerkingen_lijst = [k for k in reversed(data_to_show) if k.get("opmerking", "").strip() != ""]
        
        if len(opmerkingen_lijst) == 0:
            ctk.CTkLabel(opm_card, text="Er zijn nog geen opmerkingen achtergelaten.", font=(self.font, 13), text_color=Colors.text_grey).pack(anchor="w", padx=20, pady=(0, 20))
        else:
            for kand in opmerkingen_lijst[:5]:
                item_frame = ctk.CTkFrame(opm_card, fg_color=Colors.bg_main, corner_radius=8)
                item_frame.pack(fill="x", padx=20, pady=(0, 10))
                
                header_text = f"{kand.get('naam', 'Onbekend')} ({kand.get('leeftijd', '-')} jr) - {kand.get('datum', '-')}"
                ctk.CTkLabel(item_frame, text=header_text, font=(self.font, 11, "bold"), text_color=Colors.accent).pack(anchor="w", padx=15, pady=(10, 0))
                ctk.CTkLabel(item_frame, text=f'"{kand.get("opmerking", "")}"', font=(self.font, 13, "italic"), text_color=Colors.text_main, wraplength=700, justify="left").pack(anchor="w", padx=15, pady=(5, 15))
            ctk.CTkFrame(opm_card, fg_color=Colors.bg_card, height=10).pack()

    def exporteer_naar_csv(self):
        if not self.opgeslagen_data:
            return
            
        gekozen_filter = getattr(self, 'huidige_dashboard_filter', 'Alle Vragenlijsten')
        bestandsnaam = "StichtingZO_Alle_Inzendingen.csv" if gekozen_filter == "Alle Vragenlijsten" else f"StichtingZO_{gekozen_filter.replace(' ', '_')}.csv"
        
        filepath = filedialog.asksaveasfilename(
            defaultextension=".csv", 
            filetypes=[("CSV Bestand", "*.csv")], 
            title="Exporteer Data",
            initialfile=bestandsnaam
        )
        
        if filepath:
            try:
                with open(filepath, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f, delimiter=';') 
                    
                    data_export = self.opgeslagen_data if gekozen_filter == "Alle Vragenlijsten" else [k for k in self.opgeslagen_data if k.get("template_titel", "Standaard Vragenlijst") == gekozen_filter]
                    
                    headers = ['Naam', 'Leeftijd', 'Geslacht', 'Datum', 'Vragenlijst (Template)', 'Opmerking']
                    
                    specifieke_template = None
                    if gekozen_filter != "Alle Vragenlijsten":
                        specifieke_template = next((t for t in self.opgeslagen_templates if t.get('titel') == gekozen_filter), None)
                    
                    if specifieke_template:
                        for i, v in enumerate(specifieke_template.get('vragen', [])):
                            headers.append(v.get('vraag', f'Vraag {i+1}'))
                    else:
                        max_vragen = max([len(k.get('antwoorden', [])) for k in data_export]) if data_export else 0
                        for i in range(max_vragen):
                            headers.append(f"Vraag {i+1}")
                            headers.append(f"Antwoord {i+1}")
                            
                    writer.writerow(headers)
                    
                    for k in data_export:
                        rij = [
                            k.get('naam', ''), 
                            k.get('leeftijd', ''), 
                            k.get('geslacht', ''), 
                            k.get('datum', ''), 
                            k.get('template_titel', 'Oude Vragenlijst'),
                            k.get('opmerking', '').replace('\n', ' ')
                        ]
                        
                        antwoorden = k.get('antwoorden', [])
                        
                        if specifieke_template:
                            aantal_vragen = len(specifieke_template.get('vragen', []))
                            for i in range(aantal_vragen):
                                if i < len(antwoorden):
                                    ans = antwoorden[i]
                                    rij.append(ans.get('antwoord', '') if isinstance(ans, dict) else str(ans))
                                else:
                                    rij.append("")
                        else:
                            for ans in antwoorden:
                                if isinstance(ans, dict):
                                    rij.append(ans.get('vraag', ''))
                                    rij.append(ans.get('antwoord', ''))
                                else:
                                    rij.append("") 
                                    rij.append(str(ans))
                                    
                        writer.writerow(rij)
                self.toon_melding("📥 Data succesvol geëxporteerd!", "success")
                os.startfile(filepath)
            except Exception as e:
                self.toon_melding(f"× Fout bij exporteren: {e}", "error")


    # === TAB: INSTELLINGEN ===
    def _build_settings(self):
        self.focus_set() 
        for w in self.frames["instellingen"].winfo_children(): w.destroy()
        
        settings_container = ctk.CTkFrame(self.frames["instellingen"], fg_color="transparent")
        settings_container.pack(fill="both", expand=True, padx=35, pady=(10, 20))
        
        ctk.CTkLabel(settings_container, text="Weergave", font=(self.font, 16, "bold"), text_color=Colors.text_main).pack(anchor="w", pady=(0, 10))
        display_frame = ctk.CTkFrame(settings_container, fg_color=Colors.bg_card, corner_radius=10, border_width=1, border_color=Colors.border)
        display_frame.pack(fill="x", pady=(0, 20))
        
        ctk.CTkLabel(display_frame, text="Applicatie Thema", font=(self.font, 14, "bold"), text_color=Colors.text_main).pack(side="left", padx=20, pady=20)
        self.setting_darkmode = ctk.CTkSwitch(display_frame, text="Dark Mode", command=lambda: ctk.set_appearance_mode("Dark" if ctk.get_appearance_mode() == "Light" else "Light"), font=(self.font, 13, "bold"), text_color=Colors.text_main, progress_color=Colors.accent, border_color=Colors.text_grey, switch_width=45, switch_height=22)
        self.setting_darkmode.pack(side="right", padx=20, pady=20)
        if ctk.get_appearance_mode() == "Dark": self.setting_darkmode.select()

        ctk.CTkLabel(settings_container, text="Systeem & Database", font=(self.font, 16, "bold"), text_color=Colors.text_main).pack(anchor="w", pady=(10, 10))
        sys_card = ctk.CTkFrame(settings_container, fg_color=Colors.bg_card, corner_radius=10, border_width=1, border_color=Colors.border)
        sys_card.pack(fill="x", pady=(0, 20))
        
        ctk.CTkLabel(sys_card, text="Data Handmatig Verversen", font=(self.font, 14, "bold"), text_color=Colors.text_main).pack(anchor="w", padx=20, pady=(20, 5))
        ctk.CTkLabel(sys_card, text="Haal direct de nieuwste formulieren en inzendingen op uit de database. Handig als een collega tegelijk aan het werk is.", font=(self.font, 12), text_color=Colors.text_grey).pack(anchor="w", padx=20, pady=(0, 15))

        def forceer_data_refresh():
            self.needs_refresh = {"vragenlijsten": True, "ontwerpen": True, "inzendingen": True, "dashboard": True, "instellingen": False}
            self.toon_melding("🔄 Database succesvol ververst!", "info")
            self.show_tab_vragenlijsten()
            
        btn_refresh = ctk.CTkButton(sys_card, text="🔄 Ververs Database", font=(self.font, 13, "bold"), fg_color=Colors.bg_main, text_color=Colors.text_main, border_width=1, border_color=Colors.border, hover_color=Colors.border, command=forceer_data_refresh)
        btn_refresh.pack(anchor="w", padx=20, pady=(0, 20))

        ctk.CTkLabel(settings_container, text="Ontwikkelaar & Debugging", font=(self.font, 16, "bold"), text_color=Colors.text_main).pack(anchor="w", pady=(10, 10))
        dev_card = ctk.CTkFrame(settings_container, fg_color=Colors.bg_card, corner_radius=10, border_width=1, border_color=Colors.border)
        dev_card.pack(fill="x", pady=(0, 20))
        
        ctk.CTkLabel(dev_card, text="Systeem Terminal", font=(self.font, 14, "bold"), text_color=Colors.text_main).pack(anchor="w", padx=20, pady=(20, 5))
        ctk.CTkLabel(dev_card, text="Bekijk actuele foutmeldingen en systeemlogs van de applicatie. Handig voor probleemoplossing.", font=(self.font, 12), text_color=Colors.text_grey).pack(anchor="w", padx=20, pady=(0, 15))

        btn_terminal = ctk.CTkButton(dev_card, text="💻 Open Terminal", font=(self.font, 13, "bold"), fg_color=Colors.bg_main, text_color=Colors.text_main, border_width=1, border_color=Colors.border, hover_color=Colors.border, command=lambda: TerminalPopup(self, self.font))
        btn_terminal.pack(anchor="w", padx=20, pady=(0, 20))

# === START PUNT ===
if __name__ == "__main__":
    app = StichtingZOPortal()
    app.mainloop()
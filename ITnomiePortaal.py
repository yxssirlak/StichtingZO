import sys, os, traceback, time, psutil, pdfplumber, re, json
from datetime import datetime
from dotenv import load_dotenv
import pyrebase

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QPushButton, QLineEdit, QStackedWidget, QFrame, QGridLayout, 
    QGraphicsDropShadowEffect, QGraphicsOpacityEffect, QTableWidget, 
    QTableWidgetItem, QHeaderView, QComboBox, QTextEdit, QFileDialog, QProgressBar, QCheckBox
)
from PySide6.QtCore import (
    Qt, Signal, QTimer, QPropertyAnimation, QEasingCurve, 
    QRect, QEvent, QPointF, QThread, QParallelAnimationGroup, Property, QSettings, QPoint
)
from PySide6.QtGui import (
    QIcon, QPixmap, QColor, QPainter, QPen, QBrush, QPainterPath, QGuiApplication
)
from PySide6.QtSvg import QSvgRenderer

def log_uncaught_exceptions(ex_cls, ex, tb):
    error_msg = ''.join(traceback.format_tb(tb))
    error_msg += f'{ex_cls.__name__}: {ex}\n'
    application_path = sys._MEIPASS if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
    log_file_path = os.path.join(application_path, "error_log.txt")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with open(log_file_path, "a", encoding="utf-8") as f: f.write(f"\n[{timestamp}]\n{error_msg}{'-' * 40}\n")
    except: pass 
    sys.exit()

sys.excepthook = log_uncaught_exceptions
application_path = sys._MEIPASS if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))

class Colors:
    accent = "#00C4CC"
    accent_dark = "#009EAA"
    secondary = "#B33CFF"     
    success = "#10B981"
    warning = "#F59E0B"
    danger = "#EF4444"
    terminal_bg = "#050505"
    terminal_text = "#00FF41" 
    bg_base = ""
    bg_panel = ""
    bg_card = ""
    text_main = ""
    text_sub = ""
    border = ""

def apply_theme(mode="Systeem"):
    if mode == "Systeem": mode = "Dark" if QGuiApplication.styleHints().colorScheme() == Qt.ColorScheme.Dark else "Light"
    if mode == "Dark":
        Colors.bg_base = "#0B0F19"; Colors.bg_panel = "#111827"; Colors.bg_card = "#1F2937"       
        Colors.text_main = "#F3F4F6"; Colors.text_sub = "#9CA3AF"; Colors.border = "#374151"
    else:
        Colors.bg_base = "#E2E8F0"; Colors.bg_panel = "#F8FAFC"; Colors.bg_card = "#FFFFFF"       
        Colors.text_main = "#0F172A"; Colors.text_sub = "#64748B"; Colors.border = "#CBD5E1"        

def prepare_system_icons():
    icons_dir = os.path.join(application_path, "Icons")
    os.makedirs(icons_dir, exist_ok=True)
    icons = {
        "dashboard.svg": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="9" rx="1"/><rect x="14" y="3" width="7" height="5" rx="1"/><rect x="14" y="12" width="7" height="9" rx="1"/><rect x="3" y="16" width="7" height="5" rx="1"/></svg>',
        "pdf.svg": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/></svg>',
        "excel.svg": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><path d="M8 13h2l2 3l2-3h2"/><path d="M8 17h2l2-3l2 3h2"/></svg>',
        "settings.svg": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>',
        "SystemClose.svg": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>',
        "SystemMinimize.svg": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="5" y1="12" x2="19" y2="12"></line></svg>',
        "SystemFullscreen.svg": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3"></path></svg>',
        "SystemArrowDown.svg": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="6 9 12 15 18 9"></polyline></svg>',
        "clock.svg": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>',
        "alert.svg": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>',
        "play.svg": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg>',
        "download.svg": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>',
        "terminal.svg": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="4 17 10 11 4 5"></polyline><line x1="12" y1="19" x2="20" y2="19"></line></svg>',
        "search.svg": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>',
        "menu.svg": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="3" y1="12" x2="21" y2="12"></line><line x1="3" y1="6" x2="21" y2="6"></line><line x1="3" y1="18" x2="21" y2="18"></line></svg>'
    }
    for name, content in icons.items():
        with open(os.path.join(icons_dir, name), "w", encoding="utf-8") as f: f.write(content)

def get_stylesheet():
    prepare_system_icons()
    arrow_url = os.path.join(application_path, "Icons", "SystemArrowDown.svg").replace("\\", "/")
    return f"""
        QWidget {{ font-family: 'Segoe UI', system-ui; color: {Colors.text_main}; }}
        QMainWindow {{ background-color: transparent; }}
        QWidget#Central {{ background-color: {Colors.bg_base}; border-radius: 15px; border: 1px solid {Colors.border}; }}
        QFrame#Panel {{ background-color: {Colors.bg_panel}; border: 1px solid {Colors.border}; border-radius: 16px; }}
        QFrame#Card {{ background-color: {Colors.bg_card}; border: 1px solid {Colors.border}; border-radius: 14px; }}
        QFrame#Sidebar {{ background-color: transparent; border-top-left-radius: 15px; border-bottom-left-radius: 15px; }}
        QPushButton#MinBtn, QPushButton#MaxBtn, QPushButton#CloseBtn {{ border: none; background-color: transparent; border-radius: 4px; }}
        QPushButton#MinBtn:hover, QPushButton#MaxBtn:hover {{ background-color: rgba(150,150,150,0.2); }}
        QPushButton#CloseBtn:hover {{ background-color: #E81123; }}
        QPushButton#ActionBtn {{ background-color: {Colors.bg_card}; border: 1px solid {Colors.border}; border-radius: 10px; padding: 10px; font-weight: bold; color: {Colors.text_main}; font-size: 13px; }}
        QPushButton#ActionBtn:hover {{ background-color: {Colors.bg_panel}; border: 1px solid {Colors.accent_dark}; color: {Colors.accent}; }}
        QPushButton#TerminalBtn {{ background-color: transparent; border: 1px solid {Colors.border}; border-radius: 6px; padding: 5px 12px; font-weight: bold; color: {Colors.text_sub}; font-size: 12px; }}
        QPushButton#TerminalBtn:hover {{ background-color: {Colors.bg_card}; color: {Colors.accent}; border: 1px solid {Colors.accent}; }}
        QComboBox {{ background-color: {Colors.bg_card}; border: 1px solid {Colors.border}; border-radius: 10px; padding: 8px 15px; color: {Colors.text_main}; font-size: 13px; font-weight: bold; }}
        QComboBox:focus {{ border: 1px solid {Colors.accent}; outline: none; }}
        QComboBox::drop-down {{ subcontrol-origin: padding; subcontrol-position: top right; width: 35px; border-left: none; }}
        QComboBox::down-arrow {{ image: url('{arrow_url}'); width: 16px; height: 16px; }}
        QTableWidget {{ background-color: transparent; border: none; gridline-color: {Colors.border}; font-size: 13px; }}
        QTableWidget::item {{ border-bottom: 1px solid {Colors.border}; padding: 10px 5px; }}
        QHeaderView::section {{ background-color: transparent; color: {Colors.text_sub}; font-weight: bold; font-size: 12px; border: none; border-bottom: 2px solid {Colors.border}; padding-bottom: 8px; }}
        QTextEdit#Console {{ background-color: {Colors.terminal_bg}; color: {Colors.terminal_text}; font-family: 'Consolas', 'Courier New', monospace; font-size: 12px; border: 1px solid {Colors.border}; border-radius: 10px; padding: 10px; }}
    """

def get_tinted_pixmap(icon_filename, color, size=24):
    icon_path = os.path.join(application_path, "Icons", icon_filename)
    pix = QPixmap(size, size); pix.fill(Qt.transparent)
    if os.path.exists(icon_path):
        renderer = QSvgRenderer(icon_path); painter = QPainter(pix); renderer.render(painter)
        painter.setCompositionMode(QPainter.CompositionMode_SourceIn); painter.fillRect(pix.rect(), QColor(color)); painter.end()
    return pix

def apply_shadow(widget, blur=30, alpha=80, y=8):
    shadow = QGraphicsDropShadowEffect()
    shadow.setBlurRadius(blur); shadow.setColor(QColor(0, 0, 0, alpha)); shadow.setOffset(0, y)
    widget.setGraphicsEffect(shadow)

class FocusLineEdit(QLineEdit):
    focus_in = Signal(); focus_out = Signal()
    def focusInEvent(self, e): super().focusInEvent(e); self.focus_in.emit()
    def focusOutEvent(self, e): super().focusOutEvent(e); self.focus_out.emit()

class AnimatedSearchIcon(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedSize(24, 24)
        self._scale = 16.0
        self.focused = False
        self.anim = QPropertyAnimation(self, b"icon_scale")
        self.anim.setDuration(150)

    @Property(float)
    def icon_scale(self): return self._scale
    
    @icon_scale.setter
    def icon_scale(self, val): 
        self._scale = val; self.update()

    def set_focus_state(self, is_focused):
        self.focused = is_focused
        self.anim.stop()
        self.anim.setStartValue(self._scale)
        self.anim.setEndValue(22.0 if is_focused else 16.0)
        self.anim.start()

    def paintEvent(self, e):
        painter = QPainter()
        if painter.begin(self):
            painter.setRenderHint(QPainter.Antialiasing)
            color = Colors.accent if self.focused else Colors.text_sub
            pix = get_tinted_pixmap("search.svg", color, int(self._scale))
            x = int((self.width() - self._scale) / 2)
            y = int((self.height() - self._scale) / 2)
            painter.drawPixmap(x, y, pix)
            painter.end()

class AutomationWorker(QThread):
    log = Signal(str)
    finished = Signal()

    def __init__(self, task_name):
        super().__init__()
        self.task_name = task_name

    def run(self):
        self.log.emit(f"Start taak: {self.task_name}...")
        time.sleep(1)
        self.log.emit("Bezig met ophalen en valideren...")
        time.sleep(1)
        self.log.emit(f"Taak {self.task_name} succesvol afgerond.")
        self.finished.emit()

class DutchPDFEngine:
    def __init__(self):
        self.patterns = {
            "BEDRIJFSNAAM": r"(?i)(?:^|\n)([A-Z][a-zA-Z0-9\s\&\.\-]{2,40}?(?:B\.V\.|V\.O\.F\.|N\.V\.|VOF|GmbH))",
            "IBAN": r"[a-zA-Z]{2}[0-9]{2}[a-zA-Z0-9]{4}[0-9]{7}([a-zA-Z0-9]?){0,16}",
            "BTW_NR": r"NL\d{9}B\d{2}",
            "KVK_NR": r"(?i)(?:kvk|k\.v\.k\.)?[\s:]*(\b\d{8}\b)",
            "DATUM": r"\b(?:0?[1-9]|[12][0-9]|3[01])[-/\s](?:0?[1-9]|1[012]|januari|februari|maart|april|mei|juni|juli|augustus|september|oktober|november|december)[-/\s](?:19|20)\d{2}\b",
            "ALLE_BEDRAGEN": r"(?:€|EUR)\s?(\d{1,3}(?:\.\d{3})*(?:,\d{2}))"
        }

    def extract_smart(self, file_path):
        results = {"text": "", "metadata": {}, "tables": []}
        try:
            with pdfplumber.open(file_path) as pdf:
                full_text = ""
                for page in pdf.pages:
                    full_text += page.extract_text() + "\n"
                    tables = page.extract_tables()
                    if tables: results["tables"].extend(tables)
                
                results["text"] = full_text
                
                for key, pattern in self.patterns.items():
                    matches = re.findall(pattern, full_text)
                    if key == "ALLE_BEDRAGEN":
                        results["metadata"][key] = list(set([f"€ {m}" for m in matches]))
                    elif key in ["BEDRIJFSNAAM", "KVK_NR"]:
                        results["metadata"][key] = list(set([m.strip() for m in matches if m.strip()]))
                    else:
                        results["metadata"][key] = list(set(matches))

                results["metadata"]["SUBTOTAAL_EXCL"] = []
                results["metadata"]["BTW_BEDRAG"] = []
                results["metadata"]["TOTAAL_INCL"] = []

                for line in full_text.split('\n'):
                    line_lower = line.lower()
                    amounts = re.findall(r"(?:€|EUR)?\s?(\d{1,3}(?:\.\d{3})*(?:,\d{2}))", line)
                    if not amounts: continue
                    
                    formatted = [f"€ {a}" for a in amounts]
                    
                    if "excl" in line_lower or "subtotaal" in line_lower or "netto" in line_lower:
                        results["metadata"]["SUBTOTAAL_EXCL"].extend(formatted)
                    elif "btw" in line_lower or "b.t.w." in line_lower or "omzetbelasting" in line_lower or "%" in line_lower:
                        if "excl" not in line_lower and "incl" not in line_lower: 
                            results["metadata"]["BTW_BEDRAG"].extend(formatted)
                    elif "totaal" in line_lower or "te betalen" in line_lower or "incl" in line_lower:
                        if "excl" not in line_lower:
                            results["metadata"]["TOTAAL_INCL"].extend(formatted)

                for key in ["SUBTOTAAL_EXCL", "BTW_BEDRAG", "TOTAAL_INCL"]:
                    results["metadata"][key] = list(set(results["metadata"][key]))

            return results
        except Exception as e:
            return {"error": str(e)}

class PDFWorker(QThread):
    finished_data = Signal(dict)
    log = Signal(str)
    progress = Signal(int, str) 

    def __init__(self, file_path):
        super().__init__()
        self.file_path = file_path
        self.engine = DutchPDFEngine()

    def run(self):
        self.progress.emit(10, "Bestand inlezen...")
        time.sleep(0.5) 
        self.log.emit(f"[START] Analyseren van: {os.path.basename(self.file_path)}")
        
        self.progress.emit(40, "Gegevens extraheren en geavanceerde patronen zoeken...")
        time.sleep(0.5) 
        data = self.engine.extract_smart(self.file_path)
        
        self.progress.emit(90, "Resultaten verwerken en valideren...")
        time.sleep(0.5) 
        self.log.emit(f"[SUCCESS] Data-extractie voltooid voor {os.path.basename(self.file_path)}.")
        self.progress.emit(100, "Analyse voltooid!")
        self.finished_data.emit(data)

class AnimatedNavButton(QPushButton):
    def __init__(self, text, icon_filename, parent=None):
        super().__init__(parent)
        self.setText(text); self.icon_filename = icon_filename
        self.setFixedHeight(48); self.setCursor(Qt.PointingHandCursor); self.setCheckable(True)
        self._hover_progress = 0.0
        self.anim = QPropertyAnimation(self, b"hover_progress"); self.anim.setDuration(150); self.anim.setStartValue(0.0); self.anim.setEndValue(1.0)

    @Property(float)
    def hover_progress(self): return self._hover_progress
    @hover_progress.setter
    def hover_progress(self, val): self._hover_progress = val; self.update() 
    def enterEvent(self, e): self.anim.setDirection(QPropertyAnimation.Forward); self.anim.start(); super().enterEvent(e)
    def leaveEvent(self, e): self.anim.setDirection(QPropertyAnimation.Backward); self.anim.start(); super().leaveEvent(e)

    def paintEvent(self, e):
        painter = QPainter()
        if painter.begin(self):
            painter.setRenderHint(QPainter.Antialiasing)
            is_active = self.isChecked()
            bg_color = QColor(Colors.accent); bg_color.setAlphaF(0.15 if is_active else 0.1 * self._hover_progress)
            text_color = QColor(Colors.text_main) if (is_active or self._hover_progress > 0) else QColor(Colors.text_sub)
            icon_color = Colors.accent if (is_active or self._hover_progress > 0) else Colors.text_sub

            rect = self.rect().adjusted(10, 3, -10, -3)
            painter.setBrush(QBrush(bg_color)); painter.setPen(Qt.NoPen); painter.drawRoundedRect(rect, 10, 10)
            
            icon_pix = get_tinted_pixmap(self.icon_filename, icon_color, 20)
            
            if self.width() < 100:
                icon_x = (self.width() - 20) // 2
                painter.drawPixmap(icon_x, 14, icon_pix)
                if is_active:
                    painter.setBrush(QBrush(QColor(Colors.accent)))
                    painter.drawRoundedRect(6, 13, 4, 22, 2, 2) 
            else:
                painter.drawPixmap(28, 14, icon_pix)
                painter.setPen(QPen(text_color))
                font = self.font(); font.setBold(True); font.setPointSize(10)
                painter.setFont(font); painter.drawText(QRect(60, 0, self.width()-60, self.height()), Qt.AlignVCenter | Qt.AlignLeft, self.text())
                if is_active:
                    painter.setBrush(QBrush(QColor(Colors.accent)))
                    painter.drawRoundedRect(10, 13, 4, 22, 2, 2)
            painter.end()

class HoverCard(QFrame):
    clicked = Signal()
    files_dropped = Signal(list) 

    def __init__(self, hover_border=None):
        super().__init__()
        self.setObjectName("Card")
        self.setCursor(Qt.PointingHandCursor)
        self.b_hover = hover_border
        self.setAcceptDrops(True) 

    def enterEvent(self, e):
        hb = self.b_hover if self.b_hover else Colors.accent_dark
        self.setStyleSheet(f"QFrame#Card {{ background-color: {Colors.bg_panel}; border: 1px solid {hb}; border-radius: 14px; }}")
        super().enterEvent(e)

    def leaveEvent(self, e):
        self.setStyleSheet(""); super().leaveEvent(e)

    def mousePressEvent(self, event):
        self.clicked.emit()
        super().mousePressEvent(event)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
            self.setStyleSheet(f"QFrame#Card {{ background-color: {Colors.accent}; border: 2px dashed white; border-radius: 14px; }}")
        else:
            event.ignore()

    def dragLeaveEvent(self, event):
        self.setStyleSheet("")

    def dropEvent(self, event):
        files = [u.toLocalFile() for u in event.mimeData().urls() if u.toLocalFile().lower().endswith('.pdf')]
        if files:
            self.files_dropped.emit(files)
        self.setStyleSheet("")

class ModernTooltip(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent, Qt.ToolTip | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(140, 60)
        
        layout = QVBoxLayout(self)
        self.lbl_title = QLabel("WAARDE:")
        self.lbl_title.setStyleSheet(f"color: {Colors.text_sub}; font-size: 10px; font-weight: bold; letter-spacing: 1px;")
        
        self.content_layout = QHBoxLayout()
        self.icon_lbl = QLabel()
        self.icon_lbl.setPixmap(get_tinted_pixmap("dashboard.svg", Colors.accent, 16))
        
        self.lbl_value = QLabel("0")
        self.lbl_value.setStyleSheet(f"color: {Colors.accent}; font-size: 20px; font-weight: 900;")
        
        self.content_layout.addWidget(self.icon_lbl)
        self.content_layout.addWidget(self.lbl_value)
        self.content_layout.addStretch()
        
        layout.addWidget(self.lbl_title)
        layout.addLayout(self.content_layout)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        path = QPainterPath()
        path.addRoundedRect(self.rect().adjusted(1, 1, -1, -1), 10, 10)
        
        bg_color = QColor(Colors.bg_card)
        bg_color.setAlpha(200) 
        painter.fillPath(path, QBrush(bg_color))
        
        pen = QPen(QColor(Colors.accent))
        pen.setWidth(2)
        painter.setPen(pen)
        painter.drawPath(path)

    def update_data(self, value, pos):
        self.lbl_value.setText(str(value))
        self.move(pos + QPoint(15, -70))
        self.show()

class SparklineWidget(QWidget):
    def __init__(self, data_points, color=Colors.accent):
        super().__init__()
        self.data = data_points
        self.color = color
        self.setFixedHeight(50)
        self.setMouseTracking(True)
        self.hover_index = -1
        self.custom_tooltip = None

    def mouseMoveEvent(self, event):
        if not self.custom_tooltip:
            self.custom_tooltip = ModernTooltip(self.window())

        step_x = self.width() / (len(self.data) - 1)
        index = round(event.position().x() / step_x)
        
        if 0 <= index < len(self.data):
            if self.hover_index != index:
                self.hover_index = index
                global_pos = self.mapToGlobal(event.position().toPoint())
                self.custom_tooltip.update_data(self.data[index], global_pos)
                self.update()

    def leaveEvent(self, event):
        self.hover_index = -1
        if self.custom_tooltip:
            self.custom_tooltip.hide()
        self.update()

    def paintEvent(self, event):
        if not self.data: return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        w, h = self.width(), self.height()
        max_val, min_val = max(self.data), min(self.data)
        range_val = max_val - min_val if max_val != min_val else 1
        step_x = w / (len(self.data) - 1)
        
        path = QPainterPath()
        points = []
        for i, val in enumerate(self.data):
            x = i * step_x
            y = h - ((val - min_val) / range_val * (h - 15)) - 10
            p = QPointF(x, y)
            points.append(p)
            if i == 0: path.moveTo(p)
            else: path.lineTo(p)
            
        painter.setPen(QPen(QColor(self.color), 2))
        painter.drawPath(path)

        if self.hover_index != -1:
            p = points[self.hover_index]
            painter.setBrush(QBrush(QColor(255, 255, 255, 50)))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(p, 8, 8)
            painter.setBrush(QBrush(QColor("white")))
            painter.drawEllipse(p, 4, 4)

class SystemStatsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20, 0, 20, 10)
        
        self.cpu_lbl = QLabel("CPU: 0%")
        self.ram_lbl = QLabel("RAM: 0%")
        for lbl in [self.cpu_lbl, self.ram_lbl]:
            lbl.setStyleSheet(f"color: {Colors.text_sub}; font-size: 10px; font-weight: bold;")
            self.layout.addWidget(lbl)
            
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_stats)
        self.timer.start(2000)

    def update_stats(self):
        cpu = psutil.cpu_percent()
        ram = psutil.virtual_memory().percent
        self.cpu_lbl.setText(f"CPU GEBRUIK: {cpu}%")
        self.ram_lbl.setText(f"RAM GEBRUIK: {ram}%")

class ToastNotification(QFrame):
    def __init__(self, message, parent=None):
        super().__init__(parent)
        self.setFixedSize(250, 60)
        self.setObjectName("Toast")
        self.setStyleSheet(f"QFrame#Toast {{ background-color: {Colors.bg_card}; border: 1px solid {Colors.accent}; border-radius: 10px; }}")
        
        layout = QHBoxLayout(self)
        icon = QLabel(); icon.setPixmap(get_tinted_pixmap("alert.svg", Colors.accent, 20))
        msg = QLabel(message); msg.setStyleSheet("font-size: 12px; font-weight: bold;")
        layout.addWidget(icon); layout.addWidget(msg)

        self.opacity = QGraphicsOpacityEffect(self); self.setGraphicsEffect(self.opacity)
        self.anim = QPropertyAnimation(self.opacity, b"opacity")
        self.anim.setDuration(500); self.anim.setStartValue(0.0); self.anim.setEndValue(1.0)
        
        self.move(parent.width() - 270, parent.height() - 80)
        self.show(); self.anim.start()
        QTimer.singleShot(3000, self.close)

class ITnomieCommandCenter(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ITnomie Command Center")
        self.resize(1400, 850)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        self.settings = QSettings("ITnomie", "AutoHub")
        apply_theme(self.settings.value("theme", "Systeem"))
        self.setStyleSheet(get_stylesheet())
        
        self.normal_geometry = None; self.is_maximized = False; self.drag_start_pos = None
        self.sidebar_collapsed = False
        
        self.pdf_queue = []
        self.batch_results = []
        self.total_files = 0
        self.active_workers = 0 
        self.threads = [] 

        env_path = os.path.join(application_path, "ITnomieP.env")
        load_dotenv(env_path)
        
        firebase_config = {
            "apiKey": os.getenv("FIREBASE_API_KEY"),
            "authDomain": os.getenv("FIREBASE_AUTH_DOMAIN"),
            "databaseURL": os.getenv("FIREBASE_DATABASE_URL"),
            "projectId": os.getenv("FIREBASE_PROJECT_ID"),
            "storageBucket": os.getenv("FIREBASE_STORAGE_BUCKET"),
            "messagingSenderId": os.getenv("FIREBASE_MESSAGING_SENDER_ID"),
            "appId": os.getenv("FIREBASE_APP_ID"),
            "measurementId": os.getenv("FIREBASE_MEASUREMENT_ID")
        }
        
        if not firebase_config["databaseURL"]:
            self.firebase_active = False
            print(f"FOUT: Kon ITnomieP.env niet laden of FIREBASE_DATABASE_URL is leeg!")
        else:
            try:
                firebase = pyrebase.initialize_app(firebase_config)
                self.db = firebase.database()
                self.firebase_active = True
            except Exception as e:
                self.firebase_active = False
                print(e)

        self.build_ui()
        self.show_dashboard()

    def build_ui(self):
        central = QWidget(); central.setObjectName("Central")
        self.setCentralWidget(central); apply_shadow(central) 
        layout = QHBoxLayout(central); layout.setContentsMargins(15, 15, 15, 15); layout.setSpacing(10)
        
        self.nav_panel = QFrame(); self.nav_panel.setObjectName("Sidebar"); self.nav_panel.setFixedWidth(260)
        nav_l = QVBoxLayout(self.nav_panel); nav_l.setContentsMargins(0, 15, 0, 20)
        
        self.logo_container = QHBoxLayout(); self.logo_container.setContentsMargins(10, 0, 10, 0)
        
        self.btn_toggle = QPushButton()
        self.btn_toggle.setIcon(QIcon(get_tinted_pixmap("menu.svg", Colors.text_main, 20)))
        self.btn_toggle.setFixedSize(40, 40); self.btn_toggle.setCursor(Qt.PointingHandCursor)
        self.btn_toggle.setStyleSheet("QPushButton { background: transparent; border: none; } QPushButton:hover { background: rgba(150,150,150,0.1); border-radius: 8px; }")
        self.btn_toggle.clicked.connect(self.toggle_sidebar)
        self.logo_container.addWidget(self.btn_toggle)
        
        self.logo_lbl = QLabel()
        logo_path = os.path.join(application_path, "logo_stichtingzo_rgb.png")
        if os.path.exists(logo_path): self.logo_lbl.setPixmap(QPixmap(logo_path).scaled(110, 40, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else: self.logo_lbl.setText("ITnomie"); self.logo_lbl.setStyleSheet(f"color: {Colors.accent}; font-size: 24px; font-weight: 900; letter-spacing: -1px; border:none;")
        self.logo_container.addWidget(self.logo_lbl); self.logo_container.addStretch()
        nav_l.addLayout(self.logo_container)
        
        self.lbl_menu = QLabel("WERKOMGEVING"); self.lbl_menu.setStyleSheet(f"color: {Colors.text_sub}; font-size: 11px; font-weight: bold; letter-spacing: 1.5px; margin: 25px 0 5px 25px; border:none;")
        nav_l.addWidget(self.lbl_menu)
        
        self.btn_dash = AnimatedNavButton("Overzicht Dashboard", "dashboard.svg")
        self.btn_pdf = AnimatedNavButton("PDF Extractor", "pdf.svg")
        self.btn_excel = AnimatedNavButton("Data Combineren", "excel.svg")
        self.nav_btns = [self.btn_dash, self.btn_pdf, self.btn_excel]
        for btn in self.nav_btns: nav_l.addWidget(btn)
        nav_l.addStretch()
        
        self.nav_line = QFrame(); self.nav_line.setFixedHeight(1); self.nav_line.setStyleSheet(f"background-color: {Colors.border}; border:none; margin: 0 20px 10px 20px;"); nav_l.addWidget(self.nav_line)
        self.btn_set = AnimatedNavButton("Instellingen", "settings.svg"); self.nav_btns.append(self.btn_set); nav_l.addWidget(self.btn_set)
        layout.addWidget(self.nav_panel)
        nav_l.addSpacing(20)
        self.stats = SystemStatsWidget()
        nav_l.addWidget(self.stats)

        workspace = QWidget(); self.wl = QVBoxLayout(workspace); self.wl.setContentsMargins(0, 0, 0, 0); self.wl.setSpacing(10)
        
        top_bar = QFrame(); top_bar.setFixedHeight(50)
        top_l = QHBoxLayout(top_bar); top_l.setContentsMargins(15, 0, 0, 0)
        
        self.search_box = QFrame(); self.search_box.setObjectName("SearchBox")
        self.search_box.setFixedHeight(32); self.search_box.setFixedWidth(320)
        self.search_box.setStyleSheet(f"QFrame#SearchBox {{ background-color: {Colors.bg_base}; border: 1px solid {Colors.border}; border-radius: 16px; }}")
        s_layout = QHBoxLayout(self.search_box); s_layout.setContentsMargins(12, 0, 12, 0); s_layout.setSpacing(8)
        
        self.s_icon = AnimatedSearchIcon(); s_layout.addWidget(self.s_icon)
        
        self.search = FocusLineEdit(); self.search.setPlaceholderText("Zoek binnen systemen of bestanden...")
        self.search.setStyleSheet(f"QLineEdit {{ background: transparent; border: none; color: {Colors.text_main}; font-size: 13px; }} QLineEdit:focus {{ outline: none; border: none; background: transparent; }}")
        self.search.focus_in.connect(lambda: self.update_search_style(True))
        self.search.focus_out.connect(lambda: self.update_search_style(False))
        s_layout.addWidget(self.search)
        
        top_l.addWidget(self.search_box); top_l.addStretch()
        
        self.btn_terminal = QPushButton(" >_ Console "); self.btn_terminal.setObjectName("TerminalBtn")
        self.btn_terminal.setCursor(Qt.PointingHandCursor); self.btn_terminal.clicked.connect(self.toggle_terminal)
        is_dev = self.settings.value("dev_mode", "false") in [True, "true", "True", 1, "1"]
        self.btn_terminal.setVisible(is_dev)
        top_l.addWidget(self.btn_terminal); top_l.addSpacing(15)
        
        self.btn_min = QPushButton(); self.btn_min.setObjectName("MinBtn")
        self.btn_max = QPushButton(); self.btn_max.setObjectName("MaxBtn")
        self.btn_close = QPushButton(); self.btn_close.setObjectName("CloseBtn")
        for btn in [self.btn_min, self.btn_max, self.btn_close]:
            btn.setFixedSize(36, 36); top_l.addWidget(btn)
        self.refresh_window_icons() 
        self.btn_min.clicked.connect(self.animate_minimize); self.btn_max.clicked.connect(self.toggle_max); self.btn_close.clicked.connect(self.close)
        self.wl.addWidget(top_bar)
        
        self.pages = QStackedWidget()
        self.page_effect = QGraphicsOpacityEffect(self.pages); self.pages.setGraphicsEffect(self.page_effect)
        self.page_anim = QPropertyAnimation(self.page_effect, b"opacity"); self.page_anim.setDuration(200)
        self.wl.addWidget(self.pages)
        
        self.console = QTextEdit(); self.console.setObjectName("Console")
        self.console.setReadOnly(True); self.console.setFixedHeight(180); self.console.hide()
        self.wl.addWidget(self.console); self.log_to_console("Systeem initialisatie succesvol. Terminal gereed.")
        
        layout.addWidget(workspace, stretch=1)

        health_panel = QFrame(); health_panel.setFixedWidth(280)
        hl = QVBoxLayout(health_panel); hl.setContentsMargins(15, 20, 15, 20)
        hl.addWidget(QLabel("GEPLANDE TAKEN", styleSheet=f"color: {Colors.text_sub}; font-size: 11px; font-weight: bold; letter-spacing: 1.5px; border:none;"))
        
        def create_task_card(title, time_str, color):
            f = HoverCard(hover_border=Colors.border); f.setStyleSheet(f"background-color: transparent; border: 1px solid transparent; border-radius: 8px;")
            l = QHBoxLayout(f); l.setContentsMargins(10, 10, 10, 10)
            icn = QLabel(); icn.setPixmap(get_tinted_pixmap("clock.svg", color, 18)); l.addWidget(icn)
            v = QVBoxLayout(); v.setSpacing(2)
            v.addWidget(QLabel(title, styleSheet="font-size: 13px; font-weight: bold; background:transparent; border:none;"))
            v.addWidget(QLabel(time_str, styleSheet=f"color: {Colors.text_sub}; font-size: 11px; background:transparent; border:none;"))
            l.addLayout(v); l.addStretch(); return f
            
        hl.addWidget(create_task_card("Dagelijkse PDF Sync", "Vandaag, 18:00", Colors.accent))
        hl.addWidget(create_task_card("Excel Rapportage Export", "Vandaag, 23:30", Colors.secondary))
        hl.addWidget(create_task_card("Backup Systeem", "Morgen, 03:00", Colors.success))
        line = QFrame(); line.setFixedHeight(1); line.setStyleSheet(f"background-color: {Colors.border}; border:none; margin: 15px 0;"); hl.addWidget(line)
        hl.addWidget(QLabel("SYSTEEM MELDINGEN", styleSheet=f"color: {Colors.text_sub}; font-size: 11px; font-weight: bold; letter-spacing: 1.5px; border:none;"))
        
        def create_alert_card(title, desc, color):
            f = HoverCard(hover_border=Colors.border); f.setStyleSheet(f"background-color: transparent; border: 1px solid transparent; border-radius: 8px;")
            l = QHBoxLayout(f); l.setContentsMargins(10, 10, 10, 10)
            icn = QLabel(); icn.setPixmap(get_tinted_pixmap("alert.svg", color, 18)); l.addWidget(icn)
            v = QVBoxLayout(); v.setSpacing(2)
            v.addWidget(QLabel(title, styleSheet="font-size: 13px; font-weight: bold; background:transparent; border:none;"))
            v.addWidget(QLabel(desc, styleSheet=f"color: {Colors.text_sub}; font-size: 11px; background:transparent; border:none;"))
            l.addLayout(v); l.addStretch(); return f
            
        hl.addWidget(create_alert_card("Data Scraper", "Script succesvol afgerond.", Colors.success))
        hl.addWidget(create_alert_card("API Connectie", "Korte vertraging gemerkt.", Colors.warning))
        hl.addStretch()
        layout.addWidget(health_panel)

        self.setup_pages()
        self.setup_pdf_page()

    def toggle_sidebar(self):
        start_width = self.nav_panel.width()
        end_width = 60 if not self.sidebar_collapsed else 250
        
        self.sidebar_anim1 = QPropertyAnimation(self.nav_panel, b"minimumWidth"); self.sidebar_anim1.setDuration(250)
        self.sidebar_anim1.setStartValue(start_width); self.sidebar_anim1.setEndValue(end_width); self.sidebar_anim1.setEasingCurve(QEasingCurve.InOutQuad)

        self.sidebar_anim2 = QPropertyAnimation(self.nav_panel, b"maximumWidth"); self.sidebar_anim2.setDuration(250)
        self.sidebar_anim2.setStartValue(start_width); self.sidebar_anim2.setEndValue(end_width); self.sidebar_anim2.setEasingCurve(QEasingCurve.InOutQuad)

        self.sidebar_anim_group = QParallelAnimationGroup()
        self.sidebar_anim_group.addAnimation(self.sidebar_anim1); self.sidebar_anim_group.addAnimation(self.sidebar_anim2)
        self.sidebar_anim_group.start()

        self.sidebar_collapsed = not self.sidebar_collapsed
        if self.sidebar_collapsed:
            self.logo_lbl.hide(); self.lbl_menu.hide(); self.nav_line.hide()
        else:
            self.logo_lbl.show(); self.lbl_menu.show(); self.nav_line.show()

    def update_search_style(self, focused):
        bg = Colors.bg_panel if focused else Colors.bg_base
        border = Colors.accent if focused else Colors.border
        self.search_box.setStyleSheet(f"QFrame#SearchBox {{ background-color: {bg}; border: 1px solid {border}; border-radius: 16px; }}")
        self.s_icon.set_focus_state(focused) 

    def log_to_console(self, message):
        t = datetime.now().strftime("%H:%M:%S")
        self.console.append(f"<span style='color: #64748B;'>[{t}]</span> {message}")

    def toggle_terminal(self):
        if self.console.isHidden():
            self.console.show()
            self.btn_terminal.setStyleSheet(f"background-color: {Colors.bg_card}; color: {Colors.accent}; border: 1px solid {Colors.accent};")
        else:
            self.console.hide(); self.btn_terminal.setStyleSheet("") 

    def run_demo_script(self):
        # Check of er al een demo worker bestaat en of deze nog draait
        if hasattr(self, 'demo_worker') and self.demo_worker.isRunning():
            ToastNotification("Taak draait al...", self)
            return

        if self.console.isHidden() and self.btn_terminal.isVisible(): self.toggle_terminal()
        self.log_to_console("<br><b style='color: #00C4CC;'>--- HANDMATIGE SYNC GESTART ---</b>")
        ToastNotification("Synchronisatie gestart...", self)
        
        self.demo_worker = AutomationWorker("Database Sync")
        self.demo_worker.log.connect(self.log_to_console)
        
        # Zorg dat Qt de thread veilig opruimt als hij he-le-maal klaar is
        self.demo_worker.finished.connect(lambda: ToastNotification("Sync succesvol voltooid!", self))
        self.demo_worker.finished.connect(self.demo_worker.deleteLater) 
        
        self.demo_worker.start()

    def refresh_window_icons(self):
        self.btn_toggle.setIcon(QIcon(get_tinted_pixmap("menu.svg", Colors.text_main, 20)))
        self.btn_min.setIcon(QIcon(get_tinted_pixmap("SystemMinimize.svg", Colors.text_sub, 16)))
        if self.is_maximized: self.btn_max.setIcon(QIcon(get_tinted_pixmap("SystemNormalScreen.svg", Colors.text_sub, 16)))
        else: self.btn_max.setIcon(QIcon(get_tinted_pixmap("SystemFullscreen.svg", Colors.text_sub, 16)))
        self.btn_close.setIcon(QIcon(get_tinted_pixmap("SystemClose.svg", Colors.text_sub, 16)))

    def change_theme(self, mode):
        self.settings.setValue("theme", mode)
        apply_theme(mode)
        self.setStyleSheet(get_stylesheet())
        self.setStyleSheet(self.styleSheet() + f"\n#Central {{ background-color: {Colors.bg_base}; border-radius: 15px; border: 1px solid {Colors.border}; }}")
        self.refresh_window_icons()
        self.update_search_style(self.search.hasFocus())
        self.update() 

    def toggle_dev_mode(self, state):
        self.settings.setValue("dev_mode", state)
        self.btn_terminal.setVisible(state)
        if not state:
            self.console.hide()
            self.btn_terminal.setStyleSheet("")

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and event.position().y() < 60: self.drag_start_pos = event.globalPosition().toPoint()
    def mouseMoveEvent(self, event):
        if self.is_maximized: return
        if self.drag_start_pos:
            delta = event.globalPosition().toPoint() - self.drag_start_pos
            self.move(self.pos() + delta); self.drag_start_pos = event.globalPosition().toPoint()
    def mouseReleaseEvent(self, event): self.drag_start_pos = None

    def toggle_max(self):
        self.anim = QPropertyAnimation(self, b"geometry"); self.anim.setDuration(250); self.anim.setEasingCurve(QEasingCurve.OutCubic)
        if not self.is_maximized:
            self.normal_geometry = self.geometry(); self.anim.setStartValue(self.normal_geometry); self.anim.setEndValue(self.screen().availableGeometry())
            self.is_maximized = True
        else:
            self.anim.setStartValue(self.geometry()); self.anim.setEndValue(self.normal_geometry); self.is_maximized = False
        self.refresh_window_icons(); self.anim.start()

    def animate_minimize(self):
        if not self.is_maximized: self.normal_geometry = self.geometry()
        self.min_anim_group = QParallelAnimationGroup()
        self.fade_out = QPropertyAnimation(self, b"windowOpacity"); self.fade_out.setDuration(200); self.fade_out.setStartValue(1.0); self.fade_out.setEndValue(0.0)
        self.slide_down = QPropertyAnimation(self, b"geometry"); self.slide_down.setDuration(200); cg = self.geometry()
        self.slide_down.setStartValue(cg); self.slide_down.setEndValue(QRect(cg.x(), cg.y() + 30, cg.width(), cg.height()))
        self.min_anim_group.addAnimation(self.fade_out); self.min_anim_group.addAnimation(self.slide_down)
        self.min_anim_group.finished.connect(self.showMinimized); self.min_anim_group.start()

    def changeEvent(self, event):
        if event.type() == QEvent.WindowStateChange:
            if not self.isMinimized():
                self.restore_anim = QPropertyAnimation(self, b"windowOpacity"); self.restore_anim.setDuration(300)
                self.restore_anim.setStartValue(0.0); self.restore_anim.setEndValue(1.0); self.restore_anim.start()
                if hasattr(self, 'normal_geometry') and self.normal_geometry and not self.isMaximized(): self.setGeometry(self.normal_geometry)
        super().changeEvent(event)
        
    def closeEvent(self, event):
        """Wordt aangeroepen wanneer de applicatie sluit. Zorgt dat alle threads veilig stoppen."""
        if hasattr(self, 'threads') and self.threads:
            for worker in self.threads:
                if worker.isRunning():
                    worker.quit()
                    worker.wait() # Wacht maximaal een fractie van een seconde tot hij stopt
                    
        if hasattr(self, 'demo_worker') and self.demo_worker.isRunning():
            self.demo_worker.quit()
            self.demo_worker.wait()
            
        super().closeEvent(event)

    def set_nav(self, btn):
        for b in self.nav_btns: b.setChecked(False)
        btn.setChecked(True)
        self.page_anim.stop(); self.page_anim.setStartValue(0.0); self.page_anim.setEndValue(1.0); self.page_anim.start()

    def setup_pages(self):
        page_dash = QWidget(); dl = QVBoxLayout(page_dash); dl.setContentsMargins(20,20,20,0)
        
        banner = QFrame()
        banner.setStyleSheet(f"background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 {Colors.accent}, stop:1 {Colors.secondary}); border-radius: 14px;")
        bl = QVBoxLayout(banner); bl.setContentsMargins(35, 30, 35, 30)
        bl.addWidget(QLabel("Welkom in de ITnomie Hub", styleSheet="font-size: 26px; font-weight: bold; color: white; border: none; background: transparent;"))
        bl.addWidget(QLabel("Al je geautomatiseerde processen draaien momenteel optimaal.", styleSheet=f"color: rgba(255,255,255,0.8); font-size: 15px; border: none; background: transparent;"))
        dl.addWidget(banner)
        
        grid = QGridLayout(); grid.setSpacing(15)
        def create_kpi(titel, waarde, spark_data, color):
            c = HoverCard()
            cl = QVBoxLayout(c); cl.setContentsMargins(20, 15, 20, 15)
            cl.addWidget(QLabel(titel, styleSheet=f"color: {Colors.text_sub}; font-weight: bold; font-size: 13px; border:none; background: transparent;"))
            cl.addWidget(QLabel(waarde, styleSheet="font-size: 32px; font-weight: 900; border:none; background: transparent; margin: 5px 0;"))
            if spark_data: cl.addWidget(SparklineWidget(spark_data, color))
            return c
            
        grid.addWidget(create_kpi("Verwerkte Documenten", "1,289", [12, 15, 22, 18, 35, 42, 38, 50], Colors.accent), 0, 0)
        roi_card = HoverCard(); roi_card.setStyleSheet(f"QFrame#Card {{ background-color: {Colors.bg_card}; border: 1px solid {Colors.success}; border-radius: 14px; }}")
        roi_l = QVBoxLayout(roi_card); roi_l.setContentsMargins(20, 15, 20, 15)
        roi_l.addWidget(QLabel("Totale Besparing (YTD)", styleSheet=f"color: {Colors.text_sub}; font-weight: bold; font-size: 13px; border:none; background: transparent;"))
        roi_l.addWidget(QLabel("€ 14.850,-", styleSheet=f"color: {Colors.success}; font-size: 32px; font-weight: 900; border:none; background: transparent; margin: 5px 0;"))
        roi_l.addWidget(QLabel("Gebaseerd op 330 bespaarde uren", styleSheet=f"color: {Colors.text_sub}; font-size: 11px; border:none; background: transparent;"))
        grid.addWidget(roi_card, 0, 1)
        grid.addWidget(create_kpi("Foutmeldingen", "0", [5, 2, 0, 0, 1, 0, 0, 0], Colors.danger), 0, 2)
        dl.addLayout(grid)
        
        act_row = QHBoxLayout(); act_row.setContentsMargins(0, 10, 0, 10); act_row.setSpacing(15)
        def create_action_btn(titel, icon_name):
            btn = QPushButton(f"  {titel}"); btn.setObjectName("ActionBtn"); btn.setCursor(Qt.PointingHandCursor)
            btn.setIcon(QIcon(get_tinted_pixmap(icon_name, Colors.text_main, 18))); btn.setFixedHeight(45); return btn
            
        btn_run = create_action_btn("Run Handmatige Sync", "play.svg"); btn_run.clicked.connect(self.run_demo_script); act_row.addWidget(btn_run)
        act_row.addWidget(create_action_btn("Download Maandrapport", "download.svg")); act_row.addStretch(); dl.addLayout(act_row)
        
        tbl_frame = HoverCard(); tl = QVBoxLayout(tbl_frame); tl.setContentsMargins(20, 20, 20, 20)
        tl.addWidget(QLabel("Recente Systeem Logs", styleSheet="font-weight: bold; font-size: 14px; margin-bottom: 5px; background: transparent; border:none;"))
        tbl = QTableWidget(5, 4)
        tbl.setHorizontalHeaderLabels(["Proces ID", "Module", "Tijdstip", "Status"]); tbl.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        tbl.setShowGrid(False); tbl.verticalHeader().setVisible(False)
        data = [("TSK-892", "PDF Factuur Extractor", "10:45", "Voltooid"), ("TSK-891", "Database Sync", "10:30", "Voltooid"), ("TSK-890", "Klant Data Merge", "10:15", "Waarschuwing"), ("TSK-889", "Back-up Routine", "09:00", "Voltooid"), ("TSK-888", "Email Scraper", "08:15", "Voltooid")]
        for row, (id_v, n, t, s) in enumerate(data):
            tbl.setItem(row, 0, QTableWidgetItem(id_v)); tbl.setItem(row, 1, QTableWidgetItem(n)); tbl.setItem(row, 2, QTableWidgetItem(t))
            i = QTableWidgetItem(s)
            if s == "Voltooid": i.setForeground(QColor(Colors.success))
            elif s == "Waarschuwing": i.setForeground(QColor(Colors.warning))
            tbl.setItem(row, 3, i)
        tl.addWidget(tbl); dl.addWidget(tbl_frame); self.pages.addWidget(page_dash)
        
        for titel in ["PDF Extractor", "Data Combineren"]:
            p = QWidget(); l = QVBoxLayout(p); l.setAlignment(Qt.AlignTop)
            l.addWidget(QLabel(f"Module: {titel}", styleSheet="font-size: 26px; font-weight: bold; margin: 20px;")); self.pages.addWidget(p)

        page_set = QWidget(); sl = QVBoxLayout(page_set); sl.setAlignment(Qt.AlignTop); sl.setContentsMargins(15,15,15,15)
        sl.addWidget(QLabel("Instellingen", styleSheet="font-size: 26px; font-weight: bold; margin-bottom: 15px;"))
        set_card = QFrame(); set_card.setObjectName("Card"); scl = QVBoxLayout(set_card); scl.setContentsMargins(20, 20, 20, 20)
        scl.addWidget(QLabel("Weergave Opties", styleSheet="font-weight: bold; font-size: 14px; margin-bottom: 10px; border:none;"))
        
        row = QHBoxLayout(); row.addWidget(QLabel("Kies een weergave thema:", styleSheet="border:none;"))
        combo = QComboBox(); combo.setFixedWidth(200); combo.addItems(["Systeem", "Light", "Dark"])
        combo.setCurrentText(self.settings.value("theme", "Systeem")); combo.currentTextChanged.connect(self.change_theme)
        row.addWidget(combo); row.addStretch(); scl.addLayout(row)

        dev_row = QHBoxLayout()
        dev_row.addWidget(QLabel("Developer Mode (Toon Terminal & JSON):", styleSheet="border:none;"))
        self.dev_cb = QCheckBox()
        is_dev_checked = self.settings.value("dev_mode", "false") in [True, "true", "True", 1, "1"]
        self.dev_cb.setChecked(is_dev_checked)
        self.dev_cb.toggled.connect(self.toggle_dev_mode)
        dev_row.addWidget(self.dev_cb); dev_row.addStretch(); scl.addLayout(dev_row)

        sl.addWidget(set_card); self.pages.addWidget(page_set)
            
        self.btn_dash.clicked.connect(lambda: (self.pages.setCurrentIndex(0), self.set_nav(self.btn_dash)))
        self.btn_pdf.clicked.connect(lambda: (self.pages.setCurrentIndex(1), self.set_nav(self.btn_pdf)))
        self.btn_excel.clicked.connect(lambda: (self.pages.setCurrentIndex(2), self.set_nav(self.btn_excel)))
        self.btn_set.clicked.connect(lambda: (self.pages.setCurrentIndex(3), self.set_nav(self.btn_set)))

    def setup_pdf_page(self):
        page = self.pages.widget(1)
        
        for i in reversed(range(page.layout().count())): 
            widget = page.layout().itemAt(i).widget()
            if widget is not None: widget.deleteLater()

        layout = page.layout()
        layout.setContentsMargins(30, 30, 30, 30)

        self.drop_card = HoverCard()
        self.drop_card.setFixedHeight(200)
        self.drop_card.setStyleSheet(f"background: {Colors.bg_card}; border: 2px dashed {Colors.accent}; border-radius: 20px;")
        
        dl = QVBoxLayout(self.drop_card); dl.setAlignment(Qt.AlignCenter)
        self.drop_icon = QLabel(); self.drop_icon.setPixmap(get_tinted_pixmap("pdf.svg", Colors.accent, 48))
        dl.addWidget(self.drop_icon, alignment=Qt.AlignCenter)
        dl.addWidget(QLabel("Sleep facturen hierheen of klik om te uploaden", styleSheet=f"color: {Colors.text_sub}; font-weight: bold;"))
        
        self.drop_card.clicked.connect(self.open_pdf_dialog)
        self.drop_card.files_dropped.connect(self.handle_multiple_files)
        layout.addWidget(self.drop_card)

        self.pdf_status_container = QFrame()
        self.pdf_status_container.setObjectName("Card")
        psc_layout = QVBoxLayout(self.pdf_status_container)
        self.pdf_status_lbl = QLabel("Wachten op input...")
        self.pdf_status_lbl.setStyleSheet(f"color: {Colors.text_main}; font-weight: bold;")
        psc_layout.addWidget(self.pdf_status_lbl)
        
        self.pdf_progress = QProgressBar()
        self.pdf_progress.setFixedHeight(18)
        self.pdf_progress.setValue(0)
        self.pdf_progress.setTextVisible(True)
        self.pdf_progress.setStyleSheet(f"QProgressBar {{ background-color: {Colors.bg_base}; border: 1px solid {Colors.border}; border-radius: 9px; text-align: center; color: {Colors.text_main}; font-weight: bold; font-size: 11px; }} QProgressBar::chunk {{ background-color: {Colors.accent}; border-radius: 8px; }}")
        psc_layout.addWidget(self.pdf_progress)
        self.pdf_status_container.hide()
        layout.addWidget(self.pdf_status_container)

        self.result_wrapper = QWidget()
        rw_layout = QVBoxLayout(self.result_wrapper)
        rw_layout.setContentsMargins(0, 0, 0, 0)

        self.res_area = QTextEdit()
        self.res_area.setReadOnly(True)
        self.res_area.setStyleSheet(f"QTextEdit {{ background-color: {Colors.bg_panel}; border: 1px solid {Colors.border}; border-radius: 14px; padding: 20px; color: {Colors.text_main}; font-size: 13px; }}")
        rw_layout.addWidget(self.res_area)

        self.btn_save_data = QPushButton("  Data Opslaan naar Database")
        self.btn_save_data.setObjectName("ActionBtn")
        self.btn_save_data.setCursor(Qt.PointingHandCursor)
        self.btn_save_data.setIcon(QIcon(get_tinted_pixmap("download.svg", Colors.text_main, 18)))
        self.btn_save_data.setFixedHeight(45)
        self.btn_save_data.clicked.connect(self.save_extracted_data)
        rw_layout.addWidget(self.btn_save_data)

        self.result_wrapper.hide()
        layout.addWidget(self.result_wrapper)

    def open_pdf_dialog(self):
        paths, _ = QFileDialog.getOpenFileNames(self, "Selecteer PDF Facturen", "", "PDF Bestanden (*.pdf)")
        if paths:
            self.handle_multiple_files(paths)

    def handle_multiple_files(self, paths):
        self.pdf_queue = paths
        self.batch_results = []
        self.total_files = len(paths)
        self.res_area.clear()
        self.active_workers = 0
        
        if not self.console.isVisible() and self.btn_terminal.isVisible():
            self.toggle_terminal()
            
        self.log_to_console(f"Batch gestart: {self.total_files} bestanden in de wachtrij.")
        self.result_wrapper.hide()
        self.pdf_status_container.show()
        
        for _ in range(min(3, len(self.pdf_queue))):
            self.start_next_batch_item()

    def start_next_batch_item(self):
        if not self.pdf_queue:
            if self.active_workers == 0:
                self.pdf_status_container.hide()
                self.result_wrapper.show()
            return

        current_path = self.pdf_queue.pop(0)
        self.active_workers += 1
        
        current_index = self.total_files - len(self.pdf_queue)
        self.pdf_status_lbl.setText(f"Verwerken: {current_index}/{self.total_files} bestanden...")
        
        worker = PDFWorker(current_path)
        worker.log.connect(self.log_to_console)
        worker.progress.connect(self.update_pdf_progress)
        
        # We processen de data als het klaar is...
        worker.finished_data.connect(lambda data: self.process_batch_result(data, worker))
        # ...maar we ruimen de thread pas op als C++ zegt dat hij écht gestopt is!
        worker.finished.connect(lambda w=worker: self.cleanup_thread(w))
        
        if not hasattr(self, 'threads'): self.threads = []
        self.threads.append(worker)
        worker.start()

    def process_batch_result(self, data, worker):
        self.active_workers -= 1
        # Let op: We verwijderen de worker hier NIET meer uit de lijst, 
        # dat doet de cleanup_thread nu.

        if "error" not in data:
            meta = data["metadata"]
            payload = {
                "bedrijf": meta.get('BEDRIJFSNAAM', ["Onbekend"])[0] if meta.get('BEDRIJFSNAAM') else "Onbekend",
                "kvk_nummer": meta.get('KVK_NR', [None])[0] if meta.get('KVK_NR') else None,
                "btw_nummer": meta.get('BTW_NR', [None])[0] if meta.get('BTW_NR') else None,
                "iban": meta.get('IBAN', [None])[0] if meta.get('IBAN') else None,
                "subtotaal_excl": meta.get('SUBTOTAAL_EXCL', [None])[0] if meta.get('SUBTOTAAL_EXCL') else None,
                "btw_bedrag": meta.get('BTW_BEDRAG', [None])[0] if meta.get('BTW_BEDRAG') else None,
                "totaal_incl": meta.get('TOTAAL_INCL', [None])[0] if meta.get('TOTAAL_INCL') else None,
                "datums": meta.get('DATUM', []),
                "status": "Gereed voor import",
                "toegevoegd_op": datetime.now().isoformat()
            }
            self.batch_results.append(payload)
            self.append_result_to_ui(data, payload)
        
        self.start_next_batch_item()

    def cleanup_thread(self, worker):
        """Zorgt voor een veilige verwijdering van threads zonder memory leaks of crashes"""
        if worker in self.threads:
            self.threads.remove(worker)
        worker.deleteLater() # Vertelt PySide om de thread netjes op te ruimen in de volgende event loop

    def append_result_to_ui(self, data, payload):
        is_dev = self.settings.value("dev_mode", "false") in [True, "true", "True", 1, "1"]
        
        def make_badge(items):
            if isinstance(items, str): items = [items]
            valid_items = [str(i).strip() for i in items if str(i).strip()]
            if not valid_items or valid_items == ["None"]: return "<span style='color: #888;'>Niet gevonden</span>"
            return " ".join([f"<span style='background-color: rgba(0, 196, 204, 0.15); border: 1px solid {Colors.accent}; color: {Colors.accent}; padding: 2px 8px; border-radius: 4px; font-weight: bold;'>{i}</span>" for i in valid_items])

        current_html = self.res_area.toHtml()
        
        new_entry = f"""
        <div style='margin-bottom: 30px; border: 1px solid {Colors.border}; border-radius: 10px; padding: 15px; background-color: {Colors.bg_card};'>
            <h3 style='color: {Colors.accent}; margin-top: 0;'>📄 {payload['bedrijf']}</h3>
            <table width="100%" cellpadding="5" cellspacing="0">
                <tr><td width="150" style="color: {Colors.text_sub};">TOTAAL (INCL)</td><td>{make_badge(payload['totaal_incl'])}</td></tr>
                <tr><td style="color: {Colors.text_sub};">BTW BEDRAG</td><td>{make_badge(payload['btw_bedrag'])}</td></tr>
                <tr><td style="color: {Colors.text_sub};">IBAN</td><td>{make_badge(payload['iban'])}</td></tr>
            </table>
        """
        
        if is_dev:
            json_str = json.dumps(payload, indent=4, ensure_ascii=False)
            new_entry += f"<pre style='background-color: {Colors.terminal_bg}; color: {Colors.terminal_text}; padding: 10px; margin-top: 10px; font-size: 11px;'>{json_str}</pre>"
        
        new_entry += "</div>"
        
        self.res_area.setHtml(current_html + new_entry)
        self.btn_save_data.setText(f"  Batch Opslaan ({len(self.batch_results)} facturen)")
        self.btn_save_data.setEnabled(True)
        self.btn_save_data.setStyleSheet("")

    def save_extracted_data(self):
        if not hasattr(self, 'batch_results') or not self.batch_results:
            return

        if not getattr(self, 'firebase_active', False):
            ToastNotification("Firebase niet verbonden!", self)
            return

        success_count = 0
        self.log_to_console(f"Bezig met uploaden van {len(self.batch_results)} records...")
        
        for payload in self.batch_results:
            try:
                self.db.child('facturen').push(payload)
                success_count += 1
            except Exception as e:
                self.log_to_console(f"Fout bij upload: {e}")

        self.btn_save_data.setText(f"  {success_count} Facturen Opgeslagen")
        self.btn_save_data.setEnabled(False)
        self.btn_save_data.setStyleSheet(f"background-color: {Colors.success}; color: #ffffff; border: none; font-weight: bold; border-radius: 10px; padding: 10px;")
        
        self.log_to_console(f"Batch voltooid: {success_count} records toegevoegd aan Firebase.")
        ToastNotification(f"Batch succesvol opgeslagen!", self)
        
        self.batch_results = []

    def show_dashboard(self):
        self.set_nav(self.btn_dash); self.pages.setCurrentIndex(0)

if __name__ == "__main__":
    app = QApplication(sys.argv); app.setStyle("Fusion")
    window = ITnomieCommandCenter(); window.show()
    sys.exit(app.exec())
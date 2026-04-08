"""
Aura-X Floating Orb Window — V5
A frameless, transparent, always-on-top floating orb.
Voice-first: always speaks responses. Text input available.
Click orb to speak. Type to command. Right-click for menu.
"""

import sys
import os
import subprocess
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QApplication, QSystemTrayIcon, QMenu, QLineEdit,
    QGraphicsOpacityEffect
)
from PyQt6.QtCore import (
    Qt, QTimer, QPoint, QPropertyAnimation, QEasingCurve,
    pyqtSignal, QSize
)
from PyQt6.QtGui import (
    QFont, QColor, QPainter, QIcon, QAction, QCursor,
    QLinearGradient, QBrush, QPen, QPixmap
)
from gui.theme import COLORS, FONTS, build_stylesheet
from gui.orb_widget import OrbWidget
from gui.workers import AIWorker, SystemCheckWorker, VoiceInputWorker, VoiceSpeakWorker
from core.assistant import AuraXAssistant
from core.logger import setup_logger

logger = setup_logger("aura_x.gui.orb_window")


class StatusRing(QLabel):
    """Tiny status text under the orb."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFont(QFont(FONTS["family"], 9))
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet(f"color: {COLORS['text_muted']}; background: transparent;")
        self.setText("Starting...")


class OrbWindow(QMainWindow):
    """
    The main Aura-X floating orb window.
    Frameless, transparent, always-on-top, voice-first.
    """

    def __init__(self):
        super().__init__()

        # Window flags: frameless, always on top, transparent
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet("background: transparent;")

        # Size
        self._orb_size = 180
        self.setFixedSize(self._orb_size + 120, self._orb_size + 120)

        # Position: bottom-right of screen
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            x = geo.right() - self.width() - 30
            y = geo.bottom() - self.height() - 30
            self.move(x, y)

        # Drag support
        self._drag_pos = None
        self._press_pos = None

        # Workers
        self._current_worker = None
        self._voice_worker = None
        self._speak_worker = None

        # Initialize assistant
        self.assistant = AuraXAssistant()
        self.assistant.start()

        self._setup_ui()
        self._setup_tray()

        # Startup: run checks then greet
        QTimer.singleShot(500, self._run_system_check)

    def _setup_ui(self):
        central = QWidget()
        central.setStyleSheet("background: transparent;")
        self.setCentralWidget(central)

        layout = QVBoxLayout(central)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(6)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Orb
        orb_container = QHBoxLayout()
        orb_container.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._orb = OrbWidget(self._orb_size)
        self._orb.setCursor(Qt.CursorShape.PointingHandCursor)
        orb_container.addWidget(self._orb)
        layout.addLayout(orb_container)

        # Status text under orb
        self._status = StatusRing()
        layout.addWidget(self._status, alignment=Qt.AlignmentFlag.AlignCenter)

        # Text input below the orb
        self._text_input = QLineEdit()
        self._text_input.setPlaceholderText("Type a command...")
        self._text_input.setFont(QFont(FONTS["family"], FONTS["size_sm"]))
        self._text_input.setFixedHeight(34)
        self._text_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: rgba(6, 8, 15, 0.85);
                color: {COLORS['text_primary']};
                border: 1px solid rgba(0, 212, 255, 0.2);
                border-radius: 12px;
                padding: 4px 14px;
            }}
            QLineEdit:focus {{
                border-color: {COLORS['accent_cyan']};
            }}
        """)
        self._text_input.returnPressed.connect(self._on_text_enter)
        layout.addWidget(self._text_input)

    # ─── Startup ──────────────────────────────────────────────

    def _run_system_check(self):
        worker = SystemCheckWorker()
        worker.check_complete.connect(self._on_check_done)
        self._check_worker = worker
        worker.start()

    def _on_check_done(self, status: dict):
        """After system check, speak the greeting."""
        parts = []
        if status.get("ollama", {}).get("available"):
            n = len(status["ollama"].get("models", []))
            parts.append(f"{n} AI models")
        if status.get("screen", {}).get("available"):
            parts.append("screen control")
        if status.get("voice", {}).get("available"):
            parts.append("voice")

        if parts:
            self._status.setText("Ready")
            self._status.setStyleSheet(f"color: {COLORS['accent_green']}; background: transparent;")
        else:
            self._status.setText("⚠ No AI backend")
            self._status.setStyleSheet(f"color: {COLORS['accent_red']}; background: transparent;")

        # Speak greeting
        greeting = "Hello Prateek! Main Aura X hoon, ready at your service. Click karke bolo ya type karo, main sab samajh lunga."
        self._speak_text(greeting)

    def _speak_text(self, text: str):
        """Speak text using a background worker with proper orb animation."""
        if not self.assistant.speaker:
            self._status.setText("Ready")
            return

        worker = VoiceSpeakWorker(self.assistant.speaker, text)
        worker.speaking_started.connect(self._on_speaking_started)
        worker.speaking_finished.connect(self._on_speaking_finished)
        self._speak_worker = worker
        worker.start()

    # ─── System Tray ──────────────────────────────────────────

    def _setup_tray(self):
        """System tray icon with context menu."""
        pixmap = QPixmap(32, 32)
        pixmap.fill(QColor("transparent"))
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        grad = QLinearGradient(0, 0, 32, 32)
        grad.setColorAt(0, QColor(COLORS["accent_cyan"]))
        grad.setColorAt(1, QColor(COLORS["accent_purple"]))
        painter.setBrush(QBrush(grad))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(4, 4, 24, 24)
        painter.end()

        icon = QIcon(pixmap)
        self._tray = QSystemTrayIcon(icon, self)
        self._tray.setToolTip("Aura-X — AI Desktop Assistant")

        menu = QMenu()
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {COLORS['bg_card']};
                color: {COLORS['text_primary']};
                border: 1px solid {COLORS['border_primary']};
                border-radius: 8px;
                padding: 6px;
            }}
            QMenu::item:selected {{
                background-color: {COLORS['bg_hover']};
                color: {COLORS['accent_cyan']};
            }}
        """)

        show_action = QAction("✦ Show Orb", self)
        show_action.triggered.connect(self.show)
        menu.addAction(show_action)

        listen_action = QAction("🎤 Listen", self)
        listen_action.triggered.connect(self._start_listening)
        menu.addAction(listen_action)

        menu.addSeparator()

        quit_action = QAction("✕ Quit", self)
        quit_action.triggered.connect(self._quit)
        menu.addAction(quit_action)

        self._tray.setContextMenu(menu)
        self._tray.activated.connect(self._on_tray_click)
        self._tray.show()

    def _on_tray_click(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            if self.isVisible():
                self.hide()
            else:
                self.show()
                self.activateWindow()

    # ─── Mouse Events (Drag + Click) ─────────────────────────

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.pos()
            self._press_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if self._drag_pos and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self._press_pos and (event.globalPosition().toPoint() - self._press_pos).manhattanLength() < 5:
                self._start_listening()
        self._drag_pos = None

    def contextMenuEvent(self, event):
        """Right-click context menu on the orb."""
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {COLORS['bg_card']};
                color: {COLORS['text_primary']};
                border: 1px solid {COLORS['border_primary']};
                border-radius: 10px;
                padding: 6px;
                font-size: {FONTS['size_sm']}px;
            }}
            QMenu::item {{
                padding: 8px 20px;
                border-radius: 6px;
            }}
            QMenu::item:selected {{
                background-color: {COLORS['bg_hover']};
                color: {COLORS['accent_cyan']};
            }}
        """)

        listen_action = QAction("🎤  Listen", self)
        listen_action.triggered.connect(self._start_listening)
        menu.addAction(listen_action)

        menu.addSeparator()

        organize_action = QAction("📂  Organize Desktop", self)
        organize_action.triggered.connect(lambda: self._process_command("Organize my Desktop folder"))
        menu.addAction(organize_action)

        screen_action = QAction("🔍  What's on Screen?", self)
        screen_action.triggered.connect(lambda: self._process_command("What's on my screen right now?"))
        menu.addAction(screen_action)

        open_chrome = QAction("🌐  Open Chrome", self)
        open_chrome.triggered.connect(lambda: self._process_command("Open Google Chrome"))
        menu.addAction(open_chrome)

        menu.addSeparator()

        quit_action = QAction("✕  Quit Aura-X", self)
        quit_action.triggered.connect(self._quit)
        menu.addAction(quit_action)

        menu.exec(event.globalPos())

    # ─── Text Input ───────────────────────────────────────────

    def _on_text_enter(self):
        """Handle typed command."""
        text = self._text_input.text().strip()
        if text:
            self._text_input.clear()
            self._process_command(text)

    # ─── Voice Input ──────────────────────────────────────────

    def _start_listening(self):
        """Start microphone input."""
        # Don't listen while already busy
        if self._voice_worker and self._voice_worker.isRunning():
            return
        if self._current_worker and self._current_worker.isRunning():
            return
        if self._speak_worker and self._speak_worker.isRunning():
            return

        self._orb.set_state("listening")
        self._status.setText("Listening...")
        self._status.setStyleSheet(f"color: {COLORS['accent_amber']}; background: transparent;")

        worker = VoiceInputWorker()
        worker.text_recognized.connect(self._on_voice_recognized)
        worker.listening_stopped.connect(self._on_listening_stopped)
        worker.error_occurred.connect(self._on_voice_error)
        self._voice_worker = worker
        worker.start()

    def _on_voice_recognized(self, text: str):
        """Voice recognized — process the command."""
        self._status.setText(f"Got it!")
        self._process_command(text)

    def _on_listening_stopped(self):
        if not (self._current_worker and self._current_worker.isRunning()):
            self._orb.set_state("idle")
            self._status.setText("Ready")
            self._status.setStyleSheet(f"color: {COLORS['text_muted']}; background: transparent;")

    def _on_voice_error(self, error: str):
        self._orb.set_state("idle")
        self._status.setText(error)
        self._status.setStyleSheet(f"color: {COLORS['accent_red']}; background: transparent;")
        # Speak the error too
        if "try again" in error.lower():
            self._speak_text("Sorry boss, samajh nahi aaya. Dobara try karo.")
        QTimer.singleShot(4000, lambda: (
            self._status.setText("Ready"),
            self._status.setStyleSheet(f"color: {COLORS['text_muted']}; background: transparent;")
        ))

    # ─── Command Processing ───────────────────────────────────

    def _process_command(self, text: str):
        """Process a voice or text command through the AI."""
        # Prevent double processing
        if self._current_worker and self._current_worker.isRunning():
            return

        self._orb.set_state("thinking")
        self._status.setText("Thinking...")
        self._status.setStyleSheet(f"color: {COLORS['accent_purple']}; background: transparent;")

        worker = AIWorker(self.assistant, text)
        worker.response_ready.connect(self._on_response)
        worker.error_occurred.connect(self._on_error)
        worker.speaking_started.connect(self._on_speaking_started)
        worker.speaking_finished.connect(self._on_speaking_finished)
        worker.finished_processing.connect(self._on_done)
        self._current_worker = worker
        worker.start()

    def _on_response(self, response: str):
        """AI response received — speech is handled by the worker."""
        logger.info(f"AI response: {response[:100]}")

    def _on_error(self, error: str):
        self._orb.set_state("idle")
        self._status.setText("Error")
        self._status.setStyleSheet(f"color: {COLORS['accent_red']}; background: transparent;")
        # Speak the error
        self._speak_text(f"Sorry Prateek, ek error aaya: {error[:60]}")
        QTimer.singleShot(5000, lambda: (
            self._status.setText("Ready"),
            self._status.setStyleSheet(f"color: {COLORS['text_muted']}; background: transparent;")
        ))

    def _on_speaking_started(self):
        self._orb.set_state("speaking")
        self._status.setText("Speaking...")
        self._status.setStyleSheet(f"color: {COLORS['accent_green']}; background: transparent;")

    def _on_speaking_finished(self):
        self._orb.set_state("idle")
        self._status.setText("Ready")
        self._status.setStyleSheet(f"color: {COLORS['text_muted']}; background: transparent;")

    def _on_done(self):
        """All processing complete."""
        if not (self._speak_worker and self._speak_worker.isRunning()):
            self._orb.set_state("idle")
            self._status.setText("Ready")
            self._status.setStyleSheet(f"color: {COLORS['text_muted']}; background: transparent;")

    # ─── Quit ─────────────────────────────────────────────────

    def _quit(self):
        self.assistant.stop()
        self._tray.hide()
        QApplication.quit()

    def closeEvent(self, event):
        # Hide to tray instead of closing
        self.hide()
        event.ignore()

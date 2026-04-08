"""
Aura-X Main Window — V2 Premium
Custom title bar, polished sidebar, animated status, premium layout.
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QFrame,
    QStackedWidget, QLabel, QApplication, QPushButton, QSizePolicy
)
from PyQt6.QtCore import Qt, QTimer, QSize, QPoint
from PyQt6.QtGui import QFont, QColor, QPainter, QLinearGradient, QBrush, QPen
from gui.theme import COLORS, FONTS, SPACING, RADIUS, build_stylesheet
from gui.widgets import SidebarButton, Separator, StatusDot, IconButton
from gui.chat_panel import ChatPanel
from gui.task_panel import TaskPanel
from gui.log_panel import LogPanel
from gui.settings_panel import SettingsPanel
from gui.workers import AIWorker, SystemCheckWorker, VoiceInputWorker
from core.assistant import AuraXAssistant
from core.logger import setup_logger

logger = setup_logger("aura_x.gui.main")


class GradientLine(QWidget):
    """A thin horizontal gradient line for visual accents."""

    def __init__(self, height: int = 2, parent=None):
        super().__init__(parent)
        self.setFixedHeight(height)

    def paintEvent(self, event):
        p = QPainter(self)
        grad = QLinearGradient(0, 0, self.width(), 0)
        grad.setColorAt(0, QColor(COLORS["accent_cyan"]))
        grad.setColorAt(0.5, QColor(COLORS["accent_purple"]))
        grad.setColorAt(1, QColor(COLORS["accent_pink"]))
        p.fillRect(self.rect(), QBrush(grad))
        p.end()


class CustomTitleBar(QFrame):
    """Modern custom title bar with gradient accent line."""

    def __init__(self, parent_window, parent=None):
        super().__init__(parent)
        self._parent_window = parent_window
        self._drag_pos = None
        self.setFixedHeight(42)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_titlebar']};
                border: none;
            }}
        """)
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 8, 0)
        layout.setSpacing(8)

        # App icon + name
        icon = QLabel("✦")
        icon.setFont(QFont(FONTS["family"], 12))
        icon.setStyleSheet(f"color: {COLORS['accent_cyan']};")
        layout.addWidget(icon)

        name = QLabel("Aura-X")
        name.setFont(QFont(FONTS["family"], FONTS["size_sm"], QFont.Weight.Bold))
        name.setStyleSheet(f"color: {COLORS['text_secondary']};")
        layout.addWidget(name)

        layout.addStretch()

        # Window controls
        for text, action, hover_color in [
            ("─", "minimize", COLORS["accent_amber"]),
            ("□", "maximize", COLORS["accent_green"]),
            ("✕", "close", COLORS["accent_red"]),
        ]:
            btn = QPushButton(text)
            btn.setFixedSize(32, 28)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFont(QFont(FONTS["family"], 10))
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent;
                    color: {COLORS['text_muted']};
                    border: none;
                    border-radius: 6px;
                }}
                QPushButton:hover {{
                    background-color: {hover_color};
                    color: {COLORS['bg_primary']};
                }}
            """)
            if action == "minimize":
                btn.clicked.connect(self._parent_window.showMinimized)
            elif action == "maximize":
                btn.clicked.connect(self._toggle_maximize)
            elif action == "close":
                btn.clicked.connect(self._parent_window.close)
            layout.addWidget(btn)

    def _toggle_maximize(self):
        if self._parent_window.isMaximized():
            self._parent_window.showNormal()
        else:
            self._parent_window.showMaximized()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self._parent_window.pos()

    def mouseMoveEvent(self, event):
        if self._drag_pos and event.buttons() & Qt.MouseButton.LeftButton:
            self._parent_window.move(event.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None

    def mouseDoubleClickEvent(self, event):
        self._toggle_maximize()


class MainWindow(QMainWindow):
    """Aura-X Main Application Window — V2 Premium."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Aura-X")

        # Frameless window with custom title bar
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)

        from core.config import CONFIG
        gui_cfg = CONFIG.get("gui", {})
        self.resize(gui_cfg.get("window_width", 1100), gui_cfg.get("window_height", 750))

        # Apply theme
        self.setStyleSheet(build_stylesheet())

        # Initialize assistant
        self.assistant = AuraXAssistant()
        self.assistant.start()

        self._current_worker = None
        self._setup_ui()
        self._connect_signals()
        self._run_system_check()

    def _setup_ui(self):
        central = QWidget()
        central.setStyleSheet(f"""
            QWidget {{
                background-color: {COLORS['bg_primary']};
                border: 1px solid {COLORS['border_primary']};
                border-radius: 12px;
            }}
        """)
        self.setCentralWidget(central)

        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # Custom title bar
        self._title_bar = CustomTitleBar(self)
        root_layout.addWidget(self._title_bar)

        # Gradient accent line under title bar
        root_layout.addWidget(GradientLine(2))

        # Main content
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ─── Sidebar ───
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(230)
        sidebar.setStyleSheet(f"""
            QFrame#sidebar {{
                background-color: {COLORS['bg_sidebar']};
                border-right: 1px solid {COLORS['border_primary']};
                border-radius: 0px;
            }}
        """)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(12, 20, 12, 16)
        sidebar_layout.setSpacing(4)

        # Logo
        logo_layout = QHBoxLayout()
        logo_layout.setSpacing(10)

        logo_dot = StatusDot(COLORS["accent_cyan"], 10, glow=True)
        logo_layout.addWidget(logo_dot)

        logo_label = QLabel("Aura-X")
        logo_label.setFont(QFont(FONTS["family"], FONTS["size_2xl"], QFont.Weight.Bold))
        logo_label.setStyleSheet(f"color: {COLORS['accent_cyan']};")
        logo_layout.addWidget(logo_label)
        logo_layout.addStretch()
        sidebar_layout.addLayout(logo_layout)

        version = QLabel("AI Desktop Agent  ·  v1.0")
        version.setFont(QFont(FONTS["family"], FONTS["size_xs"]))
        version.setStyleSheet(f"color: {COLORS['text_muted']}; padding-left: 24px;")
        sidebar_layout.addWidget(version)

        sidebar_layout.addSpacing(20)

        # Section label
        nav_label = QLabel("   NAVIGATION")
        nav_label.setFont(QFont(FONTS["family"], 9, QFont.Weight.Bold))
        nav_label.setStyleSheet(f"color: {COLORS['text_muted']}; letter-spacing: 1px;")
        sidebar_layout.addWidget(nav_label)
        sidebar_layout.addSpacing(6)

        # Nav buttons
        self._nav_buttons = []
        self._btn_chat = SidebarButton("💬", "Chat")
        self._btn_tasks = SidebarButton("⚡", "Agent Tasks")
        self._btn_logs = SidebarButton("📋", "System Logs")
        self._btn_settings = SidebarButton("⚙️", "Settings")

        for btn in [self._btn_chat, self._btn_tasks, self._btn_logs, self._btn_settings]:
            sidebar_layout.addWidget(btn)
            self._nav_buttons.append(btn)

        self._btn_chat.set_active(True)

        sidebar_layout.addStretch()

        # Status section
        sidebar_layout.addWidget(Separator())
        sidebar_layout.addSpacing(10)

        status_label = QLabel("   SYSTEM STATUS")
        status_label.setFont(QFont(FONTS["family"], 9, QFont.Weight.Bold))
        status_label.setStyleSheet(f"color: {COLORS['text_muted']}; letter-spacing: 1px;")
        sidebar_layout.addWidget(status_label)
        sidebar_layout.addSpacing(6)

        self._status_items = {}
        for component in ["Ollama", "NVIDIA API", "Screen Control", "UI Automation", "OCR Engine", "Voice Output"]:
            row = QHBoxLayout()
            row.setSpacing(8)
            row.setContentsMargins(8, 0, 0, 0)

            dot = StatusDot(COLORS["status_offline"], 7)
            label = QLabel(component)
            label.setFont(QFont(FONTS["family"], FONTS["size_xs"]))
            label.setStyleSheet(f"color: {COLORS['text_secondary']};")
            row.addWidget(dot)
            row.addWidget(label)
            row.addStretch()
            self._status_items[component] = dot
            sidebar_layout.addLayout(row)

        sidebar_layout.addSpacing(10)

        # Model badge
        self._model_label = QLabel("  🧠  No model active")
        self._model_label.setFont(QFont(FONTS["family"], FONTS["size_xs"]))
        self._model_label.setStyleSheet(f"""
            color: {COLORS['text_muted']};
            background-color: {COLORS['bg_card']};
            border: 1px solid {COLORS['border_primary']};
            border-radius: 8px;
            padding: 6px 10px;
        """)
        sidebar_layout.addWidget(self._model_label)

        main_layout.addWidget(sidebar)

        # ─── Content Stack ───
        self._stack = QStackedWidget()
        self._stack.setStyleSheet(f"background-color: {COLORS['bg_primary']}; border: none;")

        self._chat_panel = ChatPanel()
        self._task_panel = TaskPanel()
        self._log_panel = LogPanel()
        self._settings_panel = SettingsPanel()

        self._stack.addWidget(self._chat_panel)
        self._stack.addWidget(self._task_panel)
        self._stack.addWidget(self._log_panel)
        self._stack.addWidget(self._settings_panel)

        main_layout.addWidget(self._stack, 1)
        root_layout.addLayout(main_layout, 1)

    def _connect_signals(self):
        self._btn_chat.clicked.connect(lambda: self._switch_panel(0))
        self._btn_tasks.clicked.connect(lambda: self._switch_panel(1))
        self._btn_logs.clicked.connect(lambda: self._switch_panel(2))
        self._btn_settings.clicked.connect(lambda: self._switch_panel(3))
        self._chat_panel.message_sent.connect(self._on_message_sent)
        self._chat_panel.watch_toggled.connect(self._on_watch_toggled)
        self._chat_panel._voice_btn.clicked.connect(self._on_voice_input)
        self._task_panel.stop_requested.connect(self._on_stop_agent)
        self._settings_panel.settings_changed.connect(self._on_settings_changed)

    def _switch_panel(self, index: int):
        self._stack.setCurrentIndex(index)
        for i, btn in enumerate(self._nav_buttons):
            btn.set_active(i == index)

    def _on_message_sent(self, text: str):
        self._chat_panel.show_thinking(True)
        self._chat_panel.set_input_enabled(False)

        worker = AIWorker(self.assistant, text)
        worker.response_ready.connect(self._on_response_ready)
        worker.error_occurred.connect(self._on_response_error)
        worker.model_used.connect(self._on_model_used)
        worker.finished_processing.connect(self._on_processing_done)
        worker.speaking_started.connect(lambda: self._chat_panel.set_orb_state("speaking"))
        worker.speaking_finished.connect(lambda: self._chat_panel.set_orb_state("idle"))
        self._current_worker = worker
        worker.start()

    def _on_response_ready(self, response: str):
        model = self.assistant.ai_router.get_last_model()
        self._chat_panel.add_assistant_message(response, model_info=model)

    def _on_response_error(self, error: str):
        self._chat_panel.add_error_message(error)

    def _on_model_used(self, model: str):
        self._model_label.setText(f"  🧠  {model}")
        self._model_label.setStyleSheet(f"""
            color: {COLORS['accent_cyan']};
            background-color: rgba(0, 212, 255, 0.06);
            border: 1px solid rgba(0, 212, 255, 0.15);
            border-radius: 8px;
            padding: 6px 10px;
        """)

    def _on_processing_done(self):
        self._chat_panel.show_thinking(False)
        self._chat_panel.set_input_enabled(True)
        self._current_worker = None

    def _on_stop_agent(self):
        if self._current_worker:
            self._current_worker.cancel()
        self._chat_panel.add_system_message("Agent stopped by user")

    def _on_settings_changed(self, settings: dict):
        if settings.get("_action") == "clear_memory":
            self.assistant.memory_manager.clear_all()
            self._chat_panel.add_system_message("All memory cleared")
            return
        self._chat_panel.add_system_message("Settings saved ✓")

    def _on_voice_input(self):
        """Start voice input from the microphone."""
        self._chat_panel.set_orb_state("listening")
        self._chat_panel.add_system_message("🎤 Listening...")

        worker = VoiceInputWorker()
        worker.text_recognized.connect(self._on_voice_recognized)
        worker.listening_stopped.connect(lambda: self._chat_panel.set_orb_state("idle"))
        worker.error_occurred.connect(self._on_voice_error)
        self._voice_worker = worker
        worker.start()

    def _on_voice_recognized(self, text: str):
        """Handle recognized speech text."""
        self._chat_panel.set_orb_state("idle")
        self._chat_panel.add_system_message(f"🎤 Heard: \"{text}\"")
        # Send it as a message
        self._on_message_sent(text)

    def _on_voice_error(self, error: str):
        self._chat_panel.set_orb_state("idle")
        self._chat_panel.add_system_message(f"🎤 {error}")

    def _on_watch_toggled(self, enabled: bool):
        """Toggle screen watch mode on the assistant."""
        if self.assistant.screen_monitor:
            self.assistant.screen_monitor.set_watch_mode(enabled)
            if enabled:
                # Update OCR status dot to show active
                if "OCR Engine" in self._status_items:
                    self._status_items["OCR Engine"].set_color(COLORS["accent_green"])
            else:
                # Revert to actual status
                ocr_ok = (self.assistant.screen_monitor._ocr_engine and
                          self.assistant.screen_monitor._ocr_engine.is_available())
                if "OCR Engine" in self._status_items:
                    color = COLORS["status_online"] if ocr_ok else COLORS["status_offline"]
                    self._status_items["OCR Engine"].set_color(color)

    def _run_system_check(self):
        worker = SystemCheckWorker()
        worker.status_update.connect(self._update_status)
        worker.check_complete.connect(self._on_system_check_done)
        self._system_check_worker = worker
        worker.start()

    def _update_status(self, component: str, available: bool):
        if component in self._status_items:
            color = COLORS["status_online"] if available else COLORS["status_offline"]
            self._status_items[component].set_color(color)

    def _on_system_check_done(self, status: dict):
        ollama = status.get("ollama", {})
        if ollama.get("available"):
            models = ollama.get("models", [])
            if models:
                self._chat_panel.add_system_message(
                    f"Ollama connected  ·  {len(models)} models available"
                )
            else:
                self._chat_panel.add_system_message("Ollama running  ·  No models installed")
        else:
            self._chat_panel.add_system_message(
                "⚠ Ollama not detected  ·  Run 'ollama serve' to enable local AI"
            )

    def closeEvent(self, event):
        self.assistant.stop()
        event.accept()

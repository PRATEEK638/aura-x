"""
Aura-X Chat Panel — V3 Orb Edition
Futuristic chat with animated AI sphere, voice output, and screen watch.
"""

from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QFrame,
    QLineEdit, QPushButton, QLabel, QSizePolicy, QTextEdit, QGridLayout
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QKeyEvent
from gui.theme import COLORS, FONTS, SPACING, RADIUS
from gui.widgets import MessageBubble, TypingIndicator, IconButton, FeatureCard
from gui.orb_widget import OrbWidget


class ChatInput(QTextEdit):
    """Multi-line chat input with Enter to send."""
    send_requested = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setPlaceholderText("  Message Aura-X...")
        self.setMaximumHeight(80)
        self.setMinimumHeight(46)
        self.setFont(QFont(FONTS["family"], FONTS["size_base"]))
        self.setAcceptRichText(False)
        self.setStyleSheet(f"""
            QTextEdit {{
                background-color: {COLORS['bg_input']};
                color: {COLORS['text_primary']};
                border: 1px solid {COLORS['border_primary']};
                border-radius: 14px;
                padding: 12px 16px;
                selection-background-color: rgba(0, 212, 255, 0.25);
            }}
            QTextEdit:focus {{
                border-color: {COLORS['accent_cyan']};
            }}
        """)

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                super().keyPressEvent(event)
            else:
                text = self.toPlainText().strip()
                if text:
                    self.send_requested.emit(text)
                    self.clear()
        else:
            super().keyPressEvent(event)


class ChatPanel(QWidget):
    """Futuristic chat panel with animated orb."""
    message_sent = pyqtSignal(str)
    watch_toggled = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._messages = []
        self._streaming_bubble = None
        self._streaming_text = ""
        self._watch_active = False
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ─── Header ───
        header = QFrame()
        header.setFixedHeight(56)
        header.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_secondary']};
                border-bottom: 1px solid {COLORS['border_primary']};
            }}
        """)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 0, 20, 0)

        # Title
        title_layout = QHBoxLayout()
        title_layout.setSpacing(8)
        icon_label = QLabel("✦")
        icon_label.setFont(QFont(FONTS["family"], FONTS["size_lg"]))
        icon_label.setStyleSheet(f"color: {COLORS['accent_cyan']};")
        title_layout.addWidget(icon_label)
        title = QLabel("Chat")
        title.setFont(QFont(FONTS["family"], FONTS["size_lg"], QFont.Weight.Bold))
        title.setStyleSheet(f"color: {COLORS['text_primary']};")
        title_layout.addWidget(title)
        header_layout.addLayout(title_layout)
        header_layout.addStretch()

        # Status badge
        self._status_badge = QLabel("  ● Online  ")
        self._status_badge.setFont(QFont(FONTS["family"], FONTS["size_xs"], QFont.Weight.Bold))
        self._status_badge.setStyleSheet(f"""
            color: {COLORS['accent_green']};
            background-color: rgba(16, 185, 129, 0.1);
            border: 1px solid rgba(16, 185, 129, 0.2);
            border-radius: 10px; padding: 3px 10px;
        """)
        header_layout.addWidget(self._status_badge)

        # Screen Watch toggle
        self._watch_btn = QPushButton("  👁  Screen Watch  ")
        self._watch_btn.setCheckable(True)
        self._watch_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._watch_btn.setFont(QFont(FONTS["family"], FONTS["size_xs"], QFont.Weight.Bold))
        self._watch_btn.setToolTip("Toggle real-time screen monitoring")
        self._watch_btn.clicked.connect(self._toggle_watch)
        self._update_watch_style(False)
        header_layout.addWidget(self._watch_btn)

        # Clear
        clear_btn = IconButton("🗑")
        clear_btn.setToolTip("Clear chat")
        clear_btn.clicked.connect(self.clear_chat)
        header_layout.addWidget(clear_btn)

        layout.addWidget(header)

        # ─── Messages Area ───
        self._scroll_area = QScrollArea()
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll_area.setStyleSheet(f"QScrollArea {{ border: none; background: {COLORS['bg_primary']}; }}")

        self._messages_container = QWidget()
        self._messages_container.setStyleSheet(f"background: {COLORS['bg_primary']};")
        self._messages_layout = QVBoxLayout(self._messages_container)
        self._messages_layout.setContentsMargins(12, 16, 12, 16)
        self._messages_layout.setSpacing(6)
        self._messages_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Welcome screen with orb
        self._welcome = self._create_welcome()
        self._messages_layout.addWidget(self._welcome)
        self._messages_layout.addStretch()

        self._scroll_area.setWidget(self._messages_container)
        layout.addWidget(self._scroll_area, 1)

        # Typing indicator
        self._typing_indicator = TypingIndicator()
        self._typing_indicator.hide()
        layout.addWidget(self._typing_indicator)

        # ─── Input Area ───
        input_frame = QFrame()
        input_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_secondary']};
                border-top: 1px solid {COLORS['border_primary']};
            }}
        """)
        input_layout = QHBoxLayout(input_frame)
        input_layout.setContentsMargins(16, 12, 16, 12)
        input_layout.setSpacing(10)

        # Voice button
        self._voice_btn = QPushButton("🎤")
        self._voice_btn.setToolTip("Voice input")
        self._voice_btn.setFixedSize(42, 42)
        self._voice_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._voice_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['bg_card']};
                border: 1px solid {COLORS['border_primary']};
                border-radius: 12px; font-size: 16px;
            }}
            QPushButton:hover {{
                background-color: {COLORS['bg_hover']};
                border-color: {COLORS['accent_cyan']};
            }}
        """)
        input_layout.addWidget(self._voice_btn)

        # Text input
        self._input = ChatInput()
        self._input.send_requested.connect(self._on_send)
        input_layout.addWidget(self._input, 1)

        # Send button
        self._send_btn = QPushButton("↑")
        self._send_btn.setFixedSize(44, 44)
        self._send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._send_btn.clicked.connect(self._on_send_click)
        self._send_btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                            stop:0 {COLORS['accent_cyan']}, stop:1 {COLORS['accent_purple']});
                color: {COLORS['bg_primary']}; border: none;
                border-radius: 14px; font-size: 20px; font-weight: bold;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                            stop:0 #33DFFF, stop:1 #C084FC);
            }}
            QPushButton:disabled {{
                background: {COLORS['bg_tertiary']}; color: {COLORS['text_muted']};
            }}
        """)
        input_layout.addWidget(self._send_btn)

        layout.addWidget(input_frame)

    def _create_welcome(self) -> QWidget:
        """Welcome screen with animated orb and feature cards."""
        container = QWidget()
        container.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(24, 20, 24, 10)
        layout.setSpacing(0)

        # ─── Animated Orb ───
        orb_container = QHBoxLayout()
        orb_container.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._orb = OrbWidget(160)
        orb_container.addWidget(self._orb)
        layout.addLayout(orb_container)

        layout.addSpacing(4)

        # Title
        hero = QLabel("Aura-X")
        hero.setFont(QFont(FONTS["family"], FONTS["size_3xl"], QFont.Weight.Bold))
        hero.setStyleSheet(f"color: {COLORS['accent_cyan']};")
        hero.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(hero)

        subtitle = QLabel("Your intelligent desktop AI assistant")
        subtitle.setFont(QFont(FONTS["family"], FONTS["size_md"]))
        subtitle.setStyleSheet(f"color: {COLORS['text_secondary']};")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)

        layout.addSpacing(4)

        desc = QLabel("I can see your screen, control your computer, and help with any task.")
        desc.setFont(QFont(FONTS["family"], FONTS["size_sm"]))
        desc.setStyleSheet(f"color: {COLORS['text_muted']};")
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(desc)

        layout.addSpacing(24)

        # Section label
        section = QLabel("Try something...")
        section.setFont(QFont(FONTS["family"], FONTS["size_sm"], QFont.Weight.Bold))
        section.setStyleSheet(f"color: {COLORS['text_muted']}; padding-left: 4px;")
        layout.addWidget(section)
        layout.addSpacing(8)

        # Feature cards grid
        grid = QGridLayout()
        grid.setSpacing(10)

        cards = [
            ("🌐", "Open an App", "\"Open Chrome and go to GitHub\"", COLORS["accent_cyan"]),
            ("📂", "Organize Files", "\"Organize my Desktop\"", COLORS["accent_green"]),
            ("💻", "Write Code", "\"Write a Python web scraper\"", COLORS["accent_purple"]),
            ("👁", "Screen Analysis", "\"What's on my screen?\"", COLORS["accent_amber"]),
            ("📝", "Create Documents", "\"Make a report in Word\"", COLORS["accent_blue"]),
            ("⚡", "Automate Task", "\"Close all Chrome windows\"", COLORS["accent_pink"]),
        ]

        for i, (emoji, title_text, desc_text, accent) in enumerate(cards):
            card = FeatureCard(emoji, title_text, desc_text, accent)
            card.mousePressEvent = lambda e, d=desc_text: self._on_feature_click(d)
            grid.addWidget(card, i // 3, i % 3)

        layout.addLayout(grid)
        layout.addStretch()

        return container

    # ─── Orb State Control ──────────────────────────────────

    def set_orb_state(self, state: str):
        """Set the orb state: idle, thinking, speaking, listening."""
        if hasattr(self, '_orb'):
            self._orb.set_state(state)

    def set_orb_amplitude(self, amplitude: float):
        """Set speech amplitude for orb vibration."""
        if hasattr(self, '_orb'):
            self._orb.set_amplitude(amplitude)

    # ─── Feature Card Click ─────────────────────────────────

    def _on_feature_click(self, description: str):
        text = description.strip('"')
        self._input.setText(text)
        self._input.setFocus()

    # ─── Send / Receive ─────────────────────────────────────

    def _on_send(self, text: str = None):
        if text is None:
            text = self._input.toPlainText().strip()
            if not text:
                return
            self._input.clear()
        if self._welcome.isVisible():
            self._welcome.hide()
        self.add_user_message(text)
        self.message_sent.emit(text)

    def _on_send_click(self):
        self._on_send()

    def add_user_message(self, text: str):
        timestamp = datetime.now().strftime("%H:%M")
        bubble = MessageBubble(text, is_user=True, timestamp=timestamp)
        self._insert_message(bubble)

    def add_assistant_message(self, text: str, model_info: str = ""):
        timestamp = datetime.now().strftime("%H:%M")
        bubble = MessageBubble(text, is_user=False, model_info=model_info, timestamp=timestamp)
        self._insert_message(bubble)
        self._streaming_bubble = None

    def start_streaming(self):
        self._streaming_text = ""
        bubble = MessageBubble("", is_user=False, timestamp=datetime.now().strftime("%H:%M"))
        self._streaming_bubble = bubble
        self._insert_message(bubble)

    def append_stream_chunk(self, chunk: str):
        if self._streaming_bubble:
            self._streaming_text += chunk
            self._streaming_bubble.update_text(self._streaming_text)
            self._scroll_to_bottom()

    def finish_streaming(self, model_info: str = ""):
        self._streaming_bubble = None

    def add_error_message(self, text: str):
        error_frame = QFrame()
        error_frame.setStyleSheet(f"""
            QFrame {{
                background-color: rgba(239, 68, 68, 0.08);
                border: 1px solid rgba(239, 68, 68, 0.2);
                border-radius: {RADIUS['lg']}px;
                margin: 4px 60px 4px 60px;
            }}
        """)
        error_layout = QHBoxLayout(error_frame)
        error_layout.setContentsMargins(16, 12, 16, 12)
        icon = QLabel("⚠")
        icon.setFont(QFont(FONTS["family"], FONTS["size_lg"]))
        error_layout.addWidget(icon)
        msg = QLabel(text)
        msg.setFont(QFont(FONTS["family"], FONTS["size_sm"]))
        msg.setStyleSheet(f"color: {COLORS['accent_red']};")
        msg.setWordWrap(True)
        error_layout.addWidget(msg, 1)
        self._insert_message(error_frame)

    def add_system_message(self, text: str):
        label = QLabel(f"  ──  {text}  ──")
        label.setFont(QFont(FONTS["family"], FONTS["size_xs"]))
        label.setStyleSheet(f"color: {COLORS['text_muted']}; padding: 6px 0;")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setWordWrap(True)
        self._insert_message(label)

    # ─── Status ─────────────────────────────────────────────

    def show_thinking(self, show: bool = True):
        if show:
            self._typing_indicator.start()
            self.set_orb_state("thinking")
            self._status_badge.setText("  ● Thinking  ")
            self._status_badge.setStyleSheet(f"""
                color: {COLORS['accent_amber']};
                background-color: rgba(245, 158, 11, 0.1);
                border: 1px solid rgba(245, 158, 11, 0.2);
                border-radius: 10px; padding: 3px 10px;
            """)
        else:
            self._typing_indicator.stop()
            self.set_orb_state("idle")
            self._status_badge.setText("  ● Online  ")
            self._status_badge.setStyleSheet(f"""
                color: {COLORS['accent_green']};
                background-color: rgba(16, 185, 129, 0.1);
                border: 1px solid rgba(16, 185, 129, 0.2);
                border-radius: 10px; padding: 3px 10px;
            """)

    def set_input_enabled(self, enabled: bool):
        self._input.setEnabled(enabled)
        self._send_btn.setEnabled(enabled)
        self._voice_btn.setEnabled(enabled)

    # ─── Screen Watch ───────────────────────────────────────

    def _toggle_watch(self):
        self._watch_active = not self._watch_active
        self._update_watch_style(self._watch_active)
        self.watch_toggled.emit(self._watch_active)
        if self._watch_active:
            self.add_system_message("👁 Screen Watch ON — I can now see your screen in real-time")
        else:
            self.add_system_message("Screen Watch OFF")

    def _update_watch_style(self, active: bool):
        if active:
            self._watch_btn.setStyleSheet(f"""
                QPushButton {{
                    color: {COLORS['accent_green']};
                    background-color: rgba(16, 185, 129, 0.15);
                    border: 1px solid rgba(16, 185, 129, 0.3);
                    border-radius: 10px; padding: 3px 10px;
                }}
                QPushButton:hover {{ background-color: rgba(16, 185, 129, 0.25); }}
            """)
        else:
            self._watch_btn.setStyleSheet(f"""
                QPushButton {{
                    color: {COLORS['text_muted']};
                    background-color: {COLORS['bg_card']};
                    border: 1px solid {COLORS['border_primary']};
                    border-radius: 10px; padding: 3px 10px;
                }}
                QPushButton:hover {{ border-color: {COLORS['accent_cyan']}; color: {COLORS['text_primary']}; }}
            """)

    # ─── Helpers ────────────────────────────────────────────

    def _insert_message(self, widget):
        count = self._messages_layout.count()
        self._messages_layout.insertWidget(count - 1, widget)
        self._scroll_to_bottom()

    def _scroll_to_bottom(self):
        QTimer.singleShot(50, lambda: self._scroll_area.verticalScrollBar().setValue(
            self._scroll_area.verticalScrollBar().maximum()
        ))

    def clear_chat(self):
        while self._messages_layout.count() > 0:
            item = self._messages_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._welcome = self._create_welcome()
        self._messages_layout.addWidget(self._welcome)
        self._messages_layout.addStretch()

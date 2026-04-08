"""
Aura-X Log Panel
Real-time log viewer with level filtering and color coding.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel,
    QScrollArea, QPlainTextEdit, QPushButton, QCheckBox
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QTextCharFormat, QColor, QTextCursor
from gui.theme import COLORS, FONTS, RADIUS
from core.logger import get_log_queue


LEVEL_COLORS = {
    "DEBUG": COLORS["text_muted"],
    "INFO": COLORS["accent_cyan"],
    "WARNING": COLORS["accent_amber"],
    "ERROR": COLORS["accent_red"],
    "CRITICAL": COLORS["accent_red"],
}


class LogPanel(QWidget):
    """Real-time log viewer panel."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._max_lines = 500
        self._filters = {"DEBUG": True, "INFO": True, "WARNING": True, "ERROR": True}
        self._setup_ui()
        self._start_polling()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = QFrame()
        header.setFixedHeight(56)
        header.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_secondary']};
                border-bottom: 1px solid {COLORS['border_primary']};
                border-radius: 0px;
            }}
        """)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 0, 20, 0)

        title = QLabel("📋  System Logs")
        title.setFont(QFont(FONTS["family"], FONTS["size_lg"], QFont.Weight.Bold))
        title.setStyleSheet(f"color: {COLORS['text_primary']}; background: transparent;")
        header_layout.addWidget(title)

        header_layout.addStretch()

        # Filter checkboxes
        for level in ["DEBUG", "INFO", "WARNING", "ERROR"]:
            cb = QCheckBox(level)
            cb.setChecked(self._filters[level])
            cb.setFont(QFont(FONTS["family"], FONTS["size_xs"]))
            color = LEVEL_COLORS.get(level, COLORS["text_primary"])
            cb.setStyleSheet(f"color: {color}; background: transparent; spacing: 4px;")
            cb.stateChanged.connect(lambda state, l=level: self._toggle_filter(l, state))
            header_layout.addWidget(cb)

        # Clear button
        clear_btn = QPushButton("🗑 Clear")
        clear_btn.setObjectName("iconButton")
        clear_btn.setFont(QFont(FONTS["family"], FONTS["size_sm"]))
        clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        clear_btn.clicked.connect(self._clear_logs)
        header_layout.addWidget(clear_btn)

        layout.addWidget(header)

        # Log display
        self._log_display = QPlainTextEdit()
        self._log_display.setReadOnly(True)
        self._log_display.setMaximumBlockCount(self._max_lines)
        self._log_display.setFont(QFont(FONTS["family_mono"].split(",")[0].strip(), FONTS["size_sm"]))
        self._log_display.setStyleSheet(f"""
            QPlainTextEdit {{
                background-color: {COLORS['bg_primary']};
                color: {COLORS['text_secondary']};
                border: none;
                padding: 12px;
                selection-background-color: rgba(0, 212, 255, 0.2);
            }}
        """)
        layout.addWidget(self._log_display, 1)

        # Status bar
        status_bar = QFrame()
        status_bar.setFixedHeight(28)
        status_bar.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_secondary']};
                border-top: 1px solid {COLORS['border_primary']};
                border-radius: 0px;
            }}
        """)
        status_layout = QHBoxLayout(status_bar)
        status_layout.setContentsMargins(16, 0, 16, 0)

        self._line_count = QLabel("0 entries")
        self._line_count.setFont(QFont(FONTS["family"], FONTS["size_xs"]))
        self._line_count.setStyleSheet(f"color: {COLORS['text_muted']}; background: transparent;")
        status_layout.addWidget(self._line_count)

        status_layout.addStretch()

        layout.addWidget(status_bar)

    def _start_polling(self):
        """Poll the log queue for new entries."""
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._poll_logs)
        self._timer.start(300)  # 300ms polling

    def _poll_logs(self):
        """Read new log entries from the queue."""
        log_queue = get_log_queue()
        entries_added = 0
        while not log_queue.empty() and entries_added < 20:
            try:
                entry = log_queue.get_nowait()
                level = entry.get("level", "INFO")
                if self._filters.get(level, True):
                    self._append_entry(entry)
                    entries_added += 1
            except Exception:
                break

        if entries_added > 0:
            count = self._log_display.document().blockCount()
            self._line_count.setText(f"{count} entries")

    def _append_entry(self, entry: dict):
        """Append a formatted log entry."""
        level = entry.get("level", "INFO")
        timestamp = entry.get("timestamp", "")
        name = entry.get("name", "")
        message = entry.get("message", "")

        color = LEVEL_COLORS.get(level, COLORS["text_secondary"])

        # Format: [HH:MM:SS] [LEVEL] module: message
        cursor = self._log_display.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)

        fmt = QTextCharFormat()
        fmt.setForeground(QColor(COLORS["text_muted"]))
        cursor.insertText(f"[{timestamp}] ", fmt)

        fmt.setForeground(QColor(color))
        fmt.setFontWeight(QFont.Weight.Bold)
        cursor.insertText(f"[{level:>7}] ", fmt)

        fmt.setForeground(QColor(COLORS["text_muted"]))
        fmt.setFontWeight(QFont.Weight.Normal)
        cursor.insertText(f"{name}: ", fmt)

        fmt.setForeground(QColor(COLORS["text_secondary"]))
        cursor.insertText(f"{message}\n", fmt)

        # Auto-scroll
        self._log_display.setTextCursor(cursor)
        self._log_display.ensureCursorVisible()

    def _toggle_filter(self, level: str, state: int):
        self._filters[level] = state == Qt.CheckState.Checked.value

    def _clear_logs(self):
        self._log_display.clear()
        self._line_count.setText("0 entries")

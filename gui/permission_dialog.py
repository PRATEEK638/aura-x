"""
Aura-X Permission Popup
A small dark popup that appears near the orb when the agent needs permission.
Shows action description, risk level, and Allow/Deny buttons.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QColor
from gui.theme import COLORS, FONTS, RADIUS


class PermissionPopup(QDialog):
    """
    Permission popup that appears when the agent wants to do something sensitive.
    Returns True if allowed, False if denied.
    """

    def __init__(self, tool: str, params: dict, explanation: str,
                 risk: str = "moderate", parent=None):
        super().__init__(parent)

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Dialog
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setModal(True)
        self._result = False

        # Auto-deny after 30 seconds
        self._timeout = QTimer(self)
        self._timeout.setSingleShot(True)
        self._timeout.timeout.connect(self.reject)
        self._timeout.start(30000)

        self._setup_ui(tool, explanation, risk)

        # Position near cursor
        from PyQt6.QtGui import QCursor
        pos = QCursor.pos()
        self.move(pos.x() - 160, pos.y() - 200)

    def _setup_ui(self, tool: str, explanation: str, risk: str):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        card = QFrame()
        card.setFixedWidth(340)
        risk_border = COLORS['accent_amber'] if risk == "moderate" else COLORS['accent_red']
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_card']};
                border: 1px solid {risk_border};
                border-radius: {RADIUS['xl']}px;
            }}
        """)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 18, 20, 18)
        card_layout.setSpacing(12)

        # Header
        header = QHBoxLayout()
        risk_icon = "⚠" if risk == "moderate" else "🛑"
        risk_text = "Permission Required" if risk == "moderate" else "Critical Action"
        risk_color = COLORS['accent_amber'] if risk == "moderate" else COLORS['accent_red']

        icon_label = QLabel(risk_icon)
        icon_label.setFont(QFont(FONTS["family"], FONTS["size_xl"]))
        header.addWidget(icon_label)

        title = QLabel(risk_text)
        title.setFont(QFont(FONTS["family"], FONTS["size_md"], QFont.Weight.Bold))
        title.setStyleSheet(f"color: {risk_color};")
        header.addWidget(title)
        header.addStretch()
        card_layout.addLayout(header)

        # Description
        desc = QLabel(f"Aura-X wants to: {explanation}")
        desc.setFont(QFont(FONTS["family"], FONTS["size_sm"]))
        desc.setStyleSheet(f"color: {COLORS['text_primary']};")
        desc.setWordWrap(True)
        card_layout.addWidget(desc)

        # Tool name
        tool_label = QLabel(f"Tool: {tool}")
        tool_label.setFont(QFont(FONTS["family"], FONTS["size_xs"]))
        tool_label.setStyleSheet(f"""
            color: {COLORS['text_muted']};
            background-color: {COLORS['bg_tertiary']};
            border-radius: 6px;
            padding: 4px 10px;
        """)
        card_layout.addWidget(tool_label)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        deny_btn = QPushButton("✕  Deny")
        deny_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        deny_btn.setFont(QFont(FONTS["family"], FONTS["size_sm"], QFont.Weight.Bold))
        deny_btn.setMinimumHeight(38)
        deny_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: rgba(239, 68, 68, 0.1);
                color: {COLORS['accent_red']};
                border: 1px solid rgba(239, 68, 68, 0.3);
                border-radius: 10px;
                padding: 6px 20px;
            }}
            QPushButton:hover {{
                background-color: rgba(239, 68, 68, 0.2);
            }}
        """)
        deny_btn.clicked.connect(self.reject)
        btn_layout.addWidget(deny_btn)

        allow_btn = QPushButton("✓  Allow")
        allow_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        allow_btn.setFont(QFont(FONTS["family"], FONTS["size_sm"], QFont.Weight.Bold))
        allow_btn.setMinimumHeight(38)
        allow_btn.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                            stop:0 {COLORS['accent_cyan']}, stop:1 {COLORS['accent_purple']});
                color: {COLORS['bg_primary']};
                border: none;
                border-radius: 10px;
                padding: 6px 20px;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                            stop:0 #33DFFF, stop:1 #C084FC);
            }}
        """)
        allow_btn.clicked.connect(self.accept)
        btn_layout.addWidget(allow_btn)

        card_layout.addLayout(btn_layout)

        # Timer label
        self._timer_label = QLabel("Auto-deny in 30s")
        self._timer_label.setFont(QFont(FONTS["family"], 9))
        self._timer_label.setStyleSheet(f"color: {COLORS['text_muted']};")
        self._timer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(self._timer_label)

        # Countdown
        self._countdown = 30
        self._tick_timer = QTimer(self)
        self._tick_timer.timeout.connect(self._tick)
        self._tick_timer.start(1000)

        outer.addWidget(card)

    def _tick(self):
        self._countdown -= 1
        if self._countdown > 0:
            self._timer_label.setText(f"Auto-deny in {self._countdown}s")
        else:
            self._tick_timer.stop()

    def exec(self) -> bool:
        """Show dialog and return True=allow, False=deny."""
        result = super().exec()
        return result == QDialog.DialogCode.Accepted


def ask_permission(tool: str, params: dict, explanation: str,
                   risk: str = "moderate") -> bool:
    """
    Show a permission popup and wait for user response.
    Must be called from the main/GUI thread.
    """
    dialog = PermissionPopup(tool, params, explanation, risk)
    return dialog.exec()

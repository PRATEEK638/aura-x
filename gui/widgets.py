"""
Aura-X Custom Widgets — V2 Premium
Modern message bubbles with avatars, animated indicators, glow effects.
"""

from PyQt6.QtWidgets import (
    QWidget, QLabel, QHBoxLayout, QVBoxLayout, QFrame,
    QPushButton, QGraphicsDropShadowEffect, QSizePolicy
)
from PyQt6.QtCore import (
    Qt, QTimer, QPropertyAnimation, QEasingCurve, QSize, QPoint, QRect
)
from PyQt6.QtGui import (
    QFont, QColor, QPainter, QPainterPath, QLinearGradient,
    QRadialGradient, QPen, QBrush
)
from gui.theme import COLORS, FONTS, RADIUS, SPACING


class AvatarIcon(QWidget):
    """Circular avatar icon with gradient background and emoji."""

    def __init__(self, emoji: str, gradient_start: str, gradient_end: str,
                 size: int = 36, parent=None):
        super().__init__(parent)
        self._emoji = emoji
        self._grad_start = QColor(gradient_start)
        self._grad_end = QColor(gradient_end)
        self.setFixedSize(size, size)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Gradient circle
        grad = QLinearGradient(0, 0, self.width(), self.height())
        grad.setColorAt(0, self._grad_start)
        grad.setColorAt(1, self._grad_end)
        p.setBrush(QBrush(grad))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(0, 0, self.width(), self.height())

        # Emoji
        font = QFont(FONTS["family"], self.width() // 3)
        p.setFont(font)
        p.setPen(QPen(QColor("#FFFFFF")))
        p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self._emoji)
        p.end()


class MessageBubble(QFrame):
    """Premium chat message bubble with avatar, timestamp, and optional code blocks."""

    def __init__(self, text: str, is_user: bool = False,
                 model_info: str = "", timestamp: str = "", parent=None):
        super().__init__(parent)
        self.is_user = is_user
        self._setup_ui(text, model_info, timestamp)

    def _setup_ui(self, text: str, model_info: str, timestamp: str):
        outer = QHBoxLayout(self)
        outer.setContentsMargins(8, 4, 8, 4)
        outer.setSpacing(12)

        # Avatar
        if self.is_user:
            outer.addStretch()
        else:
            avatar = AvatarIcon("✦", COLORS["accent_cyan"], COLORS["accent_purple"], 34)
            avatar_layout = QVBoxLayout()
            avatar_layout.addWidget(avatar)
            avatar_layout.addStretch()
            outer.addLayout(avatar_layout)

        # Bubble content
        bubble = QFrame()
        bg = COLORS["bubble_user"] if self.is_user else COLORS["bubble_assistant"]
        border = COLORS["bubble_user_border"] if self.is_user else COLORS["bubble_assistant_border"]
        border_radius = RADIUS['lg']
        bubble.setStyleSheet(f"""
            QFrame {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: {border_radius}px;
            }}
        """)
        bubble.setMaximumWidth(620)

        bubble_layout = QVBoxLayout(bubble)
        bubble_layout.setContentsMargins(16, 12, 16, 10)
        bubble_layout.setSpacing(6)

        # Header line: role + timestamp
        header = QHBoxLayout()
        header.setSpacing(8)

        role_label = QLabel("You" if self.is_user else "Aura-X")
        role_label.setFont(QFont(FONTS["family"], FONTS["size_sm"], QFont.Weight.Bold))
        role_color = COLORS["accent_purple"] if self.is_user else COLORS["accent_cyan"]
        role_label.setStyleSheet(f"color: {role_color};")
        header.addWidget(role_label)

        if timestamp:
            time_label = QLabel(timestamp)
            time_label.setFont(QFont(FONTS["family"], FONTS["size_xs"]))
            time_label.setStyleSheet(f"color: {COLORS['text_muted']};")
            header.addWidget(time_label)

        header.addStretch()
        bubble_layout.addLayout(header)

        # Message text
        msg_label = QLabel(text)
        msg_label.setWordWrap(True)
        msg_label.setTextFormat(Qt.TextFormat.PlainText)
        msg_label.setFont(QFont(FONTS["family"], FONTS["size_base"]))
        msg_label.setStyleSheet(f"""
            color: {COLORS['text_primary']};
            line-height: 1.6;
            padding: 2px 0;
        """)
        msg_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        msg_label.setMinimumWidth(80)
        bubble_layout.addWidget(msg_label)
        self._msg_label = msg_label

        # Model tag (for assistant messages)
        if model_info and not self.is_user:
            tag = QLabel(f"⚡ {model_info}")
            tag.setFont(QFont(FONTS["family"], FONTS["size_xs"]))
            tag.setStyleSheet(f"""
                color: {COLORS['text_muted']};
                background-color: rgba(255,255,255,0.03);
                border-radius: 6px;
                padding: 2px 8px;
            """)
            tag.setFixedHeight(18)
            bubble_layout.addWidget(tag, alignment=Qt.AlignmentFlag.AlignLeft)

        outer.addWidget(bubble, 1)

        if not self.is_user:
            outer.addStretch()
        else:
            avatar = AvatarIcon("👤", COLORS["accent_purple"], COLORS["accent_pink"], 34)
            avatar_layout = QVBoxLayout()
            avatar_layout.addWidget(avatar)
            avatar_layout.addStretch()
            outer.addLayout(avatar_layout)

        self.setStyleSheet("background: transparent; border: none;")

    def update_text(self, text: str):
        self._msg_label.setText(text)


class TypingIndicator(QWidget):
    """Modern animated typing dots."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(48)
        self._dots = []
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._animate)
        self._current_dot = 0
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(72, 8, 20, 8)
        layout.setSpacing(8)

        # Mini avatar
        avatar = AvatarIcon("✦", COLORS["accent_cyan"], COLORS["accent_purple"], 28)
        layout.addWidget(avatar)

        label = QLabel("Aura-X is thinking")
        label.setFont(QFont(FONTS["family"], FONTS["size_sm"]))
        label.setStyleSheet(f"color: {COLORS['text_muted']};")
        layout.addWidget(label)

        for _ in range(3):
            dot = QLabel("●")
            dot.setFont(QFont(FONTS["family"], 7))
            dot.setStyleSheet(f"color: {COLORS['text_muted']};")
            dot.setFixedWidth(10)
            dot.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(dot)
            self._dots.append(dot)

        layout.addStretch()

    def start(self):
        self.show()
        self._timer.start(350)

    def stop(self):
        self._timer.stop()
        self.hide()

    def _animate(self):
        colors = [COLORS["accent_cyan"], COLORS["accent_purple"], COLORS["accent_pink"]]
        for i, dot in enumerate(self._dots):
            if i == self._current_dot:
                dot.setStyleSheet(f"color: {colors[i % len(colors)]};")
                dot.setFont(QFont(FONTS["family"], 9))
            else:
                dot.setStyleSheet(f"color: {COLORS['text_muted']};")
                dot.setFont(QFont(FONTS["family"], 7))
        self._current_dot = (self._current_dot + 1) % 3


class StatusDot(QWidget):
    """Pulsing status indicator with optional glow."""

    def __init__(self, color: str = None, size: int = 10, glow: bool = False, parent=None):
        super().__init__(parent)
        self._color = QColor(color or COLORS["status_online"])
        self._size = size
        self._glow = glow
        self._opacity = 1.0
        self._pulse_timer = None
        self._pulse_growing = False
        self.setFixedSize(size + 4, size + 4)

        if glow:
            self._start_pulse()

    def set_color(self, color: str):
        self._color = QColor(color)
        if color == COLORS["status_online"] and not self._pulse_timer:
            self._start_pulse()
        elif color != COLORS["status_online"] and self._pulse_timer:
            self._pulse_timer.stop()
            self._pulse_timer = None
            self._opacity = 1.0
        self.update()

    def _start_pulse(self):
        self._pulse_timer = QTimer(self)
        self._pulse_timer.timeout.connect(self._pulse)
        self._pulse_timer.start(50)

    def _pulse(self):
        if self._pulse_growing:
            self._opacity += 0.04
            if self._opacity >= 1.0:
                self._opacity = 1.0
                self._pulse_growing = False
        else:
            self._opacity -= 0.04
            if self._opacity <= 0.4:
                self._opacity = 0.4
                self._pulse_growing = True
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        cx, cy = self.width() // 2, self.height() // 2
        r = self._size // 2

        # Glow ring
        if self._glow or (self._pulse_timer and self._pulse_timer.isActive()):
            glow_color = QColor(self._color)
            glow_color.setAlphaF(0.2 * self._opacity)
            p.setBrush(QBrush(glow_color))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QPoint(cx, cy), r + 2, r + 2)

        # Core dot
        core_color = QColor(self._color)
        core_color.setAlphaF(self._opacity)
        p.setBrush(QBrush(core_color))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QPoint(cx, cy), r, r)
        p.end()


class GlowCard(QFrame):
    """Card with subtle glow border on hover."""

    def __init__(self, glow_color: str = None, parent=None):
        super().__init__(parent)
        self._glow_color = glow_color or COLORS["accent_cyan"]
        self.setObjectName("glassCard")
        self.setStyleSheet(f"""
            GlowCard {{
                background-color: {COLORS['bg_card']};
                border: 1px solid {COLORS['border_primary']};
                border-radius: {RADIUS['xl']}px;
            }}
            GlowCard:hover {{
                border-color: {self._glow_color};
            }}
        """)


class FeatureCard(QFrame):
    """A compact feature suggestion card for the welcome screen."""

    def __init__(self, emoji: str, title: str, description: str,
                 accent: str = None, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        color = accent or COLORS["accent_cyan"]

        self.setStyleSheet(f"""
            FeatureCard {{
                background-color: {COLORS['bg_card']};
                border: 1px solid {COLORS['border_primary']};
                border-radius: {RADIUS['lg']}px;
                padding: 0;
            }}
            FeatureCard:hover {{
                border-color: {color};
                background-color: rgba(255, 255, 255, 0.02);
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(6)

        icon_label = QLabel(emoji)
        icon_label.setFont(QFont(FONTS["family"], FONTS["size_xl"]))
        layout.addWidget(icon_label)

        title_label = QLabel(title)
        title_label.setFont(QFont(FONTS["family"], FONTS["size_sm"], QFont.Weight.Bold))
        title_label.setStyleSheet(f"color: {COLORS['text_primary']};")
        layout.addWidget(title_label)

        desc_label = QLabel(description)
        desc_label.setFont(QFont(FONTS["family"], FONTS["size_xs"]))
        desc_label.setStyleSheet(f"color: {COLORS['text_muted']};")
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)

        self._command = description


class SidebarButton(QPushButton):
    """Navigation button for the sidebar with active bar indicator."""

    def __init__(self, icon: str, text: str, parent=None):
        super().__init__(f"  {icon}   {text}", parent)
        self.setObjectName("sidebarButton")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(46)
        font = QFont(FONTS["family"], FONTS["size_base"])
        self.setFont(font)
        self._active = False

    def set_active(self, active: bool):
        self._active = active
        self.setObjectName("sidebarButtonActive" if active else "sidebarButton")
        self.style().unpolish(self)
        self.style().polish(self)

    @property
    def active(self):
        return self._active


class Separator(QFrame):
    """Horizontal separator line."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("separator")
        self.setFixedHeight(1)


class AccentButton(QPushButton):
    """Gradient accent button."""
    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setObjectName("accentButton")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(40)


class IconButton(QPushButton):
    """Transparent icon button."""
    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setObjectName("iconButton")
        self.setCursor(Qt.CursorShape.PointingHandCursor)

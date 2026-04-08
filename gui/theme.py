"""
Aura-X GUI Theme System — V2 Premium
Custom frameless window, animated gradients, glow effects, premium dark UI.
"""

# ─── Color Palette ────────────────────────────────────────────
COLORS = {
    # Backgrounds (deeper, richer)
    "bg_primary": "#06080F",
    "bg_secondary": "#0C1018",
    "bg_tertiary": "#141A28",
    "bg_card": "#161E2E",
    "bg_input": "#0A0F1A",
    "bg_hover": "#1C2844",
    "bg_glass": "rgba(12, 16, 24, 0.92)",
    "bg_sidebar": "#090D16",
    "bg_titlebar": "#080B14",

    # Accents (vibrant gradients)
    "accent_cyan": "#00D4FF",
    "accent_cyan_dim": "#0099CC",
    "accent_purple": "#A855F7",
    "accent_purple_dim": "#7C3AED",
    "accent_green": "#10B981",
    "accent_red": "#EF4444",
    "accent_amber": "#F59E0B",
    "accent_blue": "#3B82F6",
    "accent_pink": "#EC4899",
    "accent_teal": "#14B8A6",

    # Text
    "text_primary": "#F0F4FC",
    "text_secondary": "#8B9DC3",
    "text_muted": "#4E5D78",
    "text_accent": "#00D4FF",
    "text_bright": "#FFFFFF",

    # Borders
    "border_primary": "#1A2236",
    "border_accent": "#00D4FF",
    "border_subtle": "rgba(255, 255, 255, 0.04)",
    "border_glow": "rgba(0, 212, 255, 0.25)",

    # Chat bubbles
    "bubble_user": "rgba(0, 212, 255, 0.08)",
    "bubble_user_border": "rgba(0, 212, 255, 0.18)",
    "bubble_assistant": "rgba(22, 30, 46, 0.9)",
    "bubble_assistant_border": "rgba(168, 85, 247, 0.12)",
    "bubble_code": "#0D1117",

    # Status
    "status_online": "#10B981",
    "status_busy": "#F59E0B",
    "status_error": "#EF4444",
    "status_offline": "#4E5D78",

    # Scrollbar
    "scrollbar_bg": "transparent",
    "scrollbar_handle": "#1C2844",
    "scrollbar_hover": "#283A5C",
}

# ─── Fonts ────────────────────────────────────────────────────
FONTS = {
    "family": "Segoe UI",
    "family_mono": "Cascadia Code, Consolas, monospace",
    "size_xs": 10,
    "size_sm": 11,
    "size_base": 13,
    "size_md": 14,
    "size_lg": 16,
    "size_xl": 20,
    "size_2xl": 24,
    "size_3xl": 32,
    "size_hero": 42,
    "weight_normal": "normal",
    "weight_medium": 500,
    "weight_semibold": 600,
    "weight_bold": "bold",
}

# ─── Animation Timing ────────────────────────────────────────
ANIMATION = {
    "fast": 120,
    "normal": 220,
    "slow": 380,
    "very_slow": 600,
    "spring": 350,
}

# ─── Spacing ──────────────────────────────────────────────────
SPACING = {
    "xs": 4,
    "sm": 8,
    "md": 12,
    "lg": 16,
    "xl": 24,
    "2xl": 32,
    "3xl": 48,
}

# ─── Border Radius ────────────────────────────────────────────
RADIUS = {
    "sm": 6,
    "md": 10,
    "lg": 14,
    "xl": 18,
    "2xl": 22,
    "full": 9999,
}


def build_stylesheet() -> str:
    """Generate the complete premium application stylesheet."""
    c = COLORS
    f = FONTS
    return f"""
    /* ═══════════════════════════════════════════════════════════
       AURA-X PREMIUM DARK THEME — V2
       ═══════════════════════════════════════════════════════════ */

    * {{
        font-family: "{f['family']}";
        font-size: {f['size_base']}px;
        outline: none;
    }}

    QMainWindow {{
        background-color: {c['bg_primary']};
        border: 1px solid {c['border_primary']};
    }}

    QWidget {{
        background-color: transparent;
        color: {c['text_primary']};
    }}

    /* ─── Scroll Areas ─────────────────────────────────────── */
    QScrollArea {{
        background: transparent;
        border: none;
    }}
    QScrollArea > QWidget > QWidget {{
        background: transparent;
    }}
    QScrollBar:vertical {{
        background: {c['scrollbar_bg']};
        width: 6px;
        margin: 4px 2px;
        border-radius: 3px;
    }}
    QScrollBar::handle:vertical {{
        background: {c['scrollbar_handle']};
        min-height: 40px;
        border-radius: 3px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {c['scrollbar_hover']};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0;
    }}
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
        background: none;
    }}
    QScrollBar:horizontal {{
        background: {c['scrollbar_bg']};
        height: 6px;
        border-radius: 3px;
    }}
    QScrollBar::handle:horizontal {{
        background: {c['scrollbar_handle']};
        min-width: 40px;
        border-radius: 3px;
    }}

    /* ─── Labels ───────────────────────────────────────────── */
    QLabel {{
        color: {c['text_primary']};
        background: transparent;
        border: none;
    }}

    /* ─── Buttons ──────────────────────────────────────────── */
    QPushButton {{
        background-color: {c['bg_card']};
        color: {c['text_primary']};
        border: 1px solid {c['border_primary']};
        border-radius: 10px;
        padding: 8px 18px;
        font-weight: {f['weight_medium']};
        font-size: {f['size_base']}px;
    }}
    QPushButton:hover {{
        background-color: {c['bg_hover']};
        border-color: {c['border_glow']};
        color: {c['accent_cyan']};
    }}
    QPushButton:pressed {{
        background-color: {c['bg_tertiary']};
    }}
    QPushButton:disabled {{
        background-color: {c['bg_secondary']};
        color: {c['text_muted']};
        border-color: {c['border_subtle']};
    }}
    QPushButton#accentButton {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {c['accent_cyan']}, stop:1 {c['accent_purple']});
        color: {c['bg_primary']};
        border: none;
        font-weight: {f['weight_bold']};
        padding: 10px 28px;
        border-radius: 12px;
    }}
    QPushButton#accentButton:hover {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #33DFFF, stop:1 #C084FC);
        color: {c['bg_primary']};
    }}
    QPushButton#dangerButton {{
        background-color: rgba(239, 68, 68, 0.1);
        color: {c['accent_red']};
        border-color: rgba(239, 68, 68, 0.2);
    }}
    QPushButton#dangerButton:hover {{
        background-color: rgba(239, 68, 68, 0.2);
        border-color: {c['accent_red']};
    }}
    QPushButton#iconButton {{
        background: transparent;
        border: none;
        padding: 6px;
        border-radius: 10px;
        min-width: 38px;
        min-height: 38px;
    }}
    QPushButton#iconButton:hover {{
        background-color: {c['bg_hover']};
    }}
    QPushButton#sidebarButton {{
        background: transparent;
        border: none;
        border-radius: 12px;
        padding: 11px 16px;
        text-align: left;
        font-size: {f['size_base']}px;
        color: {c['text_secondary']};
    }}
    QPushButton#sidebarButton:hover {{
        background-color: rgba(255, 255, 255, 0.04);
        color: {c['text_primary']};
    }}
    QPushButton#sidebarButtonActive {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(0, 212, 255, 0.12), stop:1 rgba(168, 85, 247, 0.06));
        border: none;
        border-left: 3px solid {c['accent_cyan']};
        border-radius: 0px 12px 12px 0px;
        padding: 11px 16px 11px 13px;
        text-align: left;
        font-size: {f['size_base']}px;
        color: {c['accent_cyan']};
        font-weight: {f['weight_semibold']};
    }}

    /* ─── Input Fields ─────────────────────────────────────── */
    QLineEdit, QTextEdit, QPlainTextEdit {{
        background-color: {c['bg_input']};
        color: {c['text_primary']};
        border: 1px solid {c['border_primary']};
        border-radius: 12px;
        padding: 10px 16px;
        font-size: {f['size_base']}px;
        selection-background-color: rgba(0, 212, 255, 0.25);
    }}
    QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
        border-color: {c['accent_cyan']};
    }}

    /* ─── Combo Box ────────────────────────────────────────── */
    QComboBox {{
        background-color: {c['bg_input']};
        color: {c['text_primary']};
        border: 1px solid {c['border_primary']};
        border-radius: 10px;
        padding: 8px 14px;
        min-height: 22px;
    }}
    QComboBox:hover {{ border-color: {c['accent_cyan']}; }}
    QComboBox::drop-down {{ border: none; width: 28px; }}
    QComboBox QAbstractItemView {{
        background-color: {c['bg_card']};
        color: {c['text_primary']};
        border: 1px solid {c['border_primary']};
        border-radius: 10px;
        selection-background-color: {c['bg_hover']};
        selection-color: {c['accent_cyan']};
        padding: 4px;
    }}

    /* ─── Frames / Cards ───────────────────────────────────── */
    QFrame#card {{
        background-color: {c['bg_card']};
        border: 1px solid {c['border_primary']};
        border-radius: {RADIUS['xl']}px;
        padding: 16px;
    }}
    QFrame#glassCard {{
        background-color: {c['bg_glass']};
        border: 1px solid rgba(255, 255, 255, 0.06);
        border-radius: {RADIUS['xl']}px;
        padding: 16px;
    }}
    QFrame#separator {{
        background-color: {c['border_primary']};
        max-height: 1px;
        min-height: 1px;
    }}
    QFrame#sidebar {{
        background-color: {c['bg_sidebar']};
        border-right: 1px solid {c['border_primary']};
        border-radius: 0px;
    }}

    /* ─── Checkboxes ───────────────────────────────────────── */
    QCheckBox {{
        color: {c['text_primary']};
        spacing: 10px;
    }}
    QCheckBox::indicator {{
        width: 20px; height: 20px;
        border: 2px solid {c['border_primary']};
        border-radius: 6px;
        background-color: {c['bg_input']};
    }}
    QCheckBox::indicator:checked {{
        background-color: {c['accent_cyan']};
        border-color: {c['accent_cyan']};
    }}
    QCheckBox::indicator:hover {{
        border-color: {c['accent_cyan']};
    }}

    /* ─── Sliders ──────────────────────────────────────────── */
    QSlider::groove:horizontal {{
        background: {c['bg_tertiary']};
        height: 6px; border-radius: 3px;
    }}
    QSlider::handle:horizontal {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 {c['accent_cyan']}, stop:1 {c['accent_purple']});
        width: 18px; height: 18px; margin: -6px 0; border-radius: 9px;
        border: 2px solid {c['bg_primary']};
    }}
    QSlider::sub-page:horizontal {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {c['accent_cyan']}, stop:1 {c['accent_purple']});
        border-radius: 3px;
    }}

    /* ─── Spinbox ──────────────────────────────────────────── */
    QSpinBox, QDoubleSpinBox {{
        background-color: {c['bg_input']};
        color: {c['text_primary']};
        border: 1px solid {c['border_primary']};
        border-radius: 10px;
        padding: 6px 12px;
    }}
    QSpinBox:focus, QDoubleSpinBox:focus {{
        border-color: {c['accent_cyan']};
    }}

    /* ─── Progress Bar ─────────────────────────────────────── */
    QProgressBar {{
        background-color: {c['bg_tertiary']};
        border: none; border-radius: 4px;
        text-align: center;
        color: transparent;
        max-height: 6px;
    }}
    QProgressBar::chunk {{
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {c['accent_cyan']}, stop:1 {c['accent_purple']});
        border-radius: 4px;
    }}

    /* ─── Tooltip ──────────────────────────────────────────── */
    QToolTip {{
        background-color: {c['bg_card']};
        color: {c['text_primary']};
        border: 1px solid {c['border_primary']};
        border-radius: 8px;
        padding: 8px 12px;
        font-size: {f['size_sm']}px;
    }}

    /* ─── Splitter ─────────────────────────────────────────── */
    QSplitter::handle {{
        background: {c['border_primary']};
    }}
    QSplitter::handle:horizontal {{ width: 1px; }}

    /* ─── Group Box ────────────────────────────────────────── */
    QGroupBox {{
        background-color: {c['bg_card']};
        border: 1px solid {c['border_primary']};
        border-radius: {RADIUS['xl']}px;
        margin-top: 10px;
        padding: 28px 20px 20px 20px;
        color: {c['accent_cyan']};
        font-weight: {f['weight_bold']};
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 20px;
        padding: 0 10px;
        font-size: {f['size_md']}px;
    }}
    """

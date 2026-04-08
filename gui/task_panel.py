"""
Aura-X Task Panel
Displays active agent tasks, step progress, and execution history.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel,
    QScrollArea, QProgressBar, QPushButton, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from gui.theme import COLORS, FONTS, RADIUS, SPACING


class StepWidget(QFrame):
    """A single step in the task execution display."""

    def __init__(self, step_id: int, description: str, parent=None):
        super().__init__(parent)
        self.step_id = step_id
        self._setup_ui(description)

    def _setup_ui(self, description: str):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(10)

        # Status icon
        self._status_icon = QLabel("○")
        self._status_icon.setFixedWidth(20)
        self._status_icon.setFont(QFont(FONTS["family"], FONTS["size_md"]))
        self._status_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status_icon.setStyleSheet(f"color: {COLORS['text_muted']}; background: transparent;")
        layout.addWidget(self._status_icon)

        # Description
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)

        step_label = QLabel(f"Step {self.step_id + 1}")
        step_label.setFont(QFont(FONTS["family"], FONTS["size_xs"], QFont.Weight.Bold))
        step_label.setStyleSheet(f"color: {COLORS['text_muted']}; background: transparent;")
        info_layout.addWidget(step_label)

        self._desc_label = QLabel(description)
        self._desc_label.setFont(QFont(FONTS["family"], FONTS["size_sm"]))
        self._desc_label.setStyleSheet(f"color: {COLORS['text_primary']}; background: transparent;")
        self._desc_label.setWordWrap(True)
        info_layout.addWidget(self._desc_label)

        self._result_label = QLabel("")
        self._result_label.setFont(QFont(FONTS["family"], FONTS["size_xs"]))
        self._result_label.setStyleSheet(f"color: {COLORS['text_secondary']}; background: transparent;")
        self._result_label.setWordWrap(True)
        self._result_label.hide()
        info_layout.addWidget(self._result_label)

        layout.addLayout(info_layout, 1)

        self.setStyleSheet(f"""
            StepWidget {{
                background-color: {COLORS['bg_tertiary']};
                border: 1px solid {COLORS['border_primary']};
                border-radius: {RADIUS['sm']}px;
            }}
        """)

    def set_running(self):
        self._status_icon.setText("◉")
        self._status_icon.setStyleSheet(f"color: {COLORS['accent_cyan']}; background: transparent;")
        self.setStyleSheet(f"""
            StepWidget {{
                background-color: rgba(0, 212, 255, 0.06);
                border: 1px solid rgba(0, 212, 255, 0.2);
                border-radius: {RADIUS['sm']}px;
            }}
        """)

    def set_success(self, result: str = ""):
        self._status_icon.setText("✓")
        self._status_icon.setStyleSheet(f"color: {COLORS['accent_green']}; background: transparent;")
        if result:
            self._result_label.setText(result[:200])
            self._result_label.show()
        self.setStyleSheet(f"""
            StepWidget {{
                background-color: rgba(16, 185, 129, 0.06);
                border: 1px solid rgba(16, 185, 129, 0.15);
                border-radius: {RADIUS['sm']}px;
            }}
        """)

    def set_failed(self, error: str = ""):
        self._status_icon.setText("✗")
        self._status_icon.setStyleSheet(f"color: {COLORS['accent_red']}; background: transparent;")
        if error:
            self._result_label.setText(f"Error: {error[:200]}")
            self._result_label.setStyleSheet(f"color: {COLORS['accent_red']}; background: transparent;")
            self._result_label.show()
        self.setStyleSheet(f"""
            StepWidget {{
                background-color: rgba(239, 68, 68, 0.06);
                border: 1px solid rgba(239, 68, 68, 0.15);
                border-radius: {RADIUS['sm']}px;
            }}
        """)

    def set_skipped(self):
        self._status_icon.setText("⊘")
        self._status_icon.setStyleSheet(f"color: {COLORS['text_muted']}; background: transparent;")


class TaskPanel(QWidget):
    """Active agent task display with step progress."""
    stop_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._step_widgets = []
        self._setup_ui()

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

        title = QLabel("⚡  Agent Tasks")
        title.setFont(QFont(FONTS["family"], FONTS["size_lg"], QFont.Weight.Bold))
        title.setStyleSheet(f"color: {COLORS['text_primary']}; background: transparent;")
        header_layout.addWidget(title)

        header_layout.addStretch()

        self._stop_btn = QPushButton("■ Stop")
        self._stop_btn.setObjectName("dangerButton")
        self._stop_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._stop_btn.clicked.connect(self.stop_requested.emit)
        self._stop_btn.hide()
        header_layout.addWidget(self._stop_btn)

        layout.addWidget(header)

        # Content area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self._content = QWidget()
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(16, 16, 16, 16)
        self._content_layout.setSpacing(8)
        self._content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Empty state
        self._empty_label = QLabel("No active tasks\n\nAgent tasks will appear here when\nAura-X executes multi-step operations.")
        self._empty_label.setFont(QFont(FONTS["family"], FONTS["size_md"]))
        self._empty_label.setStyleSheet(f"color: {COLORS['text_muted']}; background: transparent;")
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._content_layout.addWidget(self._empty_label)

        # Task goal
        self._goal_label = QLabel("")
        self._goal_label.setFont(QFont(FONTS["family"], FONTS["size_md"], QFont.Weight.Bold))
        self._goal_label.setStyleSheet(f"color: {COLORS['text_primary']}; background: transparent;")
        self._goal_label.setWordWrap(True)
        self._goal_label.hide()
        self._content_layout.addWidget(self._goal_label)

        # Progress bar
        self._progress = QProgressBar()
        self._progress.setMaximumHeight(6)
        self._progress.hide()
        self._content_layout.addWidget(self._progress)

        # Steps container
        self._steps_layout = QVBoxLayout()
        self._steps_layout.setSpacing(6)
        self._content_layout.addLayout(self._steps_layout)

        self._content_layout.addStretch()

        scroll.setWidget(self._content)
        layout.addWidget(scroll, 1)

    def start_task(self, goal: str, steps: list):
        """Display a new task with its steps."""
        self.clear_task()
        self._empty_label.hide()
        self._goal_label.setText(f"🎯 {goal}")
        self._goal_label.show()
        self._progress.setMaximum(len(steps))
        self._progress.setValue(0)
        self._progress.show()
        self._stop_btn.show()

        for i, step in enumerate(steps):
            desc = step.get("description", step.get("explanation", f"Step {i+1}"))
            widget = StepWidget(i, desc)
            self._steps_layout.addWidget(widget)
            self._step_widgets.append(widget)

    def update_step(self, step_id: int, status: str, result: str = "", error: str = ""):
        """Update a step's status."""
        if step_id < len(self._step_widgets):
            widget = self._step_widgets[step_id]
            if status == "running":
                widget.set_running()
            elif status == "success":
                widget.set_success(result)
                self._progress.setValue(step_id + 1)
            elif status == "failed":
                widget.set_failed(error)
                self._progress.setValue(step_id + 1)
            elif status == "skipped":
                widget.set_skipped()

    def complete_task(self, success: bool = True):
        """Mark the task as complete."""
        self._stop_btn.hide()
        if success:
            self._progress.setValue(self._progress.maximum())

    def clear_task(self):
        """Clear the current task display."""
        for w in self._step_widgets:
            w.deleteLater()
        self._step_widgets.clear()
        self._goal_label.hide()
        self._progress.hide()
        self._stop_btn.hide()
        self._empty_label.show()

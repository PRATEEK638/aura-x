"""
Aura-X Settings Panel
Model configuration, API keys, permissions, GUI theme, and voice settings.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel,
    QScrollArea, QLineEdit, QComboBox, QCheckBox, QSlider,
    QPushButton, QSpinBox, QDoubleSpinBox, QGroupBox, QFormLayout
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from gui.theme import COLORS, FONTS, RADIUS, SPACING
from core.config import CONFIG, save_config


class SettingsPanel(QWidget):
    """Settings configuration panel."""
    settings_changed = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._load_values()

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

        title = QLabel("⚙  Settings")
        title.setFont(QFont(FONTS["family"], FONTS["size_lg"], QFont.Weight.Bold))
        title.setStyleSheet(f"color: {COLORS['text_primary']}; background: transparent;")
        header_layout.addWidget(title)

        header_layout.addStretch()

        save_btn = QPushButton("💾 Save")
        save_btn.setObjectName("accentButton")
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.clicked.connect(self._save_settings)
        header_layout.addWidget(save_btn)

        layout.addWidget(header)

        # Scrollable content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(24, 20, 24, 20)
        content_layout.setSpacing(20)

        # ─── AI Models ───
        models_group = self._create_group("🧠 AI Models")
        models_form = QFormLayout()
        models_form.setSpacing(12)

        self._fast_model = QLineEdit()
        self._fast_model.setPlaceholderText("phi3:mini")
        models_form.addRow("Fast Model (phi3):", self._fast_model)

        self._general_model = QLineEdit()
        self._general_model.setPlaceholderText("llama3")
        models_form.addRow("General Model:", self._general_model)

        self._coding_model = QLineEdit()
        self._coding_model.setPlaceholderText("qwen2.5-coder")
        models_form.addRow("Coding Model:", self._coding_model)

        self._ollama_url = QLineEdit()
        self._ollama_url.setPlaceholderText("http://localhost:11434")
        models_form.addRow("Ollama URL:", self._ollama_url)

        models_group.layout().addLayout(models_form)
        content_layout.addWidget(models_group)

        # ─── API Keys ───
        api_group = self._create_group("🔑 API Keys")
        api_form = QFormLayout()
        api_form.setSpacing(12)

        self._nvidia_key = QLineEdit()
        self._nvidia_key.setPlaceholderText("Enter NVIDIA API key...")
        self._nvidia_key.setEchoMode(QLineEdit.EchoMode.Password)
        api_form.addRow("NVIDIA API Key:", self._nvidia_key)

        self._deepseek_key = QLineEdit()
        self._deepseek_key.setPlaceholderText("Enter DeepSeek API key...")
        self._deepseek_key.setEchoMode(QLineEdit.EchoMode.Password)
        api_form.addRow("DeepSeek API Key:", self._deepseek_key)

        api_group.layout().addLayout(api_form)
        content_layout.addWidget(api_group)

        # ─── Agent Settings ───
        agent_group = self._create_group("🤖 Agent Behavior")
        agent_form = QFormLayout()
        agent_form.setSpacing(12)

        self._max_steps = QSpinBox()
        self._max_steps.setRange(1, 50)
        self._max_steps.setValue(15)
        agent_form.addRow("Max Steps:", self._max_steps)

        self._auto_verify = QCheckBox("Auto-verify step results")
        self._auto_verify.setChecked(True)
        agent_form.addRow("", self._auto_verify)

        self._retry_failures = QCheckBox("Retry failed steps")
        self._retry_failures.setChecked(True)
        agent_form.addRow("", self._retry_failures)

        self._permission_combo = QComboBox()
        self._permission_combo.addItems(["interactive", "auto", "strict"])
        agent_form.addRow("Permission Mode:", self._permission_combo)

        agent_group.layout().addLayout(agent_form)
        content_layout.addWidget(agent_group)

        # ─── Voice Settings ───
        voice_group = self._create_group("🎤 Voice")
        voice_form = QFormLayout()
        voice_form.setSpacing(12)

        self._voice_enabled = QCheckBox("Enable voice output")
        self._voice_enabled.setChecked(True)
        voice_form.addRow("", self._voice_enabled)

        self._voice_rate = QSlider(Qt.Orientation.Horizontal)
        self._voice_rate.setRange(100, 300)
        self._voice_rate.setValue(175)
        voice_form.addRow("Speech Rate:", self._voice_rate)

        self._voice_volume = QDoubleSpinBox()
        self._voice_volume.setRange(0.0, 1.0)
        self._voice_volume.setSingleStep(0.1)
        self._voice_volume.setValue(1.0)
        voice_form.addRow("Volume:", self._voice_volume)

        voice_group.layout().addLayout(voice_form)
        content_layout.addWidget(voice_group)

        # ─── Memory Settings ───
        memory_group = self._create_group("🧠 Memory")
        memory_form = QFormLayout()
        memory_form.setSpacing(12)

        self._memory_enabled = QCheckBox("Enable long-term memory")
        self._memory_enabled.setChecked(True)
        memory_form.addRow("", self._memory_enabled)

        self._max_messages = QSpinBox()
        self._max_messages.setRange(10, 100)
        self._max_messages.setValue(30)
        memory_form.addRow("Context Window:", self._max_messages)

        clear_memory_btn = QPushButton("🗑 Clear All Memory")
        clear_memory_btn.setObjectName("dangerButton")
        clear_memory_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        clear_memory_btn.clicked.connect(self._clear_memory)
        memory_form.addRow("", clear_memory_btn)

        memory_group.layout().addLayout(memory_form)
        content_layout.addWidget(memory_group)

        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll, 1)

    def _create_group(self, title: str) -> QGroupBox:
        """Create a styled settings group box."""
        group = QGroupBox(title)
        group.setFont(QFont(FONTS["family"], FONTS["size_md"], QFont.Weight.Bold))
        group.setStyleSheet(f"""
            QGroupBox {{
                background-color: {COLORS['bg_card']};
                border: 1px solid {COLORS['border_primary']};
                border-radius: {RADIUS['lg']}px;
                margin-top: 8px;
                padding: 24px 16px 16px 16px;
                color: {COLORS['accent_cyan']};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 16px;
                padding: 0 8px;
            }}
        """)
        layout = QVBoxLayout(group)
        layout.setSpacing(8)
        return group

    def _load_values(self):
        """Load current config values into the form."""
        models = CONFIG.get("models", {})
        self._fast_model.setText(models.get("fast", "phi3:mini"))
        self._general_model.setText(models.get("general", "llama3"))
        self._coding_model.setText(models.get("coding", "qwen2.5-coder"))
        self._ollama_url.setText(CONFIG.get("ollama_base_url", "http://localhost:11434"))
        self._nvidia_key.setText(CONFIG.get("nvidia_api_key", ""))
        self._deepseek_key.setText(CONFIG.get("deepseek_api_key", ""))

        agent = CONFIG.get("agent", {})
        self._max_steps.setValue(agent.get("max_steps", 15))
        self._auto_verify.setChecked(agent.get("auto_verify", True))
        self._retry_failures.setChecked(agent.get("retry_on_failure", True))
        self._permission_combo.setCurrentText(CONFIG.get("permission_level", "interactive"))

        self._voice_enabled.setChecked(CONFIG.get("voice_enabled", True))
        self._voice_rate.setValue(CONFIG.get("voice_rate", 175))
        self._voice_volume.setValue(CONFIG.get("voice_volume", 1.0))

        memory = CONFIG.get("memory", {})
        self._memory_enabled.setChecked(memory.get("long_term_enabled", True))
        self._max_messages.setValue(memory.get("short_term_max_messages", 30))

    def _save_settings(self):
        """Save current form values to config."""
        CONFIG["models"]["fast"] = self._fast_model.text() or "phi3:mini"
        CONFIG["models"]["general"] = self._general_model.text() or "llama3"
        CONFIG["models"]["coding"] = self._coding_model.text() or "qwen2.5-coder"
        CONFIG["ollama_base_url"] = self._ollama_url.text() or "http://localhost:11434"
        CONFIG["nvidia_api_key"] = self._nvidia_key.text()
        CONFIG["deepseek_api_key"] = self._deepseek_key.text()

        CONFIG["agent"]["max_steps"] = self._max_steps.value()
        CONFIG["agent"]["auto_verify"] = self._auto_verify.isChecked()
        CONFIG["agent"]["retry_on_failure"] = self._retry_failures.isChecked()
        CONFIG["permission_level"] = self._permission_combo.currentText()

        CONFIG["voice_enabled"] = self._voice_enabled.isChecked()
        CONFIG["voice_rate"] = self._voice_rate.value()
        CONFIG["voice_volume"] = self._voice_volume.value()

        CONFIG["memory"]["long_term_enabled"] = self._memory_enabled.isChecked()
        CONFIG["memory"]["short_term_max_messages"] = self._max_messages.value()

        save_config(CONFIG)
        self.settings_changed.emit(CONFIG)

    def _clear_memory(self):
        """Signal to clear all memory."""
        self.settings_changed.emit({"_action": "clear_memory"})

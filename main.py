#!/usr/bin/env python3
"""
Aura-X — Intelligent Desktop AI Assistant
Launches the floating orb interface.
"""

import sys
import os

# Ensure project root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def main():
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtGui import QFont
    from PyQt6.QtCore import Qt

    app = QApplication(sys.argv)
    app.setApplicationName("Aura-X")
    app.setApplicationDisplayName("Aura-X — AI Desktop Assistant")
    app.setStyle("Fusion")
    app.setQuitOnLastWindowClosed(False)  # Keep running in tray

    font = QFont("Segoe UI", 13)
    app.setFont(font)

    # Build stylesheet
    from gui.theme import build_stylesheet
    app.setStyleSheet(build_stylesheet())

    # Launch floating orb
    from gui.orb_window import OrbWindow
    orb = OrbWindow()
    orb.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()

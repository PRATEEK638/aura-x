"""
Aura-X Animated Orb Widget
A glowing, pulsing, vibrating sphere that represents the AI's presence.
States: idle (gentle breathe), thinking (fast pulse), speaking (vibrate + wave).
Uses custom QPainter rendering with particle effects and glow rings.
"""

import math
import random
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QTimer, QPointF, QRectF
from PyQt6.QtGui import (
    QPainter, QColor, QRadialGradient, QLinearGradient,
    QPen, QBrush, QPainterPath, QFont
)
from gui.theme import COLORS, FONTS


class Particle:
    """A floating particle around the orb."""
    def __init__(self, cx, cy, orbit_r):
        self.angle = random.uniform(0, 2 * math.pi)
        self.orbit = orbit_r + random.uniform(-15, 15)
        self.speed = random.uniform(0.005, 0.02)
        self.size = random.uniform(1.5, 4)
        self.alpha = random.uniform(0.2, 0.7)
        self.cx = cx
        self.cy = cy
        self.drift = random.uniform(-0.5, 0.5)

    def update(self, energy=1.0):
        self.angle += self.speed * energy
        self.orbit += self.drift * 0.1
        if self.orbit < 30:
            self.drift = abs(self.drift)
        if self.orbit > 120:
            self.drift = -abs(self.drift)

    @property
    def x(self):
        return self.cx + math.cos(self.angle) * self.orbit

    @property
    def y(self):
        return self.cy + math.sin(self.angle) * self.orbit


class OrbWidget(QWidget):
    """
    Animated AI orb — the visual heart of Aura-X.

    States:
        'idle'      — gentle breathing pulse, slow particles
        'thinking'  — faster pulse, color shift to purple, particles accelerate
        'speaking'  — vibration effect, wave rings, green/cyan shimmer
        'listening' — red/amber glow, mic icon concept
    """

    def __init__(self, size: int = 200, parent=None):
        super().__init__(parent)
        self._size = size
        self.setFixedSize(size + 80, size + 80)  # Extra space for glow + particles

        # State
        self._state = "idle"
        self._energy = 0.0  # 0-1 energy level (drives animations)
        self._target_energy = 0.3
        self._phase = 0.0
        self._vibrate_offset = QPointF(0, 0)
        self._wave_rings = []

        # Colors per state
        self._colors = {
            "idle": (QColor("#00D4FF"), QColor("#0099CC"), QColor("#004466")),
            "thinking": (QColor("#A855F7"), QColor("#7C3AED"), QColor("#3B1578")),
            "speaking": (QColor("#10B981"), QColor("#00D4FF"), QColor("#003D4D")),
            "listening": (QColor("#F59E0B"), QColor("#EF4444"), QColor("#661A00")),
        }

        # Particles
        cx, cy = (size + 80) / 2, (size + 80) / 2
        self._particles = [Particle(cx, cy, size * 0.4) for _ in range(30)]

        # Status text
        self._status_text = ""

        # Animation timer — 60fps
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(16)  # ~60fps

    def set_state(self, state: str):
        """Set the orb state: 'idle', 'thinking', 'speaking', 'listening'."""
        self._state = state
        if state == "idle":
            self._target_energy = 0.3
            self._status_text = ""
        elif state == "thinking":
            self._target_energy = 0.7
            self._status_text = "thinking..."
        elif state == "speaking":
            self._target_energy = 0.85
            self._status_text = "speaking"
        elif state == "listening":
            self._target_energy = 0.6
            self._status_text = "listening..."

    def set_amplitude(self, amplitude: float):
        """Set speech amplitude (0.0-1.0) for vibration intensity."""
        self._target_energy = max(0.3, min(1.0, amplitude))

    def _tick(self):
        """Animation tick."""
        # Smooth energy transition
        self._energy += (self._target_energy - self._energy) * 0.08
        self._phase += 0.03 + self._energy * 0.04

        # Vibration in speaking state
        if self._state == "speaking":
            intensity = self._energy * 3
            self._vibrate_offset = QPointF(
                math.sin(self._phase * 7) * intensity,
                math.cos(self._phase * 5) * intensity * 0.7
            )
        elif self._state == "thinking":
            self._vibrate_offset = QPointF(
                math.sin(self._phase * 3) * 0.5,
                math.cos(self._phase * 2) * 0.5
            )
        else:
            self._vibrate_offset = QPointF(0, 0)

        # Update particles
        for p in self._particles:
            p.update(0.5 + self._energy * 2)

        # Wave rings (speaking state)
        if self._state == "speaking" and random.random() < 0.15:
            self._wave_rings.append({"radius": self._size * 0.25, "alpha": 0.6, "speed": 1.5})
        self._wave_rings = [r for r in self._wave_rings if r["alpha"] > 0.02]
        for r in self._wave_rings:
            r["radius"] += r["speed"]
            r["alpha"] *= 0.96

        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        cx, cy = w / 2 + self._vibrate_offset.x(), h / 2 + self._vibrate_offset.y()
        radius = self._size / 2

        # Get state colors
        c1, c2, c3 = self._colors.get(self._state, self._colors["idle"])

        # ─── Background glow ───
        glow_radius = radius * (1.4 + self._energy * 0.3 + math.sin(self._phase) * 0.1)
        glow = QRadialGradient(cx, cy, glow_radius)
        glow_color = QColor(c1)
        glow_color.setAlphaF(0.15 + self._energy * 0.1)
        glow.setColorAt(0, glow_color)
        glow.setColorAt(0.5, QColor(c1.red(), c1.green(), c1.blue(), 30))
        glow.setColorAt(1, QColor(0, 0, 0, 0))
        p.setBrush(QBrush(glow))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(QPointF(cx, cy), glow_radius, glow_radius)

        # ─── Wave rings (speaking) ───
        for ring in self._wave_rings:
            ring_color = QColor(c1)
            ring_color.setAlphaF(ring["alpha"] * 0.4)
            pen = QPen(ring_color, 1.5)
            p.setPen(pen)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(QPointF(cx, cy), ring["radius"], ring["radius"])

        # ─── Orbit ring ───
        orbit_alpha = 0.08 + self._energy * 0.08
        orbit_color = QColor(c1)
        orbit_color.setAlphaF(orbit_alpha)
        orbit_pen = QPen(orbit_color, 1)
        p.setPen(orbit_pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        orbit_r = radius * 1.15
        p.drawEllipse(QPointF(cx, cy), orbit_r, orbit_r)

        # ─── Particles ───
        for particle in self._particles:
            pc = QColor(c1)
            pc.setAlphaF(particle.alpha * (0.5 + self._energy * 0.5))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(pc))
            p.drawEllipse(QPointF(particle.x + self._vibrate_offset.x(),
                                   particle.y + self._vibrate_offset.y()),
                           particle.size, particle.size)

        # ─── Main sphere ───
        # Outer ring
        breath = math.sin(self._phase) * 3 * self._energy
        sphere_r = radius * 0.45 + breath

        # Sphere gradient
        sphere_grad = QRadialGradient(cx - sphere_r * 0.3, cy - sphere_r * 0.3, sphere_r * 1.4)
        sphere_grad.setColorAt(0, QColor(c1.red(), c1.green(), c1.blue(), 200))
        sphere_grad.setColorAt(0.4, QColor(c2.red(), c2.green(), c2.blue(), 160))
        sphere_grad.setColorAt(0.8, QColor(c3.red(), c3.green(), c3.blue(), 120))
        sphere_grad.setColorAt(1.0, QColor(0, 0, 0, 80))

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(sphere_grad))
        p.drawEllipse(QPointF(cx, cy), sphere_r, sphere_r)

        # Inner highlight (glass effect)
        highlight_grad = QRadialGradient(cx - sphere_r * 0.2, cy - sphere_r * 0.35, sphere_r * 0.5)
        highlight_grad.setColorAt(0, QColor(255, 255, 255, int(60 + self._energy * 40)))
        highlight_grad.setColorAt(1, QColor(255, 255, 255, 0))
        p.setBrush(QBrush(highlight_grad))
        p.drawEllipse(QPointF(cx - sphere_r * 0.1, cy - sphere_r * 0.2),
                       sphere_r * 0.5, sphere_r * 0.35)

        # Edge glow ring
        edge_color = QColor(c1)
        edge_color.setAlphaF(0.3 + self._energy * 0.3)
        edge_pen = QPen(edge_color, 1.5 + self._energy)
        p.setPen(edge_pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QPointF(cx, cy), sphere_r, sphere_r)

        # ─── Status text below orb ───
        if self._status_text:
            p.setPen(QPen(QColor(c1.red(), c1.green(), c1.blue(), 180)))
            p.setFont(QFont(FONTS["family"], FONTS["size_xs"]))
            text_rect = QRectF(0, cy + sphere_r + 12, w, 20)
            p.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, self._status_text)

        p.end()

import sys
import os
import wave
import struct
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSlider, QLabel, QPushButton, QGroupBox, QComboBox, QCheckBox,
    QScrollArea, QFrame
)
from PyQt6.QtCore import Qt, QTimer, QPointF
from PyQt6.QtGui import QPainter, QPen, QColor, QPainterPath

CONFIG_PATH = r"C:\Program Files\EqualizerAPO\config\config.txt"
VST_DIR = r"C:\Program Files\EqualizerAPO\VSTPlugins"
IR_DIR = r"C:\Program Files\EqualizerAPO\config"

BANDS = [
    ("32 Hz", 32),
    ("64 Hz", 64),
    ("125 Hz", 125),
    ("250 Hz", 250),
    ("500 Hz", 500),
    ("1 kHz", 1000),
    ("2 kHz", 2000),
    ("4 kHz", 4000),
    ("8 kHz", 8000),
    ("16 kHz", 16000),
]

PRESETS = {
    "Flat": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    "Bass Booster": [6, 5, 4, 3, 1, 0, 0, 0, 0, 0],
    "Bass Reducer": [0, 0, 0, 0, 0, 0, 0, -3, -5, -6],
    "Treble Booster": [0, 0, 0, 0, 0, 1, 2, 4, 5, 6],
    "Treble Reducer": [0, 0, 0, 0, 0, -1, -2, -4, -5, -6],
    "Acoustic": [5, 5, 4, 1, 2, 2, 4, 4, 3, 2],
    "Classical": [5, 4, 3, 2, -1, -1, 0, 2, 3, 4],
    "Dance": [4, 7, 5, 0, 2, 4, 5, 4, 3, 0],
    "Deep": [5, 4, 2, 1, 3, 3, 2, -1, -3, -4],
    "Electronic": [4, 4, 1, 0, -2, 2, 1, 1, 4, 5],
    "Hip-Hop": [5, 4, 1, 3, -1, -1, 1, 0, 2, 3],
    "Jazz": [4, 3, 1, 2, -2, -2, 0, 1, 3, 4],
    "Latin": [4, 3, 0, 0, -2, -2, -2, 0, 3, 5],
    "Loudness": [6, 4, 0, 0, -2, 0, -1, -5, 6, 1],
    "Lounge": [-3, -2, -1, 2, 4, 3, 0, -2, 2, 1],
    "Piano": [3, 2, 0, 2, 3, 2, 3, 4, 3, 4],
    "Pop": [-1, -1, 0, 2, 4, 4, 2, 0, -1, -1],
    "R&B": [3, 7, 6, 1, -3, -2, 2, 3, 3, 4],
    "Rock": [5, 4, 3, 1, -1, -1, 0, 2, 3, 4],
}


import random

def generate_reverb_ir(room_size, decay, wet, sample_rate=48000):
    """Generate a reverb impulse response and write as 16-bit PCM WAV."""
    duration = 0.3 + room_size * 2.0  # 0.3s to 2.3s
    num_samples = int(sample_rate * duration)

    ir_l = [0.0] * num_samples
    ir_r = [0.0] * num_samples

    # Direct signal (dry)
    dry = 1.0 - wet * 0.5
    ir_l[0] = dry
    ir_r[0] = dry

    # Early reflections — discrete echoes at increasing intervals
    num_reflections = 6 + int(room_size * 12)
    for i in range(num_reflections):
        # Spread reflections across time based on room size
        time = 0.01 + room_size * 0.12 * ((i + 1) / num_reflections)
        sample_pos = int(time * sample_rate)
        if sample_pos < num_samples:
            # Decay amplitude with each reflection
            amp = wet * 0.4 * (decay * 0.8 + 0.2) ** i
            ir_l[sample_pos] += amp * (0.7 + 0.3 * random.random())
            # Slightly offset right channel for stereo spread
            offset = min(sample_pos + int(0.002 * sample_rate), num_samples - 1)
            ir_r[offset] += amp * (0.7 + 0.3 * random.random())

    # Late reverb tail — many small random reflections with decay
    late_start = int(0.05 * sample_rate)
    num_late = 80 + int(room_size * 200)
    for i in range(num_late):
        time = 0.05 + (duration - 0.05) * (i / num_late)
        sample_pos = int(time * sample_rate)
        if sample_pos < num_samples:
            # Exponential decay envelope
            env = wet * 0.15 * (2.718 ** (-3.0 * time / duration * (1.5 - decay)))
            ir_l[sample_pos] += env * (random.random() * 2 - 1)
            ir_r[sample_pos] += env * (random.random() * 2 - 1)

    # Write as 16-bit PCM stereo WAV
    path = os.path.join(IR_DIR, "reverb_ir.wav")
    with wave.open(path, 'w') as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        for i in range(num_samples):
            l = max(-32767, min(32767, int(ir_l[i] * 32767)))
            r = max(-32767, min(32767, int(ir_r[i] * 32767)))
            wf.writeframes(struct.pack('<hh', l, r))

    return path


class EQCurveWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.gains = [0] * len(BANDS)
        self.setMinimumHeight(100)

    def set_gains(self, gains):
        self.gains = gains
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        margin = 30

        # Background
        painter.fillRect(0, 0, w, h, QColor(30, 30, 30))

        draw_w = w - margin * 2
        draw_h = h - margin * 2

        # Grid lines
        pen = QPen(QColor(60, 60, 60))
        pen.setWidth(1)
        painter.setPen(pen)

        # Horizontal grid lines at -20, -10, 0, +10, +20
        for db in [-20, -10, 0, 10, 20]:
            y = margin + draw_h * (1 - (db + 20) / 40.0)
            painter.drawLine(int(margin), int(y), int(w - margin), int(y))
            # Label
            painter.setPen(QColor(120, 120, 120))
            painter.drawText(2, int(y + 4), f"{db:+d}")
            painter.setPen(pen)

        # 0 dB line (brighter)
        zero_y = margin + draw_h * 0.5
        pen_zero = QPen(QColor(100, 100, 100))
        pen_zero.setWidth(1)
        painter.setPen(pen_zero)
        painter.drawLine(int(margin), int(zero_y), int(w - margin), int(zero_y))

        # Frequency labels at bottom
        painter.setPen(QColor(150, 150, 150))
        for i, (name, freq) in enumerate(BANDS):
            x = margin + draw_w * i / (len(BANDS) - 1)
            painter.drawText(int(x - 15), int(h - 5), name)

        # EQ curve
        path = QPainterPath()
        points = []
        for i in range(len(BANDS)):
            x = margin + draw_w * i / (len(BANDS) - 1)
            y = margin + draw_h * (1 - (self.gains[i] + 20) / 40.0)
            points.append(QPointF(x, y))

        if points:
            path.moveTo(points[0])
            # Straight lines between points
            for i in range(1, len(points)):
                path.lineTo(points[i])

            # Draw filled area under curve
            fill_path = QPainterPath(path)
            fill_path.lineTo(points[-1].x(), zero_y)
            fill_path.lineTo(points[0].x(), zero_y)
            fill_path.closeSubpath()
            painter.fillPath(fill_path, QColor(0, 150, 255, 40))

            # Draw curve line
            pen_curve = QPen(QColor(0, 150, 255))
            pen_curve.setWidth(2)
            painter.setPen(pen_curve)
            painter.drawPath(path)

            # Draw points
            painter.setBrush(QColor(0, 150, 255))
            for p in points:
                painter.drawEllipse(p, 4, 4)

        painter.end()


class EffectSection(QGroupBox):
    def __init__(self, title, simple_params, detailed_params, on_change):
        super().__init__(title)
        self.on_change = on_change
        self.sliders = {}
        self.detailed_sliders = {}
        self.detailed_visible = False

        main_layout = QVBoxLayout(self)

        # Top row: enable checkbox + detailed toggle
        top_row = QHBoxLayout()
        self.enabled_check = QCheckBox("ON")
        self.enabled_check.setChecked(False)
        self.enabled_check.stateChanged.connect(self.on_change)
        top_row.addWidget(self.enabled_check)
        top_row.addStretch()
        self.detail_btn = QPushButton("▸ Detailed")
        self.detail_btn.setFixedWidth(90)
        self.detail_btn.clicked.connect(self.toggle_detailed)
        top_row.addWidget(self.detail_btn)
        main_layout.addLayout(top_row)

        # Simple controls
        self.simple_frame = QFrame()
        simple_layout = QVBoxLayout(self.simple_frame)
        simple_layout.setContentsMargins(0, 0, 0, 0)
        for name, min_val, max_val, default, suffix in simple_params:
            row = QHBoxLayout()
            row.addWidget(QLabel(f"{name}:"))
            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setRange(min_val, max_val)
            slider.setValue(default)
            slider.valueChanged.connect(self.on_change)
            row.addWidget(slider)
            label = QLabel(f"{default}{suffix}")
            label.setFixedWidth(60)
            slider.valueChanged.connect(lambda v, l=label, s=suffix: l.setText(f"{v}{s}"))
            row.addWidget(label)
            simple_layout.addLayout(row)
            self.sliders[name] = slider
        main_layout.addWidget(self.simple_frame)

        # Detailed controls (hidden by default)
        self.detailed_frame = QFrame()
        detailed_layout = QVBoxLayout(self.detailed_frame)
        detailed_layout.setContentsMargins(0, 0, 0, 0)
        for name, min_val, max_val, default, suffix in detailed_params:
            row = QHBoxLayout()
            row.addWidget(QLabel(f"{name}:"))
            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setRange(min_val, max_val)
            slider.setValue(default)
            slider.valueChanged.connect(self.on_change)
            row.addWidget(slider)
            label = QLabel(f"{default}{suffix}")
            label.setFixedWidth(60)
            slider.valueChanged.connect(lambda v, l=label, s=suffix: l.setText(f"{v}{s}"))
            row.addWidget(label)
            detailed_layout.addLayout(row)
            self.detailed_sliders[name] = slider
        self.detailed_frame.setVisible(False)
        main_layout.addWidget(self.detailed_frame)

    def toggle_detailed(self):
        self.detailed_visible = not self.detailed_visible
        self.detailed_frame.setVisible(self.detailed_visible)
        self.simple_frame.setVisible(not self.detailed_visible)
        self.detail_btn.setText("▾ Simple" if self.detailed_visible else "▸ Detailed")

    def is_enabled(self):
        return self.enabled_check.isChecked()

    def get_value(self, name):
        if self.detailed_visible and name in self.detailed_sliders:
            return self.detailed_sliders[name].value()
        if name in self.sliders:
            return self.sliders[name].value()
        if name in self.detailed_sliders:
            return self.detailed_sliders[name].value()
        return 0


class EqualizerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SonaPrism")
        self.setMinimumSize(600, 500)
        self.resize(800, 700)

        self._update_timer = QTimer()
        self._update_timer.setSingleShot(True)
        self._update_timer.setInterval(150)
        self._update_timer.timeout.connect(self._do_update_config)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # Preset selector + limiter
        top_layout = QHBoxLayout()
        top_layout.addWidget(QLabel("Preset:"))
        self.preset_combo = QComboBox()
        self.preset_combo.addItems(PRESETS.keys())
        self.preset_combo.currentTextChanged.connect(self.load_preset)
        top_layout.addWidget(self.preset_combo)
        top_layout.addStretch()
        self.limiter_check = QCheckBox("Limiter")
        self.limiter_check.setChecked(True)
        self.limiter_check.stateChanged.connect(self.update_config)
        top_layout.addWidget(self.limiter_check)
        layout.addLayout(top_layout)

        # Preamp
        preamp_layout = QHBoxLayout()
        preamp_layout.addWidget(QLabel("Preamp:"))
        self.preamp_slider = QSlider(Qt.Orientation.Horizontal)
        self.preamp_slider.setRange(-20, 10)
        self.preamp_slider.setValue(0)
        self.preamp_slider.valueChanged.connect(self.update_config)
        preamp_layout.addWidget(self.preamp_slider)
        self.preamp_label = QLabel("0 dB")
        self.preamp_label.setFixedWidth(50)
        preamp_layout.addWidget(self.preamp_label)
        layout.addLayout(preamp_layout)

        # EQ curve + sliders
        eq_group = QGroupBox("Equalizer — Bass | Mid | Treble")
        eq_group_layout = QVBoxLayout(eq_group)

        self.eq_curve = EQCurveWidget()
        eq_group_layout.addWidget(self.eq_curve, stretch=1)

        eq_layout = QHBoxLayout()
        self.sliders = []
        self.slider_value_labels = []

        for name, freq in BANDS:
            band_layout = QVBoxLayout()

            # Current value label
            val_label = QLabel("0 dB")
            val_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            val_label.setStyleSheet("font-weight: bold; font-size: 10px;")
            band_layout.addWidget(val_label)
            self.slider_value_labels.append(val_label)

            label_top = QLabel("+20")
            label_top.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label_top.setStyleSheet("font-size: 9px; color: gray;")
            band_layout.addWidget(label_top)

            slider = QSlider(Qt.Orientation.Vertical)
            slider.setRange(-20, 20)
            slider.setValue(0)
            slider.setMinimumHeight(100)
            slider.setTickPosition(QSlider.TickPosition.TicksBothSides)
            slider.setTickInterval(5)
            slider.valueChanged.connect(self.update_config)
            slider.valueChanged.connect(lambda v, l=val_label: l.setText(f"{v} dB"))
            slider.valueChanged.connect(self._update_curve)
            band_layout.addWidget(slider, stretch=1, alignment=Qt.AlignmentFlag.AlignCenter)
            self.sliders.append(slider)

            label_bottom = QLabel("-20")
            label_bottom.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label_bottom.setStyleSheet("font-size: 9px; color: gray;")
            band_layout.addWidget(label_bottom)

            freq_label = QLabel(name)
            freq_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            band_layout.addWidget(freq_label)

            eq_layout.addLayout(band_layout)

        eq_group_layout.addLayout(eq_layout)
        layout.addWidget(eq_group, stretch=2)

        # Effects section
        self.compressor = EffectSection(
            "Compressor",
            simple_params=[("Strength", 0, 100, 0, "%")],
            detailed_params=[
                ("Threshold", -60, 0, -20, " dB"),
                ("Ratio", 1, 20, 4, ":1"),
                ("Attack", 1, 200, 10, " ms"),
                ("Release", 10, 1000, 100, " ms"),
            ],
            on_change=self.update_config,
        )

        self.stereo = EffectSection(
            "Stereo Width",
            simple_params=[("Width", 0, 200, 100, "%")],
            detailed_params=[
                ("Width", 0, 200, 100, "%"),
            ],
            on_change=self.update_config,
        )

        self.reverb = EffectSection(
            "Reverb",
            simple_params=[("Amount", 0, 100, 0, "%")],
            detailed_params=[
                ("Room Size", 1, 100, 50, "%"),
                ("Decay", 1, 100, 50, "%"),
                ("Wet/Dry", 0, 100, 30, "%"),
            ],
            on_change=self.update_config,
        )

        self.delay = EffectSection(
            "Delay",
            simple_params=[("Amount", 0, 100, 0, "%")],
            detailed_params=[
                ("Time", 1, 1000, 250, " ms"),
                ("Feedback", 0, 95, 30, "%"),
                ("Wet/Dry", 0, 100, 25, "%"),
            ],
            on_change=self.update_config,
        )

        # Scrollable effects area
        effects_widget = QWidget()
        effects_layout = QVBoxLayout(effects_widget)
        effects_layout.setContentsMargins(0, 0, 0, 0)
        effects_layout.addWidget(self.compressor)
        effects_layout.addWidget(self.stereo)
        effects_layout.addWidget(self.reverb)
        effects_layout.addWidget(self.delay)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(effects_widget)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        layout.addWidget(scroll, stretch=1)

        # Reset button
        btn_layout = QHBoxLayout()
        reset_btn = QPushButton("Reset All")
        reset_btn.clicked.connect(self.reset_all)
        btn_layout.addStretch()
        btn_layout.addWidget(reset_btn)
        layout.addLayout(btn_layout)

        self.update_config()

    def _update_curve(self):
        gains = [self.sliders[i].value() for i in range(len(BANDS))]
        self.eq_curve.set_gains(gains)

    def update_config(self):
        self._update_timer.start()

    def _do_update_config(self):
        preamp = self.preamp_slider.value()
        self.preamp_label.setText(f"{preamp} dB")
        gains = [self.sliders[i].value() for i in range(len(BANDS))]
        self.eq_curve.set_gains(gains)

        eq_active = preamp != 0 or any(g != 0 for g in gains)
        comp_active = self.compressor.is_enabled()
        stereo_active = self.stereo.is_enabled()
        reverb_active = self.reverb.is_enabled()
        delay_active = self.delay.is_enabled()
        anything_active = eq_active or comp_active or stereo_active or reverb_active or delay_active

        if not anything_active:
            config_text = ""
        else:
            lines = []

            # Preamp
            if preamp != 0:
                lines.append(f"Preamp: {preamp} dB")

            # EQ filters
            for i, (name, freq) in enumerate(BANDS):
                if gains[i] != 0:
                    lines.append(f"Filter: ON PK Fc {freq} Hz Gain {gains[i]} dB Q 1.0")

            # Compressor
            if comp_active:
                if self.compressor.detailed_visible:
                    thresh_db = self.compressor.get_value("Threshold")
                    ratio_val = self.compressor.get_value("Ratio")
                    attack_ms = self.compressor.get_value("Attack")
                    release_ms = self.compressor.get_value("Release")
                else:
                    strength = self.compressor.get_value("Strength")
                    thresh_db = -int(strength * 0.4)
                    ratio_val = max(1, int(1 + strength * 0.07))
                    attack_ms = 10
                    release_ms = 200

                thresh_norm = 10 ** (thresh_db / 20.0)
                ratio_norm = (ratio_val - 1) / 99.0
                attack_norm = attack_ms / 500.0
                release_norm = release_ms / 5000.0

                lines.append(
                    f'VSTPlugin: Library "{VST_DIR}\\reacomp-standalone.dll"'
                    f" Thresh {thresh_norm:.6f} Ratio {ratio_norm:.6f}"
                    f" Attack {attack_norm:.6f} Release {release_norm:.6f}"
                    f" Wet 1 Dry 0 AutoMkUp 1"
                )

            # Stereo Width using Equalizer APO's Copy command
            # Mid = (L+R)/2, Side = (L-R)/2
            # Width controls the balance between mid and side
            if stereo_active:
                width = self.stereo.get_value("Width")
                if width != 100:
                    # Convert width percentage to mid/side coefficients
                    # 0% = mono (all mid, no side)
                    # 100% = normal
                    # 200% = max wide (boosted side, reduced mid)
                    mid_coeff = (200 - width) / 100.0  # 2.0 to 0.0
                    side_coeff = width / 100.0  # 0.0 to 2.0
                    # Encode as L/R from mid/side:
                    # L = mid*M + side*S = mid*(L+R)/2 + side*(L-R)/2
                    # R = mid*M - side*S = mid*(L+R)/2 - side*(L-R)/2
                    # Simplify: L = L*(mid+side)/2 + R*(mid-side)/2
                    #           R = L*(mid-side)/2 + R*(mid+side)/2
                    ll = (mid_coeff + side_coeff) / 2.0
                    lr = (mid_coeff - side_coeff) / 2.0
                    lines.append(f"Copy: {ll:.3f}*L+{lr:.3f}*R=L {lr:.3f}*L+{ll:.3f}*R=R")

            # Reverb using Convolution with generated impulse response
            if reverb_active:
                if self.reverb.detailed_visible:
                    wet = self.reverb.get_value("Wet/Dry") / 100.0
                    room_size = self.reverb.get_value("Room Size") / 100.0
                    decay = self.reverb.get_value("Decay") / 100.0
                else:
                    amount = self.reverb.get_value("Amount")
                    wet = amount / 100.0
                    room_size = 0.5
                    decay = 0.5

                try:
                    generate_reverb_ir(room_size, decay, wet, sample_rate=48000)
                    lines.append("Convolution: reverb_ir.wav")
                except Exception:
                    pass

            # Delay
            if delay_active:
                if self.delay.detailed_visible:
                    time_ms = self.delay.get_value("Time")
                    feedback = self.delay.get_value("Feedback") / 100.0
                    wet = self.delay.get_value("Wet/Dry") / 100.0
                else:
                    amount = self.delay.get_value("Amount")
                    time_ms = 250
                    feedback = 0.3
                    wet = amount / 100.0
                lines.append(
                    f'VSTPlugin: Library "{VST_DIR}\\readelay-standalone.dll"'
                    f" Length {time_ms} Feedback {feedback:.4f} Wet {wet:.4f}"
                )

            # Limiter last
            if self.limiter_check.isChecked() and (eq_active or comp_active or reverb_active or delay_active):
                lines.append(
                    f'VSTPlugin: Library "{VST_DIR}\\LoudMax64.dll"'
                )

            config_text = "\n".join(lines) + "\n"

        try:
            with open(CONFIG_PATH, "w") as f:
                f.write(config_text)
        except PermissionError:
            self.setWindowTitle("SonaPrism — Run as Administrator!")

    def load_preset(self, name):
        values = PRESETS[name]
        for i, val in enumerate(values):
            self.sliders[i].setValue(val)

    def reset_all(self):
        self.preamp_slider.setValue(0)
        for slider in self.sliders:
            slider.setValue(0)
        self.preset_combo.setCurrentText("Flat")
        self.compressor.enabled_check.setChecked(False)
        self.stereo.enabled_check.setChecked(False)
        self.reverb.enabled_check.setChecked(False)
        self.delay.enabled_check.setChecked(False)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = EqualizerApp()
    window.show()
    sys.exit(app.exec())

"""Pitch shifting, tempo stretching, and engine selection DSP rack for Audio Tools."""

from __future__ import annotations

from PyQt6.QtWidgets import QDoubleSpinBox, QFrame, QHBoxLayout, QLabel, QSpinBox, QVBoxLayout

from src.ui.components.controls import ComboBox, ToolButton


def build_dsp_rack(page) -> QFrame:
    card = QFrame(objectName="AudioToolsCard")
    layout = QVBoxLayout(card)
    layout.setContentsMargins(12, 10, 12, 10)
    page.lblDsp = QLabel("PITCH SHIFT & TEMPO STRETCH RACK", objectName="FieldLabel")
    layout.addWidget(page.lblDsp)
    for r in (_pitch_row(page), _bpm_row(page), _engine_row(page)):
        layout.addLayout(r)
    return card


def _pitch_row(page) -> QHBoxLayout:
    row = QHBoxLayout()
    page.semitoneSpin = QSpinBox(minimum=-12, maximum=12, value=0)
    page.semitoneSpin.valueChanged.connect(page._update_preview_labels)
    page.lblSemitones = QLabel("Semitones:", objectName="MutedText")
    page.resultingKeyLabel = QLabel("Resulting key: C major (8B) · 0 st", objectName="StepBadge")
    row.addWidget(page.lblSemitones)
    row.addWidget(page.semitoneSpin)
    for step in (-2, -1, 0, 1, 2):
        btn = ToolButton(f"{f'+{step}' if step > 0 else step} st")
        btn.clicked.connect(lambda _c=False, s=step: page.semitoneSpin.setValue(s))
        row.addWidget(btn)
    row.addStretch(1)
    row.addWidget(page.resultingKeyLabel)
    return row


def _bpm_row(page) -> QHBoxLayout:
    row = QHBoxLayout()
    page.bpmSpin, page.targetBpmSpin = QDoubleSpinBox(), QDoubleSpinBox()
    for sp in (page.bpmSpin, page.targetBpmSpin):
        sp.setRange(30.0, 300.0)
        sp.setDecimals(1)
        sp.setSingleStep(0.5)
        sp.setValue(120.0)
    page.bpmSpin.valueChanged.connect(page._on_source_bpm_changed)
    page.targetBpmSpin.valueChanged.connect(page._update_preview_labels)
    page.halfBpmBtn, page.doubleBpmBtn, page.resetTempoBtn = ToolButton("0.5x BPM"), ToolButton("2x BPM"), ToolButton("1.0x Tempo")
    page.tempoRatioLabel = QLabel("Stretch: 1.00x (100%)", objectName="StepBadge")
    page.halfBpmBtn.clicked.connect(lambda: page.bpmSpin.setValue(round(max(30.0, page.bpmSpin.value() * 0.5), 1)))
    page.doubleBpmBtn.clicked.connect(lambda: page.bpmSpin.setValue(round(min(300.0, page.bpmSpin.value() * 2.0), 1)))
    page.resetTempoBtn.clicked.connect(lambda: page.targetBpmSpin.setValue(page.bpmSpin.value()))
    page.lblSrcBpm, page.lblTgtBpm = QLabel("Source BPM:", objectName="MutedText"), QLabel("Target BPM:", objectName="MutedText")
    for w in (page.lblSrcBpm, page.bpmSpin, page.halfBpmBtn, page.doubleBpmBtn, page.lblTgtBpm, page.targetBpmSpin, page.resetTempoBtn):
        row.addWidget(w)
    row.addStretch(1)
    row.addWidget(page.tempoRatioLabel)
    return row


def _engine_row(page) -> QHBoxLayout:
    row = QHBoxLayout()
    page.engineCombo, page.formatCombo = ComboBox(), ComboBox()
    for t, v in (("Rubber Band R3 Vocal (Formant + Centre Focus)", "r3_finer"), ("Rubber Band R3 Percussive / Full Mix (Wide Stereo)", "r3_percussive"), ("FFmpeg Rubber Band (Fast Formant)", "ffmpeg_formant")):
        page.engineCombo.addItem(t, v)
    for name, key in (("WAV 24-bit (Cubase / DAW Ready)", "wav"), ("FLAC Lossless", "flac"), ("MP3 320 kbps", "mp3")):
        page.formatCombo.addItem(name, key)
    page.formatCombo.currentIndexChanged.connect(page._update_preview_labels)
    page.lblEngine, page.lblFormat = QLabel("Engine:", objectName="MutedText"), QLabel("Format:", objectName="MutedText")
    for w, s in ((page.lblEngine, 0), (page.engineCombo, 1), (page.lblFormat, 0), (page.formatCombo, 1)):
        row.addWidget(w, s)
    return row

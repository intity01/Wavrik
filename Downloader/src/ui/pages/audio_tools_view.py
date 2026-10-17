"""UI layout builder for the Audio Tools page."""

from __future__ import annotations

from PyQt6.QtWidgets import QDoubleSpinBox, QFrame, QHBoxLayout, QLabel, QSpinBox, QVBoxLayout, QWidget

from src.services.audio_analysis import ALL_KEYS
from src.ui.components.controls import ComboBox, PrimaryPushButton, PushButton, SmoothScrollArea, ToolButton


def build_ui(page) -> None:
    root = QVBoxLayout(page)
    root.setContentsMargins(0, 0, 0, 0)
    scroll, content = SmoothScrollArea(), QWidget()
    scroll.setWidgetResizable(True)
    layout = QVBoxLayout(content)
    layout.setContentsMargins(24, 22, 24, 22)
    layout.setSpacing(14)
    layout.addWidget(QLabel("Audio Tools", objectName="PageTitle"))
    layout.addWidget(QLabel("Estimate Key & BPM, shift pitch with Rubber Band R3, A/B audition, and export safely.", objectName="PageSubtitle"))
    layout.addWidget(_source_card(page))
    layout.addWidget(_analysis_card(page))
    layout.addWidget(_pitch_card(page))
    layout.addWidget(_export_card(page))
    layout.addStretch(1)
    scroll.setWidget(content)
    root.addWidget(scroll)


def _source_card(page) -> QFrame:
    card, layout = _card("Source Audio")
    row = QHBoxLayout()
    page.fileLabel = QLabel("No audio file loaded. Choose a local file or send one from Library.", objectName="MutedText")
    page.fileLabel.setWordWrap(True)
    page.chooseFileBtn = PushButton("Choose audio file")
    page.chooseFileBtn.clicked.connect(page._choose_file)
    row.addWidget(page.fileLabel, 1)
    row.addWidget(page.chooseFileBtn)
    layout.addLayout(row)
    return card


def _analysis_card(page) -> QFrame:
    card, layout = _card("Key & BPM Analysis")
    page.badgeLabel = QLabel("Experimental / Estimate · ทดลอง / ค่าประมาณ", objectName="ExperimentalBadge")
    layout.addWidget(page.badgeLabel)
    key_row = QHBoxLayout()
    page.detectedKeyCombo = ComboBox()
    page.detectedKeyCombo.addItems(list(ALL_KEYS))
    page.detectedKeyCombo.currentTextChanged.connect(page._update_preview_labels)
    page.camelotLabel = QLabel("Camelot: 8B", objectName="StepBadge")
    page.reanalyzeBtn = ToolButton("Re-analyze")
    page.reanalyzeBtn.clicked.connect(page._reanalyze)
    for w in (QLabel("Detected / Override Key:"), page.detectedKeyCombo, page.camelotLabel):
        key_row.addWidget(w)
    key_row.addStretch(1)
    key_row.addWidget(page.reanalyzeBtn)
    layout.addLayout(key_row)
    layout.addLayout(_bpm_row(page))
    return card


def _bpm_row(page) -> QHBoxLayout:
    row = QHBoxLayout()
    page.bpmSpin = QDoubleSpinBox()
    page.bpmSpin.setRange(30.0, 300.0)
    page.bpmSpin.setDecimals(1)
    page.bpmSpin.setSingleStep(0.5)
    page.bpmSpin.setValue(120.0)
    page.halfBpmBtn = ToolButton("0.5x BPM")
    page.doubleBpmBtn = ToolButton("2x BPM")
    page.halfBpmBtn.clicked.connect(lambda: page.bpmSpin.setValue(round(max(30.0, page.bpmSpin.value() * 0.5), 1)))
    page.doubleBpmBtn.clicked.connect(lambda: page.bpmSpin.setValue(round(min(300.0, page.bpmSpin.value() * 2.0), 1)))
    for w in (QLabel("Estimated BPM:"), page.bpmSpin, page.halfBpmBtn, page.doubleBpmBtn):
        row.addWidget(w)
    row.addStretch(1)
    return row


def _pitch_card(page) -> QFrame:
    card, layout = _card("Pitch Shift & Engine (-12 to +12 Semitones)")
    shift_row = QHBoxLayout()
    page.semitoneSpin = QSpinBox()
    page.semitoneSpin.setRange(-12, 12)
    page.semitoneSpin.setValue(0)
    page.semitoneSpin.valueChanged.connect(page._update_preview_labels)
    shift_row.addWidget(QLabel("Semitones:"))
    shift_row.addWidget(page.semitoneSpin)
    for step in (-2, -1, 0, 1, 2):
        btn = ToolButton(f"{f'+{step}' if step > 0 else step} st")
        btn.clicked.connect(lambda _checked=False, s=step: page.semitoneSpin.setValue(s))
        shift_row.addWidget(btn)
    page.resultingKeyLabel = QLabel("Resulting key: C major (8B) · 0 st", objectName="StepBadge")
    shift_row.addStretch(1)
    shift_row.addWidget(page.resultingKeyLabel)
    layout.addLayout(shift_row)
    layout.addLayout(_engine_row(page))
    return card


def _engine_row(page) -> QHBoxLayout:
    row = QHBoxLayout()
    page.engineCombo, page.formatCombo = ComboBox(), ComboBox()
    page.engineCombo.addItem("Rubber Band R3 Finer (Studio Quality)", "r3_finer")
    page.engineCombo.addItem("FFmpeg Rubber Band (Fast Formant)", "ffmpeg_formant")
    for label, key in (("WAV 24-bit (Cubase / DAW Ready)", "wav"), ("FLAC Lossless", "flac"), ("MP3 320 kbps", "mp3")):
        page.formatCombo.addItem(label, key)
    page.formatCombo.currentIndexChanged.connect(page._update_preview_labels)
    row.addWidget(QLabel("Engine:"))
    row.addWidget(page.engineCombo, 1)
    row.addWidget(QLabel("Format:"))
    row.addWidget(page.formatCombo, 1)
    return row


def _export_card(page) -> QFrame:
    card, layout = _card("A/B Audition & Non-Destructive Export")
    page.outputPreviewLabel = QLabel("Original file is never overwritten.", objectName="MutedText")
    page.statusLabel = QLabel("Load an audio file to begin.", objectName="MutedText")
    actions = QHBoxLayout()
    page.previewOrigBtn, page.previewShiftedBtn = ToolButton("Play Original (A)"), ToolButton("Preview Shifted (B)")
    page.exportBtn, page.openFolderBtn = PrimaryPushButton("Export Shifted Copy"), PushButton("Show in folder")
    page.openFolderBtn.hide()
    page.previewOrigBtn.clicked.connect(page._play_original)
    page.previewShiftedBtn.clicked.connect(page._preview_shifted)
    page.exportBtn.clicked.connect(page._export_shifted)
    page.openFolderBtn.clicked.connect(page._open_export_folder)
    actions.addWidget(page.previewOrigBtn)
    actions.addWidget(page.previewShiftedBtn)
    actions.addStretch(1)
    actions.addWidget(page.openFolderBtn)
    actions.addWidget(page.exportBtn)
    layout.addWidget(page.outputPreviewLabel)
    layout.addWidget(page.statusLabel)
    layout.addLayout(actions)
    return card


def _card(title: str) -> tuple[QFrame, QVBoxLayout]:
    card = QFrame(objectName="AudioToolsCard")
    layout = QVBoxLayout(card)
    layout.setContentsMargins(16, 14, 16, 14)
    layout.setSpacing(10)
    layout.addWidget(QLabel(title, objectName="SectionTitle"))
    return card, layout

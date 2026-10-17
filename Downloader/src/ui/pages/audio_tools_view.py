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
    for w in (QLabel("Audio Tools", objectName="PageTitle"), QLabel("Estimate Key & BPM, shift pitch & tempo with Rubber Band R3, and export safely.", objectName="PageSubtitle"), _source_card(page), _analysis_card(page), _pitch_card(page), _export_card(page)):
        layout.addWidget(w)
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
    card, layout = _card("Key, Section Modulation & BPM Analysis")
    page.badgeLabel = QLabel("Experimental / Estimate · ทดลอง / ค่าประมาณ", objectName="ExperimentalBadge")
    page.sectionKeyLabel = QLabel("Section Key: -- (1st Half vs 2nd Half)", objectName="MutedText")
    layout.addWidget(page.badgeLabel)
    layout.addWidget(page.sectionKeyLabel)
    key_row = QHBoxLayout()
    page.detectedKeyCombo, page.camelotLabel, page.reanalyzeBtn = ComboBox(), QLabel("Camelot: 8B", objectName="StepBadge"), ToolButton("Re-analyze")
    page.detectedKeyCombo.addItems(list(ALL_KEYS))
    page.detectedKeyCombo.currentTextChanged.connect(page._update_preview_labels)
    page.reanalyzeBtn.clicked.connect(page._reanalyze)
    for w in (QLabel("Detected / Override Key:"), page.detectedKeyCombo, page.camelotLabel):
        key_row.addWidget(w)
    key_row.addStretch(1)
    key_row.addWidget(page.reanalyzeBtn)
    for row in (key_row, _candidates_row(page), _bpm_row(page)):
        layout.addLayout(row)
    return card


def _candidates_row(page) -> QHBoxLayout:
    row = QHBoxLayout()
    row.addWidget(QLabel("Top-3 Candidates:", objectName="MutedText"))
    page.candButtons = [ToolButton(f"#{i} --") for i in (1, 2, 3)]
    for idx, btn in enumerate(page.candButtons):
        btn.clicked.connect(lambda _c=False, i=idx: page._select_candidate(i))
        row.addWidget(btn)
    row.addStretch(1)
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
    for w in (QLabel("Source BPM:"), page.bpmSpin, page.halfBpmBtn, page.doubleBpmBtn, QLabel("Target BPM:"), page.targetBpmSpin, page.resetTempoBtn, page.tempoRatioLabel):
        row.addWidget(w)
    row.addStretch(1)
    return row


def _pitch_card(page) -> QFrame:
    card, layout = _card("Pitch Shift & Engine (-12 to +12 Semitones)")
    shift_row = QHBoxLayout()
    page.semitoneSpin = QSpinBox(minimum=-12, maximum=12, value=0)
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
    for w, stretch in ((QLabel("Engine:"), 0), (page.engineCombo, 1), (QLabel("Format:"), 0), (page.formatCombo, 1)):
        row.addWidget(w, stretch)
    return row


def _export_card(page) -> QFrame:
    card, layout = _card("A/B Audition & Non-Destructive Export")
    page.outputPreviewLabel, page.statusLabel = QLabel("Original file is never overwritten.", objectName="MutedText"), QLabel("Load an audio file to begin.", objectName="MutedText")
    actions = QHBoxLayout()
    page.previewOrigBtn, page.previewShiftedBtn = ToolButton("Play Original (A)"), ToolButton("Preview Shifted (B)")
    page.exportBtn, page.openFolderBtn = PrimaryPushButton("Export Shifted Copy"), PushButton("Show in folder")
    page.openFolderBtn.hide()
    for btn, fn in ((page.previewOrigBtn, page._play_original), (page.previewShiftedBtn, page._preview_shifted), (page.exportBtn, page._export_shifted), (page.openFolderBtn, page._open_export_folder)):
        btn.clicked.connect(fn)
    for w in (page.previewOrigBtn, page.previewShiftedBtn):
        actions.addWidget(w)
    actions.addStretch(1)
    actions.addWidget(page.openFolderBtn)
    actions.addWidget(page.exportBtn)
    for w in (page.outputPreviewLabel, page.statusLabel):
        layout.addWidget(w)
    layout.addLayout(actions)
    return card


def _card(title: str) -> tuple[QFrame, QVBoxLayout]:
    card = QFrame(objectName="AudioToolsCard")
    layout = QVBoxLayout(card)
    layout.setContentsMargins(16, 14, 16, 14)
    layout.setSpacing(10)
    layout.addWidget(QLabel(title, objectName="SectionTitle"))
    return card, layout

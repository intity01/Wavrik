"""Studio Inspector, Stem Separation, and DSP Rack layout for the Audio Tools page."""
from __future__ import annotations
from PyQt6.QtWidgets import QDoubleSpinBox, QFrame, QHBoxLayout, QLabel, QSpinBox, QVBoxLayout, QWidget
from src.services.audio_analysis import ALL_KEYS
from src.ui.components.controls import ComboBox, ElidedLabel, PrimaryPushButton, PushButton, SmoothScrollArea, ToolButton
from src.ui.components.waveform_widget import WaveformWidget
from src.ui.i18n import tr
from .audio_tools_presenter import build_stem_rack


def build_ui(page) -> None:
    root = QVBoxLayout(page)
    root.setContentsMargins(0, 0, 0, 0)
    scroll, content = SmoothScrollArea(widgetResizable=True), QWidget()
    layout = QVBoxLayout(content)
    layout.setContentsMargins(20, 14, 20, 14)
    layout.setSpacing(8)
    page.titleLabel = QLabel("Audio Tools", objectName="PageTitle")
    page.subtitleLabel = QLabel(tr("at.subtitle", "en"), objectName="PageSubtitle", wordWrap=True)
    for w in (page.titleLabel, page.subtitleLabel, _source_bar(page), _inspector_rack(page), build_stem_rack(page), _dsp_rack(page), _audition_bar(page)):
        layout.addWidget(w)
    layout.addStretch(1)
    scroll.setWidget(content)
    root.addWidget(scroll)


def _source_bar(page) -> QFrame:
    card = QFrame(objectName="AudioToolsCard")
    row = QHBoxLayout(card)
    row.setContentsMargins(12, 8, 12, 8)
    page.fileLabel = ElidedLabel(tr("at.no_file", "en"), objectName="MutedText")
    page.chooseFileBtn, page.batchBtn = PushButton("Choose audio file"), ToolButton("Batch Process...")
    page.chooseFileBtn.clicked.connect(page._choose_file)
    page.batchBtn.clicked.connect(page._open_batch_dialog)
    for w, st in ((QLabel("SOURCE", objectName="FieldLabel"), 0), (page.fileLabel, 1), (page.chooseFileBtn, 0), (page.batchBtn, 0)):
        row.addWidget(w, st)
    return card


def _inspector_rack(page) -> QFrame:
    card = QFrame(objectName="AudioToolsCard")
    layout = QVBoxLayout(card)
    layout.setContentsMargins(12, 10, 12, 10)
    top, key_row = QHBoxLayout(), QHBoxLayout()
    page.sectionKeyLabel, page.badgeLabel, page.reanalyzeBtn = ElidedLabel("Section Key: -- (1st Half vs 2nd Half)", objectName="MutedText"), QLabel("Experimental / Estimate", objectName="ExperimentalBadge"), ToolButton("Re-analyze")
    page.reanalyzeBtn.clicked.connect(page._reanalyze)
    for w, st in ((QLabel("HARMONIC & WAVEFORM INSPECTOR", objectName="FieldLabel"), 0), (page.sectionKeyLabel, 1), (page.badgeLabel, 0), (page.reanalyzeBtn, 0)):
        top.addWidget(w, st)
    page.waveformWidget, page.detectedKeyCombo, page.camelotLabel = WaveformWidget(), ComboBox(), QLabel("Camelot: 8B", objectName="StepBadge")
    page.waveformWidget.seekRequested.connect(page._on_seek_requested)
    page.detectedKeyCombo.addItems(list(ALL_KEYS))
    page.detectedKeyCombo.currentTextChanged.connect(page._update_preview_labels)
    for w in (QLabel("Detected / Override Key:", objectName="MutedText"), page.detectedKeyCombo, page.camelotLabel):
        key_row.addWidget(w)
    key_row.addStretch(1)
    c_row, page.candButtons = _buttons_row("Top-3 Candidates:", 3, page._select_candidate)
    h_row, page.camelotButtons = _buttons_row("Harmonic Mix (Camelot):", 4, page._select_harmonic_neighbor)
    layout.addLayout(top)
    layout.addWidget(page.waveformWidget)
    for r in (key_row, c_row, h_row):
        layout.addLayout(r)
    return card


def _buttons_row(label: str, count: int, on_click) -> tuple[QHBoxLayout, list[ToolButton]]:
    row, btns = QHBoxLayout(), [ToolButton(f"#{i + 1} --") for i in range(count)]
    row.addWidget(QLabel(label, objectName="MutedText", minimumWidth=148))
    for idx, btn in enumerate(btns):
        btn.clicked.connect(lambda _c=False, i=idx: on_click(i))
        row.addWidget(btn)
    row.addStretch(1)
    return row, btns


def _dsp_rack(page) -> QFrame:
    card = QFrame(objectName="AudioToolsCard")
    layout = QVBoxLayout(card)
    layout.setContentsMargins(12, 10, 12, 10)
    layout.addWidget(QLabel("PITCH SHIFT & TEMPO STRETCH RACK", objectName="FieldLabel"))
    for r in (_pitch_row(page), _bpm_row(page), _engine_row(page)):
        layout.addLayout(r)
    return card


def _pitch_row(page) -> QHBoxLayout:
    row = QHBoxLayout()
    page.semitoneSpin = QSpinBox(minimum=-12, maximum=12, value=0)
    page.semitoneSpin.valueChanged.connect(page._update_preview_labels)
    row.addWidget(QLabel("Semitones:", objectName="MutedText"))
    row.addWidget(page.semitoneSpin)
    for step in (-2, -1, 0, 1, 2):
        btn = ToolButton(f"{f'+{step}' if step > 0 else step} st")
        btn.clicked.connect(lambda _checked=False, s=step: page.semitoneSpin.setValue(s))
        row.addWidget(btn)
    page.resultingKeyLabel = QLabel("Resulting key: C major (8B) · 0 st", objectName="StepBadge")
    row.addStretch(1)
    row.addWidget(page.resultingKeyLabel)
    return row


def _bpm_row(page) -> QHBoxLayout:
    row = QHBoxLayout()
    page.bpmSpin, page.targetBpmSpin = QDoubleSpinBox(), QDoubleSpinBox()
    for sp in (page.bpmSpin, page.targetBpmSpin):
        sp.setRange(30.0, 300.0) or sp.setDecimals(1) or sp.setSingleStep(0.5) or sp.setValue(120.0)
    page.bpmSpin.valueChanged.connect(page._on_source_bpm_changed)
    page.targetBpmSpin.valueChanged.connect(page._update_preview_labels)
    page.halfBpmBtn, page.doubleBpmBtn, page.resetTempoBtn = ToolButton("0.5x BPM"), ToolButton("2x BPM"), ToolButton("1.0x Tempo")
    page.tempoRatioLabel = QLabel("Stretch: 1.00x (100%)", objectName="StepBadge")
    page.halfBpmBtn.clicked.connect(lambda: page.bpmSpin.setValue(round(max(30.0, page.bpmSpin.value() * 0.5), 1)))
    page.doubleBpmBtn.clicked.connect(lambda: page.bpmSpin.setValue(round(min(300.0, page.bpmSpin.value() * 2.0), 1)))
    page.resetTempoBtn.clicked.connect(lambda: page.targetBpmSpin.setValue(page.bpmSpin.value()))
    for w in (QLabel("Source BPM:", objectName="MutedText"), page.bpmSpin, page.halfBpmBtn, page.doubleBpmBtn, QLabel("Target BPM:", objectName="MutedText"), page.targetBpmSpin, page.resetTempoBtn):
        row.addWidget(w)
    row.addStretch(1)
    row.addWidget(page.tempoRatioLabel)
    return row


def _engine_row(page) -> QHBoxLayout:
    row = QHBoxLayout()
    page.engineCombo, page.formatCombo = ComboBox(), ComboBox()
    for text, val in (("Rubber Band R3 Vocal (Formant + Centre Focus)", "r3_finer"), ("Rubber Band R3 Percussive / Full Mix (Wide Stereo)", "r3_percussive"), ("FFmpeg Rubber Band (Fast Formant)", "ffmpeg_formant")):
        page.engineCombo.addItem(text, val)
    for label, key in (("WAV 24-bit (Cubase / DAW Ready)", "wav"), ("FLAC Lossless", "flac"), ("MP3 320 kbps", "mp3")):
        page.formatCombo.addItem(label, key)
    page.formatCombo.currentIndexChanged.connect(page._update_preview_labels)
    for w, stretch in ((QLabel("Engine:", objectName="MutedText"), 0), (page.engineCombo, 1), (QLabel("Format:", objectName="MutedText"), 0), (page.formatCombo, 1)):
        row.addWidget(w, stretch)
    return row


def _audition_bar(page) -> QFrame:
    card = QFrame(objectName="AudioToolsCard")
    layout = QVBoxLayout(card)
    layout.setContentsMargins(12, 10, 12, 10)
    info_row, actions = QHBoxLayout(), QHBoxLayout()
    page.outputPreviewLabel, page.statusLabel = ElidedLabel("Original file is never overwritten.", objectName="MonoValue"), QLabel("Load an audio file to begin.", objectName="MutedText")
    info_row.addWidget(page.outputPreviewLabel, 1)
    info_row.addWidget(page.statusLabel)
    page.previewOrigBtn, page.previewShiftedBtn, page.stopAudioBtn = ToolButton("Play Original (A)"), ToolButton("Preview Shifted (B)"), ToolButton("Stop")
    page.exportBtn, page.openFolderBtn = PrimaryPushButton("Export Shifted Copy"), PushButton("Show in folder")
    page.openFolderBtn.hide()
    for btn, fn in ((page.previewOrigBtn, page._play_original), (page.previewShiftedBtn, page._preview_shifted), (page.stopAudioBtn, page._stop_playback), (page.exportBtn, page._export_shifted), (page.openFolderBtn, page._open_export_folder)):
        btn.clicked.connect(fn)
    for w, st in ((page.previewOrigBtn, 0), (page.previewShiftedBtn, 0), (page.stopAudioBtn, 0), (QWidget(), 1), (page.openFolderBtn, 0), (page.exportBtn, 0)):
        actions.addWidget(w, st)
    layout.addLayout(info_row)
    layout.addLayout(actions)
    return card

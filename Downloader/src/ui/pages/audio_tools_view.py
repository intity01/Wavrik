"""Studio Inspector, Stem Separation, and DSP Rack layout for the Audio Tools page."""

from __future__ import annotations

from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from src.services.audio_analysis import ALL_KEYS
from src.services.audio_stems import STEM_MODES, is_separator_available
from src.ui.components.controls import ComboBox, ElidedLabel, PrimaryPushButton, PushButton, SmoothScrollArea, ToolButton
from src.ui.components.waveform_widget import WaveformWidget
from src.ui.i18n import tr

from .audio_tools_dsp import build_dsp_rack



def build_ui(page) -> None:
    root = QVBoxLayout(page)
    root.setContentsMargins(0, 0, 0, 0)
    scroll, content = SmoothScrollArea(widgetResizable=True), QWidget()
    layout = QVBoxLayout(content)
    layout.setContentsMargins(24, 24, 24, 24)
    layout.setSpacing(14)
    page.titleLabel = QLabel("Audio Tools", objectName="PageTitle")
    page.subtitleLabel = QLabel(tr("at.subtitle", "en"), objectName="PageSubtitle", wordWrap=True)
    for w in (page.titleLabel, page.subtitleLabel, _source_bar(page), _inspector_rack(page), build_stem_rack(page), build_dsp_rack(page), _audition_bar(page)):
        layout.addWidget(w)
    layout.addStretch(1)
    scroll.setWidget(content)
    root.addWidget(scroll)
    from .audio_tools_i18n import wire_tab_order
    wire_tab_order(page)


def _source_bar(page) -> QFrame:
    card = QFrame(objectName="AudioToolsCard")
    row = QHBoxLayout(card)
    row.setContentsMargins(12, 8, 12, 8)
    page.fileLabel = ElidedLabel(tr("at.no_file", "en"), objectName="MutedText")
    page.chooseFileBtn, page.batchBtn = PushButton("Choose audio file"), PushButton("Batch Process...")
    page.chooseFileBtn.clicked.connect(page._choose_file)
    page.batchBtn.clicked.connect(page._open_batch_dialog)
    page.lblSource = QLabel("SOURCE", objectName="FieldLabel")
    for w, st in ((page.lblSource, 0), (page.fileLabel, 1), (page.chooseFileBtn, 0), (page.batchBtn, 0)):
        row.addWidget(w, st)
    return card


def build_stem_rack(page) -> QFrame:
    card = QFrame(objectName="AudioToolsCard")
    layout = QVBoxLayout(card)
    layout.setContentsMargins(12, 8, 12, 8)
    row = QHBoxLayout()
    page.stemModeCombo = ComboBox()
    for label, key in STEM_MODES:
        page.stemModeCombo.addItem(label, key)
    if not is_separator_available():
        page.stemModeCombo.setCurrentIndex(2)
    page.separateStemsBtn = PushButton("Separate Stems")
    page.loadVocalsBtn, page.loadInstBtn = ToolButton("Use Vocals"), ToolButton("Use Instrumental")
    page.loadVocalsBtn.setEnabled(False)
    page.loadInstBtn.setEnabled(False)
    page.separateStemsBtn.clicked.connect(page._separate_stems)
    page.loadVocalsBtn.clicked.connect(page._load_vocals_stem)
    page.loadInstBtn.clicked.connect(page._load_inst_stem)
    page.lblStem = QLabel("STEM SEPARATOR", objectName="FieldLabel")
    for w, st in ((page.lblStem, 0), (page.stemModeCombo, 1), (page.separateStemsBtn, 0), (page.loadVocalsBtn, 0), (page.loadInstBtn, 0)):
        row.addWidget(w, st)
    page.stemNoticeLabel = QLabel("", objectName="MutedText")
    page.stemNoticeLabel.setWordWrap(True)
    page.stemNoticeLabel.hide()
    layout.addLayout(row)
    layout.addWidget(page.stemNoticeLabel)
    from .audio_tools_presenter import update_stem_guidance
    page.stemModeCombo.currentIndexChanged.connect(lambda: update_stem_guidance(page))
    return card



def _inspector_rack(page) -> QFrame:
    card = QFrame(objectName="AudioToolsCard")
    layout = QVBoxLayout(card)
    layout.setContentsMargins(12, 10, 12, 10)
    top, key_row = QHBoxLayout(), QHBoxLayout()
    page.sectionKeyLabel = ElidedLabel("Section Key: -- (1st Half vs 2nd Half)", objectName="MutedText")
    page.badgeLabel, page.reanalyzeBtn = QLabel(tr("at.experimental_badge", "en"), objectName="ExperimentalBadge"), ToolButton("Re-analyze")
    page.reanalyzeBtn.clicked.connect(page._reanalyze)
    page.lblInspector = QLabel("HARMONIC & WAVEFORM INSPECTOR", objectName="FieldLabel")
    for w, st in ((page.lblInspector, 0), (page.sectionKeyLabel, 1), (page.badgeLabel, 0), (page.reanalyzeBtn, 0)):
        top.addWidget(w, st)
    page.waveformWidget, page.detectedKeyCombo, page.camelotLabel = WaveformWidget(), ComboBox(), QLabel("Camelot: 8B", objectName="StepBadge")
    page.waveformWidget.seekRequested.connect(page._on_seek_requested)
    page.detectedKeyCombo.addItems(list(ALL_KEYS))
    page.detectedKeyCombo.currentTextChanged.connect(page._update_preview_labels)
    page.lblDetectedKey = QLabel("Detected / Override Key:", objectName="MutedText")
    for w in (page.lblDetectedKey, page.detectedKeyCombo, page.camelotLabel):
        key_row.addWidget(w)
    key_row.addStretch(1)
    c_row, page.candButtons, page.lblCand = _buttons_row("Top-3 Candidates:", 3, page._select_candidate)
    h_row, page.camelotButtons, page.lblCamelot = _buttons_row("Harmonic Mix (Camelot):", 4, page._select_harmonic_neighbor)
    layout.addLayout(top)
    layout.addWidget(page.waveformWidget)
    for r in (key_row, c_row, h_row):
        layout.addLayout(r)
    return card


def _buttons_row(label: str, count: int, on_click) -> tuple[QHBoxLayout, list[ToolButton], QLabel]:
    row, btns, lbl = QHBoxLayout(), [ToolButton(f"#{i + 1} --") for i in range(count)], QLabel(label, objectName="MutedText", minimumWidth=148)
    row.addWidget(lbl)
    for idx, btn in enumerate(btns):
        btn.clicked.connect(lambda _c=False, i=idx: on_click(i))
        row.addWidget(btn)
    row.addStretch(1)
    return row, btns, lbl


def _audition_bar(page) -> QFrame:
    card = QFrame(objectName="AudioToolsCard")
    layout = QVBoxLayout(card)
    layout.setContentsMargins(12, 10, 12, 10)
    info_row, actions = QHBoxLayout(), QHBoxLayout()
    page.outputPreviewLabel = ElidedLabel(tr("at.safe_notice", "en"), objectName="MonoValue")
    page.statusLabel = QLabel(tr("at.load_to_begin", "en"), objectName="MutedText")
    info_row.addWidget(page.outputPreviewLabel, 1)
    info_row.addWidget(page.statusLabel)
    page.previewOrigBtn, page.previewShiftedBtn, page.stopAudioBtn = ToolButton("Play Original (A)"), PushButton("Preview Shifted (B)"), ToolButton("Stop")
    page.exportBtn, page.openFolderBtn = PrimaryPushButton("Export Shifted Copy"), ToolButton("Show in folder")
    page.openFolderBtn.hide()
    for btn, fn in ((page.previewOrigBtn, page._play_original), (page.previewShiftedBtn, page._preview_shifted), (page.stopAudioBtn, page._stop_playback), (page.exportBtn, page._export_shifted), (page.openFolderBtn, page._open_export_folder)):
        btn.clicked.connect(fn)
    for w, st in ((page.previewOrigBtn, 0), (page.previewShiftedBtn, 0), (page.stopAudioBtn, 0), (QWidget(), 1), (page.openFolderBtn, 0), (page.exportBtn, 0)):
        actions.addWidget(w, st)
    layout.addLayout(info_row)
    layout.addLayout(actions)
    return card

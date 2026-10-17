"""UI layout builder for the Audio Tools page with Waveform and Camelot advisor."""

from __future__ import annotations

from PyQt6.QtWidgets import QDoubleSpinBox, QFrame, QHBoxLayout, QLabel, QSpinBox, QVBoxLayout, QWidget

from src.services.audio_analysis import ALL_KEYS
from src.ui.components.controls import ComboBox, PrimaryPushButton, PushButton, SmoothScrollArea, ToolButton
from src.ui.components.waveform_widget import WaveformWidget


def build_ui(page) -> None:
    root = QVBoxLayout(page)
    root.setContentsMargins(0, 0, 0, 0)
    scroll, content = SmoothScrollArea(), QWidget()
    scroll.setWidgetResizable(True)
    layout = QVBoxLayout(content)
    layout.setContentsMargins(24, 20, 24, 20)
    layout.setSpacing(12)
    for w in (QLabel("Audio Tools · สตูดิโอวิเคราะห์และปรับคีย์/ความเร็ว", objectName="PageTitle"), QLabel("ทำงาน 4 ขั้นตอน: (1) เลือกไฟล์ -> (2) วิเคราะห์ Key/BPM -> (3) ปรับแต่งด้วย Rubber Band R3 -> (4) ฟังเทียบและส่งออก", objectName="PageSubtitle"), _source_card(page), _analysis_card(page), _pitch_card(page), _export_card(page)):
        layout.addWidget(w)
    layout.addStretch(1)
    scroll.setWidget(content)
    root.addWidget(scroll)


def _source_card(page) -> QFrame:
    card, layout = _card("STEP 1 · SOURCE", "1. ไฟล์เสียงต้นฉบับ (Source Audio)", "เลือกไฟล์เสียงในเครื่อง (.wav, .mp3, .flac, .m4a) หรือส่งต่อจาก Library (ไฟล์เดิมปลอดภัย)")
    row, page.fileLabel = QHBoxLayout(), QLabel("No audio file loaded. Choose a local file or send one from Library.", objectName="MutedText")
    page.fileLabel.setWordWrap(True)
    page.chooseFileBtn, page.batchBtn = PushButton("Choose audio file"), ToolButton("Batch Process...")
    page.chooseFileBtn.clicked.connect(page._choose_file)
    page.batchBtn.clicked.connect(page._open_batch_dialog)
    row.addWidget(page.fileLabel, 1)
    for btn in (page.chooseFileBtn, page.batchBtn):
        row.addWidget(btn)
    layout.addLayout(row)
    return card


def _analysis_card(page) -> QFrame:
    card, layout = _card("STEP 2 · HARMONIC ANALYSIS", "2. วิเคราะห์คีย์เพลง รหัส Camelot และจังหวะ (Key & BPM)", "วิเคราะห์ด้วย HPCP + MIREX: แสดงคีย์หลัก, Camelot Code (จับคู่คีย์เพลง), คีย์ทางเลือก 3 อันดับ และตรวจจับการเปลี่ยนคีย์")
    page.badgeLabel, page.sectionKeyLabel, page.waveformWidget = QLabel("Experimental / Estimate · ทดลอง / ค่าประมาณ", objectName="ExperimentalBadge"), QLabel("Section Key: -- (1st Half vs 2nd Half)", objectName="MutedText"), WaveformWidget()
    for w in (page.badgeLabel, page.sectionKeyLabel, page.waveformWidget):
        layout.addWidget(w)
    key_row = QHBoxLayout()
    page.detectedKeyCombo, page.camelotLabel, page.reanalyzeBtn = ComboBox(), QLabel("Camelot: 8B", objectName="StepBadge"), ToolButton("Re-analyze")
    page.detectedKeyCombo.addItems(list(ALL_KEYS))
    page.detectedKeyCombo.currentTextChanged.connect(page._update_preview_labels)
    page.reanalyzeBtn.clicked.connect(page._reanalyze)
    for w in (QLabel("Detected / Override Key:"), page.detectedKeyCombo, page.camelotLabel):
        key_row.addWidget(w)
    key_row.addStretch(1)
    key_row.addWidget(page.reanalyzeBtn)
    c_row, page.candButtons = _buttons_row("Top-3 Candidates:", 3, page._select_candidate)
    h_row, page.camelotButtons = _buttons_row("Harmonic Mix (Camelot):", 4, page._select_harmonic_neighbor)
    for row in (key_row, c_row, h_row, _bpm_row(page)):
        layout.addLayout(row)
    return card


def _buttons_row(label: str, count: int, on_click) -> tuple[QHBoxLayout, list[ToolButton]]:
    row, btns = QHBoxLayout(), [ToolButton(f"#{i + 1} --") for i in range(count)]
    row.addWidget(QLabel(label, objectName="MutedText"))
    for idx, btn in enumerate(btns):
        btn.clicked.connect(lambda _c=False, i=idx: on_click(i))
        row.addWidget(btn)
    row.addStretch(1)
    return row, btns


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
    for w in (QLabel("Source BPM:"), page.bpmSpin, page.halfBpmBtn, page.doubleBpmBtn, QLabel("Target BPM:"), page.targetBpmSpin, page.resetTempoBtn, page.tempoRatioLabel):
        row.addWidget(w)
    row.addStretch(1)
    return row


def _pitch_card(page) -> QFrame:
    card, layout = _card("STEP 3 · PITCH & TEMPO", "3. ปรับคีย์เสียงและความเร็วเพลง (Pitch Shift & Time-Stretch)", "ปรับคีย์ขึ้น/ลง (-12..+12 Semitones) โดยความเร็วไม่เปลี่ยน และยืด/หดความเร็ว (Target BPM 0.5x–2.0x) โดยคีย์ไม่เพี้ยน")
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
    for text, val in (("Rubber Band R3 Finer (Studio Quality)", "r3_finer"), ("FFmpeg Rubber Band (Fast Formant)", "ffmpeg_formant")):
        page.engineCombo.addItem(text, val)
    for label, key in (("WAV 24-bit (Cubase / DAW Ready)", "wav"), ("FLAC Lossless", "flac"), ("MP3 320 kbps", "mp3")):
        page.formatCombo.addItem(label, key)
    page.formatCombo.currentIndexChanged.connect(page._update_preview_labels)
    for w, stretch in ((QLabel("Engine:"), 0), (page.engineCombo, 1), (QLabel("Format:"), 0), (page.formatCombo, 1)):
        row.addWidget(w, stretch)
    return row


def _export_card(page) -> QFrame:
    card, layout = _card("STEP 4 · AUDITION & EXPORT", "4. ฟังเปรียบเทียบเสียงและส่งออกไฟล์ใหม่ (Audition & Export)", "กด Play Original (A) เทียบกับ Preview Shifted (B) เพื่อตรวจคุณภาพเสียง แล้วกด Export Shifted Copy เพื่อสร้างไฟล์ใหม่")
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
    for w in (page.openFolderBtn, page.exportBtn):
        actions.addWidget(w)
    for w in (page.outputPreviewLabel, page.statusLabel):
        layout.addWidget(w)
    layout.addLayout(actions)
    return card


def _card(pill: str, title: str, desc: str) -> tuple[QFrame, QVBoxLayout]:
    card, layout = QFrame(objectName="AudioToolsCard"), QVBoxLayout()
    card.setLayout(layout)
    layout.setContentsMargins(16, 14, 16, 14) or layout.setSpacing(8)
    top = QHBoxLayout()
    top.addWidget(QLabel(pill, objectName="CategoryPill"))
    top.addWidget(QLabel(title, objectName="SectionTitle"), 1)
    layout.addLayout(top) or layout.addWidget(QLabel(desc, objectName="SectionDesc"))
    return card, layout

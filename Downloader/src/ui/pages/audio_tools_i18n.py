"""Language and keyboard navigation setup for Audio Tools UI."""

from __future__ import annotations

from src.ui.i18n import tr


def wire_tab_order(page) -> None:
    page.setTabOrder(page.chooseFileBtn, page.batchBtn)
    page.setTabOrder(page.batchBtn, page.reanalyzeBtn)
    page.setTabOrder(page.reanalyzeBtn, page.detectedKeyCombo)
    if hasattr(page, "stemModeCombo") and hasattr(page, "separateStemsBtn"):
        page.setTabOrder(page.detectedKeyCombo, page.stemModeCombo)
        page.setTabOrder(page.stemModeCombo, page.separateStemsBtn)
        page.setTabOrder(page.separateStemsBtn, page.semitoneSpin)
    else:
        page.setTabOrder(page.detectedKeyCombo, page.semitoneSpin)
    page.setTabOrder(page.semitoneSpin, page.bpmSpin)
    page.setTabOrder(page.bpmSpin, page.targetBpmSpin)
    page.setTabOrder(page.targetBpmSpin, page.engineCombo)
    page.setTabOrder(page.engineCombo, page.formatCombo)
    page.setTabOrder(page.formatCombo, page.previewOrigBtn)
    page.setTabOrder(page.previewOrigBtn, page.previewShiftedBtn)
    page.setTabOrder(page.previewShiftedBtn, page.stopAudioBtn)
    page.setTabOrder(page.stopAudioBtn, page.exportBtn)


def set_language(page, lang: str) -> None:
    page._lang = lang
    page.titleLabel.setText(tr("at.title", lang))
    page.subtitleLabel.setText(tr("at.subtitle", lang))
    if not page._source:
        page.fileLabel.setText(tr("at.no_file", lang))
        page.outputPreviewLabel.setText(tr("at.safe_notice", lang))
        page.statusLabel.setText(tr("at.load_to_begin", lang))
    page.badgeLabel.setText(tr("at.experimental_badge", lang))
    page.lblSource.setText(tr("at.field_source", lang))
    page.chooseFileBtn.setText(tr("at.choose_file", lang))
    page.batchBtn.setText(tr("at.batch_process", lang))
    page.lblInspector.setText(tr("at.field_inspector", lang))
    page.reanalyzeBtn.setText(tr("at.reanalyze", lang))
    page.lblDetectedKey.setText(tr("at.detected_key", lang))
    if hasattr(page, "lblCand"):
        page.lblCand.setText(tr("at.top3_candidates", lang))
    if hasattr(page, "lblCamelot"):
        page.lblCamelot.setText(tr("at.harmonic_mix", lang))
    _set_dsp_language(page, lang)
    _set_stem_language(page, lang)


def _set_dsp_language(page, lang: str) -> None:
    page.lblDsp.setText(tr("at.field_dsp", lang))
    page.lblSemitones.setText(tr("at.semitones", lang))
    page.lblSrcBpm.setText(tr("at.source_bpm", lang))
    page.lblTgtBpm.setText(tr("at.target_bpm", lang))
    page.halfBpmBtn.setText(tr("at.half_bpm", lang))
    page.doubleBpmBtn.setText(tr("at.double_bpm", lang))
    page.resetTempoBtn.setText(tr("at.reset_tempo", lang))
    page.lblEngine.setText(tr("at.engine", lang))
    page.lblFormat.setText(tr("at.format", lang))
    page.previewOrigBtn.setText(tr("at.play_original", lang))
    page.previewShiftedBtn.setText(tr("at.preview_shifted", lang))
    page.stopAudioBtn.setText(tr("at.stop", lang))
    page.exportBtn.setText(tr("at.export_shifted", lang))
    page.openFolderBtn.setText(tr("at.show_in_folder", lang))


def _set_stem_language(page, lang: str) -> None:
    if hasattr(page, "lblStem"):
        page.lblStem.setText(tr("at.field_stem", lang))
    if hasattr(page, "separateStemsBtn"):
        page.separateStemsBtn.setText(tr("at.separate_stems", lang))
    if hasattr(page, "loadVocalsBtn"):
        page.loadVocalsBtn.setText(tr("at.use_vocals", lang))
    if hasattr(page, "loadInstBtn"):
        page.loadInstBtn.setText(tr("at.use_inst", lang))
    if hasattr(page, "stemNoticeLabel"):
        page.stemNoticeLabel.setText(tr("at.ai_separator_required", lang))


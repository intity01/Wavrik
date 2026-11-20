"""Background analysis job lifecycle of the Audio Tools page."""

from __future__ import annotations

from pathlib import Path

from src.ui.workers.audio_worker import AnalyzeAudioWorker, AudioToolSignals

from .audio_tools_presenter import apply_analysis_result

# Signal holders of background jobs; muted when a job is superseded so stale results are ignored.
_JOB_SIGNAL_ATTRS = ("_signals", "_stemSignals", "_stem4Signals")


class AnalysisJobsMixin:
    """Expects the host page to provide ``_source``, ``_busy``, ``_pool``, ``_hist`` and the status widgets."""

    def _cached_analysis(self, path: Path, cached: dict | None) -> dict | None:
        if cached and cached.get("key"):
            return cached
        lookup = getattr(self._hist, "getCachedAnalysis", None)
        return lookup(path) if lookup else None

    def _discard_active_job(self) -> None:
        """Cancel the running job and mute its signals so a late result cannot touch a newer file."""
        worker = self._activeWorker
        if worker is not None and hasattr(worker, "cancel"):
            worker.cancel()
        for name in _JOB_SIGNAL_ATTRS:
            if (signals := getattr(self, name, None)) is not None:
                signals.blockSignals(True)

    def _reanalyze(self) -> None:
        if not self._source or self._busy:
            return
        self._busy, self._signals = True, AudioToolSignals()
        self.statusLabel.setText(self._text("at.analyzing"))
        self._signals.analyzed.connect(self._on_analyzed)
        self._signals.error.connect(self._on_error)
        self._activeWorker = AnalyzeAudioWorker(self._source, self._signals)
        self._pool.start(self._activeWorker)

    def _on_analyzed(self, result: dict) -> None:
        self._busy = False
        if self._source is not None and hasattr(self._hist, "updateAnalysis"):
            self._hist.updateAnalysis(str(self._source), result)
        apply_analysis_result(self, result)
        self.analysisCompleted.emit(result)

    def _on_error(self, message: str) -> None:
        self._busy = False
        self.separateStemsBtn.setEnabled(bool(self._source))
        self.exportBtn.setEnabled(bool(self._source))
        self.statusLabel.setText(message)

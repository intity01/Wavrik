"""In-app studio audio transport controller with A/B slot switching."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QObject, QUrl, pyqtSignal

try:
    from PyQt6.QtMultimedia import QAudioOutput, QMediaPlayer
except ImportError:  # pragma: no cover
    QAudioOutput = None
    QMediaPlayer = None


class AudioTransportController(QObject):
    stateChanged = pyqtSignal(bool, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._slot_a: Path | None = None
        self._slot_b: Path | None = None
        self._active_slot: str = "A"
        self._playing: bool = False
        self._current_source: Path | None = None
        self._pending_seek_ms: int | None = None
        self._player = QMediaPlayer(self) if QMediaPlayer else None
        self._output = QAudioOutput(self) if QAudioOutput else None
        if self._player and self._output:
            self._player.setAudioOutput(self._output)
            self._output.setVolume(0.9)
            self._player.playbackStateChanged.connect(self._on_playback_state)
            self._player.mediaStatusChanged.connect(self._on_media_status)

    def setSlotA(self, path: str | Path | None) -> None:
        self._slot_a = Path(path) if path else None
        self._slot_b = None
        self._active_slot = "A"
        self._current_source = None
        self._pending_seek_ms = None
        self.stop()

    def setSlotB(self, path: str | Path | None) -> None:
        self._slot_b = Path(path) if path else None
        if self._current_source == self._slot_b and path is None:
            self._current_source = None

    def playSlot(self, slot: str = "A", start_sec: float = 0.0) -> bool:
        target = self._slot_b if slot == "B" else self._slot_a
        if not target or not target.is_file():
            return False
        self._active_slot = "B" if slot == "B" else "A"
        pos_ms = max(0, int(start_sec * 1000))
        if self._player:
            if self._current_source == target:
                if start_sec >= 0:
                    self._player.setPosition(pos_ms)
                if self._player.playbackState() != QMediaPlayer.PlaybackState.PlayingState:
                    self._player.play()
            else:
                self._current_source = target
                self._pending_seek_ms = pos_ms if start_sec > 0 else None
                self._player.stop()
                self._player.setSource(QUrl.fromLocalFile(str(target)))
                if self._pending_seek_ms is not None and self._is_loaded():
                    self._player.setPosition(self._pending_seek_ms)
                    self._pending_seek_ms = None
                self._player.play()
        self._playing = True
        self.stateChanged.emit(True, self._active_slot)
        return True

    def seek(self, sec: float) -> None:
        pos_ms = max(0, int(sec * 1000))
        if not self._player:
            return
        if self._current_source is not None and self._is_loaded():
            self._player.setPosition(pos_ms)
        else:
            self._pending_seek_ms = pos_ms

    def toggleAB(self, start_sec: float = 0.0) -> str:
        next_slot = "B" if (self._active_slot == "A" and self._slot_b and self._slot_b.is_file()) else "A"
        if start_sec <= 0.0 and self._player and self._player.position() > 0:
            start_sec = self._player.position() / 1000.0
        self.playSlot(next_slot, start_sec)
        return self._active_slot

    def stop(self) -> None:
        if self._player:
            self._player.stop()
        self._pending_seek_ms = None
        self._playing = False
        self.stateChanged.emit(False, self._active_slot)

    def isPlaying(self) -> bool:
        return self._playing

    def activeSlot(self) -> str:
        return self._active_slot

    def _is_loaded(self) -> bool:
        if not self._player or not hasattr(QMediaPlayer, "MediaStatus"):
            return False
        return self._player.mediaStatus() in (QMediaPlayer.MediaStatus.LoadedMedia, QMediaPlayer.MediaStatus.BufferedMedia)

    def _on_media_status(self, status) -> None:
        if not self._player or not hasattr(QMediaPlayer, "MediaStatus"):
            return
        if status in (QMediaPlayer.MediaStatus.LoadedMedia, QMediaPlayer.MediaStatus.BufferedMedia):
            if self._pending_seek_ms is not None:
                self._player.setPosition(self._pending_seek_ms)
                self._pending_seek_ms = None

    def _on_playback_state(self, state) -> None:
        if self._player and hasattr(QMediaPlayer, "PlaybackState") and state == QMediaPlayer.PlaybackState.StoppedState:
            self._playing = False
            self.stateChanged.emit(False, self._active_slot)

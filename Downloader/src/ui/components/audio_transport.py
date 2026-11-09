"""In-app studio audio transport controller with A/B slot switching and stem audition."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QObject, QUrl, pyqtSignal

try:
    from PyQt6.QtMultimedia import QAudioOutput, QMediaPlayer
except ImportError:  # pragma: no cover
    QAudioOutput = None
    QMediaPlayer = None


def _is_loaded(player: QMediaPlayer | None) -> bool:
    if not player or not hasattr(QMediaPlayer, "MediaStatus"):
        return False
    return player.mediaStatus() in (QMediaPlayer.MediaStatus.LoadedMedia, QMediaPlayer.MediaStatus.BufferedMedia)


class AudioTransportController(QObject):
    stateChanged = pyqtSignal(bool, str)
    auditionChanged = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._slot_a: Path | None = None
        self._slot_b: Path | None = None
        self._active_slot, self._playing = "A", False
        self._stem_name, self._audition_label = "", ""
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
        self._slot_b, self._stem_name, self._audition_label = None, "", ""
        self._active_slot, self._current_source, self._pending_seek_ms = "A", None, None
        self.stop()
        self.auditionChanged.emit("")

    def setSlotB(self, path: str | Path | None) -> None:
        old_b = self._slot_b
        self._slot_b = Path(path) if path else None
        if path is None:
            self._stem_name, self._audition_label = "", ""
            self.auditionChanged.emit("")
        if self._current_source == old_b and path is None:
            self._current_source = None
            if self._active_slot == "B":
                self.stop()
                self._active_slot = "A"

    def setStemPreview(self, path: str | Path | None, stem_name: str = "", auto_play: bool = False) -> None:
        self.setSlotB(path)
        name = str(stem_name).strip() if stem_name else (Path(path).stem if path else "")
        self._stem_name = name if path else ""
        self._audition_label = f"Auditioning {self._stem_name} (B)" if self._stem_name else ""
        self.auditionChanged.emit(self._stem_name)
        if path and (auto_play or (self._playing and self._active_slot == "B")):
            pos = self.positionSec() if self._playing else None
            self.playSlot("B", pos)

    def playSlot(self, slot: str = "A", start_sec: float | None = None) -> bool:
        target = self._slot_b if slot == "B" else self._slot_a
        if not target or not target.is_file():
            return False
        self._active_slot = "B" if slot == "B" else "A"
        pos_ms = max(0, int(start_sec * 1000)) if (start_sec is not None and start_sec >= 0) else None
        if self._player:
            if self._current_source == target:
                if pos_ms is not None:
                    self._player.setPosition(pos_ms)
                if self._player.playbackState() != QMediaPlayer.PlaybackState.PlayingState:
                    self._player.play()
            else:
                self._current_source = target
                if pos_ms is not None:
                    self._pending_seek_ms = pos_ms
                self._player.stop()
                self._player.setSource(QUrl.fromLocalFile(str(target)))
                if self._pending_seek_ms is not None and _is_loaded(self._player):
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
        if self._current_source is not None and _is_loaded(self._player):
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

    def isPlaying(self) -> bool: return self._playing
    def activeSlot(self) -> str: return self._active_slot
    def activeStem(self) -> str: return self._stem_name
    def auditionLabel(self) -> str: return self._audition_label
    def isAuditioning(self) -> bool: return bool(self._playing and self._active_slot == "B" and self._stem_name)
    def positionSec(self) -> float:
        return (self._player.position() / 1000.0) if (self._player and self._player.position() > 0) else 0.0
    def _is_loaded(self) -> bool: return _is_loaded(self._player)

    def _on_media_status(self, status) -> None:
        if self._player and hasattr(QMediaPlayer, "MediaStatus") and status in (QMediaPlayer.MediaStatus.LoadedMedia, QMediaPlayer.MediaStatus.BufferedMedia):
            if self._pending_seek_ms is not None:
                self._player.setPosition(self._pending_seek_ms)
                self._pending_seek_ms = None

    def _on_playback_state(self, state) -> None:
        if self._player and hasattr(QMediaPlayer, "PlaybackState") and state == QMediaPlayer.PlaybackState.StoppedState:
            self._playing = False
            self.stateChanged.emit(False, self._active_slot)

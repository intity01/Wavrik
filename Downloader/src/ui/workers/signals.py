"""Qt worker signals."""

from PyQt6.QtCore import QObject, pyqtSignal


class WorkerSignals(QObject):
    thumbnailReady = pyqtSignal(str, object)
    metaReady = pyqtSignal(str, object)
    progress = pyqtSignal(str, float, str, str)
    status = pyqtSignal(str, str, str)
    finished = pyqtSignal(str, object)
    error = pyqtSignal(str, str)
    playlistDetected = pyqtSignal(str, str, int, object)

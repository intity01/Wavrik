"""Global crash handler capturing unhandled exceptions into the log file."""

from __future__ import annotations

import sys
import threading
from typing import Any


def install_crash_handler(logger: Any) -> None:
    """Register top-level and thread exception hooks to log unhandled tracebacks."""
    def _sys_hook(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        if hasattr(logger, "critical"):
            logger.critical("Unhandled exception", exc_info=(exc_type, exc_value, exc_traceback))
        sys.__excepthook__(exc_type, exc_value, exc_traceback)

    sys.excepthook = _sys_hook

    def _thread_hook(args: threading.ExceptHookArgs) -> None:
        if issubclass(args.exc_type, KeyboardInterrupt):
            return
        thread_name = args.thread.name if args.thread else "unknown"
        if hasattr(logger, "critical"):
            logger.critical(
                f"Unhandled thread exception in {thread_name}",
                exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
            )
        if hasattr(threading, "__excepthook__"):
            threading.__excepthook__(args)

    threading.excepthook = _thread_hook

# Architecture

Entry: `main.py`

- `src/core`: configuration, logging, runtime discovery, tray, update check
- `src/domain`: download models, presets, yt-dlp options and per-job engine
- `src/services`: atomic history and OS file actions
- `src/ui/components`: reusable Qt widgets with no inline colors
- `src/ui/pages`: Downloads, History, Settings
- `src/ui/workers`: QRunnable metadata, thumbnail and download jobs
- `src/ui/theme`: semantic tokens and global QSS

The UI owns two thread pools: metadata (4 workers) and downloads (`maxConcurrentDownloads`). Every DownloadWorker creates its own MediaDownloader session and cancellation event.

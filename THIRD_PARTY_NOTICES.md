# Third-Party Notices and Distribution Gate

This project is licensed under the **GNU General Public License v3.0 or later (GPL-3.0-or-later)**; see [`LICENSE`](LICENSE) for terms. This license aligns with the GPLv3 terms of the bundled PyQt6 and FFmpeg dependencies. This file is an operational notice, not legal advice.

## PyQt6

This project uses PyQt6 under the GNU General Public License v3.0 (GPLv3). Riverbank states that PyQt is dual-licensed under GPLv3 or the Riverbank Commercial License. Any distribution under GPLv3 must include the complete corresponding source code and GPLv3 license notices.

- Official licensing information: https://www.riverbankcomputing.com/software/pyqt
- License FAQ: https://www.riverbankcomputing.com/commercial/license-faq

## FFmpeg and Rubber Band R3 binaries

The bundled `ffmpeg.exe` reports itself as `8.1.1-essentials_build-www.gyan.dev`, built with `--enable-gpl --enable-version3`, and reports GPLv3-or-later terms with `ffmpeg.exe -L`. The optional bundled `rubberband.exe` (Rubber Band Library v4.0.0 R3 CLI utility) and `sndfile.dll` are distributed under the GNU General Public License v2.0 or later (and LGPLv2.1+ for libsndfile). Any release that includes these executables must meet the GPL obligations for those builds, including the applicable notices and corresponding-source obligations.

- FFmpeg licensing guidance: https://ffmpeg.org/legal.html
- Rubber Band Library licensing information: https://breakfastquay.com/rubberband/

## yt-dlp, yt-dlp-ejs, Deno, and Requests

- `yt-dlp` source distributions are released under the Unlicense: https://github.com/yt-dlp/yt-dlp/blob/master/LICENSE
- `yt-dlp-ejs` is distributed under the Unlicense and its prebuilt wheel also contains MIT- and ISC-licensed components: https://github.com/yt-dlp/ejs
- `deno` redistributes the Deno runtime under the MIT license: https://github.com/denoland/deno_pypi
- `requests` is Apache-2.0 licensed. Retain its required notices when redistributing it.

## Release checklist

1. Distribute the application under GPL-3.0-or-later with [`LICENSE`](LICENSE) and complete corresponding source code.
2. Include this notice and all required third-party license texts in the release package.
3. Record the exact FFmpeg source, build configuration, checksum, and source-offer method.
4. Include the license texts required by yt-dlp-ejs, Deno, and Requests in the release package.


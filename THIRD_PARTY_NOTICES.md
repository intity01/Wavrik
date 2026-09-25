# Third-Party Notices and Distribution Gate

This source package has no declared license for Media Downloader PRO itself. Before distributing a Windows package, its copyright holder must choose a project license that is compatible with every bundled dependency or obtain the required commercial licenses. This file is an operational notice, not legal advice.

## PyQt6

This project uses PyQt6. Riverbank states that PyQt is dual-licensed under GPLv3 or the Riverbank Commercial License. A closed-source or otherwise GPL-incompatible Windows package requires an appropriate commercial PyQt license; do not assume that the LGPL license of Qt itself applies to PyQt.

- Official licensing information: https://www.riverbankcomputing.com/software/pyqt
- License FAQ: https://www.riverbankcomputing.com/commercial/license-faq

## FFmpeg binary

The bundled `ffmpeg.exe` reports itself as `8.1.1-essentials_build-www.gyan.dev`, built with `--enable-gpl --enable-version3`, and reports GPLv3-or-later terms with `ffmpeg.exe -L`. Any release that includes this executable must meet the GPL obligations for that exact build, including the applicable notices and corresponding-source obligations. Keep a reproducible source/build record for the exact FFmpeg artifact or replace it with an artifact whose licensing and source-distribution obligations have been reviewed.

- FFmpeg licensing guidance: https://ffmpeg.org/legal.html

## yt-dlp, yt-dlp-ejs, Deno, and Requests

- `yt-dlp` source distributions are released under the Unlicense: https://github.com/yt-dlp/yt-dlp/blob/master/LICENSE
- `yt-dlp-ejs` is distributed under the Unlicense and its prebuilt wheel also contains MIT- and ISC-licensed components: https://github.com/yt-dlp/ejs
- `deno` redistributes the Deno runtime under the MIT license: https://github.com/denoland/deno_pypi
- `requests` is Apache-2.0 licensed. Retain its required notices when redistributing it.

## Release checklist

1. Select the Media Downloader PRO project license or obtain commercial PyQt licensing.
2. Include this notice and all required license texts in the package.
3. Record the exact FFmpeg source, build configuration, checksum, and source-offer method.
4. Include the license texts required by yt-dlp-ejs and Deno in the release package.
5. Review the final distribution with legal counsel when commercial distribution or proprietary licensing is intended.

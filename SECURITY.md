# Security Policy

## Supported versions

Only the latest release receives security fixes.

## Reporting a vulnerability

Please **do not** open a public issue for security problems.
Report privately via **[GitHub Security Advisories](https://github.com/intity01/Wavrik/security/advisories/new)** with steps to reproduce, the affected version, and impact.

You should get a first response within 7 days. Once a fix is released, the advisory will be published with credit to the reporter unless you prefer to stay anonymous.

## Scope

In scope: path traversal or arbitrary file writes from downloaded content, URL/scheme validation bypasses, unsafe execution of downloaded files, update-channel tampering (SHA-256 / release verification), and leakage of cookies, tokens or secrets into logs.

Out of scope: issues in third-party sites or services, and vulnerabilities in bundled upstream binaries (FFmpeg, yt-dlp, Deno) — please report those upstream.

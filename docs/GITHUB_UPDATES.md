# GitHub Updates

## What the app does

Media Downloader PRO checks the repository's latest published full release through the GitHub Releases API. The request runs in a background worker and can be disabled in Settings.

When a newer version exists:

1. A compact banner appears on Downloads.
2. Settings shows the installed and available versions.
3. The user can always open the release page.
4. `Download verified package` appears only when GitHub reports both:
   - `immutable: true`
   - an asset digest in `sha256:<hex>` form
5. The app streams the asset to a `.part` file, limits size, verifies the host and SHA-256, then performs an atomic rename.
6. The installer/package is never executed automatically.

## Repository configuration

Set the repository slug before building:

```python
# Downloader/src/core/config.py
GITHUB_REPO = "owner/repository"
```

The repository must be public for anonymous checks. Private repositories require authentication, which this desktop app intentionally does not collect.

## Release asset naming

The updater prefers assets in this order:

1. `.exe` or `.msi`
2. `.zip`
3. Names containing `Setup` or `Installer`
4. Names containing `Windows`, `Win64` or `x64`

Recommended asset name:

```text
MediaDownloaderPRO-Windows-x64.zip
```

## Publishing safely

- Create a signed tag such as `v2.1.0`.
- Ensure `Config.VERSION` matches the tag without the leading `v`.
- Ensure `Config.GITHUB_REPO` exactly matches the GitHub repository that runs the workflow.
- Add the selected project `LICENSE` and review `THIRD_PARTY_NOTICES.md` before distributing a package.
- Build and test on Windows.
- Attach the Windows package before publishing the release.
- Enable immutable releases for the repository or organization. The workflow now creates the release as a draft, uploads every asset, then publishes it; GitHub recommends this order when immutable releases are enabled.
- Keep automatic execution disabled until the package also has a publisher signature such as Authenticode or another verification method trusted by the app.

The included `.github/workflows/release.yml` runs tests, builds with PyInstaller, creates a SHA-256 file and creates a draft release when a `v*` tag is pushed. It publishes only after all assets are attached. It intentionally fails when the approved `ffmpeg.exe` is not present at the repository root rather than downloading an unpinned binary during the build.

## Failure behavior

- No internet / GitHub unavailable: the current app remains usable and shows a retryable message.
- No newer release: Settings reports that the installed version is current.
- Release is mutable or lacks a digest: only `Open release` is shown.
- Hash mismatch, oversized file or unexpected redirect host: the partial file is removed and installation is not offered.

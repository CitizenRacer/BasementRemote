# UI assets

All artwork needed to compile the Basement Remote UI is stored in this repository. Firmware builds no longer depend on third-party SVG hosts or Google Fonts.

## Vendored sources

- `vendor/heroicons-v2.2.0/` — the Heroicons v2.2.0 solid SVGs used by the awake remote controls. Upstream: `tailwindlabs/heroicons`, tag `v2.2.0`.
- `vendor/material-design-icons-v7.4.47/sleep.svg` — the Material Design Icons sleep glyph retained from the previous sleep face. Upstream: `Templarian/MaterialDesign-SVG`, tag `v7.4.47`.
- `hulu.svg` — Hulu wordmark artwork previously sourced from Wikimedia Commons.
- `hbo-max.svg` — HBO Max 2025 monochrome logo artwork previously sourced from Wikimedia Commons.
- `paramount-plus.svg` — Paramount+ launcher artwork.
- `disney-d.png` — user-provided Disney launcher artwork.
- `sleep-screen.svg` — project-owned 480×800 approved sleep-screen composition, including the moon/Z mark, labels, and two-loop power-button arrow.

The streaming-service marks are trademarks of their respective owners and are included only as launcher artwork for this personal remote-control project.

## ESPHome package note

ESPHome 2026.8 resolves a local `image.file` path relative to the Device Builder wrapper, not to the cached checkout of a remote Git package. For that reason the production package references these vendored files through `raw.githubusercontent.com/CitizenRacer/BasementRemote/main/...`. This keeps every build-time UI asset under the control of this repository and removes dependencies on third-party asset hosts. The Device Builder package itself is already Git-backed from this same repository.

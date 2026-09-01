# Basement Remote

Touchscreen TV remote firmware for the **Seeed Studio reTerminal Sticky**, backed directly by Home Assistant over ESPHome's encrypted native API.

## Architecture

The Sticky is intentionally another front end for the already-working Home Assistant **Basement Remote** dashboard. It does **not** introduce a second remote-control architecture and does not use the older `automation.remote_navigation_2` / `esphome.remote_button_pressed` event path as its primary control plane.

Target flow:

```text
Sticky touchscreen / physical buttons
        ↓
ESPHome encrypted native API
        ↓
Home Assistant actions already used by Basement Remote
        ↓
Apple TV / Sonos Arc / LG TV
```

The existing Home Assistant dashboard remains the behavioral reference and should not need modification.

## Home Assistant dependencies

Primary entities:

- `remote.basement_apple_tv`
- `media_player.basement_apple_tv`
- `media_player.basement_sonos_arc`
- `media_player.basement_tv` where appropriate

The installed `custom:universal-remote-card` is configured as Apple TV and establishes these semantics:

- Navigation / remote keys: `remote.send_command` to `remote.basement_apple_tv`
- Power tap: Apple TV command `wakeup`
- Power hold: Apple TV command `suspend`
- Apps: `media_player.select_source` on `media_player.basement_apple_tv`
- Play/pause: `media_player.media_play_pause` on `media_player.basement_apple_tv`
- Volume up/down: Apple TV remote commands `volume_up` / `volume_down`
- Mute: **explicitly target `media_player.basement_sonos_arc`** because the Apple TV media player does not expose mute

When Phase 2 enables Home Assistant actions from the device, Home Assistant must be configured to **Allow the device to perform Home Assistant actions** for this ESPHome integration.

## Sticky hardware

| Function | GPIO |
| --- | ---: |
| PWR_HOLD | 45 |
| PWR_LOCK | 46 |
| AI / Power button | 4 |
| Up button | 5 |
| Down button | 6 |
| E-paper SCK | 13 |
| E-paper MOSI / SDI | 14 |
| E-paper CS | 15 |
| E-paper DC | 16 |
| E-paper RST | 17 |
| E-paper BUSY | 18 |
| E-paper EN | 47 |
| Touch SCL | 2 |
| Touch SDA | 3 |
| Touch INT | 21 |
| Touch RST | 41 |
| Touch EN | 42 |

**Touch bus note:** Seeed's current Sticky hardware documentation specifies **SCL = GPIO2 and SDA = GPIO3**. That is the assignment used in the firmware even though the original project notes had those two labels reversed.

The ESP32-S3 has 32 MB flash and 8 MB octal PSRAM. ESPHome's integrated display model `Seeed-reTerminal-Sticky` supplies the SSD1677 display pin/dimension defaults; the project still declares the shared SPI clock/data pins explicitly.

## Repository layout

```text
esphome/
  basement-remote-sticky.yaml          # Canonical GitHub-hosted ESPHome package
  device-builder-wrapper.example.yaml  # Tiny local Device Builder config
  secrets.example.yaml                 # Secret key names only; no credentials
README.md
```

`esphome/basement-remote-sticky.yaml` is the source of truth. The Device Builder configuration should remain a small local wrapper that resolves secrets and imports that file directly from the repository's `main` branch.

## ESPHome Device Builder

This project follows the same Git-backed package pattern as the Garage Door Keypad project. Do not copy the full firmware into Device Builder.

Create a local Device Builder YAML containing:

```yaml
substitutions:
  wifi_ssid: !secret wifi_ssid
  wifi_password: !secret wifi_password
  ota_password: !secret ota_password
  fallback_ap_password: !secret fallback_ap_password
  basement_remote_api_encryption_key: !secret basement_remote_api_encryption_key

packages:
  basement_remote:
    url: https://github.com/CitizenRacer/BasementRemote
    ref: main
    files:
      - esphome/basement-remote-sticky.yaml
    refresh: 60s
```

The same content is checked in as [`esphome/device-builder-wrapper.example.yaml`](esphome/device-builder-wrapper.example.yaml).

ESPHome's remote-package mechanism does not allow the Git-hosted package itself to resolve `!secret` values. The local wrapper therefore reads Device Builder's `secrets.yaml` and supplies those values as substitutions. All non-secret firmware logic remains in GitHub.

This intentionally uses the same shared `wifi_ssid`, `wifi_password`, `fallback_ap_password`, and `ota_password` secret names as the Garage Door Keypad wrapper. On a Device Builder already configured for that project, the only new secret required for Basement Remote is `basement_remote_api_encryption_key`.

With `ref: main`, Device Builder pulls the production source from GitHub. `refresh: 60s` means ESPHome may refresh its cached repository copy when validation/build activity occurs after that interval; it does not automatically flash the device when GitHub changes.

## Phase 1: hardware bring-up

Current firmware status: **compile-validated and ready for the first hardware test**.

The canonical Phase 1 configuration passed both `esphome config` and a full `esphome compile` using **ESPHome 2026.8.2** in GitHub Actions. CI builds the firmware as an ESPHome package and also validates the production GitHub-backed Device Builder wrapper on `main`.

Phase 1 intentionally keeps the device awake. It verifies components independently before remote-control behavior or deep sleep is introduced:

- PWR_HOLD / PWR_LOCK keep-alive behavior
- 480×800 portrait e-paper output
- GT911 touch and coordinate reporting
- Wi-Fi
- encrypted ESPHome native API
- ESPHome OTA
- GPIO4 / GPIO5 / GPIO6 physical buttons
- diagnostics (Wi-Fi signal, uptime, IP, last touch coordinates)

The e-paper uses `update_interval: never`; it renders once at boot and only refreshes on explicit request. Touch and button activity therefore does **not** cause an e-paper refresh.

Battery reporting is deferred from the first bring-up image. Sticky uses a BQ27220 fuel gauge on the system I²C bus, but ESPHome does not currently provide a first-party BQ27220 sensor component. Adding an external component is not justified until the core hardware is proven.

### First hardware-test checklist

After flashing Phase 1, verify these in order:

1. The Sticky stays powered continuously rather than shutting itself off.
2. The e-paper shows the `BASEMENT REMOTE / PHASE 1` portrait test screen.
3. The device joins Wi-Fi and appears online in ESPHome / Home Assistant.
4. Touching all four regions produces sensible portrait `Last Touch X` / `Last Touch Y` coordinates.
5. GPIO4, GPIO5, and GPIO6 each change their corresponding binary sensor and produce the expected log message.
6. The diagnostic `Refresh E-Paper` button performs an explicit display refresh.
7. OTA remains reachable after the initial USB flash.

Do **not** evaluate deep sleep in this phase; it is intentionally absent.

## Building

This project targets **ESPHome 2026.8.2 or newer**.

For normal Device Builder use:

1. Ensure Device Builder's local `secrets.yaml` contains the shared Wi-Fi/fallback/OTA keys plus `basement_remote_api_encryption_key`; see `esphome/secrets.example.yaml` for the expected names.
2. Create a new Device Builder configuration using the contents of `esphome/device-builder-wrapper.example.yaml`.
3. Validate or install from that local wrapper. ESPHome fetches `esphome/basement-remote-sticky.yaml` from GitHub `main`.
4. Future firmware changes are made and reviewed in GitHub. Device Builder remains only the secret-bearing import wrapper.

For repository/CI development, `.github/workflows/esphome.yml` creates a local package wrapper with dummy CI-only secrets, validates it, validates the production remote GitHub wrapper on `main`, and compiles the firmware.

## Planned phases

### Phase 2 — remote UI

Create a 480×800 portrait, mostly-static remote face with large touch targets for power, menu/home/back, d-pad/select, playback/skip, volume/mute, and app launchers. Touches will call the same Home Assistant actions as the working dashboard directly over the native API. GPIO5/GPIO6 are expected to become tactile volume down/up controls after button polarity is confirmed on hardware.

### Phase 3 — useful state

Add low-refresh state such as Apple TV state, active app/source, current title where useful, battery, and connectivity. State changes will be debounced so e-paper refreshes stay infrequent.

### Phase 4 — battery optimization

Only after normal operation is reliable: add a session-based sleep policy. Recently used / TV-on sessions stay awake; idle / TV-off sessions may sleep. GPIO4 is the initial deep-sleep wake candidate. Touch wake is not assumed.

## Safety / development policy

- GitHub `CitizenRacer/BasementRemote` is the canonical source of truth.
- Device Builder contains only the small package wrapper and local secrets; do not maintain a second full firmware copy there.
- Do not commit credentials.
- Do not modify the working Home Assistant Basement Remote dashboard unless a proven requirement emerges.
- Do not introduce deep sleep until the remote is stable.
- Do not flash the Sticky until the firmware has passed configuration validation and compilation.

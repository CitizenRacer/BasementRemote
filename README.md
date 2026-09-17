# Basement Remote

Touchscreen e-paper TV remote firmware backed directly by Home Assistant over ESPHome's encrypted native API.

## Targets

| Hardware | Firmware | Status |
| --- | --- | --- |
| Seeed Studio reTerminal Sticky | **v1.0.39** | Production target / OTA-encryption migration bridge |
| M5Stack M5PaperMono Lite (C153-LITE) | **v0.1.0** | Initial bring-up / compile validated; hardware not yet available |

The production Sticky source is [`esphome/basement-remote-sticky.yaml`](esphome/basement-remote-sticky.yaml). `CitizenRacer/BasementRemote` is the canonical source of truth.

## Architecture

```text
Touchscreen / physical buttons
        ↓
ESPHome native API
        ↓
Home Assistant actions
        ↓
Apple TV / HDMI-CEC / LG TV
```

The Sticky reuses the same Home Assistant entities/actions as the working Basement Remote dashboard, including `remote.basement_apple_tv`, `media_player.basement_apple_tv`, `media_player.basement_tv`, and `script.tv_turn_on_the_tv_cable`.

## Current Sticky behavior

The Sticky uses a 480×800 portrait e-paper layout with D-pad/Select, Back/Home, playback controls, and streaming-service launchers. The two side buttons control volume and the AI / Power button controls TV power. Ordinary remote commands do not refresh the e-paper display.

The current production power behavior is intentionally conservative after the v1.0.35 light-sleep experiment caused touch failures:

- CPU dynamic frequency scaling remains enabled at 40–160 MHz;
- automatic ESP32 light sleep is disabled while awake so the GT911 remains continuously serviced;
- Wi-Fi uses `fast_connect: true`, `power_save_mode: HIGH`, and `output_power: 8.5dB`;
- physical UART logging is disabled; DEBUG logs remain available over the ESPHome native API;
- e-paper `update_interval` is `never`; refreshes are explicit only;
- when `media_player.basement_tv` reports exactly `off`, the approved sleep face is rendered, Wi-Fi is disabled, and the Sticky enters deep sleep;
- GPIO4 (AI / Power) wakes the Sticky from deep sleep and runs the shared Home Assistant TV-on sequence.

## Touch / wake reliability

Production behavior retains the known-good touch path:

- GT911 I²C address `0x5D`;
- touch I²C on GPIO2/GPIO3;
- touch interrupt on GPIO21;
- touch reset on GPIO41 and enable on GPIO42;
- no automatic light sleep dependency on GPIO21 wake behavior;
- GPIO45/GPIO46/GPIO47 are not manipulated by touch-recovery code.

The authoritative readiness line is:

```text
Basement Remote firmware 1.0.39 ready
```

Readiness waits for Home Assistant state subscription, a valid TV state, a healthy touchscreen component, and proof that the startup SSD1677 refresh reached hardware and completed.

## Battery telemetry and BQ27220 diagnostics

The Sticky's BQ27220 fuel gauge is on the dedicated sensor I²C bus at address `0x55`. Existing telemetry includes Battery Level, Battery Voltage, Battery Current, and Battery Charging.

Beginning with v1.0.38, the firmware also exposes these read-only diagnostics once per minute:

- **Battery Remaining Capacity** — `RemainingCapacity()` at `0x10/0x11`, mAh;
- **Battery Full Charge Capacity** — `FullChargeCapacity()` at `0x12/0x13`, mAh;
- **Battery State of Health** — `StateOfHealth()` at `0x2E/0x2F`, percent;
- **Battery Design Capacity** — `DesignCapacity()` at `0x3C/0x3D`, mAh;
- **Battery Status Raw** — `BatteryStatus()` at `0x0A/0x0B` as the raw 16-bit value.

These are diagnostic reads only. Do not write a new BQ27220 profile until the reported Remaining Capacity, Full Charge Capacity, Design Capacity, State of Health, voltage, current, and status have been reviewed together.

## OTA encryption migration

ESPHome 2026.9.0 adds encrypted OTA using the same Noise key as the native API. The installed Sticky previously ran firmware built with ESPHome 2026.8.2, which cannot offer the new encrypted OTA protocol. Requiring encryption immediately would therefore risk locking out OTA updates.

**v1.0.39 is the one-time migration bridge.** It must be built with ESPHome 2026.9.0 and deliberately retains the existing OTA password for this install. Once v1.0.39 is running, ESPHome 2026.9.0 can offer encrypted OTA using `basement_remote_api_encryption_key` while still accepting the legacy authenticated path. The next firmware release will remove the OTA password and require:

```yaml
ota:
  - platform: esphome
    encryption:
```

Do not manually remove `ota_password` from the Device Builder wrapper or `secrets.yaml` before v1.0.39 has been installed successfully. The password-related warning during this transition build is expected once; after the encrypted-OTA requirement is enabled in the following release, the separate OTA password will no longer be needed.

After installing v1.0.39, check the device log for ESPHome's encryption-offer message before moving to the final migration release.

## Sticky hardware mapping

| Function | GPIO |
| --- | ---: |
| Sensor I²C SCL / BQ27220 | 0 |
| Sensor I²C SDA / BQ27220 | 1 |
| Touch SCL | 2 |
| Touch SDA | 3 |
| AI / Power button | 4 |
| Volume Up button | 5 |
| Volume Down button | 6 |
| E-paper SCK | 13 |
| E-paper MOSI / SDI | 14 |
| E-paper CS | 15 |
| E-paper DC | 16 |
| E-paper RST | 17 |
| E-paper BUSY | 18 |
| Touch INT | 21 |
| Touch RST | 41 |
| Touch EN | 42 |
| PWR_HOLD | 45 |
| PWR_LOCK | 46 |
| E-paper EN | 47 |
| Built-in buzzer PWM | 48 |

The Sticky uses 32 MB flash and 8 MB octal PSRAM.

## v1.0.39 validation checklist

1. Build and install v1.0.39 with ESPHome 2026.9.0 using the existing OTA password path.
2. Confirm the device boots and logs `Basement Remote firmware 1.0.39 ready`.
3. Confirm ESPHome reports that OTA encryption is offered while the migration password remains accepted.
4. Confirm touchscreen input remains responsive immediately after boot and after idle periods.
5. Confirm Volume Up, Volume Down, AI / Power short/long press, app launchers, Find Remote, sleep-screen rendering, and deep-sleep wake remain unchanged.
6. Record Battery Level, Voltage, Current, Remaining Capacity, Full Charge Capacity, Design Capacity, State of Health, and Status Raw while the charge LED is green.
7. Only after v1.0.39 is confirmed running should the following release remove the OTA password and require encryption.

# M5PaperMono Lite

The PaperMono target is [`esphome/basement-remote-papermono-lite.yaml`](esphome/basement-remote-papermono-lite.yaml) and imports board support from `CitizenRacer/M5PaperMonoLite`. Its hardware is not yet available for validation.

# ESPHome Device Builder

Device Builder should remain a small secret-bearing wrapper. Complete device behavior belongs in GitHub.

- Sticky wrapper: [`esphome/device-builder-wrapper.example.yaml`](esphome/device-builder-wrapper.example.yaml)
- PaperMono wrapper: [`esphome/device-builder-wrapper-papermono-lite.example.yaml`](esphome/device-builder-wrapper-papermono-lite.example.yaml)
- Secret names: [`esphome/secrets.example.yaml`](esphome/secrets.example.yaml)

Never commit real Wi-Fi credentials, OTA credentials, or the ESPHome API encryption key.

# Building and CI

The repository CI is pinned to ESPHome **2026.9.0**. `.github/workflows/esphome.yml` validates and compiles the Sticky and PaperMono targets independently and validates the production Git-backed wrappers on `main`.

# Maintenance rules

- `CitizenRacer/BasementRemote` on GitHub is the canonical source of truth.
- **Every code check-in must update the README in the same commit whenever behavior, UI, dependencies, setup, versioning, or operational expectations change.**
- Keep Sticky and PaperMono hardware definitions separate.
- Keep Device Builder limited to secret-bearing wrappers.
- Keep app launcher source names aligned with `media_player.basement_apple_tv`.
- Keep UI artwork vendored under `assets/`.
- Do not refresh e-paper for ordinary navigation, playback, volume, or app-launch presses unless visible UI state requires it.

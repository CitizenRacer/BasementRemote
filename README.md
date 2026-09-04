# Basement Remote

Touchscreen e-paper TV remote firmware backed directly by Home Assistant over ESPHome's encrypted native API.

This repository supports two hardware targets:

| Hardware | Firmware | Status |
| --- | --- | --- |
| Seeed Studio reTerminal Sticky | **v1.0.13** | Production / hardware validated |
| M5Stack M5PaperMono Lite (C153-LITE) | **v0.1.0** | Initial bring-up / compile validated, hardware not yet available |

The production Sticky source remains [`esphome/basement-remote-sticky.yaml`](esphome/basement-remote-sticky.yaml). Adding the PaperMono target does not replace or modify the Sticky hardware configuration.

<p align="center">
  <img src="docs/remote.jpg" alt="Seeed Studio reTerminal Sticky running the Basement Remote interface" width="420">
</p>

## Architecture

Both targets are front ends for the existing Home Assistant **Basement Remote** setup. They use the same Home Assistant entities and actions rather than introducing a second remote-control architecture.

```text
Touchscreen / physical buttons
        ↓
ESPHome encrypted native API
        ↓
Home Assistant actions
        ↓
Apple TV / HDMI-CEC / LG TV
```

The firmware does not use `automation.remote_navigation_2` or `esphome.remote_button_pressed` as its control plane.

## Home Assistant dependencies

Both targets directly depend on:

- `remote.basement_apple_tv` — navigation, transport, power, and volume commands
- `media_player.basement_apple_tv` — streaming-service app launchers via `media_player.select_source`
- `media_player.basement_tv` — imported as **TV State Seen By Remote**; on the Sticky this is also the authority for automatic deep sleep

For the ESPHome integration, Home Assistant must have **Allow the device to perform Home Assistant actions** enabled.

## Shared touchscreen controls

Both targets use the same 480×800 portrait awake layout:

1. Large D-pad and Select
2. Back and Home
3. Playback controls
4. Hulu, HBO Max, Disney+, and Paramount+ launchers

| Touch control | Behavior |
| --- | --- |
| D-pad | `up`, `down`, `left`, `right`, `select` |
| Back | Apple TV `menu` |
| Home | Apple TV `home` |
| Playback row | `skip_backward`, `play`, `pause`, `skip_forward` |
| Hulu launcher | Select Apple TV source `Hulu` |
| HBO Max launcher | Select Apple TV source `HBO Max` |
| Disney+ launcher | Select Apple TV source `Disney+` |
| Paramount+ launcher | Select Apple TV source `Paramount+` |

D-pad hold-to-repeat fires immediately, begins repeating after 500 ms, and repeats every 175 ms while held.

All UI artwork is stored under [`assets/`](assets/). The awake controls use vendored Heroicons v2.2.0 SVGs and repository-owned streaming-service artwork. Firmware references those assets through this repository's raw GitHub paths so a Git-backed ESPHome package does not depend on third-party artwork hosts.

## reTerminal Sticky target

The Sticky remains the production remote and is intentionally isolated in [`esphome/basement-remote-sticky.yaml`](esphome/basement-remote-sticky.yaml).

### Sticky physical controls

| Control | Behavior |
| --- | --- |
| AI / Power short press | Apple TV `wakeup` |
| AI / Power hold ≥ 800 ms | Apple TV `suspend` |
| Upper side button | Apple TV `volume_up` |
| Lower side button | Apple TV `volume_down` |

The two volume buttons support the same 500 ms / 175 ms hold-to-repeat behavior as the D-pad.

### Sticky display and sleep behavior

The Sticky uses ESPHome's integrated `Seeed-reTerminal-Sticky` SSD1677 display model with a 480×800 logical portrait UI. While awake, it performs a full e-paper refresh every 10 minutes and on explicit **Refresh E-Paper** requests. Navigation and media commands do not refresh the screen.

`media_player.basement_tv` is the authority for the automatic awake/asleep lifecycle. When Home Assistant reports exactly `off`, the firmware debounces the state for 10 seconds, renders the approved sleep face, waits for the asynchronous full refresh to complete, and enters indefinite ESP32 deep sleep.

The sleep artwork is [`assets/sleep-screen.svg`](assets/sleep-screen.svg). The e-paper image remains visible while the ESP32 is asleep. GPIO4, the physical AI / Power button, is the only deep-sleep wake source.

The Sticky exposes TI BQ27220 battery level, voltage, signed current, and charging state. A low-battery glyph is displayed when state of charge is 20% or less.

### Sticky hardware mapping

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

The Sticky uses 32 MB flash and 8 MB octal PSRAM. Its production firmware remains v1.0.13; no Sticky GPIO, power, touch, display, or sleep behavior was changed when PaperMono Lite support was added.

## M5PaperMono Lite target

The M5 target is [`esphome/basement-remote-papermono-lite.yaml`](esphome/basement-remote-papermono-lite.yaml). It imports the hardware package from:

`https://github.com/CitizenRacer/M5PaperMonoLite`

The BasementRemote repository intentionally does **not** duplicate PaperMono hardware initialization. The dependency owns ESP32-S3/PSRAM configuration, M5PM1, M5IOE1, SSD1677 setup, FT6336G touch power/reset/calibration, frontlight PWM, and battery-voltage telemetry. BasementRemote extends the package's `m5_display` and `m5_touch` IDs with the remote UI and hit regions.

### PaperMono physical controls

| Control | Behavior |
| --- | --- |
| User button on GPIO2 | Apple TV `volume_up` |
| User button on GPIO3 | Apple TV `volume_down` |
| Touchscreen | Same navigation, transport, and launcher layout as Sticky |
| Home Assistant **TV Power On** button | Apple TV `wakeup` |
| Home Assistant **TV Power Off** button | Apple TV `suspend` |
| Home Assistant **Refresh E-Paper** button | Request a display refresh |
| Home Assistant **Frontlight** light | M5PM1-controlled frontlight brightness |

The two physical volume buttons support tap and hold-to-repeat.

### Deliberate first-bring-up limitations

The PaperMono target currently stays awake. Automatic TV-off deep sleep and use of the PMIC-managed physical system power button are intentionally deferred until the M5PM1 power-button IRQ/wake path has been validated on real C153-LITE hardware. This avoids copying the Sticky's unrelated GPIO wake/latch logic onto different hardware and risking an un-wakeable device.

The PaperMono hardware package currently provides monochrome full-refresh support. Partial refresh and four-level grayscale are future hardware-package work and are not prerequisites for the remote UI.

The support package exposes **Battery Voltage** and **Frontlight**. Battery percentage/charging-state UI is not synthesized from voltage because that would be less reliable than actual fuel-gauge telemetry.

## ESPHome Device Builder

Keep Device Builder as a small secret-bearing wrapper. The complete firmware remains in GitHub.

### reTerminal Sticky

Use [`esphome/device-builder-wrapper.example.yaml`](esphome/device-builder-wrapper.example.yaml).

### M5PaperMono Lite

Use [`esphome/device-builder-wrapper-papermono-lite.example.yaml`](esphome/device-builder-wrapper-papermono-lite.example.yaml).

For either device, ensure the keys from [`esphome/secrets.example.yaml`](esphome/secrets.example.yaml) exist in Device Builder's local `secrets.yaml`. Real Wi-Fi credentials, OTA passwords, and the ESPHome API encryption key must never be committed to this repository.

## Repository layout

```text
.github/workflows/
  esphome.yml                                      # validates and compiles both hardware targets
assets/
  README.md                                        # asset provenance/build notes
  disney-d.png
  hbo-max.svg
  hulu.svg
  paramount-plus.svg
  sleep-screen.svg                                # Sticky deep-sleep artwork
  vendor/
    heroicons-v2.2.0/
docs/
  remote.jpg                                      # production Sticky photo
esphome/
  basement-remote-sticky.yaml                     # production Sticky firmware, v1.0.13
  basement-remote-papermono-lite.yaml             # PaperMono Lite firmware, v0.1.0
  device-builder-wrapper.example.yaml             # Sticky Device Builder wrapper
  device-builder-wrapper-papermono-lite.example.yaml
  secrets.example.yaml
README.md
```

## Building and CI

Both targets require ESPHome 2026.8.2 or newer.

`.github/workflows/esphome.yml` uses a matrix and independently validates/compiles:

- `esphome/basement-remote-sticky.yaml`
- `esphome/basement-remote-papermono-lite.yaml`

On `main`, CI also validates both Git-backed Device Builder wrapper examples. A PaperMono failure therefore does not remove the Sticky target, and the existing Sticky firmware remains a separate compile target.

## PaperMono hardware validation plan

When C153-LITE hardware is available:

1. Confirm the M5PM1 and M5IOE1 initialize successfully.
2. Confirm the frontlight turns on/off and dims correctly.
3. Confirm the 480×800 remote face is correctly oriented.
4. Confirm FT6336G touch coordinates align with every control.
5. Confirm GPIO2/GPIO3 map to the intended physical user buttons and volume direction.
6. Confirm tap and hold-to-repeat for both physical volume buttons.
7. Confirm all Home Assistant navigation, playback, and app-launch actions.
8. Confirm **Battery Voltage** is plausible on USB and battery.
9. Validate repeated SSD1677 full refreshes and power-down/wake cycles.
10. Add and validate PMIC system-power-button handling and TV-off sleep only after the wake path is proven reliable.

## Sticky operational validation

After any change that touches the Sticky target, confirm the v1.0.13 production behavior still works: touchscreen navigation, both physical volume buttons, short/long AI power actions, TV-state-driven sleep, approved sleep artwork, wake on GPIO4, battery telemetry, and the 100 ms GT911 startup yield.

## Maintenance rules

- `CitizenRacer/BasementRemote` on GitHub is the canonical source of truth.
- **Every code check-in must update the README in the same change whenever behavior, UI, dependencies, setup, versioning, or operational expectations change.**
- Keep the Sticky and PaperMono hardware definitions separate so development of one target cannot silently replace pins, buses, power sequencing, or wake behavior on the other.
- Keep Device Builder limited to secret-bearing package wrappers.
- Do not commit credentials or the actual ESPHome API encryption key.
- Keep app launcher source names aligned with `media_player.basement_apple_tv`.
- Keep UI artwork vendored under `assets/`; do not add third-party build-time asset URLs back to production firmware.
- Do not add e-paper refreshes for individual navigation, playback, volume, or app-launch presses unless the visible UI requires them.

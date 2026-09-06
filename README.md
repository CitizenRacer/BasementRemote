# Basement Remote

Touchscreen e-paper TV remote firmware backed directly by Home Assistant over ESPHome's encrypted native API.

## Targets

| Hardware | Firmware | Status |
| --- | --- | --- |
| Seeed Studio reTerminal Sticky | **v1.0.21** | Production target; current work focuses on reliable deep-sleep wake and GT911 recovery |
| M5Stack M5PaperMono Lite (C153-LITE) | **v0.1.0** | Initial bring-up / compile validated; hardware not yet available |

The production Sticky source is [`esphome/basement-remote-sticky.yaml`](esphome/basement-remote-sticky.yaml). The PaperMono target remains separate.

<p align="center">
  <img src="docs/remote.jpg" alt="Seeed Studio reTerminal Sticky running the Basement Remote interface" width="420">
</p>

## Architecture

```text
Touchscreen / physical buttons
        ↓
ESPHome encrypted native API
        ↓
Home Assistant actions
        ↓
Apple TV / HDMI-CEC / LG TV
```

The remote uses the same Home Assistant entities/actions as the working Basement Remote dashboard rather than maintaining a separate control architecture.

### Home Assistant dependencies

- `remote.basement_apple_tv` — navigation, transport, awake power actions, and volume
- `media_player.basement_apple_tv` — streaming-service app launchers
- `media_player.basement_tv` — imported as **TV State Seen By Remote** and used as the Sticky sleep authority
- `script.tv_turn_on_the_tv_cable` — authoritative deep-sleep wake TV-on sequence, shared with Alexa

For the ESPHome integration, **Allow the device to perform Home Assistant actions** must be enabled.

## Shared touchscreen layout

Both hardware targets use a 480×800 portrait remote layout with a D-pad/Select, Back/Home, playback controls, and Hulu/HBO Max/Disney+/Paramount+ launchers. D-pad hold-to-repeat starts after 500 ms and repeats every 175 ms. UI artwork is vendored under [`assets/`](assets/).

# reTerminal Sticky

## Physical controls

| Control | Behavior |
| --- | --- |
| AI / Power while awake, short press | Apple TV `wakeup` |
| AI / Power while awake, hold ≥ 800 ms | Apple TV `suspend` |
| AI / Power while asleep | Wake the Sticky; after Home Assistant reconnects, call `script.tv_turn_on_the_tv_cable` |
| Upper side button | Apple TV `volume_up` |
| Lower side button | Apple TV `volume_down` |

The side volume buttons use the same 500 ms / 175 ms hold-to-repeat behavior as the D-pad.

## Display and automatic sleep

The Sticky uses ESPHome's `Seeed-reTerminal-Sticky` SSD1677 display model with a 480×800 portrait UI. Normal remote commands do not refresh the e-paper display. A full refresh occurs on the configured periodic refresh and on explicit **Refresh E-Paper** requests.

`media_player.basement_tv` is the authority for automatic sleep. When it reports exactly `off`, firmware debounces the state, renders [`assets/sleep-screen.svg`](assets/sleep-screen.svg), waits for the asynchronous refresh to finish, disables Wi-Fi, and then enters ESP32 deep sleep. GPIO4, the physical AI / Power button, is the wake source.

## Entity availability while asleep

Beginning with v1.0.19, the deliberate sleep-entry path disables Wi-Fi one second before `deep_sleep.enter`. This is intentional so Home Assistant sees connectivity loss and marks the Sticky's ESPHome entities **Unavailable** while the board is asleep. On wake, Wi-Fi/API reconnect and the entities become available again. OTA/reboots still use normal ESPHome shutdown behavior.

## Wake/touch reliability history

### v1.0.15–v1.0.16

Early retained-GPIO recovery experiments could interfere with the Sticky's board power latch. A short AI press could fail to keep the unit powered, while holding AI long enough allowed it to wake.

### v1.0.17

All added manipulation of GPIO45/GPIO46/GPIO47 was removed, restoring the known-good v1.0.14 board power-latch sequence. Short-press wake returned, but touchscreen recovery still failed after wake.

### v1.0.18–v1.0.19

GT911 recovery was isolated from the board power latch. GPIO42 was retained HIGH through deep sleep to avoid cold-power-cycling the touchscreen. These versions also delayed touch setup and disabled the touch-bus scan.

However, v1.0.18/v1.0.19 incorrectly forced the GT911 to **0x14**. Hardware logs from the production Sticky showed an immediate `Communication failed` error at that address.

### v1.0.20

v1.0.20 corrects the GT911 address to **0x5D**, matching Seeed's reTerminal Sticky ESPHome hardware definition and ESPHome's GT911 primary/default address. The manual calibration override is removed so the GT911 driver reads the controller's own configuration normally.

The other reliability behavior remains unchanged:

- GPIO45/GPIO46/GPIO47 remain owned by the known-good v1.0.14 power-latch sequence.
- GPIO42 / GT911 remains powered through deep sleep.
- GT911 setup remains delayed until after touch power restoration.
- The touch I²C bus does not perform an unnecessary startup scan.
- Deep-sleep wake waits for Home Assistant and calls `script.tv_turn_on_the_tv_cable`.
- The deliberate sleep path drops Wi-Fi so entities are unavailable while asleep.

### v1.0.21

v1.0.21 makes **no intentional runtime behavior change**. It removes the remaining compile-time `-Wformat` warning from the inherited AI / Power button release logger.

The v1.0.14 base logged a `uint32_t held_ms` with `%u`. Under the ESP32-S3 ESP-IDF toolchain used by ESPHome 2026.8.2, the compiler reports that argument as `long unsigned int`, so GCC warned that `%u` expected `unsigned int`.

v1.0.21 replaces only that inherited binary-sensor definition and logs the value using `%lu` with an explicit `static_cast<unsigned long>(held_ms)`. Short-press/long-press thresholds and actions are unchanged. CI should therefore compile the Sticky with no instance of that format warning.

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

The Sticky uses 32 MB flash and 8 MB octal PSRAM.

## v1.0.21 validation checklist

1. Compile/install v1.0.21 and confirm the prior `%u` / `long unsigned int` `-Wformat` warning is absent.
2. Confirm the boot log reports **GT911 Address: 0x5D** with no `Communication failed` or `Calibration error`.
3. Confirm awake touchscreen controls work and **Last Touch X/Y** updates.
4. Turn the TV off and allow the remote to render the sleep screen.
5. Confirm the Sticky's ESPHome entities change to **Unavailable** when Wi-Fi drops for sleep.
6. Wake with a **brief tap** of AI / Power.
7. Confirm `script.tv_turn_on_the_tv_cable` turns the TV on and the entities return from **Unavailable**.
8. Confirm touchscreen controls and both physical volume buttons work after wake.
9. Repeat the sleep/wake/touch cycle several times.

# M5PaperMono Lite

The PaperMono target is [`esphome/basement-remote-papermono-lite.yaml`](esphome/basement-remote-papermono-lite.yaml) and imports board support from `CitizenRacer/M5PaperMonoLite`. Its initial bring-up intentionally stays awake; PMIC-managed power-button handling and automatic TV-off sleep are deferred until real hardware is available for validation.

# ESPHome Device Builder

Device Builder should remain a small secret-bearing wrapper. Complete device behavior belongs in GitHub.

- Sticky wrapper: [`esphome/device-builder-wrapper.example.yaml`](esphome/device-builder-wrapper.example.yaml)
- PaperMono wrapper: [`esphome/device-builder-wrapper-papermono-lite.example.yaml`](esphome/device-builder-wrapper-papermono-lite.example.yaml)
- Secret names: [`esphome/secrets.example.yaml`](esphome/secrets.example.yaml)

Never commit real Wi-Fi credentials, OTA passwords, or the ESPHome API encryption key.

# Building and CI

Both targets require ESPHome 2026.8.2 or newer. `.github/workflows/esphome.yml` validates and compiles the Sticky and PaperMono targets independently and validates the production Git-backed wrapper where applicable.

# Maintenance rules

- `CitizenRacer/BasementRemote` on GitHub is the canonical source of truth.
- **Every code check-in must update the README in the same commit whenever behavior, UI, dependencies, setup, versioning, or operational expectations change.**
- Keep Sticky and PaperMono hardware definitions separate.
- Keep Device Builder limited to secret-bearing wrappers.
- Never commit credentials or the real ESPHome API encryption key.
- Keep app launcher source names aligned with `media_player.basement_apple_tv`.
- Keep UI artwork vendored under `assets/`.
- Do not refresh e-paper for ordinary navigation, playback, volume, or app-launch presses unless visible UI state requires it.

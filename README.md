# Basement Remote

Touchscreen e-paper TV remote firmware backed directly by Home Assistant over ESPHome's encrypted native API.

## Targets

| Hardware | Firmware | Status |
| --- | --- | --- |
| Seeed Studio reTerminal Sticky | **v1.0.17** | Production / hardware validated through v1.0.14; v1.0.17 wake/touch recovery pending deployment validation |
| M5Stack M5PaperMono Lite (C153-LITE) | **v0.1.0** | Initial bring-up / compile validated; hardware not yet available |

The production Sticky source is [`esphome/basement-remote-sticky.yaml`](esphome/basement-remote-sticky.yaml). The PaperMono target is separate and does not replace Sticky hardware configuration.

<p align="center">
  <img src="docs/remote.jpg" alt="Seeed Studio reTerminal Sticky running the Basement Remote interface" width="420">
</p>

## Architecture

Both targets are front ends for the existing Home Assistant **Basement Remote** setup:

```text
Touchscreen / physical buttons
        ↓
ESPHome encrypted native API
        ↓
Home Assistant actions
        ↓
Apple TV / HDMI-CEC / LG TV
```

The remote intentionally uses the same Home Assistant entities and actions as the working dashboard rather than introducing a parallel control architecture.

### Home Assistant dependencies

- `remote.basement_apple_tv` — navigation, transport, power, and volume commands
- `media_player.basement_apple_tv` — streaming-service app launchers
- `media_player.basement_tv` — imported as **TV State Seen By Remote** and used as the Sticky's sleep authority
- `script.tv_turn_on_the_tv_cable` — authoritative TV-on sequence shared with Alexa and the Sticky deep-sleep recovery path

For the ESPHome integration, **Allow the device to perform Home Assistant actions** must be enabled.

## Shared touchscreen layout

Both targets use the same 480×800 portrait awake layout:

1. D-pad and Select
2. Back and Home
3. Playback controls
4. Hulu, HBO Max, Disney+, and Paramount+ launchers

| Control | Behavior |
| --- | --- |
| D-pad | `up`, `down`, `left`, `right`, `select` |
| Back | Apple TV `menu` |
| Home | Apple TV `home` |
| Playback | `skip_backward`, `play`, `pause`, `skip_forward` |
| Hulu | Select source `Hulu` |
| HBO Max | Select source `HBO Max` |
| Disney+ | Select source `Disney+` |
| Paramount+ | Select source `Paramount+` |

D-pad hold-to-repeat fires immediately, begins repeating after 500 ms, and repeats every 175 ms while held.

All awake UI artwork is repository-owned under [`assets/`](assets/). The interface uses vendored Heroicons plus local streaming-service artwork so builds do not depend on third-party asset hosts.

# reTerminal Sticky

## Physical controls

| Control | Behavior |
| --- | --- |
| AI / Power while awake, short press | Apple TV `wakeup` |
| AI / Power while awake, hold ≥ 800 ms | Apple TV `suspend` |
| AI / Power while asleep | Wake using the v1.0.14 hardware latch sequence; recovery then calls `script.tv_turn_on_the_tv_cable` after Home Assistant reconnects |
| Upper side button | Apple TV `volume_up` |
| Lower side button | Apple TV `volume_down` |

The two volume buttons use the same 500 ms / 175 ms hold-to-repeat behavior as the D-pad.

## Display and sleep behavior

The Sticky uses ESPHome's integrated `Seeed-reTerminal-Sticky` SSD1677 display model with a 480×800 portrait UI. While awake it performs a full refresh every 10 minutes and on explicit **Refresh E-Paper** requests. Normal navigation/media actions do not refresh the screen.

`media_player.basement_tv` is the authority for automatic sleep. When Home Assistant reports exactly `off`, firmware debounces the state for 10 seconds, renders the approved sleep face, waits for the asynchronous refresh to finish, and enters indefinite ESP32 deep sleep.

The sleep artwork is [`assets/sleep-screen.svg`](assets/sleep-screen.svg). GPIO4, the physical AI / Power button, is the only configured ESP32 deep-sleep wake source.

## Wake/recovery history

v1.0.15 attempted to harden two observed wake regressions from v1.0.14: a TV-on command that could be lost during a slow Home Assistant reconnect and a GT911 touchscreen that could remain dead after wake. It added a longer reconnect path and an early priority-1150 GPIO recovery step.

Hardware testing exposed a more serious regression: a normal short AI-button press could fail to wake the Sticky, while **holding the AI button down did wake it**. That behavior shows that the physical wake input still worked, but the button had to be held long enough to keep the board powered until firmware took over the power latch. The early recovery step had released retained `PWR_HOLD` / `PWR_LOCK` related GPIOs before the known-good v1.0.14 latch sequence reasserted them, creating a power-latch gap during wake.

v1.0.16 changed the reconnect recovery action to call `script.tv_turn_on_the_tv_cable`, the same TV-on sequence used by Alexa, but it still inherited the risky early latch override.

## v1.0.17 wake fix

v1.0.17 removes that risky override completely:

- the complete v1.0.14 GPIO45/GPIO46/GPIO47 wake/latch sequence is left untouched;
- no extra boot hook releases or manipulates `PWR_HOLD`, `PWR_LOCK`, or the e-paper power rail;
- GT911 recovery is isolated to **GPIO42 only**, after the v1.0.14 priority-900 wake code has restored the retained rails;
- GPIO42 is cold-cycled for 25 ms off / 150 ms on before normal GT911 setup;
- the secondary reconnect path still waits up to 60 seconds for Home Assistant and then calls `script.tv_turn_on_the_tv_cable` after a 2-second subscription grace period.

The design rule going forward is that touch recovery must never alter the known-good Sticky power-latch timing.

### v1.0.17 implementation note

`esphome/basement-remote-sticky.yaml` imports the last hardware-validated v1.0.14 production file from commit `dc4113e58f1b3d96a08825d5e63aadbaac05603b` and layers only the isolated v1.0.17 recovery behavior on top. Main-file substitutions override the base version to `1.0.17`.

This keeps the complete v1.0.14 UI, control mappings, wake pin, battery telemetry, assets, sleep implementation, and latch sequencing frozen while the touch/reconnect changes are validated.

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

## Sticky validation checklist

After deploying v1.0.17, validate in this order:

1. With the TV off and the sleep face visible, **briefly tap** the AI / Power button; do not hold it.
2. Confirm the Sticky itself wakes and remains powered. This specifically verifies the v1.0.16 latch regression is gone.
3. Confirm the TV powers on without a second press through `script.tv_turn_on_the_tv_cable`.
4. Confirm **Last Touch X/Y** changes immediately when the screen is touched after wake.
5. Confirm D-pad, Select, Back, Home, playback, and all app launchers work.
6. Confirm both physical volume buttons work and repeat when held.
7. Turn the TV off using a long AI / Power press and confirm the remote returns to the sleep face.
8. Repeat the short-press sleep/wake cycle several times to verify both latch and GT911 recovery are consistent.
9. Confirm battery level, voltage, current, and charging state remain plausible.

# M5PaperMono Lite

The PaperMono target is [`esphome/basement-remote-papermono-lite.yaml`](esphome/basement-remote-papermono-lite.yaml) and imports its board support from `CitizenRacer/M5PaperMonoLite`.

Its initial bring-up intentionally stays awake. PMIC-managed system-power-button handling and automatic TV-off sleep are deferred until real C153-LITE hardware is available for validation.

| Control | Behavior |
| --- | --- |
| GPIO2 user button | Apple TV `volume_up` |
| GPIO3 user button | Apple TV `volume_down` |
| Touchscreen | Same navigation/media/app layout as Sticky |
| Home Assistant **TV Power On** | Apple TV `wakeup` |
| Home Assistant **TV Power Off** | Apple TV `suspend` |
| Home Assistant **Refresh E-Paper** | Refresh display |
| Home Assistant **Frontlight** | PMIC-controlled frontlight |

# ESPHome Device Builder

Device Builder should remain only a small secret-bearing wrapper. The complete device behavior belongs in GitHub.

- Sticky wrapper example: [`esphome/device-builder-wrapper.example.yaml`](esphome/device-builder-wrapper.example.yaml)
- PaperMono wrapper example: [`esphome/device-builder-wrapper-papermono-lite.example.yaml`](esphome/device-builder-wrapper-papermono-lite.example.yaml)
- Secret names: [`esphome/secrets.example.yaml`](esphome/secrets.example.yaml)

Real Wi-Fi credentials, OTA passwords, and the ESPHome API encryption key must never be committed.

# Repository layout

```text
.github/workflows/
  esphome.yml
assets/
  disney-d.png
  hbo-max.svg
  hulu.svg
  paramount-plus.svg
  sleep-screen.svg
  vendor/heroicons-v2.2.0/
docs/
  remote.jpg
esphome/
  basement-remote-sticky.yaml
  basement-remote-papermono-lite.yaml
  device-builder-wrapper.example.yaml
  device-builder-wrapper-papermono-lite.example.yaml
  secrets.example.yaml
README.md
```

# Building and CI

Both targets require ESPHome 2026.8.2 or newer. `.github/workflows/esphome.yml` validates and compiles the Sticky and PaperMono targets independently and also validates the Git-backed wrapper examples on `main`.

# Maintenance rules

- `CitizenRacer/BasementRemote` on GitHub is the canonical source of truth.
- **Every code check-in must update the README in the same commit whenever behavior, UI, dependencies, setup, versioning, or operational expectations change.**
- Keep Sticky and PaperMono hardware definitions separate.
- Keep Device Builder limited to secret-bearing package wrappers.
- Never commit credentials or the real ESPHome API encryption key.
- Keep app launcher source names aligned with `media_player.basement_apple_tv`.
- Keep UI artwork vendored under `assets/`.
- Do not refresh the e-paper display for ordinary navigation, playback, volume, or app-launch presses unless visible UI state requires it.

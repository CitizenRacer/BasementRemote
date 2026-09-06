# Basement Remote

Touchscreen e-paper TV remote firmware backed directly by Home Assistant over ESPHome's encrypted native API.

## Targets

| Hardware | Firmware | Status |
| --- | --- | --- |
| Seeed Studio reTerminal Sticky | **v1.0.15** | Production / hardware validated through v1.0.14; v1.0.15 wake recovery pending deployment validation |
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
| AI / Power while asleep | Wake the Sticky and wake the Apple TV after Home Assistant reconnects |
| Upper side button | Apple TV `volume_up` |
| Lower side button | Apple TV `volume_down` |

The two volume buttons use the same 500 ms / 175 ms hold-to-repeat behavior as the D-pad.

## Display and sleep behavior

The Sticky uses ESPHome's integrated `Seeed-reTerminal-Sticky` SSD1677 display model with a 480×800 portrait UI. While awake it performs a full refresh every 10 minutes and on explicit **Refresh E-Paper** requests. Normal navigation/media actions do not refresh the screen.

`media_player.basement_tv` is the authority for automatic sleep. When Home Assistant reports exactly `off`, firmware debounces the state for 10 seconds, renders the approved sleep face, waits for the asynchronous refresh to finish, and enters indefinite ESP32 deep sleep.

The sleep artwork is [`assets/sleep-screen.svg`](assets/sleep-screen.svg). GPIO4, the physical AI / Power button, is the only configured ESP32 deep-sleep wake source.

## v1.0.15 wake/recovery hardening

v1.0.15 addresses two observed wake regressions from v1.0.14:

1. **TV wake command could be lost during API reconnect.** Home Assistant logged an ESPHome encrypted-handshake failure during a real wake and the reconnect took longer than the old 20-second wait. ESPHome also documents that Home Assistant actions sent immediately after an API connection can be dropped before Home Assistant finishes subscribing to device actions.
2. **GT911 touch could remain dead after wake.** Home Assistant showed the Sticky back online while **Last Touch X/Y** remained `unknown`, confirming that the touchscreen itself had not recovered.

v1.0.15 therefore adds:

- a second idempotent deep-sleep recovery path that waits up to 60 seconds for a Home Assistant state-subscribing API client;
- an additional 2-second grace period before sending the Apple TV `wakeup` action so Home Assistant has time to register the action subscription;
- a wake interlock that remains asserted while HDMI-CEC/LG state converges;
- an early boot recovery step at priority 1150 that releases retained deep-sleep GPIO holds before normal touch power setup;
- a guaranteed GT911 cold power cycle on GPIO42: 25 ms off, then 150 ms powered before the normal ESPHome GT911 initialization sequence;
- explicit recovery logging for the touch power cycle, HA subscription readiness, and recovery wake command.

The original v1.0.14 wake path remains in place. The new wake command is intentionally idempotent: sending Apple TV `wakeup` twice is safer than allowing a slow reconnect to lose the only wake request.

### v1.0.15 implementation note

To keep the recovery delta small and auditable, `esphome/basement-remote-sticky.yaml` currently imports the last hardware-validated v1.0.14 production file from commit `dc4113e58f1b3d96a08825d5e63aadbaac05603b` and layers the v1.0.15 recovery configuration on top using ESPHome packages. Main-file substitutions override the base version to `1.0.15`.

This layering is deliberate: the complete v1.0.14 UI, control mappings, assets, battery telemetry, and sleep implementation remain frozen while the wake/touch fix is validated on hardware.

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

After deploying v1.0.15, validate in this order:

1. With the TV off and the sleep face visible, press the AI / Power button once.
2. Confirm the Sticky wakes and the Apple TV/TV powers on without a second press.
3. Confirm **Last Touch X/Y** changes immediately when the screen is touched after wake.
4. Confirm D-pad, Select, Back, Home, playback, and all app launchers work.
5. Confirm both physical volume buttons work and repeat when held.
6. Turn the TV off using a long AI / Power press and confirm the remote returns to the sleep face.
7. Repeat the sleep/wake cycle several times to verify GT911 recovery is consistent.
8. Confirm battery level, voltage, current, and charging state remain plausible.

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

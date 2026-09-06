# Basement Remote

Touchscreen e-paper TV remote firmware backed directly by Home Assistant over ESPHome's encrypted native API.

## Targets

| Hardware | Firmware | Status |
| --- | --- | --- |
| Seeed Studio reTerminal Sticky | **v1.0.29** | Production target |
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

The Sticky intentionally reuses the same Home Assistant entities/actions as the working Basement Remote dashboard.

### Home Assistant dependencies

- `remote.basement_apple_tv` — navigation, transport, awake power actions, and volume
- `media_player.basement_apple_tv` — streaming-service app launchers
- `media_player.basement_tv` — imported as **TV State Seen By Remote** and used as the sleep authority
- `script.tv_turn_on_the_tv_cable` — authoritative TV-on sequence shared with Alexa and Sticky wake

For the ESPHome integration, **Allow the device to perform Home Assistant actions** must be enabled.

# reTerminal Sticky

## User interface

The Sticky uses a 480×800 portrait e-paper layout with D-pad/Select, Back/Home, playback controls, and Hulu/HBO Max/Disney+/Paramount+ launchers. D-pad hold-to-repeat starts after 500 ms and repeats every 175 ms. UI artwork is vendored under [`assets/`](assets/).

Normal remote commands do not refresh the e-paper display unless visible state needs to change. A full refresh occurs on the configured periodic refresh and on explicit **Refresh E-Paper** requests.

## Awake power behavior

Beginning with **v1.0.27**, the reTerminal Sticky runs the ESP32-S3 at **160 MHz** while awake instead of the 240 MHz default. The goal is to reduce battery consumption while the TV is on without sacrificing normal touchscreen or Home Assistant responsiveness.

Wi-Fi remains connected using ESPHome's normal ESP32 power-saving behavior; the remote does not enter light sleep while the TV is on. TV-off behavior is unchanged: the Sticky still renders the sleep screen, disables Wi-Fi, and enters deep sleep.

Beginning with **v1.0.29**, physical UART logging is disabled with `logger.baud_rate: 0` to avoid continuously driving the serial console during normal battery operation. The logger remains at DEBUG for native-API log clients, so ESPHome Device Builder / network log sessions still receive diagnostic output when connected. The existing RTTTL `WARN` override remains in effect.

## Physical controls

| Control | Behavior |
| --- | --- |
| AI / Power while awake, short press | Call `script.tv_turn_on_the_tv_cable` |
| AI / Power while awake, hold ≥ 800 ms | Apple TV `suspend` |
| AI / Power while asleep | Wake the Sticky and call `script.tv_turn_on_the_tv_cable` after Home Assistant reconnects |
| Upper side button | Apple TV `volume_up` |
| Lower side button | Apple TV `volume_down` |

The side volume buttons use the same 500 ms / 175 ms hold-to-repeat behavior as the D-pad.

## Find Remote

The Sticky exposes a Home Assistant **Find Remote** switch backed by the built-in passive buzzer on **GPIO48**.

Turning **Find Remote** on starts an alternating-pitch locator pattern. A 250 ms watchdog restarts the short RTTTL phrase whenever the player goes idle, so the locator continues until it is cancelled.

Find Remote stops when either:

- **Find Remote** is turned off in Home Assistant; or
- any local input is detected on the Sticky: AI / Power, Volume Up, Volume Down, or any touchscreen press.

Local cancellation calls `switch.turn_off` on the same exposed **Find Remote** switch. ESPHome therefore publishes **Off** back to Home Assistant immediately, and the local press still performs its normal remote-control action.

While Find Remote is active, the normal TV-off sleep path is inhibited so the remote cannot go to sleep and silence itself. When Find Remote is turned off, normal TV-state-driven sleep resumes. The switch uses `restore_mode: ALWAYS_OFF`, so rebooting/waking cannot unexpectedly restart the buzzer.

Because deliberate TV-off sleep disables Wi-Fi, Find Remote is unavailable while the Sticky is already asleep.

### Find Remote logging

Beginning with **v1.0.26**, the RTTTL component log level is overridden to `WARN`. The locator watchdog deliberately restarts a short phrase many times; ESPHome otherwise emits repetitive RTTTL DEBUG lines such as `Playing song` and `Playback finished` for every cycle.

The firmware still logs the meaningful Find Remote lifecycle events (enabled/disabled/cancelled through normal switch handling) and preserves RTTTL warnings/errors, but normal continuous locator playback no longer floods the device log.

## Automatic sleep and Home Assistant availability

`media_player.basement_tv` is the authority for automatic sleep. When it reports exactly `off`, firmware debounces the state, renders [`assets/sleep-screen.svg`](assets/sleep-screen.svg), waits for the asynchronous refresh to finish, disables Wi-Fi, and then enters ESP32 deep sleep. GPIO4, the physical AI / Power button, is the wake source.

The deliberate sleep-entry path disables Wi-Fi **before** `deep_sleep.enter`. This makes Home Assistant see the native API connection disappear unexpectedly, so the Sticky's state-bearing ESPHome entities should become **Unavailable** while asleep and become available again after wake/reconnect.

This includes battery telemetry, Wi-Fi signal, uptime, Last Touch X/Y, IP address, physical-button states, charging state, **TV State Seen By Remote**, and **Find Remote**. Home Assistant's ESPHome firmware-update entity is an integration-level exception and may remain available for a deep-sleep device.

Ordinary OTA updates and reboots still use normal ESPHome shutdown behavior; only the deliberate TV-off sleep path forces the connectivity drop.

## Touch / wake reliability

Production behavior retains these validated fixes:

- short AI-button wake uses the known-good Sticky board-latch sequence;
- GPIO45/GPIO46/GPIO47 are not manipulated by touch-recovery code;
- GT911 power is retained through deep sleep on GPIO42;
- GT911 uses the hardware-confirmed **0x5D** I²C address;
- the touch-bus startup scan is disabled;
- both awake short-press TV-on and deep-sleep wake use `script.tv_turn_on_the_tv_cable`;
- the previous `%u` / `long unsigned int` compile warning is fixed with `%lu` and an explicit `unsigned long` cast.

## Authoritative readiness log

The old early boot `ready` message is removed. Firmware emits exactly one readiness line per boot:

```text
Basement Remote firmware 1.0.29 ready
```

Beginning with **v1.0.28**, that line is emitted only after all of the following are true:

- a Home Assistant state-subscribing API client is connected;
- **TV State Seen By Remote** has received a real value rather than `unknown`/`unavailable`;
- the GT911 touchscreen has completed component setup and has not failed; and
- the initial asynchronous e-paper refresh has fully completed and the display driver has returned to its idle state.

This fixes a latent race exposed by the 160 MHz change: the previous readiness test checked only that the display had not failed, so it could log `ready` while the startup e-paper refresh was still running. The new check uses the e-paper component's actual idle/completion state instead of an arbitrary delay.

Readiness checks are serialized through a `mode: single` script so Device Builder's live logger or other transient API clients cannot produce duplicate/spurious post-ready initialization errors. If the complete readiness criteria are not satisfied within 30 seconds, firmware logs an initialization error and deliberately does not claim to be ready.

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

The Sticky uses 32 MB flash and 8 MB octal PSRAM. While awake, production firmware runs the ESP32-S3 at 160 MHz.

## v1.0.29 validation checklist

1. Compile v1.0.29 and confirm the previous `%u` / `long unsigned int` `-Wformat` warning remains absent.
2. Confirm the generated ESP32 configuration uses a **160 MHz** CPU frequency.
3. Confirm the logger configuration has physical UART output disabled (`baud_rate: 0`) while DEBUG/API logging remains available.
4. Boot and confirm GT911 reports **Address: 0x5D** with no communication/calibration failure.
5. Confirm the initial e-paper refresh fully finishes before `Basement Remote firmware 1.0.29 ready` is logged.
6. Confirm exactly one readiness line is emitted per boot and that it includes `1.0.29`.
7. With the TV on, confirm touchscreen navigation, app launchers, and physical volume controls remain immediately responsive and Home Assistant stays connected.
8. Turn **Find Remote** on and confirm the alternating-pitch locator repeats continuously.
9. Confirm continuous Find Remote playback does **not** flood API logs with RTTTL `Playing song` / `Playback finished` DEBUG lines.
10. Turn **Find Remote** off in Home Assistant and confirm the buzzer stops immediately.
11. Start Find Remote again, press a physical/touch control, and confirm the buzzer stops and Home Assistant's Find Remote switch changes to **Off**.
12. With the TV off, confirm Find Remote blocks deep sleep while active and normal sleep resumes after cancellation.
13. Confirm state-bearing entities become **Unavailable** while asleep and return after wake.
14. Wake with a brief AI / Power tap and confirm the shared Home Assistant TV-on script turns the TV on.
15. Confirm touchscreen and physical volume controls still work after repeated sleep/wake cycles.

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

# Basement Remote

Touchscreen e-paper TV remote firmware backed directly by Home Assistant over ESPHome's encrypted native API.

## Targets

| Hardware | Firmware | Status |
| --- | --- | --- |
| Seeed Studio reTerminal Sticky | **v1.0.35** | Production target |
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

Normal remote commands do not refresh the e-paper display unless visible state needs to change. Beginning with **v1.0.30**, there is no periodic display refresh. The e-paper refreshes at startup, when the low-battery threshold changes, when **Refresh E-Paper** is explicitly requested, and when rendering the sleep screen before deep sleep.

## Awake power behavior

Beginning with **v1.0.27**, the reTerminal Sticky runs the ESP32-S3 at a maximum of **160 MHz** while awake instead of the 240 MHz default. The goal is to reduce battery consumption while the TV is on without sacrificing normal touchscreen or Home Assistant responsiveness.

Beginning with **v1.0.35**, ESP-IDF power management and FreeRTOS tickless idle are enabled. After the first 20 seconds of boot, the firmware configures dynamic frequency scaling from **160 MHz down to 40 MHz** and enables automatic ESP32-S3 light sleep whenever no power-management lock or runnable task requires the CPU. GPIO4 (AI / Power), GPIO5 (Volume Up), GPIO6 (Volume Down), and GPIO21 (GT911 touch interrupt) are explicit active-low light-sleep wake sources. Wi-Fi remains associated and the native Home Assistant API remains connected; wake from light sleep resumes the existing process rather than rebooting it. TV-off behavior is unchanged: the Sticky still renders the sleep screen, disables Wi-Fi, and enters deep sleep.

The 20-second delay is deliberate. It keeps the validated e-paper refresh, GT911 initialization, Home Assistant state subscription, and authoritative readiness sequence identical to v1.0.34 before automatic light sleep becomes eligible. If ESP-IDF rejects any GPIO wake source or the power-management configuration, firmware logs an error and continues awake instead of crashing or entering an unsafe power state.

Beginning with **v1.0.29**, physical UART logging is disabled with `logger.baud_rate: 0` to avoid continuously driving the serial console during normal battery operation. The logger remains at DEBUG for native-API log clients, so ESPHome Device Builder / network log sessions still receive diagnostic output when connected. The existing RTTTL `WARN` override remains in effect.

Beginning with **v1.0.30**, the automatic 10-minute full e-paper refresh is disabled with `update_interval: never`. Because the normal remote face is static, this avoids unnecessary full-panel refreshes while preserving all explicit refresh paths.

Beginning with **v1.0.33**, `wifi.fast_connect: true` is enabled. The remote is intended to be pinned to the nearby access point, so ESPHome can skip the normal Wi-Fi scan and begin association directly, reducing wake-to-network time and the energy spent scanning. If the configured/pinned AP is unavailable, fast-connect behavior can make recovery less flexible than normal scanning, so the nearby AP should remain the intended attachment point.

Beginning with **v1.0.34**, awake Wi-Fi uses `power_save_mode: HIGH` and `output_power: 8.5dB`. `HIGH` is ESPHome's most aggressive Wi-Fi power-saving mode, while 8.5 dB is ESPHome's supported minimum transmit-power setting. These settings are intentionally paired with the same-room, pinned access point to reduce awake radio power while minimizing the connection-reliability and latency risks that would be less acceptable with a distant or roaming AP. If responsiveness, state-update latency, or connection stability regress, revert the Wi-Fi power-saving settings before pursuing more aggressive sleep behavior.

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

`media_player.basement_tv` is the authority for automatic deep sleep. When it reports exactly `off`, firmware debounces the state, renders [`assets/sleep-screen.svg`](assets/sleep-screen.svg), waits for the asynchronous refresh to finish, disables Wi-Fi, and then enters ESP32 deep sleep. GPIO4, the physical AI / Power button, is the deep-sleep wake source.

Automatic light sleep while the TV is on is intentionally different: it does not disconnect Wi-Fi, does not make Home Assistant entities unavailable, does not redraw the display, and does not reboot the ESP32. It simply lets ESP-IDF clock down or sleep the CPU between work while preserving normal remote state.

The deliberate deep-sleep entry path disables Wi-Fi **before** `deep_sleep.enter`. This makes Home Assistant see the native API connection disappear unexpectedly, so the Sticky's state-bearing ESPHome entities should become **Unavailable** while deeply asleep and become available again after wake/reconnect.

This includes battery telemetry, Wi-Fi signal, uptime, Last Touch X/Y, IP address, physical-button states, charging state, **TV State Seen By Remote**, and **Find Remote**. Home Assistant's ESPHome firmware-update entity is an integration-level exception and may remain available for a deep-sleep device.

Ordinary OTA updates and reboots still use normal ESPHome shutdown behavior; only the deliberate TV-off deep-sleep path forces the connectivity drop.

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
Basement Remote firmware 1.0.35 ready
```

Beginning with **v1.0.32**, that line is emitted only after all of the following are true:

- a Home Assistant state-subscribing API client is connected;
- **TV State Seen By Remote** has received a real value rather than `unknown`/`unavailable`;
- the GT911 touchscreen has completed component setup and has not failed;
- the SSD1677 hardware **BUSY** signal on GPIO18 has been observed asserted after the startup `component.update`, proving that the physical e-paper update actually entered hardware work; and
- after that BUSY assertion, the ESPHome e-paper state machine has returned to IDLE, meaning the full update, power-off, and controller-deep-sleep sequence completed.

The v1.0.28 readiness change incorrectly treated `Component::is_idle()` as a sufficient refresh-completion signal. In ESPHome, `Component::is_idle()` means the component loop is disabled and may already be true before the startup refresh begins. v1.0.32 therefore requires a hardware BUSY event first and only then accepts the later return to component IDLE.

**v1.0.31 was superseded before deployment.** Its first implementation attempted to replace the inherited readiness script under the same ID, and CI correctly rejected the package merge with a duplicate-ID validation error. v1.0.32 starts from the last validated v1.0.30 package, removes the inherited API readiness callback, and uses new versioned script IDs so the old script can remain defined but unreachable.

Readiness checks are serialized through a `mode: single` script so Device Builder's live logger or other transient API clients cannot produce duplicate readiness lines. If the complete readiness criteria are not satisfied within 45 seconds, firmware logs an initialization error and deliberately does not claim to be ready.

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

The Sticky uses 32 MB flash and 8 MB octal PSRAM. With the TV on, v1.0.35 allows the ESP32-S3 to scale between 40 and 160 MHz and automatically enter light sleep when idle.

## v1.0.35 validation checklist

1. Compile v1.0.35 and confirm the previous `%u` / `long unsigned int` `-Wformat` warning remains absent.
2. Confirm the generated ESP32 configuration keeps a **160 MHz** maximum CPU frequency and enables `CONFIG_PM_ENABLE` plus `CONFIG_FREERTOS_USE_TICKLESS_IDLE`.
3. Confirm the logger configuration has physical UART output disabled (`baud_rate: 0`) while DEBUG/API logging remains available.
4. Confirm `epaper_display` uses `update_interval: never` and no periodic full refresh occurs while the TV remains on.
5. Confirm the resolved Wi-Fi configuration still has `fast_connect: true`, `power_save_mode: HIGH`, and `output_power: 8.5dB`.
6. Boot with the TV on and confirm the normal readiness sequence completes before the power-management activation delay.
7. About 20 seconds after boot, confirm the log contains `Automatic light sleep enabled; CPU range 40-160 MHz; wake GPIOs 4/5/6/21` and contains no `power` error for GPIO wake or `esp_pm_configure()`.
8. Confirm the remote remains continuously available in Home Assistant while the TV is on; automatic light sleep must not cause ESPHome entities to become unavailable.
9. Confirm the remote associates to the intended nearby access point and remains stably connected while awake/light-sleeping.
10. Confirm Home Assistant state changes reflected on the remote do not show objectionable latency.
11. Confirm a touchscreen press after at least 30 seconds of no interaction responds immediately, including D-pad hold-to-repeat.
12. Confirm Volume Up and Volume Down respond immediately after the remote has been idle, including 500 ms / 175 ms hold-to-repeat.
13. Confirm a short AI / Power press and a ≥800 ms long press are still classified correctly after idle periods.
14. Confirm startup GT911 reports **Address: 0x5D** with no communication/calibration failure.
15. Confirm startup logs show `Startup e-paper BUSY observed; waiting for display state machine to finish` and then `Startup e-paper refresh state machine complete`.
16. Confirm `Basement Remote firmware 1.0.35 ready` occurs only after the state-machine-complete message and after the startup e-paper refresh is visibly finished.
17. Confirm exactly one readiness line is emitted per boot and that it includes `1.0.35`.
18. Confirm the low-battery threshold change still refreshes the battery glyph and **Refresh E-Paper** still forces a refresh.
19. Turn **Find Remote** on and confirm the alternating-pitch locator repeats continuously without RTTTL DEBUG log flooding.
20. Turn **Find Remote** off in Home Assistant and confirm the buzzer stops immediately.
21. Start Find Remote again, press a physical/touch control, and confirm the buzzer stops and Home Assistant's Find Remote switch changes to **Off**.
22. With the TV off, confirm Find Remote still blocks deep sleep while active and normal deep sleep resumes after cancellation.
23. Turn the TV off and confirm state-bearing entities become **Unavailable** only after deliberate deep sleep, not during TV-on light sleep.
24. Wake from TV-off deep sleep with a brief AI / Power tap and confirm the shared Home Assistant TV-on script turns the TV on.
25. Confirm touchscreen, physical volume controls, Wi-Fi, Home Assistant actions, and repeated deep-sleep wake cycles remain reliable after several hours of TV-on automatic light sleep.
26. Compare battery-current telemetry and battery percentage loss over a similar TV-on usage window against v1.0.34 before deciding whether v1.0.35 remains production.

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

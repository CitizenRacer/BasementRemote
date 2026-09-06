# Basement Remote

Touchscreen e-paper TV remote firmware backed directly by Home Assistant over ESPHome's encrypted native API.

## Targets

| Hardware | Firmware | Status |
| --- | --- | --- |
| Seeed Studio reTerminal Sticky | **v1.0.25** | Production target; wake, touch, readiness, sleep availability, and Find Remote support |
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
- `script.tv_turn_on_the_tv_cable` — authoritative TV-on sequence, shared with Alexa and the Sticky wake path

For the ESPHome integration, **Allow the device to perform Home Assistant actions** must be enabled.

## Shared touchscreen layout

Both hardware targets use a 480×800 portrait remote layout with a D-pad/Select, Back/Home, playback controls, and Hulu/HBO Max/Disney+/Paramount+ launchers. D-pad hold-to-repeat starts after 500 ms and repeats every 175 ms. UI artwork is vendored under [`assets/`](assets/).

# reTerminal Sticky

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

Turning **Find Remote** on starts an alternating-pitch locator pattern. Beginning with v1.0.25, a 250 ms watchdog checks whether Find Remote is still on and whether the RTTTL player is idle. If the short locator phrase has ended, the watchdog starts it again. This avoids relying on the RTTTL completion callback and makes the locator continue until it is explicitly cancelled.

Find Remote stops when either:

- **Find Remote** is turned off in Home Assistant; or
- any local input is detected on the Sticky: AI / Power, Volume Up, Volume Down, or any touchscreen press.

Local cancellation calls `switch.turn_off` on the same exposed **Find Remote** template switch. Because that switch is optimistic, ESPHome immediately publishes the new **Off** state back through the native API, so Home Assistant's Find Remote control also visibly turns off when the remote itself is pressed. The buzzer is stopped by the switch's normal turn-off action. The local press still performs its normal remote-control function; cancelling the locator does not consume the command.

While **Find Remote** is active, the normal TV-off sleep path is inhibited so the remote cannot go to sleep and silence itself before it is found. When Find Remote is turned off, normal TV-state-driven sleep resumes. The switch uses `restore_mode: ALWAYS_OFF`, so rebooting or waking the Sticky cannot unexpectedly restart the buzzer.

Because deliberate TV-off sleep disables Wi-Fi, **Find Remote is unavailable while the Sticky is already asleep**. It can be activated only while the remote is awake and connected to Home Assistant.

## Display and automatic sleep

The Sticky uses ESPHome's `Seeed-reTerminal-Sticky` SSD1677 display model with a 480×800 portrait UI. Normal remote commands do not refresh the e-paper display. A full refresh occurs on the configured periodic refresh and on explicit **Refresh E-Paper** requests.

`media_player.basement_tv` is the authority for automatic sleep. When it reports exactly `off`, firmware debounces the state, renders [`assets/sleep-screen.svg`](assets/sleep-screen.svg), waits for the asynchronous refresh to finish, disables Wi-Fi, and then enters ESP32 deep sleep. GPIO4, the physical AI / Power button, is the wake source. Active Find Remote temporarily blocks this sleep decision.

## Home Assistant availability while asleep

The deliberate sleep-entry path disables Wi-Fi **before** calling `deep_sleep.enter`. Home Assistant normally preserves the last values for an expected ESPHome deep-sleep disconnect. By dropping Wi-Fi first, the ESPHome connection is lost unexpectedly, so the remote's state-bearing ESPHome entities should become **Unavailable** while the board is asleep and become available again after wake/reconnect.

This applies to the remote's sensors, binary sensors, text sensors, and the **Find Remote** switch, including battery telemetry, Wi-Fi signal, uptime, Last Touch X/Y, IP address, physical-button states, charging state, and **TV State Seen By Remote**. Action-only entities such as template buttons do not have a persistent sensor value; Home Assistant may represent them as unavailable/disabled while disconnected. Home Assistant's ESPHome firmware-update entity is a special integration-level exception that is intentionally kept available for deep-sleep devices.

Ordinary OTA updates and reboots still use normal ESPHome shutdown behavior; only the deliberate TV-off sleep path forces the unexpected disconnect.

## Authoritative readiness log

Beginning with v1.0.22, the old early boot `ready` message is removed. The firmware emits exactly one readiness line per boot:

```text
Basement Remote firmware 1.0.25 ready
```

That line is emitted only after:

- hardware/component setup has completed;
- the GT911 and e-paper components are not marked failed;
- Wi-Fi and the ESPHome native API are connected;
- a Home Assistant state-subscribing client is present; and
- `TV State Seen By Remote` has received a real state instead of `unknown`/`unavailable`.

v1.0.23 serializes readiness checks through a `mode: single` script. ESPHome Device Builder's live logger and other transient API clients can still fire `on_client_connected`, but they can no longer race the Home Assistant readiness check or emit a false `initialization incomplete` error after `ready` has already been logged. Once `ready` has been emitted, later client connections are intentionally silent.

If the Home Assistant readiness conditions are genuinely not satisfied after the state wait, the firmware does **not** claim it is ready and logs an initialization-incomplete error. The `ready` line is intentionally the final startup health signal, not merely an ESP32 boot-complete message.

## Wake/touch reliability history

### v1.0.15–v1.0.16

Early retained-GPIO recovery experiments could interfere with the Sticky's board power latch. A short AI press could fail to keep the unit powered, while holding AI long enough allowed it to wake.

### v1.0.17

All added manipulation of GPIO45/GPIO46/GPIO47 was removed, restoring the known-good v1.0.14 board power-latch sequence. Short-press wake returned, but touchscreen recovery still failed after wake.

### v1.0.18–v1.0.19

GT911 recovery was isolated from the board power latch. GPIO42 was retained HIGH through deep sleep to avoid cold-power-cycling the touchscreen. These versions also delayed touch setup and disabled the touch-bus scan. They incorrectly forced the GT911 to `0x14`, which hardware logs showed failed immediately.

### v1.0.20

The GT911 address was corrected to **0x5D**, matching the production Sticky hardware. The manual calibration override was removed so the driver reads the controller normally.

### v1.0.22

v1.0.22 keeps the working `0x5D` GT911 configuration and board-latch behavior, and adds three cleanup/reliability changes:

- removes the inherited early `ready` log and replaces it with the authoritative post-initialization readiness check described above;
- removes the compile-time `-Wformat` warning by logging AI-button hold time with `%lu` and an explicit `unsigned long` cast instead of passing a `long unsigned int` argument to `%u`;
- makes both awake short-press TV-on and deep-sleep wake use `script.tv_turn_on_the_tv_cable`, the same Home Assistant/Alexa power-on sequence.

Implementation detail: the production package explicitly removes the inherited v1.0.14 `on_boot` automation and recreates only its required power/display sequencing, which guarantees the obsolete early `ready` logger cannot also fire.

### v1.0.23

v1.0.23 fixes a readiness-log race observed while ESPHome Device Builder's live logger was attached. Any API client can trigger `on_client_connected`; in v1.0.22, a second client connection after a valid `ready` could fall into the readiness check's `else` branch and log `Basement Remote initialization incomplete; not reporting ready` even though initialization had already succeeded.

The readiness check now runs through a `mode: single` script and immediately becomes a no-op once `ready_logged` is true. This preserves the authoritative readiness criteria while eliminating duplicate/spurious post-ready errors.

### v1.0.24

v1.0.24 adds Find Remote using the Sticky's GPIO48 buzzer. ESPHome LEDC drives the passive buzzer and RTTTL generates a two-pitch locator pattern. The new Home Assistant switch is always restored off, local button/touch activity cancels it, and an active locator blocks automatic deep sleep until cancelled.

### v1.0.25

v1.0.25 fixes the locator stopping after a single short RTTTL phrase. The RTTTL completion callback is no longer used to recursively restart playback. A 250 ms watchdog instead restarts the locator whenever Find Remote is on and the RTTTL player is idle. Local button/touch cancellation turns the exposed Find Remote switch itself off, ensuring Home Assistant also receives and displays the Off state.

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

## v1.0.25 validation checklist

1. Compile v1.0.25 and confirm the previous `%u` / `long unsigned int` `-Wformat` warning remains absent.
2. Boot and confirm GT911 reports **Address: 0x5D** with no communication/calibration failure.
3. Confirm exactly one readiness line is emitted and it includes `1.0.25`.
4. Turn **Find Remote** on in Home Assistant and confirm the alternating-pitch locator continues indefinitely instead of stopping after one phrase.
5. Turn **Find Remote** off in Home Assistant and confirm the buzzer stops immediately.
6. Start Find Remote again, then press AI / Power, either physical volume button, and a touchscreen control. Confirm each local interaction stops the buzzer, changes the Home Assistant **Find Remote** switch to **Off**, and still performs the normal remote action.
7. With the TV off, confirm an active Find Remote session prevents deep sleep; after cancelling it, confirm the normal sleep sequence resumes.
8. Confirm the remote's state-bearing ESPHome entities, including Find Remote, become **Unavailable** while asleep.
9. Wake with a brief AI / Power tap and confirm the shared Home Assistant TV-on script turns the TV on.
10. Confirm the entities become available again, then confirm touchscreen and physical volume controls work.
11. Repeat the sleep/wake/touch cycle several times.

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

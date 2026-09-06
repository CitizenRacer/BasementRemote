# Basement Remote

Touchscreen e-paper TV remote firmware backed directly by Home Assistant over ESPHome's encrypted native API.

## Targets

| Hardware | Firmware | Status |
| --- | --- | --- |
| Seeed Studio reTerminal Sticky | **v1.0.19** | Production target; v1.0.19 keeps the current wake/touch recovery work and makes entities unavailable while the board is asleep |
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

Both hardware targets use a 480×800 portrait remote layout with:

- D-pad and Select
- Back and Home
- skip backward, play, pause, skip forward
- Hulu, HBO Max, Disney+, and Paramount+ launchers

D-pad hold-to-repeat fires immediately, starts repeating after 500 ms, and repeats every 175 ms while held. UI artwork is vendored under [`assets/`](assets/).

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

Home Assistant normally keeps ESPHome entities available during an expected deep-sleep disconnect when the device reports `has_deep_sleep=true`. That behavior is useful for ordinary battery sensors because it preserves the last reading, but it is intentionally not used for this remote.

Beginning with v1.0.19, the Sticky disables Wi-Fi immediately before invoking `deep_sleep.enter`. This makes Home Assistant observe a real/unexpected API connectivity loss before ESPHome performs its normal graceful deep-sleep shutdown. The result is intentional:

- while the Sticky is asleep, its ESPHome entities should be **Unavailable**;
- when the AI / Power button wakes the Sticky and Wi-Fi/API reconnect, the entities should become available again and publish their current values;
- ordinary OTA updates and reboots still use ESPHome's normal shutdown path; only the deliberate sleep-entry path drops Wi-Fi first.

The one-second pause between `wifi.disable` and `deep_sleep.enter` exists to give Home Assistant time to process the TCP/API disconnect before the MCU enters deep sleep.

## Wake/touch reliability history

### v1.0.15–v1.0.16

These versions added wake-reconnect and GT911 recovery experiments. The early retained-GPIO handling could interfere with the Sticky's board power latch: a short AI press could fail to keep the unit powered, while holding AI long enough allowed it to wake.

### v1.0.17

v1.0.17 removed all added manipulation of GPIO45/GPIO46/GPIO47 and restored the known-good v1.0.14 board power-latch sequence. This restored short-press wake, but hardware testing still showed that the display touchscreen could remain unresponsive after wake.

### v1.0.18–v1.0.19

These versions isolate the remaining wake work to the GT911 touchscreen and do not alter the board power latch.

GPIO42 / GT911 is kept powered through ESP32 deep sleep instead of being cold-power-cycled on every sleep/wake transition. The v1.0.14 base shutdown briefly requests the touch rail off; the current shutdown hook runs afterward and restores GPIO42 HIGH, then holds that HIGH level through deep sleep. The normal GT911 reset-pin initialization still runs on boot.

Additional GT911 startup hardening:

- the dedicated touch I²C bus does not perform an unnecessary startup scan;
- GT911 setup is delayed to priority **500**, after the v1.0.14 priority-600 touch-power restoration;
- the known Sticky GT911 I²C address is fixed at **0x14**;
- known raw dimensions are supplied as calibration (`480×800`), avoiding an additional startup calibration-register read.

This deliberately favors reliable wake/touch behavior over minimum sleep current. Keeping the GT911 powered may use more battery than holding GPIO42 low. Once repeated sleep/wake testing is reliable, a future optimization can put the powered GT911 into its documented hardware sleep mode instead of cutting its power.

The deep-sleep TV-on recovery path waits for Home Assistant to reconnect and then invokes `script.tv_turn_on_the_tv_cable`, the same TV-on sequence used by Alexa.

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

## v1.0.19 validation checklist

1. Install v1.0.19 while the Sticky is awake.
2. Confirm awake touchscreen controls work before the first sleep cycle.
3. Turn the TV off and allow the remote to render the sleep screen.
4. Confirm the Sticky's ESPHome entities change to **Unavailable** when Wi-Fi drops for sleep.
5. Wake with a **brief tap** of AI / Power; do not hold it.
6. Confirm the Sticky stays powered and `script.tv_turn_on_the_tv_cable` turns the TV on.
7. Confirm the ESPHome entities return from **Unavailable** after Wi-Fi/API reconnect.
8. Immediately touch several D-pad buttons and confirm **Last Touch X/Y** updates in Home Assistant.
9. Confirm Back, Home, playback, app launchers, and both physical volume buttons work.
10. Repeat the TV-off → unavailable → sleep → brief-tap wake → available cycle at least five times.
11. Confirm battery telemetry remains plausible and observe sleep-current/battery-life impact before further power optimization.

# M5PaperMono Lite

The PaperMono target is [`esphome/basement-remote-papermono-lite.yaml`](esphome/basement-remote-papermono-lite.yaml) and imports board support from `CitizenRacer/M5PaperMonoLite`.

Its initial bring-up intentionally stays awake. PMIC-managed system-power-button handling and automatic TV-off sleep are deferred until real hardware is available for validation.

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

# Basement Remote

Touchscreen e-paper TV remote firmware backed directly by Home Assistant over ESPHome's encrypted native API.

## Targets

| Hardware | Firmware | Status |
| --- | --- | --- |
| Seeed Studio reTerminal Sticky | **v1.0.36** | Production target |
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

Beginning with **v1.0.27**, the reTerminal Sticky runs the ESP32-S3 at a maximum of **160 MHz** while awake instead of the 240 MHz default.

Beginning with **v1.0.35**, ESP-IDF power management and FreeRTOS tickless idle are enabled. After the first 20 seconds of boot, dynamic frequency scaling allows the CPU to run from **40–160 MHz** and automatic ESP32-S3 light sleep is enabled whenever the system is idle. GPIO4 (AI / Power), GPIO5 (Volume Up), GPIO6 (Volume Down), and GPIO21 (GT911 touch interrupt) are active-low light-sleep wake sources. Wi-Fi remains associated and the native Home Assistant API remains connected during TV-on light sleep.

Beginning with **v1.0.36**, automatic light sleep is deliberately suspended during the final TV-off e-paper render window. Normal TV-on power savings are unchanged.

Beginning with **v1.0.29**, physical UART logging is disabled with `logger.baud_rate: 0`; DEBUG logs remain available over the ESPHome native API. RTTTL logging is limited to WARN so Find Remote does not flood the log.

Beginning with **v1.0.30**, `epaper_display` uses `update_interval: never`; the static remote face is refreshed only when explicitly required.

Beginning with **v1.0.33**, `wifi.fast_connect: true` skips normal AP scanning for the intended nearby/pinned access point.

Beginning with **v1.0.34**, awake Wi-Fi uses `power_save_mode: HIGH` and ESPHome's minimum supported transmit-power setting of `8.5dB`.

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

The Sticky exposes a Home Assistant **Find Remote** switch backed by the built-in passive buzzer on GPIO48. A 250 ms watchdog restarts the locator phrase whenever RTTTL becomes idle, so the sound continues until cancelled.

Find Remote stops when it is turned off in Home Assistant or when any local input is detected: AI / Power, Volume Up, Volume Down, or touchscreen input. Local cancellation does not consume the user's remote command.

While Find Remote is active, TV-off deep sleep is inhibited. When Find Remote is turned off, normal TV-state-driven sleep resumes. The switch uses `restore_mode: ALWAYS_OFF`, so waking/rebooting cannot unexpectedly restart the buzzer.

Because deliberate TV-off sleep disables Wi-Fi, Find Remote is unavailable after the Sticky has already entered deep sleep.

## Automatic TV-off deep sleep

`media_player.basement_tv` is the authority for automatic deep sleep. When it reports exactly `off`, firmware debounces the state, renders [`assets/sleep-screen.svg`](assets/sleep-screen.svg), gives the asynchronous SSD1677 full refresh its existing 10-second completion window, disables Wi-Fi, and enters ESP32 deep sleep. GPIO4, the physical AI / Power button, is the deep-sleep wake source.

The sleep-screen regression appeared after **v1.0.35** added automatic ESP32 light sleep. The final TV-off render was still using the older path's assumption that the ESP32 remained fully awake during its e-paper transaction. **v1.0.36 restores that assumption without replacing the validated sleep scripts.**

A 250 ms power-management guard watches the existing sleep state. When the TV is confirmed `off`, Find Remote is not active, and no TV-wake action is in progress, it configures ESP-IDF for a fixed **160 MHz** CPU frequency with automatic light sleep disabled. Once `sleep_display_active` is set by the inherited renderer, the guard remains active unconditionally until deep sleep resets the ESP32. This also protects against the narrow case where v1.0.35's delayed 20-second light-sleep setup runs during the TV-off debounce.

If the TV returns on or the sleep attempt is otherwise cancelled before the sleep face is rendered, v1.0.36 restores the normal **40–160 MHz** dynamic-frequency/light-sleep configuration. During the first 20 seconds after boot it instead preserves the existing fully-awake startup policy and lets v1.0.35's normal delayed power-management setup take over.

The deliberate deep-sleep path disables Wi-Fi **before** `deep_sleep.enter`. Home Assistant should therefore mark the Sticky's state-bearing ESPHome entities **Unavailable** while deeply asleep and make them available again after wake/reconnect. Automatic TV-on light sleep is different: it keeps Wi-Fi/API connectivity and does not redraw the display or reboot the ESP32.

## Touch / wake reliability

Production behavior retains these validated fixes:

- short AI-button wake uses the known-good Sticky board-latch sequence;
- GPIO45/GPIO46/GPIO47 are not manipulated by touch-recovery code;
- GT911 power is retained through deep sleep on GPIO42;
- GT911 uses the hardware-confirmed **0x5D** I²C address;
- the touch-bus startup scan is disabled;
- both awake short-press TV-on and deep-sleep wake use `script.tv_turn_on_the_tv_cable`;
- the `%u` / `long unsigned int` compile warning is fixed with `%lu` and an explicit `unsigned long` cast.

## Authoritative readiness log

Firmware emits exactly one authoritative line per boot:

```text
Basement Remote firmware 1.0.36 ready
```

Beginning with **v1.0.32**, readiness requires all of the following:

- a Home Assistant state-subscribing API client is connected;
- **TV State Seen By Remote** has received a real value rather than `unknown`/`unavailable`;
- the GT911 touchscreen has completed setup and has not failed;
- GPIO18 BUSY has been observed asserted after the startup `component.update`, proving the SSD1677 refresh reached hardware; and
- after that BUSY assertion, the e-paper component returns to IDLE.

`Component::is_idle()` alone is not sufficient because it may already be true before an asynchronous refresh begins. The BUSY assertion is the start-of-hardware-work evidence; the later return to IDLE is the completion evidence.

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

## v1.0.36 validation checklist

1. Compile v1.0.36 with ESPHome 2026.8.2 and confirm there are no configuration/compiler errors.
2. Confirm `CONFIG_PM_ENABLE` and `CONFIG_FREERTOS_USE_TICKLESS_IDLE` remain enabled and the normal TV-on CPU range is 40–160 MHz.
3. Confirm physical UART logging remains disabled while native-API DEBUG logging works.
4. Confirm `epaper_display` still uses `update_interval: never`.
5. Confirm Wi-Fi still resolves to `fast_connect: true`, `power_save_mode: HIGH`, and `output_power: 8.5dB`.
6. Boot with the TV on and confirm startup BUSY evidence completes before `Basement Remote firmware 1.0.36 ready` is logged.
7. About 20 seconds after boot, confirm `Automatic light sleep enabled; CPU range 40-160 MHz; wake GPIOs 4/5/6/21` appears without a power-management error.
8. Confirm the remote stays available in Home Assistant while the TV is on and idle.
9. Confirm touchscreen, side-volume buttons, AI / Power short/long press, app launchers, and D-pad hold-to-repeat remain responsive after idle periods.
10. Confirm Find Remote still repeats continuously, cancels on local input, and blocks TV-off sleep while active.
11. Turn the TV off and confirm `TV-off e-paper guard active; automatic light sleep disabled; CPU fixed at 160 MHz` appears before the sleep render begins.
12. Confirm the normal `Rendering approved sleep face` log appears and the approved sleep artwork is fully visible before the remote disconnects.
13. Confirm `Sleep face rendered; dropping Wi-Fi before deep sleep` is logged after the existing refresh window and that the device then becomes unavailable in Home Assistant.
14. Wake with a brief AI / Power tap and confirm the shared Home Assistant TV-on script turns the TV on.
15. Repeat TV-off / wake cycles several times and confirm the sleep artwork is reliable on every cycle.
16. Test a cancelled TV-off transition (TV returns on before render) and confirm `TV-off e-paper guard released; automatic light sleep restored; CPU range 40-160 MHz` appears.
17. Confirm low-battery threshold changes and the **Refresh E-Paper** diagnostic button still perform explicit display refreshes.

# M5PaperMono Lite

The PaperMono target is [`esphome/basement-remote-papermono-lite.yaml`](esphome/basement-remote-papermono-lite.yaml) and imports board support from `CitizenRacer/M5PaperMonoLite`. Its initial bring-up intentionally stays awake; PMIC-managed power-button handling and automatic TV-off sleep are deferred until real hardware is available for validation.

# ESPHome Device Builder

Device Builder should remain a small secret-bearing wrapper. Complete device behavior belongs in GitHub.

- Sticky wrapper: [`esphome/device-builder-wrapper.example.yaml`](esphome/device-builder-wrapper.example.yaml)
- PaperMono wrapper: [`esphome/device-builder-wrapper-papermono-lite.example.yaml`](esphome/device-builder-wrapper-papermono-lite.example.yaml)
- Secret names: [`esphome/secrets.example.yaml`](esphome/secrets.example.yaml)

Never commit real Wi-Fi credentials, OTA passwords, or the ESPHome API encryption key.

# Building and CI

Both targets require ESPHome 2026.8.2 or newer. `.github/workflows/esphome.yml` validates and compiles the Sticky and PaperMono targets independently and validates the production Git-backed wrappers on main.

# Maintenance rules

- `CitizenRacer/BasementRemote` on GitHub is the canonical source of truth.
- **Every code check-in must update the README in the same commit whenever behavior, UI, dependencies, setup, versioning, or operational expectations change.**
- Keep Sticky and PaperMono hardware definitions separate.
- Keep Device Builder limited to secret-bearing wrappers.
- Never commit credentials or the real ESPHome API encryption key.
- Keep app launcher source names aligned with `media_player.basement_apple_tv`.
- Keep UI artwork vendored under `assets/`.
- Do not refresh e-paper for ordinary navigation, playback, volume, or app-launch presses unless visible UI state requires it.

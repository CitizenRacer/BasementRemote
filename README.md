# Basement Remote

Touchscreen TV remote firmware for the **Seeed Studio reTerminal Sticky**, backed directly by Home Assistant over ESPHome's encrypted native API.

Current firmware on `main`: **v1.0**. The authoritative version is the `firmware_version` substitution in [`esphome/basement-remote-sticky.yaml`](esphome/basement-remote-sticky.yaml).

<p align="center">
  <img src="docs/remote.jpg" alt="Seeed Studio reTerminal Sticky running the Basement Remote interface" width="420">
</p>

## Architecture

The Sticky is another front end for the existing Home Assistant **Basement Remote** setup. It uses the same Apple TV and TV entities directly rather than introducing a second remote-control architecture.

```text
Sticky touchscreen / physical buttons
        ↓
ESPHome encrypted native API
        ↓
Home Assistant actions
        ↓
Apple TV / HDMI-CEC / LG TV
```

The firmware does not use `automation.remote_navigation_2` or `esphome.remote_button_pressed` as its control plane.

## Home Assistant dependencies

The firmware directly depends on:

- `remote.basement_apple_tv` — navigation, transport, power, and volume commands
- `media_player.basement_apple_tv` — streaming-service app launchers via `media_player.select_source`
- `media_player.basement_tv` — authoritative TV power state for the remote's deep-sleep lifecycle

For the ESPHome integration, Home Assistant must have **Allow the device to perform Home Assistant actions** enabled.

## Controls

| Control | Behavior |
| --- | --- |
| Physical AI / Power button, short press | Apple TV `wakeup` |
| Physical AI / Power button, hold ≥ 800 ms | Apple TV `suspend` |
| Physical upper side button | Apple TV `volume_up` |
| Physical lower side button | Apple TV `volume_down` |
| Touch D-pad | `up`, `down`, `left`, `right`, `select` |
| Back | Apple TV `menu` |
| Home | Apple TV `home` |
| Playback row | `skip_backward`, `play`, `pause`, `skip_forward` |
| Hulu launcher | Select Apple TV source `Hulu` |
| HBO Max launcher | Select Apple TV source `HBO Max` |
| Disney+ launcher | Select Apple TV source `Disney+` |
| Paramount+ launcher | Select Apple TV source `Paramount+` |

The D-pad and both physical volume buttons support hold-to-repeat. They fire immediately, begin repeating after 500 ms, and repeat every 175 ms while held.

The physical AI / Power button is the **only power control**. There is no on-screen power or mute button.

## Display and touch UI

The remote uses the Sticky's 480×800 portrait e-paper display with a static, icon-only layout:

1. Large D-pad and Select
2. Back and Home
3. Playback controls
4. Hulu, HBO Max, Disney+, and Paramount+ launchers

The up/down D-pad controls are 180×90. Left/right use the same dimensions rotated 90 degrees, so they are 90×180.

Control icons use pinned **Heroicons v2.2.0** solid SVGs. Disney+ and Paramount+ artwork is stored in this repository under [`assets/`](assets/) and referenced by commit-pinned raw GitHub URLs so ESPHome can resolve them from the Device Builder package context. Hulu and HBO Max currently use external SVG sources at compile time.

The GT911 touch transform was calibrated on the physical device. Native X matches portrait X; Y is mirrored. The axes must not be swapped.

The e-paper display uses `update_interval: never`. It refreshes at boot, on an explicit Home Assistant **Refresh E-Paper** command, and when the low-battery threshold changes. Normal navigation, playback, volume, and app-launch actions do not refresh the display.

## Battery telemetry

The Sticky's **TI BQ27220** fuel gauge is read over the sensor I²C bus at address `0x55`. The firmware exposes:

- **Battery Level** — state of charge in percent
- **Battery Voltage** — pack voltage in volts
- **Battery Current** — signed battery current in mA
- **Battery Charging** — charging-state binary sensor derived from measured current

Telemetry is sampled every 60 seconds while the ESP32 is awake. When battery level is **20% or less**, a small low-battery glyph appears in the upper-right corner. The display only refreshes when that threshold changes.

Battery telemetry stops while the device is in deep sleep and resumes when it wakes.

## Power and deep sleep

`media_player.basement_tv` is the authority for whether the remote should remain awake. When the TV is confirmed `off`, the firmware waits 10 seconds to debounce transient state changes and then enters indefinite ESP32 deep sleep if no power transition is in progress.

While asleep:

- the ESP32 is in deep sleep indefinitely;
- touch and display power rails are shut down;
- the e-paper image remains visible without power;
- the Sticky normally appears offline in ESPHome and Home Assistant;
- battery telemetry stops updating;
- the touchscreen and side volume buttons do not wake the device; and
- GPIO4, the physical AI / Power button, is the only wake source.

A power-button press that wakes the device is timed through release, so short-press and long-press behavior is the same whether the Sticky starts awake or asleep.

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

The Sticky uses two independent I²C buses: the BQ27220 sensor bus on GPIO0/GPIO1 and the GT911 touchscreen bus on GPIO2/GPIO3.

The ESP32-S3 configuration uses 32 MB flash and 8 MB octal PSRAM. ESPHome's integrated `Seeed-reTerminal-Sticky` display model supplies the SSD1677 display-specific defaults. The e-paper and microSD interfaces share SCK/MOSI; this firmware does not configure the microSD card.

## Repository layout

```text
.github/workflows/
  esphome.yml                         # CI validation and compilation
assets/
  disney-d.png                       # Disney+ launcher artwork
  paramount-plus.svg                 # Paramount+ launcher artwork
docs/
  remote.jpg                         # Photo of the completed remote
esphome/
  basement-remote-sticky.yaml        # Canonical production firmware package
  device-builder-wrapper.example.yaml
  secrets.example.yaml
README.md
```

[`esphome/basement-remote-sticky.yaml`](esphome/basement-remote-sticky.yaml) is the firmware source of truth. The Device Builder configuration should remain a small local wrapper that resolves secrets and imports the production package from GitHub `main`.

## ESPHome Device Builder setup

This project uses a Git-backed package so the full firmware is maintained only in this repository.

1. Open **ESPHome Device Builder** in Home Assistant.
2. Create a device using **Empty Configuration**.
3. Name it **Basement Remote Sticky**.
4. Replace the generated YAML with [`esphome/device-builder-wrapper.example.yaml`](esphome/device-builder-wrapper.example.yaml).
5. Ensure the required keys from [`esphome/secrets.example.yaml`](esphome/secrets.example.yaml) exist in Device Builder's local `secrets.yaml`.
6. Validate and install from the wrapper.

The wrapper imports `esphome/basement-remote-sticky.yaml` from `main` with a 60-second package refresh interval. The real API encryption key and passwords belong only in Home Assistant's local ESPHome `secrets.yaml`; never commit them to this repository.

## Building and CI

The firmware requires **ESPHome 2026.8.2 or newer**. CI currently installs and tests against **ESPHome 2026.8.2**.

`.github/workflows/esphome.yml` runs on pushes and pull requests, creates CI-only dummy secrets, validates the package configuration, compiles the firmware, and validates the production GitHub-backed Device Builder wrapper on `main`.

## Operational validation

After installing v1.0:

1. Confirm the boot log contains `Basement Remote firmware 1.0 ready`.
2. Confirm **Battery Level**, **Battery Voltage**, **Battery Current**, and **Battery Charging** report plausible values while awake.
3. Test all D-pad directions and Select, including hold-to-repeat.
4. Test Back, Home, playback controls, and all four app launchers.
5. Test both physical volume buttons with tap and hold.
6. Test short- and long-press behavior of the AI / Power button.
7. Confirm the Sticky enters deep sleep after the LG TV is reported off and wakes only from the AI / Power button.
8. If battery level is at or below 20%, confirm the low-battery glyph appears.

## Maintenance rules

- `CitizenRacer/BasementRemote` on GitHub is the canonical source of truth.
- Keep Device Builder limited to the secret-bearing package wrapper.
- Do not commit credentials or the actual ESPHome API encryption key.
- Keep app launcher source names aligned with `media_player.basement_apple_tv`.
- Keep repository-owned launcher artwork deterministic and resolvable from the Device Builder package context.
- Do not add routine e-paper refreshes for button presses or continuously changing telemetry unless the visible UI requires them.

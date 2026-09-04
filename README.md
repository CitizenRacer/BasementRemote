# Basement Remote

Touchscreen TV remote firmware for the **Seeed Studio reTerminal Sticky**, backed directly by Home Assistant over ESPHome's encrypted native API.

Current firmware on `main`: **v1.0.13**. The authoritative version is the `firmware_version` substitution in [`esphome/basement-remote-sticky.yaml`](esphome/basement-remote-sticky.yaml).

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
- `media_player.basement_tv` — authoritative TV power state for the remote's automatic deep-sleep lifecycle

For the ESPHome integration, Home Assistant must have **Allow the device to perform Home Assistant actions** enabled.

ESPHome exposes a native Home Assistant **Sleep Remote** button. Pressing it forces the Sticky to render the sleep face and enter deep sleep immediately, regardless of the TV's current state. As expected for a deep-sleep device, that button becomes unavailable while the Sticky is asleep and returns after the AI / Power button wakes it.

Firmware v1.0.11 explicitly exposes **TV State Seen By Remote** as a non-internal diagnostic text sensor. It is the exact imported state of `media_player.basement_tv` that the Sticky uses for its automatic sleep decision. If it says anything other than `off`, the normal automatic sleep path will not proceed.

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
| Home Assistant **Sleep Remote** button | Render the sleep face with one full refresh and enter deep sleep |

The D-pad and both physical volume buttons support hold-to-repeat. They fire immediately, begin repeating after 500 ms, and repeat every 175 ms while held.

The physical AI / Power button is the **only power control and the only deep-sleep wake source**. There is no on-screen power or mute button.

## Display and touch UI

The remote uses the Sticky's 480×800 portrait e-paper display with a static, icon-only awake layout:

1. Large D-pad and Select
2. Back and Home
3. Playback controls
4. Hulu, HBO Max, Disney+, and Paramount+ launchers

The up/down D-pad controls are 180×90. Left/right use the same dimensions rotated 90 degrees, so they are 90×180.

All UI artwork used by the firmware is stored under [`assets/`](assets/). The awake controls use vendored **Heroicons v2.2.0** solid SVGs. Hulu, HBO Max, Disney+, and Paramount+ launcher artwork is also repository-owned. The previous external Heroicons, Material Design Icons, Wikimedia, Google Fonts, and commit-pinned launcher fetches have been removed from the firmware configuration.

ESPHome currently resolves local `image.file` paths relative to the Device Builder wrapper rather than to a remote package's cached checkout. Because the production configuration is intentionally a Git-backed package, the firmware references vendored artwork through this repository's own `raw.githubusercontent.com/CitizenRacer/BasementRemote/...` paths. Builds therefore still fetch the BasementRemote repository itself, but they no longer rely on any third-party UI asset host. Source/provenance details are in [`assets/README.md`](assets/README.md).

Immediately before deep sleep, the firmware replaces the normal remote face with the dedicated 480×800 artwork in [`assets/sleep-screen.svg`](assets/sleep-screen.svg). It shows a large crescent-moon-and-Z sleep mark in the upper-middle of the display with **Sleeping** beneath it. Near the bottom, **Press power to wake** is connected to the right edge by a whimsical hand-drawn arrow. The arrow terminates at approximately 14% from the top of the display, aligning with the physical AI / Power button on the Sticky's right side. Its two loops are intentionally irregular rather than uniform.

Firmware v1.0.5 made two physical-display corrections discovered on the real Sticky: **Press power to wake** was made larger and heavier, and the arrow shaft was moved to join behind the arrowhead rather than crowding the two lines that form the point.

Firmware v1.0.6 added an explicit white cleaning refresh before the sleep image. Physical testing showed that this produced an undesirable multi-second blank interval.

Firmware v1.0.7 restored `transparency: chroma_key` for the sleep image after testing showed that making the image opaque did not fix the missing-label problem.

Firmware v1.0.8 converts both **Sleeping** and **Press power to wake** from live SVG text elements into ordinary vector path geometry. ESPHome/resvg therefore has no font selection, font loading, or text shaping to perform for the sleep face. The firmware pins the vector-only sleep asset by commit so an older cached SVG cannot be reused.

Firmware v1.0.9 removes the explicit white pre-refresh. Because `full_update_every: 1`, the sleep-face update is already a full SSD1677 refresh and performs the panel's normal full-refresh waveform. The firmware now requests the final sleep artwork immediately, then stays awake for 10 seconds so that asynchronous refresh can finish before display power is removed. This removes the long deliberately blank phase while retaining the protection against entering deep sleep before the e-paper update completes. A short blank/flash during the physical full-refresh waveform itself is intrinsic to the panel.

Firmware v1.0.12 removed the previous 1-second delay between restoring the Sticky's power/touch rails and requesting the normal e-paper face on cold boot or deep-sleep wake. Physical testing showed that starting the full e-paper refresh with no scheduler yield could prevent the GT911 touchscreen from completing startup reliably.

Firmware v1.0.13 adds back only a **100 ms** startup yield before the full e-paper refresh. This gives the GT911 reset/initialization sequence time to complete while retaining 90% of the wake-latency improvement from removing the old 1-second delay.

The entire sleep face is rasterized to a 1-bit image at compile time. All visible lettering in the sleep artwork is already vector outline geometry before ESPHome sees it, so the sleep screen has no font dependency at build time. Because e-paper retains its image without power, the sleep face remains visible while the ESP32 is asleep.

The GT911 touch transform was calibrated on the physical device. Native X matches portrait X; Y is mirrored. The axes must not be swapped.

While awake, the e-paper performs a full refresh every **10 minutes**. It also refreshes at boot/wake, on an explicit Home Assistant **Refresh E-Paper** command, when the low-battery threshold changes, and once immediately before deep sleep to render the sleep face. Normal navigation, playback, volume, and app-launch actions do not trigger refreshes.

## Battery telemetry

The Sticky's **TI BQ27220** fuel gauge is read over the sensor I²C bus at address `0x55`. The firmware exposes:

- **Battery Level** — state of charge in percent
- **Battery Voltage** — pack voltage in volts
- **Battery Current** — signed battery current in mA
- **Battery Charging** — charging-state binary sensor derived from measured current

Telemetry is sampled every 60 seconds while the ESP32 is awake. When battery level is **20% or less**, a small low-battery glyph appears in the upper-right corner of the awake remote face.

Battery telemetry stops while the device is in deep sleep and resumes when it wakes.

## Power and deep sleep

`media_player.basement_tv` is the authority for the remote's **automatic** awake/asleep lifecycle. The Sticky subscribes to that entity over the ESPHome native API; it does **not** poll the TV on a fixed interval. Home Assistant state updates are pushed to the imported text sensor and trigger its `on_value` automation. When the imported state is exactly `off`, the firmware waits 10 seconds to debounce transient state changes. If the TV is still `off` and no power transition is in progress, it renders the approved sleep face with a single full refresh, waits 10 seconds for that asynchronous refresh to finish, and then enters indefinite ESP32 deep sleep.

The exposed **TV State Seen By Remote** diagnostic shows the exact state driving that decision. States such as `on`, `playing`, `paused`, `idle`, `unknown`, or `unavailable` do not satisfy the automatic-sleep condition.

Home Assistant can bypass the TV-state check by pressing the ESPHome **Sleep Remote** button. This is an explicit manual override: the sleep face is rendered and the Sticky enters the same indefinite deep-sleep state even if `media_player.basement_tv` is still on.

While asleep:

- the ESP32 is in deep sleep indefinitely;
- touch and display power rails are shut down;
- the e-paper sleep face remains visible without power;
- the Sticky normally appears offline in ESPHome and Home Assistant;
- ESPHome entities, including **Sleep Remote** and **TV State Seen By Remote**, are unavailable;
- battery telemetry stops updating;
- the touchscreen and side volume buttons do not wake the device; and
- GPIO4, the physical AI / Power button, is the only wake source.

A power-button press that wakes the device is timed through release, so short-press and long-press behavior is the same whether the Sticky starts awake or asleep. On wake, the touch power rail is restored, startup yields for 100 ms so the GT911 can initialize, and then the normal remote face begins its full e-paper refresh.

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
  README.md                           # Asset provenance/build notes
  disney-d.png                       # Disney+ launcher artwork
  hbo-max.svg                        # Vendored HBO Max launcher artwork
  hulu.svg                           # Vendored Hulu launcher artwork
  paramount-plus.svg                 # Paramount+ launcher artwork
  sleep-screen.svg                   # Approved 480x800 deep-sleep artwork, including outlined text
  vendor/
    heroicons-v2.2.0/                # Vendored awake-control SVGs
    material-design-icons-v7.4.47/   # Vendored MDI source artwork
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

The firmware requires **ESPHome 2026.8.2 or newer**.

The repository still contains `.github/workflows/esphome.yml`, so GitHub Actions may run automatically after pushes. It is **not a release gate** for this project: requested changes are checked directly into `main` without waiting for Actions to complete.

## Operational validation

After installing v1.0.13:

1. Confirm the boot log contains `Basement Remote firmware 1.0.13 ready`.
2. Confirm **TV State Seen By Remote** appears as a diagnostic entity and matches the current state of `media_player.basement_tv`.
3. Confirm **Battery Level**, **Battery Voltage**, **Battery Current**, and **Battery Charging** report plausible values while awake.
4. Test all D-pad directions and Select, including hold-to-repeat.
5. Test Back, Home, playback controls, and all four app launchers.
6. Test both physical volume buttons with tap and hold.
7. Test short- and long-press behavior of the AI / Power button.
8. Turn the TV off and confirm the remote receives the state change, waits for the 10-second debounce period, then goes directly into the sleep-face full refresh without a separate long white-screen phase.
9. Confirm **Sleeping** and **Press power to wake** are both visible; both are compiled from vector outlines rather than SVG text.
10. Confirm no visible ghost of the awake remote remains once the full refresh completes.
11. Confirm the Sticky remains awake long enough for the sleep-face refresh to finish before it goes offline.
12. Wake the Sticky with the physical AI / Power button and confirm the normal remote face starts refreshing after only the 100 ms GT911 startup yield, then confirm touches register normally.
13. With the Sticky awake, press **Sleep Remote** in Home Assistant and confirm it uses the same single-refresh sleep transition even if the TV remains on.
14. Wake it again with the physical AI / Power button and confirm the **Sleep Remote** and **TV State Seen By Remote** entities become available again.
15. If battery level is at or below 20%, confirm the low-battery glyph appears on the awake face.

## Maintenance rules

- `CitizenRacer/BasementRemote` on GitHub is the canonical source of truth.
- **Every code check-in must update the README in the same change whenever behavior, UI, dependencies, setup, versioning, or operational expectations change.** The README must remain accurate and consistent with `main`.
- Keep Device Builder limited to the secret-bearing package wrapper.
- Do not commit credentials or the actual ESPHome API encryption key.
- Keep app launcher source names aligned with `media_player.basement_apple_tv`.
- Keep UI artwork vendored under `assets/`; do not add third-party build-time asset URLs back to the production firmware.
- Do not add e-paper refreshes for individual navigation, playback, volume, or app-launch presses unless the visible UI requires them.
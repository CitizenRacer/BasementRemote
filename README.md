# Basement Remote

Touchscreen TV remote firmware for the **Seeed Studio reTerminal Sticky**, backed directly by Home Assistant over ESPHome's encrypted native API.

Current firmware: **v0.2.9** — TV-state deep sleep, physical AI-button power control, and an icon-only remote UI.

## Architecture

The Sticky is intentionally another front end for the already-working Home Assistant **Basement Remote** dashboard. It does **not** introduce a second remote-control architecture and does not use the older `automation.remote_navigation_2` / `esphome.remote_button_pressed` event path as its primary control plane.

```text
Sticky touchscreen / physical buttons
        ↓
ESPHome encrypted native API
        ↓
Home Assistant actions already used by Basement Remote
        ↓
Apple TV / Sonos Arc / LG TV
```

The existing Home Assistant dashboard remains the behavioral reference and should not need modification.

## Home Assistant dependencies

Primary entities:

- `remote.basement_apple_tv`
- `media_player.basement_apple_tv`
- `media_player.basement_sonos_arc`
- `media_player.basement_tv`

The installed `custom:universal-remote-card` establishes the semantics mirrored by the Sticky:

- Navigation / remote keys: `remote.send_command` to `remote.basement_apple_tv`
- Power on: Apple TV command `wakeup`
- Power off: Apple TV command `suspend`
- Playback: Apple TV commands `play`, `pause`, `skip_backward`, and `skip_forward`
- Volume up/down: Apple TV commands `volume_up` / `volume_down`
- Mute: `media_player.volume_mute` on `media_player.basement_sonos_arc`
- TV power-state authority: `media_player.basement_tv`

Home Assistant must be configured to **Allow the device to perform Home Assistant actions** for this ESPHome integration.

## Current remote behavior

The 480×800 portrait face is text-free and uses pinned Heroicons v2.2.0 solid assets. There is deliberately **no on-screen power control** and no on-screen volume control.

### Physical buttons

- **AI / Power (GPIO4)**
  - Short press: wake the Sticky if sleeping and send Apple TV `wakeup`.
  - Long press (800 ms or longer): send Apple TV `suspend`.
  - The same short/long semantics apply whether the Sticky was already awake or GPIO4 just woke it from deep sleep.
- **Upper side button (GPIO5):** volume up, with hold-to-repeat.
- **Lower side button (GPIO6):** volume down, with hold-to-repeat.

A short AI-button press is never treated as a power toggle. If the TV is already on it simply requests `wakeup` again; it cannot accidentally turn the TV off. A long press is the explicit off gesture.

### Touchscreen

- D-pad: Up, Down, Left, Right
- Select: filled center button using Heroicons `cursor-arrow-ripple`
- Back: Heroicons `arrow-uturn-left`
- Home
- Skip backward
- Play
- Pause
- Skip forward
- Mute

The D-pad supports hold-to-repeat. Mute is white when the Sonos Arc is unmuted and inverts to black when muted. App launchers are intentionally omitted.

## TV-state sleep policy

Battery life is tied to the actual LG TV state rather than an idle timer:

- When `media_player.basement_tv` is confirmed **on**, the Sticky remains fully awake and responsive.
- When `media_player.basement_tv` is confirmed **off**, the Sticky waits briefly for state/display activity to settle and enters ESP32 deep sleep.
- `unknown` and `unavailable` are treated fail-safe: the Sticky stays awake instead of sleeping on an uncertain TV state.
- GPIO4 (AI / Power) is the only deep-sleep wake source.
- Touch power and the e-paper power rail are shut down before deep sleep; the e-paper image itself remains visible without continuous refresh power.
- On wake, the physical press is timed through button release before deciding whether it was a short ON press or a long OFF press.

### Deep-sleep limitation

While the ESP32 is in deep sleep, Wi-Fi and the Home Assistant API are off. Therefore, if the TV is turned on by some other remote while the Sticky is already sleeping, Home Assistant cannot wake the Sticky over the network. Press the Sticky's AI / Power button to wake it. This is intentional because keeping networking alive would give up most of the battery savings of deep sleep.

## Sticky hardware

| Function | GPIO |
| --- | ---: |
| PWR_HOLD | 45 |
| PWR_LOCK | 46 |
| AI / Power button | 4 |
| Volume Up button | 5 |
| Volume Down button | 6 |
| E-paper SCK | 13 |
| E-paper MOSI / SDI | 14 |
| E-paper CS | 15 |
| E-paper DC | 16 |
| E-paper RST | 17 |
| E-paper BUSY | 18 |
| E-paper EN | 47 |
| Touch SCL | 2 |
| Touch SDA | 3 |
| Touch INT | 21 |
| Touch RST | 41 |
| Touch EN | 42 |

**Touch bus note:** Seeed's current Sticky hardware documentation specifies **SCL = GPIO2 and SDA = GPIO3**. That is the assignment used in the firmware even though the original project notes had those two labels reversed.

The ESP32-S3 has 32 MB flash and 8 MB octal PSRAM. ESPHome's integrated display model `Seeed-reTerminal-Sticky` supplies the SSD1677 display pin/dimension defaults; the project still declares the shared SPI clock/data pins explicitly.

## Repository layout

```text
esphome/
  basement-remote-sticky.yaml          # Canonical GitHub-hosted ESPHome package
  device-builder-wrapper.example.yaml  # Tiny local Device Builder config example
  secrets.example.yaml                 # Secret key names only; no credentials
README.md
```

`esphome/basement-remote-sticky.yaml` is the source of truth. Device Builder should remain a small local wrapper that resolves secrets and imports that file directly from the repository's `main` branch.

## ESPHome Device Builder

Do not copy the full firmware into Device Builder.

Create an **Empty Configuration** named **Basement Remote Sticky**, then use the checked-in wrapper:

```yaml
substitutions:
  wifi_ssid: !secret wifi_ssid
  wifi_password: !secret wifi_password
  ota_password: !secret ota_password
  fallback_ap_password: !secret fallback_ap_password
  basement_remote_api_encryption_key: !secret basement_remote_api_encryption_key

packages:
  basement_remote:
    url: https://github.com/CitizenRacer/BasementRemote
    ref: main
    files:
      - esphome/basement-remote-sticky.yaml
    refresh: 60s
```

The required local secret names are documented in `esphome/secrets.example.yaml`. The actual API encryption key belongs only in Home Assistant's local ESPHome `secrets.yaml`; never commit it to this repository.

With `ref: main`, Device Builder pulls the production source from GitHub. `refresh: 60s` controls ESPHome's package-cache refresh during validation/build activity; it does not automatically flash the device when GitHub changes.

## Build and validation

This project targets **ESPHome 2026.8.2 or newer**.

GitHub Actions:

1. Installs ESPHome 2026.8.2.
2. Creates CI-only dummy secrets.
3. Builds a local package wrapper.
4. Runs `esphome config` validation.
5. Validates the production GitHub-backed wrapper on `main`.
6. Runs a full firmware compile.

Normal deployment flow:

1. Change firmware in GitHub.
2. Allow CI validation and compilation to pass.
3. Merge to `main`.
4. In ESPHome Device Builder, validate/install the small local wrapper.
5. Confirm the boot log contains `Basement Remote firmware 0.2.9 ready`.

## v0.2.9 test checklist

1. With the TV on, confirm the Sticky remains awake indefinitely.
2. Short-press the AI / Power button while the TV is on; verify the TV stays on.
3. Long-press AI / Power for at least 800 ms; verify Apple TV suspends and the LG TV turns off.
4. Confirm the Sticky subsequently disappears from Wi-Fi / Home Assistant as it enters deep sleep.
5. Short-press AI / Power while asleep; verify the Sticky wakes, reconnects to Home Assistant, and turns the Apple TV / TV on.
6. Confirm the remote stays awake after the LG state reports on.
7. Turn the TV off by another control path; confirm the Sticky enters deep sleep after the TV state is confirmed off.
8. Verify all touchscreen controls after the layout shift, especially the D-pad hit regions.
9. Verify the center Select control uses `cursor-arrow-ripple` and still sends Apple TV `select`.
10. Verify physical side-volume tap/hold and Sonos mute state/appearance.

## Safety / development policy

- GitHub `CitizenRacer/BasementRemote` is the canonical source of truth.
- Device Builder contains only the small package wrapper and local secrets; do not maintain a second full firmware copy there.
- Do not commit credentials or the actual ESPHome API encryption key.
- Do not modify the working Home Assistant Basement Remote dashboard unless a proven requirement emerges.
- Do not flash firmware that has not passed configuration validation and compilation.

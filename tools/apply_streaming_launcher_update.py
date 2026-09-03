from pathlib import Path
import sys

path = Path("esphome/basement-remote-sticky.yaml")
s = path.read_text()

if 'firmware_version: "0.2.10"' in s:
    print("Streaming launcher update already applied")
    sys.exit(0)


def replace_once(old: str, new: str, label: str) -> None:
    global s
    if old not in s:
        raise SystemExit(f"Expected block not found: {label}")
    s = s.replace(old, new, 1)

replace_once('firmware_version: "0.2.9"', 'firmware_version: "0.2.10"', 'firmware version')

replace_once(
'''  # Import the Sonos Arc mute attribute so the physical e-paper face reflects
  # the actual audio state even when mute changes somewhere else.
  - platform: homeassistant
    id: sonos_muted
    internal: true
    entity_id: media_player.basement_sonos_arc
    attribute: is_volume_muted
    on_state:
      then:
        - if:
            condition:
              lambda: |-
                const int new_state = x ? 1 : 0;
                return new_state != id(displayed_mute_state);
            then:
              - component.update: epaper_display

''',
'',
'mute state sensor')

replace_once(
'''  # Retain the last rendered mute face so a deep-sleep wake does not cause an
  # unnecessary full e-paper refresh when the Sonos state is unchanged.
  - id: displayed_mute_state
    type: int
    restore_value: true
    initial_value: "-1"

''',
'',
'displayed mute state')

replace_once(
'''  - id: sonos_toggle_mute
    mode: restart
    then:
      - logger.log: "Sonos Arc command: toggle mute"
      - homeassistant.action:
          action: media_player.volume_mute
          data:
            entity_id: media_player.basement_sonos_arc
          data_template:
            is_volume_muted: >-
              {{ not state_attr('media_player.basement_sonos_arc',
                                'is_volume_muted') }}

''',
'''  - id: apple_tv_launch_hulu
    mode: restart
    then:
      - logger.log: "Apple TV app: Hulu"
      - homeassistant.action:
          action: media_player.select_source
          data:
            entity_id: media_player.basement_apple_tv
            source: Hulu

  - id: apple_tv_launch_hbo_max
    mode: restart
    then:
      - logger.log: "Apple TV app: HBO Max"
      - homeassistant.action:
          action: media_player.select_source
          data:
            entity_id: media_player.basement_apple_tv
            source: HBO Max

  - id: apple_tv_launch_disney_plus
    mode: restart
    then:
      - logger.log: "Apple TV app: Disney+"
      - homeassistant.action:
          action: media_player.select_source
          data:
            entity_id: media_player.basement_apple_tv
            source: Disney+

  - id: apple_tv_launch_paramount_plus
    mode: restart
    then:
      - logger.log: "Apple TV app: Paramount+"
      - homeassistant.action:
          action: media_player.select_source
          data:
            entity_id: media_player.basement_apple_tv
            source: Paramount+

''',
'app launcher scripts')

replace_once(
'''      - id: icon_mute
        file: https://raw.githubusercontent.com/tailwindlabs/heroicons/v2.2.0/optimized/24/solid/speaker-x-mark.svg
''',
'''  # Streaming-service logos are rendered monochrome for the 1-bit e-paper.
  - platform: file
    defaults:
      type: BINARY
      transparency: chroma_key
    files:
      - id: logo_hulu
        file: https://upload.wikimedia.org/wikipedia/commons/f/f9/Hulu_logo_%282018%29.svg
        resize: 90x30
      - id: logo_hbo_max
        file: https://upload.wikimedia.org/wikipedia/commons/b/b3/HBO_Max_%282025%29.svg
        resize: 72x52
      - id: logo_disney_plus
        file: https://upload.wikimedia.org/wikipedia/commons/3/3e/Disney%2B_logo.svg
        resize: 82x44
      - id: logo_paramount_plus
        file: https://upload.wikimedia.org/wikipedia/commons/4/4e/Paramount%2B_logo.svg
        resize: 92x28
''',
'logo image definitions')

replace_once(
'''      rounded_rect(30, 135, 120, 110, 14);
      it.image(90, 190, id(icon_left), ImageAlign::CENTER, black, white);
      fill_rounded_rect(170, 135, 140, 110, 14, black);
      it.image(240, 190, id(icon_select), ImageAlign::CENTER, white, black);
      rounded_rect(330, 135, 120, 110, 14);
      it.image(390, 190, id(icon_right), ImageAlign::CENTER, black, white);
''',
'''      // Left/right are the same 180x90 control as up/down, rotated 90 deg.
      rounded_rect(45, 100, 90, 180, 14);
      it.image(90, 190, id(icon_left), ImageAlign::CENTER, black, white);
      fill_rounded_rect(170, 135, 140, 110, 14, black);
      it.image(240, 190, id(icon_select), ImageAlign::CENTER, white, black);
      rounded_rect(345, 100, 90, 180, 14);
      it.image(390, 190, id(icon_right), ImageAlign::CENTER, black, white);
''',
'left/right display geometry')

replace_once(
'''      // Volume is handled by the two physical side buttons. Mute is white
      // while sound is active and inverts to black when the Sonos Arc is muted.
      const bool muted = id(sonos_muted).has_state() && id(sonos_muted).state;
      id(displayed_mute_state) = muted ? 1 : 0;
      if (muted) {
        fill_rounded_rect(160, 665, 160, 100, 14, black);
        it.image(240, 715, id(icon_mute), ImageAlign::CENTER, white, black);
      } else {
        rounded_rect(160, 665, 160, 100, 14);
        it.image(240, 715, id(icon_mute), ImageAlign::CENTER, black, white);
      }
''',
'''      // Volume remains on the physical side buttons. The bottom row is
      // dedicated to one-touch Apple TV streaming-service launchers.
      rounded_rect(8, 665, 110, 100, 14);
      it.image(63, 715, id(logo_hulu), ImageAlign::CENTER, black, white);
      rounded_rect(126, 665, 110, 100, 14);
      it.image(181, 715, id(logo_hbo_max), ImageAlign::CENTER, black, white);
      rounded_rect(244, 665, 110, 100, 14);
      it.image(299, 715, id(logo_disney_plus), ImageAlign::CENTER, black, white);
      rounded_rect(362, 665, 110, 100, 14);
      it.image(417, 715, id(logo_paramount_plus), ImageAlign::CENTER, black, white);
''',
'launcher display row')

replace_once(
'''            } else if (x >= 30 && x < 150 && y >= 135 && y < 245) {
              id(touch_repeat_command) = 3;
              id(apple_tv_left).execute();
            } else if (x >= 330 && x < 450 && y >= 135 && y < 245) {
              id(touch_repeat_command) = 4;
              id(apple_tv_right).execute();
''',
'''            } else if (x >= 45 && x < 135 && y >= 100 && y < 280) {
              id(touch_repeat_command) = 3;
              id(apple_tv_left).execute();
            } else if (x >= 345 && x < 435 && y >= 100 && y < 280) {
              id(touch_repeat_command) = 4;
              id(apple_tv_right).execute();
''',
'left/right touch geometry')

replace_once(
'''              } else if (x >= 160 && x < 320 && y >= 665 && y < 765) {
                id(sonos_toggle_mute).execute();
''',
'''              } else if (x >= 8 && x < 118 && y >= 665 && y < 765) {
                id(apple_tv_launch_hulu).execute();
              } else if (x >= 126 && x < 236 && y >= 665 && y < 765) {
                id(apple_tv_launch_hbo_max).execute();
              } else if (x >= 244 && x < 354 && y >= 665 && y < 765) {
                id(apple_tv_launch_disney_plus).execute();
              } else if (x >= 362 && x < 472 && y >= 665 && y < 765) {
                id(apple_tv_launch_paramount_plus).execute();
''',
'launcher touch regions')

path.write_text(s)
print("Applied streaming launcher UI update")

# The tile catalogue

What a tile of each entity type can do lives in one place: `catalogue/`, one YAML file per type. The add-on, the
editor and the screen firmware all read it, so a rule is written once and cannot drift apart between them. Home
Assistant's own facts (feature flags, which action needs which flag) are read from Home Assistant's source code, never
copied by hand.

## How it fits together

```
catalogue/<type>.yaml       our options for one entity type: controls, displays, the small slider, taps, guards
catalogue/_tile.yaml        what every tile has: its taps, its named sizes, the hours a graph shows
catalogue/_ha.json          Home Assistant's facts for every type we have, read from its source (tools/read_ha_source.py)
        |
        |  tools/generate_catalogue.py (checks everything, then writes)
        v
screen_manager/app/catalogue.json        read by screen_manager/app/catalogue.py (the add-on)
web/src/model/catalogue.json             read by web/src/model/catalogue.ts (the editor)
components/smart_display/tile_catalogue.h  the firmware: the types it draws, Home Assistant's flags by name
```

At run time the add-on does not guess what a device can do. It asks the user's Home Assistant: the actions Home
Assistant lists for that entity (`get_services_for_target`), the fields of those actions, the entity's
`supported_features`, its attributes and its history. The catalogue only says what each of our options needs, in Home
Assistant's own terms, and the add-on matches the two.

Three questions are answered by the catalogue, the same way in Python and TypeScript:

1. **What may be chosen for an entity** (`offers`): the options of its type whose `needs` the entity meets. The editor
   shows only these.
2. **What a card of a given size draws** (`resolve_controls`): the chosen control or the type's default, and on a card
   one row high what fits there (`one_row`).
3. **What a screen gets** (`drawn_controls`): what that entity can draw (`fallback`) on that screen (`screen`, what the
   screen's firmware says it draws).

`tests/fixtures/catalogue-conformance.json` holds cases the add-on and the editor must answer alike;
`tests/test_catalogue.py` and `web/tests/catalogue.spec.ts` run them.

## The files are the list of types

A type exists in the add-on, the editor and the firmware only when it has a file in `catalogue/`. Home Assistant has
many more (valve, humidifier, water heater, lawn mower): none of them appears until someone adds its file, and that
comes after the firmware can draw it. `tools/read_ha_source.py` reads Home Assistant's facts only for types that have a
file; it never adds one.

## The keys of a type's file

```yaml
domain: climate               # the file's name without .yaml
firmware: 0.19.0              # the first firmware that draws this type; required for every type added after 0.4.32
displays:                     # the faces a tile of this type may have, in the order the editor offers them
  standard: {}
  forecast:
    needs: {features: [FORECAST_DAILY]}   # what the entity must have (see "needs")
    wide: true                            # only on a card of two columns or more
controls:                     # direct controls on a card; the first is the default on a card of more than one column
  setpoint:
    needs: {actions: [climate.set_temperature], features: [TARGET_TEMPERATURE, TARGET_TEMPERATURE_RANGE]}
    range:                                # a variant: when it holds, the screen needs more
      when: {features: [TARGET_TEMPERATURE_RANGE], unless: {features: [TARGET_TEMPERATURE]}}
      screen: {feature: climate_range, else: none}
    fallback: none                        # what is drawn when the entity lacks the features
  setpoint_mode:
    of: [setpoint, mode]                  # a pair: offered when both parts are; drawn as the part that is left
    rows: 2                               # needs a card two rows high
    screen: {firmware: 0.3.1}             # a hard requirement: the add-on asks for this firmware first
    one_row: setpoint                     # what a card one row high draws instead
inline:                       # the small slider beside the name
  needs: {actions: [{action: light.turn_on, field: brightness_pct}]}
toggle: {actions: [lock.lock]}   # what On / off as a tap needs; without this key: <domain>.toggle listed by Home Assistant
taps: [run]                   # taps of this type beyond every tile's
guards: [confirm, lock_only]  # a lock's guard choices
picture: {fit: [...], overlay: [...], refresh: [...]}   # how a live picture sits on its tile
key: false                    # may not stand as a key under the bedside clock
```

**`needs`**, what an entity must have:

- `actions`: any one of these actions listed by Home Assistant for the entity, optionally with a `field` Home Assistant
  offers for it.
- `features`: any one of these flags, checked where Home Assistant reports the entity's features. An entity that
  reports none (one that is unavailable) keeps what it may have.
- `attributes`: attributes that must be present.
- `history: line`: a history of numbers (a status sensor has none).
- `unless`: holds when this does not.

A variant's `when` is stricter than `needs`: it only holds on features Home Assistant does report.

**`screen`**, what a screen must have: `firmware` (a version), `feature` (a name in the list its hello message sends),
`pictures` (a board that draws pictures). With `else`, an older screen gets the `else` instead and nothing waits. Without
`else`, the requirement is hard: the add-on asks for a firmware update before it sends a layout that uses the option.

Every action and every feature a file names must be one Home Assistant has for that type (`catalogue/_ha.json`), every
control needs its words in the translations (`addon.labels.controls.<type>.<key>`), and every option another one names
must exist. `tools/generate_catalogue.py` stops on anything else.

## Adding an entity type

1. **The firmware first**: how a tile and its card draw the type (`components/smart_display`), with tests.
2. **The editor's mockup**: how the tile looks in the editor (`web/src/components/TileCard.vue`).
3. **Home Assistant's facts**: make sure `catalogue/_ha.json` has the type (see below).
4. **The file**: `catalogue/<type>.yaml` with `firmware:` set to the version from step 1, its displays and controls,
   and the words of its controls in `screen_manager/translations/en.json` (then the other languages).
5. Run `tools/generate_catalogue.py`, `python tests/catalogue_conformance.py`, add a case to
   `tests/test_layout_audit.py`, and run `tools/check.sh`.

## When Home Assistant changes

Home Assistant's code is written in Python 3.14, so the reader runs under it:

```sh
git clone --depth 1 https://github.com/home-assistant/core /tmp/ha-core
uv run --no-project --python 3.14 python tools/read_ha_source.py /tmp/ha-core
git diff catalogue/_ha.json
```

The diff is exactly what Home Assistant changed for our types: a new flag, an action that asks another flag, one that
is gone. `tools/generate_catalogue.py` then says which of our options name something that no longer exists.
`tools/check.sh` runs the same comparison when `HA_CORE` names a checkout.

## Updating keeps what people have

`tests/test_compat_0431.py` runs every tile the app of 0.4.31 could save (every type, size and option, on three grids)
through this app and compares with what that release stored and sent (`tests/fixtures/compat/golden-0.4.31.json.gz`):
every saved page loads, compiles to the same tiles, asks no newer firmware and keeps every setting, and a screen that
is not updated gets what it got before, apart from a listed, intended fix. `web/tests/compat-0431.spec.ts` checks the
editor loads the same pages. A change to the catalogue that breaks a saved layout fails these tests.

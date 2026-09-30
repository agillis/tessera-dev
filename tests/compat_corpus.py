"""The compatibility corpus (app 0.4.32): every kind of tile the app of 0.4.31 could store, run through an app's own code.

Someone who updates from the release that is live keeps what they have: their saved pages load, every tile keeps its
settings, and a screen that is not updated yet gets what it got before. This corpus proves it without a Home Assistant or
a screen. It builds one-tile layouts of every entity type (Home Assistant's demo entities in fixtures/compat/ha.json and
the edge cases the demo lacks, below), in every size, with every option the app of 0.4.31 offered, on three grids, and
runs them through an app:

    python tests/compat_corpus.py record <app dir> <golden.json.gz>   what that app stores and sends (the golden record)
    python tests/compat_corpus.py check <app dir> <golden.json.gz>    the same through this app, as JSON on stdout

`record` ran once against the app of 0.4.31 (the release before the tile catalogue); tests/test_compat_0431.py runs
`check` against this one and compares. The options are the ones of 0.4.31, frozen here: the corpus must not follow the
code it tests.
"""
import gzip
import inspect
import json
import sys
from itertools import count
from pathlib import Path

FIXTURE = Path(__file__).resolve().parent / 'fixtures/compat/ha.json'

# ---- What the app of 0.4.31 knew (core.DOMAINS, CONTROLS, DISPLAYS, ha_catalogue.INLINE), frozen ----
DOMAINS = ['alarm_control_panel', 'automation', 'binary_sensor', 'button', 'camera', 'climate', 'cover', 'fan', 'image',
           'input_boolean', 'input_button', 'input_number', 'input_select', 'light', 'lock', 'media_player', 'number',
           'person', 'scene', 'script', 'select', 'sensor', 'sun', 'switch', 'timer', 'vacuum', 'weather']
CONTROLS = {'climate': ['setpoint', 'mode', 'setpoint_mode'], 'switch': ['toggle'], 'input_boolean': ['toggle'],
            'automation': ['toggle', 'run'], 'light': ['toggle', 'brightness'], 'fan': ['toggle', 'speed'],
            'vacuum': ['buttons'], 'cover': ['buttons', 'position', 'tilt', 'buttons_tilt', 'position_tilt'],
            'media_player': ['volume', 'playback'], 'number': ['stepper', 'slider'], 'input_number': ['stepper', 'slider'],
            'select': ['stepper'], 'input_select': ['stepper'], 'timer': ['buttons'], 'scene': ['run'], 'script': ['run'],
            'button': ['run'], 'input_button': ['run']}
DISPLAYS = {'weather': ['standard', 'watch', 'forecast'], 'sensor': ['standard', 'watch', 'graph'],
            'screen': ['digital', 'analog', 'dial', 'flip'], 'sun': ['standard', 'watch', 'sunpath'],
            'camera': ['standard', 'live'], 'image': ['standard', 'live'], 'media_player': ['standard', 'watch', 'cover']}
INLINE = ['cover', 'fan', 'input_number', 'light', 'media_player', 'number']
SIZES = ['single', 'wide', 'tall', 'square', 'full']
TAPS = ['detail', 'toggle', 'none']
GRIDS = [(2, 3), (3, 3), (1, 4)]
PER_DOMAIN = 6   # demo entities per type; the edge cases below come on top

# ---- The edge cases Home Assistant's demo lacks: every way an entity can say less than the demo's ----
SYNTHETIC = {
    'climate.range_only': {'state': 'heat_cool', 'attributes': {'supported_features': 2 | 8 | 128 | 256, 'hvac_modes': ['off', 'heat_cool', 'cool'],
                                                                'current_temperature': 21, 'target_temp_low': 19, 'target_temp_high': 23,
                                                                'min_temp': 7, 'max_temp': 35, 'fan_modes': ['low', 'high'], 'fan_mode': 'low'}},
    'climate.both_in_range': {'state': 'heat_cool', 'attributes': {'supported_features': 3, 'hvac_modes': ['off', 'heat', 'heat_cool'],
                                                                   'current_temperature': 20, 'temperature': None, 'target_temp_low': 18,
                                                                   'target_temp_high': 22, 'min_temp': 7, 'max_temp': 35}},
    'climate.no_temperature': {'state': 'fan_only', 'attributes': {'supported_features': 8, 'hvac_modes': ['off', 'fan_only'],
                                                                   'fan_modes': ['low', 'high'], 'fan_mode': 'high', 'current_temperature': 22}},
    'climate.unknown_features': {'state': 'heat', 'attributes': {'temperature': 20, 'current_temperature': 19, 'hvac_modes': ['off', 'heat']}},
    'cover.no_position': {'state': 'open', 'attributes': {'supported_features': 1 | 2 | 8, 'device_class': 'garage'}},
    'cover.tilt_only': {'state': 'open', 'attributes': {'supported_features': 16 | 32 | 64 | 128, 'current_tilt_position': 40}},
    'cover.position_only': {'state': 'open', 'attributes': {'supported_features': 4, 'current_position': 60}},
    'light.onoff': {'state': 'on', 'attributes': {'supported_color_modes': ['onoff'], 'color_mode': 'onoff', 'supported_features': 0}},
    'light.dimmer': {'state': 'on', 'attributes': {'supported_color_modes': ['brightness'], 'color_mode': 'brightness', 'brightness': 128, 'supported_features': 0}},
    'fan.no_speed': {'state': 'on', 'attributes': {'supported_features': 16 | 32}},
    'media_player.no_volume': {'state': 'playing', 'attributes': {'supported_features': 1 | 16 | 32 | 16384, 'media_title': 'Song'}},
    'input_boolean.guest_mode': {'state': 'off', 'attributes': {'editable': True}},
    'input_select.house_mode': {'state': 'Home', 'attributes': {'options': ['Home', 'Away', 'Night'], 'editable': True}},
    'input_number.target_level': {'state': '40.0', 'attributes': {'min': 0, 'max': 100, 'step': 5, 'mode': 'slider', 'editable': True}},
    'input_button.doorbell_test': {'state': '2026-09-30T08:00:00+00:00', 'attributes': {'editable': True}},
    'scene.evening': {'state': '2026-09-30T08:00:00+00:00', 'attributes': {'entity_id': ['light.dimmer']}},
    'timer.egg': {'state': 'idle', 'attributes': {'duration': '0:05:00', 'editable': True}},
    'timer.laundry': {'state': 'active', 'attributes': {'duration': '1:00:00', 'remaining': '0:42:00', 'finishes_at': '2026-09-30T09:00:00+00:00'}},
    'automation.hall_lights': {'state': 'on', 'attributes': {'last_triggered': None, 'mode': 'single', 'current': 0, 'id': '1'}},
    'person.alex': {'state': 'home', 'attributes': {'editable': True, 'id': 'alex'}},
    'image.floor_map': {'state': '2026-09-30T08:00:00+00:00', 'attributes': {}},
    'sensor.washer_status': {'state': 'Rinsing', 'attributes': {}},
    'sensor.phone_battery': {'state': '54', 'attributes': {'unit_of_measurement': '%', 'device_class': 'battery', 'state_class': 'measurement'}},
    'binary_sensor.front_door': {'state': 'off', 'attributes': {'device_class': 'door'}},
    'weather.hourly_only': {'state': 'rainy', 'attributes': {'supported_features': 2, 'temperature': 12, 'temperature_unit': '°C'}},
    'lock.no_open': {'state': 'locked', 'attributes': {'supported_features': 0}},
    'alarm_control_panel.no_code': {'state': 'disarmed', 'attributes': {'supported_features': 1 | 2, 'code_format': None, 'code_arm_required': False}},
    'vacuum.basic': {'state': 'docked', 'attributes': {'supported_features': 8192 | 16 | 4096}},
}
BUILTINS = ['screen.clock', 'screen.settings']


def entities(states):
    """The entities of the corpus: up to PER_DOMAIN of each type from the demo, every edge case, and the built-in cards."""
    chosen, per = [], {}
    for entity in sorted(states):
        domain = entity.split('.', 1)[0]
        if domain in DOMAINS and per.get(domain, 0) < PER_DOMAIN and entity not in SYNTHETIC:
            per[domain] = per.get(domain, 0) + 1
            chosen.append(entity)
    return chosen + sorted(SYNTHETIC) + BUILTINS


def variants(entity):
    """Every option of 0.4.31 for this entity's type, one at a time: none, each control, each display, the small slider,
    the tap choices and a few of every tile (background, icon, second line)."""
    domain = entity.split('.', 1)[0]
    found = [{}]
    found += [{'controls': key} for key in CONTROLS.get(domain, []) + (['none'] if domain in CONTROLS else [])]
    found += [{'display': key} for key in DISPLAYS.get(domain, ['standard', 'watch'])]
    if domain in INLINE:
        found.append({'inline': 'slider'})
    if domain != 'screen':
        found += [{'tap': key} for key in TAPS]
        found += [{'background': 'none'}, {'icon': 'lightbulb'}, {'sub': 'none'}]
    if domain == 'sensor':
        found.append({'display': 'graph', 'history_hours': 6})
    return found


def cases(states):
    """(key, grid, tile) for every case of the corpus, in a fixed order."""
    for columns, rows in GRIDS:
        for entity in entities(states):
            for size in SIZES:
                for options in variants(entity):
                    tile = {'entity': entity, 'name': '', 'slot': 0, 'options': {'size': size, **options}}
                    key = f'{columns}x{rows} {entity} ' + json.dumps(tile['options'], sort_keys=True)
                    yield key, (columns, rows), tile


def load_app(app):
    """The app's own modules, from its directory, as it would import them."""
    sys.path.insert(0, str(Path(app).resolve()))
    import core, page_layout, layout_migrations, ha_catalogue  # noqa: E401
    return core, page_layout, layout_migrations, ha_catalogue


def screen_messages(core, compiled, states, features):
    """What a screen gets for each placed tile: its state message, cut to what that screen draws where this app does
    so (drawn_controls, app 0.4.32) for a screen whose hello said `features` (an empty set: firmware before 0.19.0)."""
    out = []
    for index, tile in enumerate(compiled):
        if 'in' in tile:
            continue
        message = core.state_message(index, tile, states)
        if hasattr(core, 'drawn_controls'):
            message = core.drawn_controls(message, features)
        out.append({key: message.get(key) for key in ('entity', 'name', 'state', 'a', 'o')})
    return out


def run(mode, app, golden=None):
    core, page_layout, layout_migrations, ha_catalogue = load_app(app)
    data = json.loads(FIXTURE.read_text())
    states = {**data['states'], **SYNTHETIC}
    services = data['services']
    capabilities = {}

    def caps(entity):
        if entity not in capabilities:
            state = states.get(entity) or {}
            actions = ha_catalogue.local_actions(services, entity, state.get('attributes') or {}, None)
            capabilities[entity] = ha_catalogue.capabilities(entity, actions, state, services)
        return capabilities[entity]

    results = {}
    recorded = golden['cases'] if golden else None
    for key, (columns, rows), tile in cases(states):
        grid = core.Grid(columns, rows)
        if mode == 'record':
            ids = count()
            try:
                record = layout_migrations.migrate_legacy({'title': 'Compat', 'tiles': [tile]}, grid, id_factory=lambda: f'{next(ids):016x}')
            except Exception as error:   # noqa: BLE001: whatever the app refused, and in its own words
                results[key] = {'refused': f'{type(error).__name__}: {error}'}
                continue
            document = record['layout']
        else:
            old = recorded.get(key)
            if old is None:
                continue
            if 'refused' in old:
                try:
                    layout_migrations.migrate_legacy({'title': 'Compat', 'tiles': [tile]}, grid)
                    results[key] = {'refused_before': True, 'accepted_now': True}
                except Exception:   # noqa: BLE001
                    results[key] = {'refused_before': True, 'accepted_now': False}
                continue
            try:
                document = page_layout.validate_document(json.loads(json.dumps(old['document'])), grid)
            except Exception as error:   # noqa: BLE001
                results[key] = {'broken': f'{type(error).__name__}: {error}'}
                continue
        compiled = page_layout.compile_tiles(document, grid)
        flat = {'title': document['title'], 'tiles': compiled}
        placed = [t for t in compiled if 'in' not in t]
        results[key] = {
            'document': document if mode == 'record' else None,
            'compiled': compiled,
            'min_firmware': list(core.min_firmware(flat) or ()),
            'old_screen': screen_messages(core, compiled, states, frozenset()),
            'unsupported': [ha_catalogue.unsupported(t, t, caps(t['entity'])) for t in placed if not t['entity'].startswith('screen.')],
        }
    return {'app': str(app), 'cases': results, 'capabilities': capabilities}


if __name__ == '__main__':
    mode, app, path = sys.argv[1], sys.argv[2], Path(sys.argv[3])
    if mode == 'record':
        output = run('record', app)
        with gzip.open(path, 'wt', encoding='utf-8') as handle:
            json.dump(output, handle, sort_keys=True, separators=(',', ':'))
        refused = sum('refused' in case for case in output['cases'].values())
        print(f'{len(output["cases"])} cases, {refused} refused by that app, written to {path}', file=sys.stderr)
    else:
        with gzip.open(path, 'rt', encoding='utf-8') as handle:
            golden = json.load(handle)
        json.dump(run('check', app, golden), sys.stdout, sort_keys=True, separators=(',', ':'))

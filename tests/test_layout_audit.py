"""The geometry of every card on every glass, without drawing a picture (app 0.4.32).

The firmware's own layout code (runtime_tiles.h with LVGL, built to WebAssembly for the editor's preview) lays out
each card the way a screen does; web/wasm/layout_audit.mjs asks it where every object, text and control ended up
(preview_layout). This test builds the layouts, one card a page, for every board lying down and standing up, every
kind of card, every size the grid takes (the five names and its spans) and a short and a very long name, with the
options the app sends a screen (core.screen_options), and checks what the renders were for:

- nothing leaves its card, and no card leaves the glass or runs into another;
- no two texts of a card lie over each other;
- a text wider than its line has dots or rolls by (a marquee), never a hard cut; a line fits its box's height, and
  wrapped text fits its box;
- a text keeps a margin from its card's edge;
- a full page of cards (every cell a card, and every row one wide card) lays out without one running into another.

The checks themselves are tested on made-up reports below (Checks), so a check that can never fail shows up.

It needs Node and web/src/wasm/firmware_preview.wasm (web/wasm/build.sh); without them it is skipped.
LAYOUT_AUDIT_BOARDS=cyd,guition limits the boards; LAYOUT_AUDIT_OUT=<file> keeps the raw report.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'screen_manager/app'))
from core import Grid, screen_options, span_offered  # noqa: E402

WASM = ROOT / 'web/src/wasm/firmware_preview.wasm'
SHORT, LONG = 'Lamp', 'The ceiling light above the long dining table in the back room'
# One of each kind of card, with what Home Assistant says about it. `displays`: faces to try besides the standard one.
KINDS = {
    'light': ('light.audit', 'on', {'brightness': 200, 'color_mode': 'brightness', 'supported_color_modes': ['brightness']}, ()),
    'switch': ('switch.audit', 'on', {}, ()),
    'climate': ('climate.audit', 'heat', {'current_temperature': 20.5, 'temperature': 21.5, 'hvac_modes': ['off', 'heat', 'cool', 'auto'],
                                          'min_temp': 7, 'max_temp': 35, 'target_temp_step': 0.5, 'supported_features': 385}, ()),
    'climate-range': ('climate.range', 'heat_cool', {'current_temperature': 73, 'target_temp_low': 70, 'target_temp_high': 75,
                                                     'target_temp_step': 1, 'hvac_modes': ['off', 'heat_cool', 'cool'],
                                                     'min_temp': 45, 'max_temp': 95, 'supported_features': 442}, ()),
    'climate-range-halves': ('climate.halves', 'heat_cool', {'current_temperature': 21.5, 'target_temp_low': 19.5, 'target_temp_high': 23,
                                                             'target_temp_step': 0.5, 'hvac_modes': ['off', 'heat_cool'], 'min_temp': 7,
                                                             'max_temp': 35, 'supported_features': 442}, ()),
    # A thermostat's modes on their own and under its -/+ (firmware 0.19.0: one bar, climate_tile::bar_room), six of them.
    'climate-modes': ('climate.modes', 'cool', {'current_temperature': 73, 'target_temp_low': 61, 'target_temp_high': 75,
                                                'hvac_modes': ['off', 'cool', 'heat_cool', 'auto', 'dry', 'fan_only'],
                                                'min_temp': 45, 'max_temp': 95, 'target_temp_step': 1, 'supported_features': 442}, ()),
    'climate-both': ('climate.both', 'heat', {'current_temperature': 20.5, 'temperature': 21.5,
                                              'hvac_modes': ['off', 'heat', 'cool', 'heat_cool', 'auto', 'dry', 'fan_only'],
                                              'min_temp': 7, 'max_temp': 35, 'target_temp_step': 0.5, 'supported_features': 387}, ()),
    'media': ('media_player.audit', 'playing', {'media_title': 'A remarkably long title for a song that keeps going on',
                                               'media_artist': 'An artist with a long name as well', 'volume_level': 0.3,
                                               'supported_features': 8321599}, ()),
    'sensor': ('sensor.audit', '21.4', {'unit_of_measurement': '°C', 'device_class': 'temperature'}, ('big',)),
    'cover': ('cover.audit', 'open', {'current_position': 70, 'supported_features': 15}, ()),
    'vacuum': ('vacuum.audit', 'docked', {'battery_level': 80, 'supported_features': 30524}, ()),
    'person': ('person.audit', 'home', {}, ()),
    'scene': ('scene.audit', 'scening', {}, ()),
}


def boards():
    """The glass and grids of every board as the editor's preview has them, one per distinct shape and density."""
    shapes = json.loads((ROOT / 'screen_manager/app/boards.json').read_text())
    wanted = [key for key in os.environ.get('LAYOUT_AUDIT_BOARDS', '').split(',') if key]
    seen, found = set(), []
    for key, shape in shapes.items():
        if key.startswith('checkout/') or key.startswith('packages/') or (wanted and key not in wanted):
            continue
        for side in ('landscape', 'portrait'):
            o = shape['orientations'].get(side)
            if not o:
                continue
            shape_key = (o['width'], o['height'], o['columns'], o['rows'], shape['dpi'])
            if shape_key in seen:
                continue
            seen.add(shape_key)
            found.append({'key': f'{key}-{side}', 'width': o['width'], 'height': o['height'], 'columns': o['columns'],
                          'rows': o['rows'], 'dpi': shape['dpi']})
    return found


def sizes(grid):
    """The five names this grid takes, and its spans."""
    out = ['single']
    if grid.columns >= 2: out.append('wide')
    if grid.rows >= 2: out.append('tall')
    if grid.columns >= 2 and grid.rows >= 2: out.append('square')
    out.append('full')
    out += [f'{c}x{r}' for c in range(1, grid.columns + 1) for r in range(1, grid.rows + 1) if span_offered(c, r, grid)]
    return out


# The control a kind is laid out with where it is not its type's default.
CONTROLS = {'climate-modes': 'mode', 'climate-both': 'setpoint_mode'}


def message(kind, size, name, display=None):
    entity, state, attrs, _ = KINDS[kind]
    options = {'size': size, **({'display': display} if display else {}), **({'controls': CONTROLS[kind]} if kind in CONTROLS else {})}
    tile = {'entity': entity, 'name': name, 'slot': 0, 'options': options}
    return {'entity': entity, 'name': name, 'state': state, 'a': attrs, 'o': screen_options(tile, attrs, state) or {}, 'slot': 0}


def layouts(screen):
    grid = Grid(screen['columns'], screen['rows'])
    out = []
    for kind, (_, _, _, displays) in KINDS.items():
        for display in (None, *displays):
            for size in sizes(grid):
                for name in (SHORT, LONG):
                    out.append({'key': f'{kind}{"-" + display if display else ""} {size} {"long" if name == LONG else "short"}',
                                'tiles': [message(kind, size, name, display)]})
    # Full pages: a card in every cell, and one wide card a row, the kinds taking turns, every name the long one.
    kinds = list(KINDS)
    cells = grid.columns * grid.rows
    out.append({'key': 'every cell', 'tiles': [{**message(kinds[i % len(kinds)], 'single', LONG), 'slot': i} for i in range(cells)]})
    if grid.columns >= 2:
        out.append({'key': 'wide rows', 'tiles': [{**message(kinds[i % len(kinds)], 'wide', LONG), 'slot': i * grid.columns}
                                                  for i in range(grid.rows)]})
    return out


def inside(inner, outer, slack=1):
    return (inner['x1'] >= outer['x1'] - slack and inner['y1'] >= outer['y1'] - slack
            and inner['x2'] <= outer['x2'] + slack and inner['y2'] <= outer['y2'] + slack)


def overlap(a, b):
    return a['x1'] <= b['x2'] and b['x1'] <= a['x2'] and a['y1'] <= b['y2'] and b['y1'] <= a['y2']


MARGIN = 2  # px a text keeps from its card's edge


def problems(report):
    """What is wrong in one layout's report, as readable lines."""
    found = []
    objects = {o['id']: o for o in report.get('objects', [])}
    glass = {'x1': 0, 'y1': 0, 'x2': report['width'] - 1, 'y2': report['height'] - 1}
    cards = report.get('cards', [])
    for card in cards:
        box = objects[card['object']]
        if not inside(box, glass):
            found.append(f"card {card['entity']} leaves the glass")
        members = [o for o in objects.values() if o['card'] == cards.index(card) and o['id'] != card['object']]
        # A picture may be cut to its card on purpose (a camera, an album cover filling it): only what is not.
        for o in members:
            if o['type'] != 'image' and o['x2'] > o['x1'] and o['y2'] > o['y1'] and not inside(o, box):
                what = f"text '{o['text'][:30]}'" if o['type'] == 'label' else o['type']
                found.append(f"{what} leaves its card by {max(box['x1'] - o['x1'], o['x2'] - box['x2'], box['y1'] - o['y1'], o['y2'] - box['y2'])} px")
        for o in members:
            parent = objects.get(o['parent'])
            if parent and parent['id'] != box['id'] and parent['clips'] and o['type'] != 'image' and not inside(o, parent):
                what = f"text '{o['text'][:30]}'" if o['type'] == 'label' else o['type']
                found.append(f"{what} is cut by its {parent['type']}")
        texts = [o for o in members if o['type'] == 'label' and o['text'].strip() and not o['icon']]
        for o in texts:
            edge = min(o['x1'] - box['x1'], box['x2'] - o['x2'], o['y1'] - box['y1'], box['y2'] - o['y2'])
            if edge < MARGIN:
                found.append(f"text '{o['text'][:30]}' is {edge} px from its card's edge")
            if 0 < o['content_height'] < o['line_height'] - 1:
                found.append(f"text '{o['text'][:30]}' is cut at the bottom ({o['content_height']} of {o['line_height']} px)")
        for i, a in enumerate(texts):
            for b in texts[i + 1:]:
                if overlap(a, b):
                    found.append(f"texts '{a['text'][:24]}' and '{b['text'][:24]}' lie over each other")
        for o in texts:
            if o['mode'] in ('clip', 'wrap') and '\n' not in o['text']:
                if o['mode'] == 'clip' and o['text_width'] > o['content_width'] + 1:
                    found.append(f"text '{o['text'][:30]}' is cut without dots ({o['text_width']} of {o['content_width']} px)")
                if o['mode'] == 'wrap' and o['wrapped_height'] > o['content_height'] + 1 and o['content_height'] > 0:
                    found.append(f"wrapped text '{o['text'][:30]}' is higher than its box ({o['wrapped_height']} of {o['content_height']} px)")
    for i, a in enumerate(cards):
        for b in cards[i + 1:]:
            if overlap(objects[a['object']], objects[b['object']]):
                found.append(f"cards {a['entity']} and {b['entity']} run into each other")
    return found


def label(ident, text, box, **more):
    x1, y1, x2, y2 = box
    return {'id': ident, 'parent': 1, 'card': 0, 'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2, 'clips': True, 'type': 'label',
            'text': text, 'mode': 'dots', 'text_width': x2 - x1, 'content_width': x2 - x1 + 1, 'content_height': y2 - y1 + 1,
            'line_height': y2 - y1 + 1, 'wrapped_height': y2 - y1 + 1, 'icon': False, **more}


def report(*objects, cards=((0, 0, 99, 59),)):
    boxes = [{'id': 1 + i * 100, 'parent': 0, 'card': i, 'x1': c[0], 'y1': c[1], 'x2': c[2], 'y2': c[3], 'clips': True,
              'type': 'object'} for i, c in enumerate(cards)]
    return {'width': 320, 'height': 240, 'objects': [*boxes, *objects],
            'cards': [{'object': b['id'], 'entity': f'light.{i}'} for i, b in enumerate(boxes)]}


class Checks(unittest.TestCase):
    """Each check finds what it is there for, and a good card passes them all."""

    def test_a_good_card_passes(self):
        self.assertEqual(problems(report(label(2, 'Lamp', (10, 10, 60, 25)), label(3, 'On', (10, 30, 60, 45)))), [])

    def test_each_fault_is_found(self):
        faults = {
            'leaves its card': label(2, 'Lamp', (10, 10, 120, 25)),
            'lie over each other': [label(2, 'Lamp', (10, 10, 60, 25)), label(3, 'On', (10, 20, 60, 35))],
            'cut without dots': label(2, 'Lamp', (10, 10, 60, 25), mode='clip', text_width=80),
            'higher than its box': label(2, 'Lamp', (10, 10, 60, 25), mode='wrap', wrapped_height=40),
            "from its card's edge": label(2, 'Lamp', (1, 10, 60, 25)),
            'cut at the bottom': label(2, 'Lamp', (10, 10, 60, 25), line_height=24),
            'is cut by its': [{'id': 5, 'parent': 1, 'card': 0, 'x1': 10, 'y1': 10, 'x2': 40, 'y2': 40, 'clips': True, 'type': 'object'},
                              label(6, 'Lamp', (20, 20, 60, 30), parent=5)],
        }
        for words, objects in faults.items():
            with self.subTest(words):
                found = problems(report(*(objects if isinstance(objects, list) else [objects])))
                self.assertTrue(any(words in line for line in found), found)
        self.assertTrue(any('leaves the glass' in line for line in problems(report(cards=((300, 0, 399, 59),)))))
        self.assertTrue(any('run into each other' in line for line in problems(report(cards=((0, 0, 99, 59), (50, 0, 149, 59))))))


@unittest.skipUnless(shutil.which('node') and WASM.exists(), 'needs Node and the firmware preview (web/wasm/build.sh)')
class LayoutAudit(unittest.TestCase):
    maxDiff = None

    @classmethod
    def setUpClass(cls):
        screens = boards()
        for screen in screens:
            screen['layouts'] = layouts(screen)
        with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False) as f:
            json.dump(screens, f)
        try:
            run = subprocess.run(['node', str(ROOT / 'web/wasm/layout_audit.mjs'), f.name], capture_output=True, text=True, timeout=1800)
        finally:
            os.unlink(f.name)
        if run.returncode:
            raise RuntimeError(run.stderr[-2000:])
        cls.reports = json.loads(run.stdout)
        if os.environ.get('LAYOUT_AUDIT_OUT'):
            Path(os.environ['LAYOUT_AUDIT_OUT']).write_text(json.dumps(cls.reports))

    def test_every_layout_was_laid_out(self):
        self.assertTrue(self.reports)
        self.assertEqual([r for r in self.reports if 'error' in r], [])
        # Every layout drew its card: an empty page means the firmware refused it.
        empty = [f"{r['screen']}: {r['layout']}" for r in self.reports if not r.get('cards')]
        self.assertEqual(empty, [])

    def test_nothing_leaves_its_card_or_runs_into_another(self):
        found = {f"{r['screen']}: {r['layout']}": p for r in self.reports if (p := problems(r))}
        self.assertEqual(found, {})


if __name__ == '__main__':
    unittest.main()

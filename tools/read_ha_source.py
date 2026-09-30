"""Home Assistant's own facts for the tile catalogue, read from its source (app 0.4.32).

    python tools/read_ha_source.py <home-assistant/core checkout>            writes catalogue/_ha.json
    python tools/read_ha_source.py <checkout> --check                        fails when catalogue/_ha.json differs

For every entity type the catalogue has (catalogue/*.yaml), it reads with Python's own parser, never by hand:

- the type's feature flags: the `*EntityFeature(IntFlag)` class in homeassistant/components/<type>/const.py (or its
  __init__.py), name and bit;
- the actions Home Assistant registers for its entities and the flags it asks of an entity for each: every
  `async_register_entity_service(SERVICE, schema, func, [flags])` and `async_register_platform_entity_service(...,
  required_features=[flags])` call in the type's own files, the SERVICE constant resolved to its name. A flag list reads
  as Home Assistant reads it: any one item, and every flag of an item joined by `|`.

catalogue/_ha.json is what tools/generate_catalogue.py checks every file against: an action or a flag the catalogue names
that Home Assistant does not have stops it. Home Assistant updated: run this against the new checkout, and the change to
catalogue/_ha.json is exactly what Home Assistant changed. docs/CATALOGUE.md says more.
"""
import ast
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'catalogue/_ha.json'
REGISTER = {'async_register_entity_service', 'async_register_platform_entity_service'}


def constants(tree):
    """Module-level NAME = "text" (and NAME: Final = "text") assignments."""
    found = {}
    for node in tree.body:
        targets, value = ([node.target], node.value) if isinstance(node, ast.AnnAssign) else (node.targets, node.value) if isinstance(node, ast.Assign) else ([], None)
        if isinstance(value, ast.Constant) and isinstance(value.value, str):
            for target in targets:
                if isinstance(target, ast.Name):
                    found[target.id] = value.value
    return found


def feature_enum(folder):
    """(class name, {flag: bit}) of the type's *EntityFeature IntFlag, or (None, {})."""
    for name in ('const.py', '__init__.py'):
        path = folder / name
        if not path.exists():
            continue
        for node in ast.parse(path.read_text()).body:
            if isinstance(node, ast.ClassDef) and node.name.endswith('EntityFeature'):
                bits = {}
                for item in node.body:
                    if isinstance(item, ast.Assign) and isinstance(item.value, ast.Constant) and isinstance(item.value.value, int):
                        bits[item.targets[0].id] = item.value.value
                return node.name, bits
    return None, {}


def flag_names(node):
    """The flags of one item of a required-features list: X.A, or X.A | X.B."""
    if isinstance(node, ast.Attribute):
        return [node.attr]
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
        return flag_names(node.left) + flag_names(node.right)
    raise ValueError(f'unexpected feature expression {ast.dump(node)[:80]}')


def service_name(node, known):
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Name) and node.id in known:
        return known[node.id]
    if isinstance(node, ast.Attribute) and node.attr in known:
        return known[node.attr]
    return None


def imported_constants(tree, components):
    """The constants a module imports from another component (input_select takes select's action names)."""
    found = {}
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and (node.module or '').startswith('homeassistant.components.'):
            other = components / node.module.split('.')[2]
            for name in ('const.py', '__init__.py'):
                if (other / name).exists():
                    found.update(constants(ast.parse((other / name).read_text())))
    return found


def registered_actions(folder, known, components):
    """{action: [[flag, ...], ...]} for every action the type registers: its entity actions with the flags they ask,
    and the actions it registers for its own domain (a script's turn_on), which ask none."""
    actions = {}
    for path in sorted(folder.glob('*.py')):
        tree = ast.parse(path.read_text())
        local = {**known, **imported_constants(tree, components), **constants(tree)}
        for node in ast.walk(tree):
            # hass.services.async_register(DOMAIN, SERVICE, handler, ...): an action of the domain, no flags asked.
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == 'async_register' \
                    and len(node.args) >= 2 and isinstance(node.args[0], ast.Name) and node.args[0].id == 'DOMAIN':
                name = service_name(node.args[1], local)
                if name is not None:
                    actions.setdefault(name, [])
                continue
            if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in REGISTER
                    or isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in REGISTER):
                continue
            called = node.func.attr if isinstance(node.func, ast.Attribute) else node.func.id
            keywords = {item.arg: item.value for item in node.keywords}
            if called == 'async_register_entity_service':
                name_node = node.args[0] if node.args else keywords.get('name')
                features = node.args[3] if len(node.args) > 3 else keywords.get('required_features')
            else:   # async_register_platform_entity_service(hass, DOMAIN, SERVICE, *, ..., required_features=...)
                name_node = node.args[2] if len(node.args) > 2 else keywords.get('service_name') or keywords.get('service')
                features = keywords.get('required_features')
            name = service_name(name_node, local)
            if name is None:
                continue
            items = [flag_names(item) for item in features.elts] if isinstance(features, (ast.List, ast.Tuple)) else []
            actions[name] = items
    return actions


def read(core):
    """{domain: {'enum': ..., 'features': {...}, 'actions': {...}}} for every type of the catalogue."""
    components = core / 'homeassistant/components'
    shared = constants(ast.parse((core / 'homeassistant/const.py').read_text()))
    domains = sorted(path.stem for path in (ROOT / 'catalogue').glob('*.yaml') if not path.name.startswith('_') and path.stem != 'screen')
    facts = {}
    for domain in domains:
        folder = components / domain
        own = {}
        for name in ('const.py', '__init__.py'):
            if (folder / name).exists():
                own.update(constants(ast.parse((folder / name).read_text())))
        enum, bits = feature_enum(folder)
        facts[domain] = {'enum': enum, 'features': bits, 'actions': dict(sorted(registered_actions(folder, {**shared, **own}, components).items()))}
    return facts


def output(core):
    commit = subprocess.run(['git', '-C', str(core), 'log', '-1', '--format=%h %cs'], capture_output=True, text=True).stdout.strip()
    version = next((line.split('=')[1].strip().strip('"') for line in (core / 'pyproject.toml').read_text().splitlines()
                    if line.startswith('version')), '?')
    return json.dumps({'source': f'home-assistant/core {version} ({commit})', 'domains': read(core)}, indent=1, sort_keys=True) + '\n'


if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    text = output(Path(sys.argv[1]).resolve())
    if '--check' in sys.argv:
        if not OUTPUT.exists() or json.loads(OUTPUT.read_text())['domains'] != json.loads(text)['domains']:
            sys.exit('catalogue/_ha.json differs from this Home Assistant: run tools/read_ha_source.py without --check and read the change.')
    else:
        OUTPUT.write_text(text)
        print(f'wrote {OUTPUT.relative_to(ROOT)}')

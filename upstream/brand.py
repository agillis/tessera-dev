#!/usr/bin/env python3
"""Tessera Dev's own identity: what tells this project apart from the one it came from.

Two kinds of change live here, and neither may ever go upstream:

- **The name Home Assistant shows.** The add-on's `name` and `panel_title` in screen_manager/config.yaml and the
  repository's `name` in repository.yaml, so the store, the add-on page and the sidebar all say Tessera Dev.
- **Where everything comes from and goes to.** The repository a screen's firmware is built from (core.REPO, which the
  entry generator and the add-on both read since the commit that put it in one place), the Docker image, the
  repository the docs tell people to add to Home Assistant, and the website the feedback card would post to, which is
  the upstream project's and must not receive this fork's installations.

    python3 upstream/brand.py            make this checkout Tessera Dev
    python3 upstream/brand.py --check    say whether it is (exit 1 when it is not, for a hook or CI)
    python3 upstream/brand.py --remove   put upstream's identity back, for a branch that goes upstream

Both directions are the same tables read the other way, so this is safe to run twice and after a rebase: it says what
it changed and leaves alone what is already the way it wants it. packages/<board>.yaml is not edited here: it is
generated from core.REPO, so this runs tools/generate_entries.py afterwards. upstream/README.md is the whole procedure.
"""
import argparse
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]

UPSTREAM_SLUG = 'MaxGramser/homeassistant_espscreen'
FORK_SLUG = 'agillis/tessera-dev'

# (file, what upstream says, what this fork says). The text has to be unique in the file: an exact swap keeps the rest
# of the line, and the comments and the order of the YAML, as they are.
BRANDING = [
    ('repository.yaml', 'name: Tessera\n', 'name: Tessera Dev\n'),
    ('repository.yaml', 'url: https://tessera-maxgramser.on-forge.com\n',
     f'url: https://github.com/{FORK_SLUG}\n'),
    ('repository.yaml', 'maintainer: MaxGramser\n', 'maintainer: agillis\n'),
    ('screen_manager/config.yaml', 'name: Tessera Screen Manager\n', 'name: Tessera Dev Screen Manager\n'),
    ('screen_manager/config.yaml', 'panel_title: Tessera\n', 'panel_title: Tessera Dev\n'),
    ('screen_manager/config.yaml',
     'description: "Tessera: touch screens for Home Assistant.',
     'description: "Tessera Dev: touch screens for Home Assistant.'),
    # The screens build their firmware from this repository, so a firmware change here reaches them once it is pushed.
    ('screen_manager/app/core.py', f"REPO = 'https://github.com/{UPSTREAM_SLUG}'",
     f"REPO = 'https://github.com/{FORK_SLUG}'"),
    # The feedback card shares an answer about a board with a website. Upstream's is not this fork's to write to, and
    # this fork has none, so there is no endpoint and the card never asks (screen_manager/app/feedback.py).
    ('screen_manager/app/feedback.py', "API = 'https://tessera-maxgramser.on-forge.com/api/v1/addon'",
     "API = ''  # Tessera Dev has no website of its own, and upstream's is not this fork's to write to"),
    ('screen_manager/app/feedback.py', "PRIVACY_URL = 'https://tessera-maxgramser.on-forge.com/privacy'",
     "PRIVACY_URL = ''"),
    # A pull request goes out under the owner's own account; the release workflow must not commit as upstream's.
    ('.github/workflows/preview.yml', 'git config user.email "maxgramser@gmail.com"',
     'git config user.email "41898282+github-actions[bot]@users.noreply.github.com"'),
    # Upstream's donation link is upstream's.
    ('.github/FUNDING.yml', 'custom: ["https://buymeacoffee.com/f5j9jnkmhpv"]\n', '# Tessera Dev takes no funding.\n'),
]

# Files where a plain reference to the repository is this fork's own: the Docker image and compose guide, the docs
# that say which repository to add to Home Assistant, and the issue template's link. The slug appears in GitHub URLs
# as owner/name and in the image name in lower case.
URL_FILES = ('docker/compose.yaml', 'README.md', 'docs/EASY_SETUP.md', '.github/ISSUE_TEMPLATE/config.yml')
SLUGS = ((UPSTREAM_SLUG, FORK_SLUG), (UPSTREAM_SLUG.lower(), FORK_SLUG.lower()))


def entries(remove):
    """Every (path, from, to) this run would apply, in both kinds."""
    for name, upstream, fork in BRANDING:
        yield name, (fork if remove else upstream), (upstream if remove else fork)
    for name in URL_FILES:
        for upstream, fork in SLUGS:
            yield name, (fork if remove else upstream), (upstream if remove else fork)


def swap(remove):
    """Apply this fork's identity, or take it off. Returns (changed, problems) as lists of lines to print."""
    changed, problems = [], []
    for name, source, target in entries(remove):
        path = ROOT / name
        text = path.read_text(encoding='utf-8')
        if source not in text:
            continue                                    # already the way we want it, or not in this file
        path.write_text(text.replace(source, target), encoding='utf-8')
        changed.append(f'{name}: {source.strip()[:60]} -> {target.strip()[:60]}')
    # packages/<board>.yaml is generated from core.REPO: rewrite it rather than edit fourteen files here.
    if changed:
        subprocess.run([sys.executable, str(ROOT / 'tools/generate_entries.py')], check=True, cwd=ROOT,
                       stdout=subprocess.DEVNULL)
        changed.append('packages/<board>.yaml: written again from core.REPO')
    return changed, problems


def check():
    """0 when nothing in this checkout still says upstream, 1 otherwise. A line that is already this fork's, and a
    file that never mentioned the repository, both say nothing."""
    left = []
    for name, source, target in entries(remove=False):
        text = (ROOT / name).read_text(encoding='utf-8')
        if source in text:
            left.append(f'{name}: {source.strip()[:70]}')
    for line in left:
        print(f'still upstream: {line}')
    print('branded as Tessera Dev' if not left else 'run python3 upstream/brand.py')
    return 1 if left else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--check', action='store_true', help='only say whether this fork owns this checkout')
    group.add_argument('--remove', action='store_true', help="put upstream's identity back, for a pull request branch")
    args = parser.parse_args()
    if args.check:
        return check()
    changed, problems = swap(args.remove)
    for line in changed:
        print(line)
    for line in problems:
        print(line, file=sys.stderr)
    if not changed:
        print('nothing to do: already ' + ('upstream' if args.remove else 'Tessera Dev'))
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main())

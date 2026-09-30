"""Disposable editor hints learned from real firmware handshakes.

This cache never restores a delivery session. Every connection still negotiates
with the running firmware. Missing or corrupt cache data only restricts offline
editing until the next handshake; it cannot affect the saved page document.
"""
import json
import re
import logging
import os
from pathlib import Path
import tempfile

LOG = logging.getLogger('screen_manager')
SIZES = {'single', 'wide', 'full', 'tall', 'square'}
# A span such as "3x2" (firmware 0.19.0, app 0.4.32): the sizes a screen's grid takes besides the names.
SPAN = re.compile(r'^[1-9]x[1-9]$')

def known_size(size):
    return isinstance(size, str) and (size in SIZES or SPAN.match(size) is not None)


def identity(screen):
    return {key: screen.get(key) for key in ('device_id', 'firmware_known', 'node', 'board', 'shape')
            if screen.get(key) not in (None, '', 'unknown', 'unavailable')}


class CapabilityCache:
    def __init__(self, path):
        self.path = Path(path)
        try:
            data = json.loads(self.path.read_text())
            self.records = data['screens'] if data.get('version') == 1 and isinstance(data.get('screens'), dict) else {}
        except (OSError, ValueError, AttributeError, TypeError):
            self.records = {}

    def restore(self, inbox, screen, sender):
        record = self.records.get(inbox)
        current = identity(screen)
        if not current.get('device_id') or not isinstance(record, dict): return
        saved = record.get('identity')
        if not isinstance(saved, dict) or any(saved.get(key) != value for key, value in current.items()): return
        protocol, sizes = record.get('protocol'), record.get('sizes')
        if type(protocol) is not int or protocol not in (1, 2) or not isinstance(sizes, list): return
        if not all(known_size(size) for size in sizes): return
        sender.last_protocol, sender.last_tile_sizes = protocol, set(sizes)

    def remember(self, inbox, screen, sender):
        marker = identity(screen)
        if not marker.get('device_id') or sender.protocol not in (1, 2): return
        record = {'identity': marker, 'protocol': sender.protocol, 'sizes': sorted(size for size in sender.tile_sizes if known_size(size))}
        if self.records.get(inbox) == record: return
        self.records[inbox] = record
        self._save()

    def forget(self, inbox):
        if self.records.pop(inbox, None) is not None: self._save()

    def _save(self):
        temporary = None
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(mode='w', dir=self.path.parent, delete=False) as handle:
                temporary = handle.name
                json.dump({'version': 1, 'screens': self.records}, handle)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self.path)
        except OSError as error:
            LOG.warning('Could not retain offline screen capabilities (%s)', type(error).__name__)
        finally:
            if temporary and os.path.exists(temporary): os.unlink(temporary)

// Preview counterpart of tile_controls::keys_for/panel_available. These are
// display descriptions only; the firmware owns touch and Home Assistant actions. Home Assistant's feature bits by the names
// its source gives them (model/catalogue.ts, catalogue/_ha.json): none is counted by hand here.
import { bits } from './catalogue';
type Attributes = Record<string, any>;
export type ControlKey = { icon: string; primary?: boolean; disabled?: boolean; mode?: string };
export function controlKeys(domain: string, kind: string, state: string, a: Attributes, room = 3): ControlKey[] {
  const f = Number(a.supported_features || 0), keys: ControlKey[] = [];
  const add = (icon: string, disabled = false, primary = false) => keys.push({ icon, disabled, primary });
  if (kind === 'playback') {
    const media = (name: string) => f & bits('media_player', name);
    if (media('PREVIOUS_TRACK')) add('skip-previous');
    if (f & bits('media_player', 'PAUSE', 'PLAY')) add(state === 'playing' ? 'pause' : 'play', !media(state === 'playing' ? 'PAUSE' : 'PLAY'), true);
    if (media('NEXT_TRACK')) add('skip-next');
  } else if (kind === 'buttons' && domain === 'cover') {
    const sideways = ['curtain', 'awning', 'door', 'gate'].includes(a.device_class);
    const open = typeof a.current_position === 'number' ? a.current_position >= 99.5 : state === 'open';
    const closed = typeof a.current_position === 'number' ? a.current_position <= .5 : state === 'closed';
    if (f & bits('cover', 'OPEN')) add(sideways ? 'arrow-expand-horizontal' : 'arrow-up', open && state !== 'closing');
    if (f & bits('cover', 'STOP')) add('stop');
    if (f & bits('cover', 'CLOSE')) add(sideways ? 'arrow-collapse-horizontal' : 'arrow-down', closed && state !== 'opening');
  } else if (kind === 'buttons' && domain === 'vacuum') {
    const vacuum = (...names: string[]) => f & bits('vacuum', ...names);
    if (state === 'cleaning' && (vacuum('PAUSE') || vacuum('TURN_OFF') && !vacuum('START'))) add('pause');
    else if (vacuum('START', 'TURN_ON')) add('play');
    if (vacuum('STOP')) add('stop');
    if (vacuum('RETURN_HOME')) add('home-map-marker');
  } else if (kind === 'buttons' && domain === 'timer') {
    add(state === 'active' ? 'pause' : 'play'); add('close');
  } else if (kind === 'stepper' && domain.endsWith('select')) {
    add('chevron-left', (a.options?.length || 0) < 2); add('chevron-right', (a.options?.length || 0) < 2);
  } else if (kind === 'mode') {
    keys.push(...barKeys(a, state, room));
  }
  return keys;
}
const MODE_ICONS: Record<string, string> = { off: 'power', heat: 'fire', cool: 'snowflake', heat_cool: 'sun-snowflake-variant', auto: 'thermostat-auto', dry: 'water-percent', fan_only: 'fan' };
/** A thermostat's mode bar (tile_controls::climate_bar_keys), for "Mode" and under the -/+ of "Temperature and mode":
 * heat and cool before the rest, never off (the tile's circle switches it), the mode it is in always among them; "…"
 * (the card) in the last place when they do not all fit, two modes rather than one and a "…" in a bar for two. None for
 * a device with fewer than two modes, or a bar with room for fewer than two. */
export function barKeys(a: Attributes, state: string, room = 6): ControlKey[] {
  const listed: string[] = Array.isArray(a.hvac_modes) ? a.hvac_modes.slice(0, 8).map((m: unknown) => String(m).toLowerCase()) : [];
  const modes = ['heat', 'cool', 'heat_cool', 'auto', 'dry', 'fan_only'].filter((mode) => listed.includes(mode));
  room = Math.min(room, 6);
  if (modes.length < 2 || room < 2) return [];
  const more = modes.length > room, shown = !more ? modes.length : room === 2 ? 2 : room - 1;
  const pick = modes.slice(0, shown), current = String(state).toLowerCase();
  if (modes.includes(current) && !pick.includes(current)) pick[pick.length - 1] = current;
  const keys: ControlKey[] = pick.map((mode) => ({ icon: MODE_ICONS[mode] || 'fan', mode }));
  if (more && shown < room) keys.push({ icon: 'dots-horizontal' });
  return keys;
}
// `range`: the screen draws a thermostat's range on its -/+ (its firmware's climate_range, 0.19.0+); an older one gets a
// thermostat with only a range without them (core.drawn_controls), and so does its picture here.
export function availableControl(domain: string, kind: string | null, state: string, a: Attributes, range = true): string {
  if (!kind || ['unavailable', 'unknown', ''].includes(state)) return '';
  if (domain === 'cover') kind = coverPrimary(kind);
  const f = Number(a.supported_features || 0);
  if (['buttons', 'playback', 'mode'].includes(kind) || kind === 'stepper' && domain.endsWith('select'))
    return controlKeys(domain, kind, state, a).length ? kind : '';
  if (kind === 'brightness') return domain === 'light' && (!a.supported_color_modes?.length || a.supported_color_modes.some((mode: string) => ['brightness', 'white', 'color_temp', 'hs', 'rgb', 'rgbw', 'rgbww', 'xy'].includes(mode))) ? kind : '';
  if (kind === 'speed') return domain === 'fan' && f & bits('fan', 'SET_SPEED') ? kind : '';
  if (kind === 'position') return domain === 'cover' && f & bits('cover', 'SET_POSITION') ? kind : '';
  if (kind === 'volume') return domain === 'media_player' && f & bits('media_player', 'VOLUME_SET', 'VOLUME_MUTE') ? kind : '';
  // A single temperature (feature 1) or a range with its chip (feature 2, firmware 0.19.0).
  if (kind === 'setpoint' || kind === 'setpoint_mode')
    return domain === 'climate' && (f & bits('climate', 'TARGET_TEMPERATURE') || (f & bits('climate', 'TARGET_TEMPERATURE_RANGE') && range)) ? kind : '';
  if (kind === 'stepper' || kind === 'slider') return ['number', 'input_number'].includes(domain) ? kind : '';
  if (kind === 'toggle') return ['light', 'switch', 'input_boolean', 'automation', 'fan'].includes(domain) ? kind : '';
  if (kind === 'run') return ['scene', 'script', 'button', 'input_button', 'automation'].includes(domain) ? kind : '';
  return '';
}

// Preserve the primary choice while toggling the additional slat group.
export const hasCoverTilt = (kind: string | null | undefined) => ['tilt', 'buttons_tilt', 'position_tilt'].includes(kind || '');
export const coverPrimary = (kind: string | null | undefined) => kind === 'tilt' ? 'none' : (kind || 'none').replace(/_tilt$/, '');
export const withCoverTilt = (primary: string, tilt: boolean) => tilt ? (primary === 'none' ? 'tilt' : primary + '_tilt') : primary;
export function coverTiltKind(state: string, a: Attributes): '' | 'position' | 'buttons' {
  if (['unavailable', 'unknown', ''].includes(state)) return '';
  const f = Number(a.supported_features || 0);
  return f & 128 ? 'position' : f & 112 ? 'buttons' : '';
}
export function coverTiltKeys(a: Attributes): ControlKey[] {
  const f = Number(a.supported_features || 0), value = a.current_tilt_position;
  return [
    ...(f & 16 ? [{ icon: 'blinds-open', disabled: typeof value === 'number' && value >= 99.5 }] : []),
    ...(f & 64 ? [{ icon: 'stop' }] : []),
    ...(f & 32 ? [{ icon: 'blinds', disabled: typeof value === 'number' && value <= .5 }] : []),
  ];
}

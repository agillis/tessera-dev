// The firmware's sizes in the editor's mockup (app 0.4.32): ui_scale.h's px() and the -/+ pill of a card's controls
// (runtime_tiles panel_metrics, stepper_keys), computed the same way from the board's density and look, so the mockup
// draws them at the size the glass does instead of sizes of its own.
type Shape = { width?: number; dpi?: number; look?: string; fonts?: { watch_value?: number; sublabel_big?: number; sublabel?: number; icon_mini?: number };
  spacing?: { margin: number; gap: number; tile_pad: number } };

/** ui::configure and ui::px: a size of the reference look (170 dpi standard, 143 dpi compact) in this board's pixels. */
export function uiScale(shape: Shape) {
  const compact = shape.look === "compact", reference = compact ? 143 : 170;
  const dpi = Math.round(shape.dpi || reference);
  const scalePct = Math.floor((dpi * 100 + Math.floor(reference / 2)) / reference);
  const px = (n: number) => (scalePct === 100 ? n : n >= 0 ? Math.floor((n * scalePct + 50) / 100) : -Math.floor((-n * scalePct + 50) / 100));
  return { compact, large: !compact, px };
}

/** The pill of a wide card's -/+ in glass pixels: its height (panel_metrics key_h + 2), the inset of its keys and their
 * diameter (stepper_keys), and the faces its number is drawn in (watch_value first, then sublabel_big, then sublabel). */
export function pillMetrics(shape: Shape) {
  const { large, px } = uiScale(shape);
  const height = px(large ? 46 : 34) + 2, inset = Math.max(2, px(large ? 4 : 3)), key = Math.max(1, height - 2 * inset);
  const fonts = shape.fonts || {};
  return { height, inset, key, faces: [fonts.watch_value, fonts.sublabel_big, fonts.sublabel].filter((size): size is number => Boolean(size)) };
}

/** A number's width in em as the screens' Roboto draws it: a digit .56, the degree sign .37, a minus .33, a decimal mark
 * .27. Enough to pick among a board's faces as the firmware does, which measures the glyphs themselves. */
export const textEms = (text: string) => [...text].reduce((sum, ch) => sum + (/\d/.test(ch) ? 0.56 : ch === "°" ? 0.37 : ch === "-" ? 0.33 : 0.27), 0);

/** The widest temperature a thermostat's -/+ can show (tile_controls::widest_setpoint): as many 8s as its highest or
 * lowest temperature has digits, with the decimal its step shows. The face measured by it keeps its size from tap to tap. */
export function widestSetpoint(a: Record<string, any>) {
  const minimum = Number.isFinite(Number(a.min_temp)) ? Number(a.min_temp) : 7, maximum = Number.isFinite(Number(a.max_temp)) ? Number(a.max_temp) : 35;
  const reach = Math.max(Math.abs(minimum), Math.abs(maximum)), step = Number(a.target_temp_step) > 0 ? Number(a.target_temp_step) : 0.5;
  return `${minimum < 0 ? "-" : ""}${"8".repeat(String(Math.trunc(reach)).length)}${step < 1 ? ".8" : ""}°`;
}

/** A thermostat's mode bar in a card's panel (climate_tile::bar_room and bar_width, the panel's key as a finger:
 * runtime_tiles panel_metrics, the taller card's finger, panel_metrics_full): how many modes fit in `reach` glass pixels
 * and how wide the bar is. `place`: beside the name on a card of one row, over the card on a taller one or the page. */
export function modeBar(shape: Shape, place: "row" | "tall" | "full", reach: number, modes: number) {
  const { large, compact, px } = uiScale(shape);
  const touchMin = Math.floor(((shape.dpi || (compact ? 143 : 170)) * 7 + 12) / 25);
  const finger = place === "tall" ? Math.max(touchMin, px(large ? 48 : 34)) : place === "full" ? px(large ? 84 : 44) : px(large ? 46 : 34);
  const inset = Math.max(2, px(large ? 4 : 3));
  reach = Math.min(reach, px(compact ? 620 : 740));
  const fit = modes >= 2 ? Math.min(modes, Math.floor((reach - 2 * inset) / finger)) : 0;
  const room = fit >= 2 ? fit : 0;
  const width = !room ? 0 : place === "row" ? Math.min(reach, room * finger + 2 * inset) : reach;
  return { room, width, finger, inset };
}

/** A card's content width in glass pixels (runtime_tiles cell_content_width and the card's own content): `columns` of
 * the page's `across` cells, the page less its margins shared between them with a gap between two, less the card's
 * padding and its border. One column of a wide card is the cell its controls fill. */
export function cardContent(shape: Shape, across: number, columns: number) {
  const s = shape.spacing ?? (uiScale(shape).compact ? { margin: 9, gap: 6, tile_pad: 8 } : { margin: 16, gap: 12, tile_pad: 12 });
  const cell = Math.floor(((shape.width ?? 320) - 2 * s.margin - (across - 1) * s.gap) / Math.max(1, across));
  return columns * cell + (columns - 1) * s.gap - 2 * s.tile_pad - 2;
}

/** A range's chip on a wide card's -/+ pill (runtime_tiles stepper_keys and range_chip), in glass pixels: the face its
 * number is drawn in, the largest whose line fits the pill and whose widest temperature fits the chip on its own, and
 * whether its heat or cool icon fits beside that number (else the number stands alone in its end's colour). */
export function wideChip(shape: Shape, across: number, widest: string) {
  const { px } = uiScale(shape), pill = pillMetrics(shape), fonts = shape.fonts || {};
  const width = cardContent(shape, across, 1), chip = width - 2 * (pill.inset + pill.key + pill.inset), pad = px(6);
  const line = (size: number) => Math.round(size * 1.172), ems = textEms(widest);
  let face = pill.faces[pill.faces.length - 1] ?? 14;
  for (const size of pill.faces) if (line(size) <= pill.height && ems * size + pad <= chip) { face = size; break; }
  const icon = line(fonts.icon_mini ?? (uiScale(shape).large ? 26 : 18));
  return { face, icon: icon + pad / 2 + ems * face + pad <= chip };
}

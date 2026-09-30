// ---- A tile's size (app 0.4.32) ----
// Five names and every other rectangle as a span ("3x2": three columns, two rows), set with the tile's handles. The
// same rules as the add-on (core.py span_of, span_offered) and the firmware (page_protocol.h): a span is any rectangle
// smaller than the grid that no name already says, and a screen names the ones its grid takes in tile_sizes. What a
// card looks like follows its columns and rows the way the firmware draws it: more than one column is a wide card,
// more than one row a tall one.
export type NamedSize = "single" | "wide" | "tall" | "square" | "full";
export type Span = `${number}x${number}`;
export type Size = NamedSize | Span;
export const NAMED_SIZES: NamedSize[] = ["single", "wide", "tall", "square", "full"];
type Grid = { columns: number; rows: number };

/** { columns, rows } of a span such as "3x2", or null for a name or anything else. */
export function spanOf(size: unknown): Grid | null {
  const found = typeof size === "string" ? /^([1-9])x([1-9])$/.exec(size) : null;
  return found ? { columns: Number(found[1]), rows: Number(found[2]) } : null;
}
export const isSize = (size: unknown): size is Size => NAMED_SIZES.includes(size as NamedSize) || spanOf(size) !== null;
/** Whether a grid takes this rectangle as a span: smaller than the grid, and more than the names say (2 x 2). */
export const spanOffered = (columns: number, rows: number, grid: Grid) =>
  columns <= grid.columns && rows <= grid.rows && !(columns === grid.columns && rows === grid.rows) && (columns > 2 || rows > 2);
/** Rows a size is high, the whole page aside: tall and square two, a span its own. */
export const sizeRows = (size: unknown) => spanOf(size)?.rows ?? (size === "tall" || size === "square" ? 2 : 1);
/** Columns a size is wide, the whole page aside: wide and square two, a span its own. */
export const sizeColumns = (size: unknown) => spanOf(size)?.columns ?? (size === "wide" || size === "square" ? 2 : 1);
/** Taller than a row: the tall layouts (a second row of controls, a picture over the card). */
export const isTallSize = (size: unknown) => size !== "full" && sizeRows(size) > 1;
/** Wider than a column, or the whole page: the wide layouts. */
export const isWideSize = (size: unknown) => size === "full" || sizeColumns(size) > 1;
/** The size a rectangle on this grid is: its name, else its span; null when the grid does not take it. */
export function sizeFor(columns: number, rows: number, grid: Grid): Size | null {
  if (columns === grid.columns && rows === grid.rows) return "full";
  if (columns === 1 && rows === 1) return "single";
  if (columns === Math.min(2, grid.columns) && rows === 1) return "wide";
  if (columns === 1 && rows === 2) return "tall";
  if (columns === 2 && rows === 2) return "square";
  return spanOffered(columns, rows, grid) ? `${columns}x${rows}` as Span : null;
}

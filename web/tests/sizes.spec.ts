// A tile's size (app 0.4.32): the five names and every other rectangle smaller than the grid as a span, the same rules
// as the add-on (tests/test_tile_spans.py) and the firmware (tests/test_page_protocol.cpp).
import { describe, expect, it } from "vitest";
import { isTallSize, isWideSize, sizeFor, spanOf, spanOffered } from "../src/model/sizes";
import { dimensions } from "../src/model/layout";

describe("tile sizes and spans", () => {
  it("reads a span, and offers only what no name says and the whole grid is not", () => {
    expect(spanOf("3x2")).toEqual({ columns: 3, rows: 2 });
    expect(spanOf("square")).toBeNull();
    expect(spanOffered(3, 2, { columns: 3, rows: 3 })).toBe(true);
    expect(spanOffered(2, 2, { columns: 3, rows: 3 })).toBe(false);
    expect(spanOffered(3, 3, { columns: 3, rows: 3 })).toBe(false);
    expect(spanOffered(4, 1, { columns: 3, rows: 3 })).toBe(false);
  });
  it("names a rectangle by its name first, else its span", () => {
    const grid = { columns: 4, rows: 4 };
    expect(sizeFor(2, 2, grid)).toBe("square");
    expect(sizeFor(4, 4, grid)).toBe("full");
    expect(sizeFor(3, 2, grid)).toBe("3x2");
    expect(sizeFor(5, 1, grid)).toBeNull();
    expect(dimensions("2x3", grid)).toEqual({ columns: 2, rows: 3 });
  });
  it("draws as the firmware does: more than one column is wide, more than one row tall", () => {
    expect([isWideSize("3x2"), isTallSize("3x2")]).toEqual([true, true]);
    expect([isWideSize("1x3"), isTallSize("1x3")]).toEqual([false, true]);
    expect([isWideSize("3x1"), isTallSize("3x1")]).toEqual([true, false]);
    expect([isWideSize("full"), isTallSize("full")]).toEqual([true, false]);
  });
});

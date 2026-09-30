import { describe, expect, it } from "vitest";
import { pillMetrics, textEms, uiScale, widestSetpoint, cardContent, modeBar, wideChip } from "../src/model/ui-scale";

describe("the firmware's sizes in the mockup (app 0.4.32)", () => {
  it("scales as ui::px does, from the board's density and look", () => {
    expect(uiScale({ dpi: 170, look: "standard" }).px(46)).toBe(46);
    expect(uiScale({ dpi: 143, look: "compact" }).px(34)).toBe(34);
    // A 7-inch at 133 dpi draws the standard look at 78 %: (46 x 78 + 50) / 100.
    expect(uiScale({ dpi: 133, look: "standard" }).px(46)).toBe(36);
    expect(pillMetrics({ dpi: 170, look: "standard", fonts: { watch_value: 38, sublabel_big: 21 } })).toEqual({ height: 48, inset: 4, key: 40, faces: [38, 21] });
  });
  it("measures a thermostat's -/+ by the widest temperature it can show, as tile_controls::widest_setpoint", () => {
    expect(widestSetpoint({ min_temp: 7, max_temp: 35, target_temp_step: 0.5 })).toBe("88.8°");
    expect(widestSetpoint({ min_temp: 45, max_temp: 95, target_temp_step: 1 })).toBe("88°");
    expect(widestSetpoint({ min_temp: 45, max_temp: 110, target_temp_step: 1 })).toBe("888°");
    expect(widestSetpoint({ min_temp: -20, max_temp: 30, target_temp_step: 1 })).toBe("-88°");
    expect(widestSetpoint({})).toBe("88.8°");   // 7 to 35 in halves when Home Assistant says nothing, as the firmware
    expect(textEms("88.8°")).toBeCloseTo(0.56 * 3 + 0.27 + 0.37);
  });
});

describe("a card's room as the glass works it out (app 0.4.32)", () => {
  const guition = { width: 480, dpi: 170, look: "standard", fonts: { watch_value: 38, sublabel_big: 21, sublabel: 16, icon_mini: 26 }, spacing: { margin: 16, gap: 12, tile_pad: 12 } };
  const cyd = { width: 320, dpi: 143, look: "compact", fonts: { watch_value: 22, sublabel_big: 14, sublabel: 11, icon_mini: 18 }, spacing: { margin: 9, gap: 6, tile_pad: 8 } };
  it("gives a wide card's controls one cell and a taller card its whole content (runtime_tiles cell_content_width)", () => {
    expect(cardContent(guition, 2, 1)).toBe(192);
    expect(cardContent(guition, 2, 2)).toBe(422);
    expect(cardContent(cyd, 2, 1)).toBe(130);
  });
  it("fits as many modes as climate_tile::bar_room does", () => {
    expect(modeBar(guition, "row", 192, 5)).toMatchObject({ room: 4, width: 4 * 46 + 8 });
    expect(modeBar(guition, "tall", 422, 5)).toMatchObject({ room: 5, width: 422 });
    expect(modeBar(guition, "row", 192, 1).room).toBe(0);
  });
  it("draws a wide chip's number as large as it fits alone, and its icon only where that fits too (range_chip)", () => {
    expect(wideChip(guition, 2, "88°")).toEqual({ face: 38, icon: true });
    expect(wideChip(cyd, 2, "88°")).toEqual({ face: 22, icon: false });
  });
});

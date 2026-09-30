<script setup lang="ts">
// A thermostat's mode bar in the editor's mockup, as the screen draws it (firmware 0.19.0, runtime_tiles draw_mode_bar):
// for "Mode" and under the -/+ of "Temperature and mode" alike. The same modes (barKeys, tile_controls::climate_bar_keys)
// and as many as the same room holds (modeBar, climate_tile::bar_room), in the glass pixels this mockup stands for;
// the mode it is in filled in Home Assistant's colour for it, and its word beside each icon where every segment has
// room for its own.
import { computed } from "vue";
import { te } from "../i18n";
import { glyph } from "../model/topbar";
import { barKeys } from "../model/tall-controls";
import { modeColor } from "../model/tile-palette";
import { cardContent, modeBar, uiScale } from "../model/ui-scale";
import { deviceStyle, screenShape, screenText, state } from "../store";

// `columns`: how many of the page's columns the card spans.
const props = defineProps<{ a: Record<string, any>; mode: string; place: "row" | "tall" | "full"; columns: number }>();
const glass = computed(() => Number(deviceStyle.value["--glass"]) || 1);
// The room the glass gives the bar: the cell beside the name on a card of one row, the card's content on a taller one
// or the page (runtime_tiles layout_panel), from the board's own spacing.
const bar = computed(() => {
  const shape = screenShape.value, across = state.documentGrid?.columns ?? shape.columns;
  const reach = cardContent(shape, across, props.place === "row" ? 1 : props.place === "full" ? across : props.columns);
  return modeBar(shape, props.place, reach, barKeys(props.a, props.mode, 6).length);
});
const keys = computed(() => barKeys(props.a, props.mode, bar.value.room));
const word = (mode?: string) => (mode && te(`screen.ha.climate.${mode}`) ? screenText(`screen.ha.climate.${mode}`) : "");
// Words where every segment has room for its icon, a gap and its word (runtime_tiles draw_mode_bar), measured with
// the board's own sizes: its key icons and the card's value line.
const words = computed(() => {
  const { width, inset } = bar.value, shape = screenShape.value;
  if (!width || !keys.value.length) return false;
  const { large, px } = uiScale(shape), fonts = ("fonts" in shape ? shape.fonts : undefined) || {};
  const segment = (width - 2 * inset) / keys.value.length, icon = Math.round((fonts.icon_mini ?? (large ? 26 : 18)) * 1.172);
  const text = fonts.sublabel ?? (large ? 16 : 11);
  return keys.value.every((k) => !k.mode || segment >= icon + px(large ? 26 : 14) + word(k.mode).length * 0.55 * text);
});
const icons = computed(() => state.inventory.icons?.controls || {});
const icon = (name: string) => (icons.value[name] ? glyph(icons.value[name]) : "");
// The board's sizes in the mockup's pixels: the bar, its inset, its icons and its words.
const style = computed(() => {
  const shape = screenShape.value, { large } = uiScale(shape), fonts = ("fonts" in shape ? shape.fonts : undefined) || {}, g = glass.value;
  const sizes = { "--icon": `${((fonts.icon_mini ?? (large ? 26 : 18)) * g).toFixed(2)}px`, "--word": `${((fonts.sublabel ?? (large ? 16 : 11)) * g).toFixed(2)}px` };
  if (!bar.value.width) return sizes;
  return { ...sizes, width: `${(bar.value.width * g).toFixed(2)}px`, height: `${(bar.value.finger * g).toFixed(2)}px`, padding: `${(bar.value.inset * g).toFixed(2)}px` };
});
</script>

<template>
  <span class="mode-bar" :class="place">
    <span v-if="keys.length" class="track" :style="style">
      <span v-for="(k, i) in keys" :key="i" class="seg" :class="{ on: k.mode === mode }"
        :style="k.mode === mode ? { '--mode': modeColor(k.mode) } : undefined">
        <span class="mdi">{{ icon(k.icon) }}</span><span v-if="words && k.mode" class="word">{{ word(k.mode) }}</span>
      </span>
    </span>
  </span>
</template>

<style scoped>
.mode-bar { display: flex; width: 100%; min-width: 0; justify-content: center; }
.mode-bar.row { justify-content: flex-end; }
.track { display: flex; box-sizing: border-box; min-width: 0; height: 24px; padding: 2px; border-radius: 999px; background: #f1f1f1; }
.seg { flex: 1 1 0; min-width: 0; display: flex; align-items: center; justify-content: center; gap: 3px; border-radius: 999px; color: #46525e; overflow: hidden; }
.seg .mdi { font-size: var(--icon, 14px); line-height: 1; }
.seg .word { font-size: var(--word, 10px); white-space: nowrap; }
.seg.on { background: var(--mode); color: #fff; }
</style>

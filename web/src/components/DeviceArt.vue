<script setup lang="ts">
// A screen drawn as it hangs on the wall (app 0.4.32): the dark frame, the glass in its own proportions, the top bar
// with the name typed so far, and a page of tiles in the Tessera colours. New screen shows each board this way, the
// chosen one large while it is named, and the installation lights its tiles one by one as it goes (`lit`, 0 to 1).
import { computed, useId } from "vue";

const props = withDefaults(defineProps<{
  width: number; height: number; columns: number; rows: number; name?: string; lit?: number;
  state?: "idle" | "working" | "done" | "failed"; bare?: boolean;
}>(), { name: "", lit: 1, state: "idle", bare: false });

// The glass is 100 units high; its width follows the board's pixels, so a CYD reads wide and a Guition square.
const glassW = computed(() => Math.round((props.width / props.height) * 100));
const PAD = 7;
const BAR = 15;
const GAP = 3;
const box = computed(() => `${-PAD} ${-PAD} ${glassW.value + PAD * 2} ${100 + PAD * 2}`);
// Amber, blue, purple and green: the four squares of the mark, each as the pastel card and the lit circle on it.
const TONES = [["#FFF1C7", "#F4B400"], ["#DCF0FB", "#0A96D6"], ["#ECE3F7", "#8E63C4"], ["#E2F2E3", "#43A047"]];
const cells = computed(() => {
  const cols = Math.max(1, props.columns), rows = Math.max(1, props.rows);
  const top = BAR + 2, inner = 4;
  const w = (glassW.value - inner * 2 - GAP * (cols - 1)) / cols;
  const h = (100 - top - inner - GAP * (rows - 1)) / rows;
  const count = cols * rows;
  const shown = Math.round(Math.max(0, Math.min(1, props.lit)) * count);
  return Array.from({ length: count }, (_, i) => {
    const c = i % cols, r = Math.floor(i / cols);
    const tone = TONES[i % TONES.length];
    return { x: inner + c * (w + GAP), y: top + r * (h + GAP), w, h, tone, on: i < shown, next: i === shown && props.state === "working", i };
  });
});
const iconR = computed(() => Math.max(2.2, Math.min(cells.value[0]?.w ?? 10, cells.value[0]?.h ?? 10) * 0.16));
const frame = `da-frame-${useId()}`;
// The name as the screen shows it: what fits between the mark and the time, with dots when it is longer (about 3.2
// units a character at this size; the time takes 18).
const label = computed(() => {
  const name = props.name || "", room = Math.max(4, Math.floor((glassW.value - 36) / 3.2));
  return name.length > room ? `${name.slice(0, room - 1).trimEnd()}…` : name;
});
</script>

<template>
  <svg class="device-art" :class="[state, { bare }]" :viewBox="box" role="img" :aria-label="name || undefined" preserveAspectRatio="xMidYMid meet">
    <defs>
      <linearGradient :id="frame" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stop-color="#2b2e35" />
        <stop offset="1" stop-color="#16181c" />
      </linearGradient>
    </defs>
    <rect v-if="!bare" class="da-frame" :x="-PAD" :y="-PAD" :width="glassW + PAD * 2" :height="100 + PAD * 2" rx="9" :fill="`url(#${frame})`" />
    <rect class="da-glass" x="0" y="0" :width="glassW" height="100" rx="3" />
    <!-- The top bar: the mark, the name as it is typed, the time. -->
    <g class="da-bar" transform="translate(4 4)">
      <rect x="0" y="0" width="3.2" height="3.2" rx="0.8" fill="#FFC107" />
      <rect x="3.8" y="0" width="3.2" height="3.2" rx="0.8" fill="#009FE3" />
      <rect x="0" y="3.8" width="3.2" height="3.2" rx="0.8" fill="#926BC7" />
      <rect x="3.8" y="3.8" width="3.2" height="3.2" rx="0.8" fill="#4CAF50" />
      <text v-if="label" class="da-name" x="10" y="5.9">{{ label }}</text>
      <rect v-else class="da-name-blank" x="10" y="1.6" :width="Math.min(28, glassW * 0.35)" height="3.8" rx="1.9" />
      <text class="da-time" :x="glassW - 8" y="5.9" text-anchor="end">10:08</text>
    </g>
    <g class="da-tiles">
      <g v-for="cell in cells" :key="cell.i" class="da-tile" :class="{ on: cell.on, next: cell.next }" :style="{ '--i': cell.i }">
        <rect :x="cell.x" :y="cell.y" :width="cell.w" :height="cell.h" rx="2.6" :fill="cell.on ? '#ffffff' : 'transparent'" />
        <template v-if="cell.on">
          <circle :cx="cell.x + iconR * 1.9" :cy="cell.y + iconR * 1.9" :r="iconR * 1.15" :fill="cell.tone[0]" />
          <circle :cx="cell.x + iconR * 1.9" :cy="cell.y + iconR * 1.9" :r="iconR * 0.5" :fill="cell.tone[1]" />
          <rect :x="cell.x + iconR * 1.2" :y="cell.y + cell.h - iconR * 2.1" :width="Math.max(4, cell.w * 0.45)" :height="Math.max(1.4, iconR * 0.55)" rx="0.7" fill="#d6d8dd" />
        </template>
      </g>
    </g>
    <g v-if="state === 'done' || state === 'failed'" class="da-badge" :transform="`translate(${glassW + PAD - 3} ${-PAD + 3})`">
      <circle r="8" :fill="state === 'done' ? '#1e9a5f' : '#c6372e'" stroke="#fff" stroke-width="1.6" />
      <path v-if="state === 'done'" d="M-3.4 0.2 L-1 2.6 L3.6 -2.4" fill="none" stroke="#fff" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
      <path v-else d="M-2.6 -2.6 L2.6 2.6 M2.6 -2.6 L-2.6 2.6" fill="none" stroke="#fff" stroke-width="1.8" stroke-linecap="round" />
    </g>
  </svg>
</template>

<style scoped>
.device-art { display: block; width: 100%; height: 100%; overflow: visible; }
/* On a dark page the dark frame keeps an edge. */
@media (prefers-color-scheme: dark) { .da-frame { stroke: rgba(255, 255, 255, 0.14); stroke-width: 0.8; } }
.da-glass { fill: #ececee; }
.bare .da-glass { fill: var(--surface-2); stroke: var(--line); stroke-width: 0.6; }
.da-name { font: 600 5.4px var(--ui-font); fill: #1d1f24; }
.da-name-blank { fill: #d6d8dd; }
.da-time { font: 500 4.6px var(--ui-font); fill: #6b7079; }
.da-tile rect:first-child { stroke: #dcdee3; stroke-width: 0.5; stroke-dasharray: 1.6 1.4; transition: fill 0.3s ease; }
.da-tile.on rect:first-child { stroke: rgba(0, 0, 0, 0.06); stroke-dasharray: none; }
/* The tile that lights next breathes while the installation works on it. */
.da-tile.next rect:first-child { animation: da-breathe 1.4s ease-in-out infinite; stroke: #0A96D6; stroke-dasharray: none; stroke-width: 0.8; }
.da-tile.on { animation: da-pop 0.36s cubic-bezier(0.2, 0.9, 0.3, 1.3) both; transform-box: fill-box; transform-origin: center; }
.idle .da-tile.on { animation: none; }
.da-badge { animation: da-pop 0.4s cubic-bezier(0.2, 0.9, 0.3, 1.4) both; transform-box: fill-box; transform-origin: center; }
@keyframes da-breathe { 50% { fill: rgba(10, 150, 214, 0.12); } }
@keyframes da-pop { from { opacity: 0; transform: scale(0.82); } }
@media (prefers-reduced-motion: reduce) { .da-tile, .da-tile.next rect:first-child, .da-badge { animation: none; } }
</style>

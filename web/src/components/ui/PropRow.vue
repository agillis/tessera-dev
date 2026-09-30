<script setup lang="ts">
// One setting of the inspector (app 0.4.32): an icon that says what kind of thing it is and its name on the left, the
// value on the right. `stack` puts a wide value (swatches, a list of icons) under the name instead. A `hint` makes the
// name itself the way to it (underlined with dots), rather than one more (i) in the column (app 0.4.32).
import type { IconName } from "../../model/ui-icons";
import HelpTip from "../HelpTip.vue";
import Icon from "./Icon.vue";
defineProps<{ label: string; icon?: IconName; hint?: string; stack?: boolean; for?: string }>();
</script>

<template>
  <div class="prop" :class="{ stack }">
    <span class="prop-label">
      <Icon v-if="icon" :name="icon" />
      <HelpTip v-if="hint" :text="hint" :label="label" />
      <label v-else-if="$props.for" :for="$props.for">{{ label }}</label><span v-else>{{ label }}</span>
      <span v-if="$slots.aside" class="prop-aside"><slot name="aside" /></span>
    </span>
    <div class="prop-value"><slot /></div>
    <div v-if="$slots.note" class="prop-note"><slot name="note" /></div>
  </div>
</template>

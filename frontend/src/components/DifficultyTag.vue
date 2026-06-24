<!--
  DifficultyTag.vue — 难度标签组件
  P1浅绿 → P2浅黄 → P3浅橙 → P4浅红 → P5深红
-->
<template>
  <view
    v-if="style"
    class="difficulty-tag"
    :style="{ backgroundColor: style.bg, color: style.color }"
  >
    {{ style.label }}
  </view>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { getDifficultyStyle } from '@/utils/difficulty'

const props = defineProps<{ level: number | null }>()
const style = computed(() => getDifficultyStyle(props.level))
</script>

<style scoped>
.difficulty-tag {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
  line-height: 1.4;
}
</style>

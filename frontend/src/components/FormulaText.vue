<!--
  FormulaText.vue — Markdown + LaTeX 公式渲染组件（核心）
  接收 Markdown 文本（含 $...$ / $$...$$ LaTeX 公式），输出渲染后的 HTML
  
  H5 端：markdown-it + KaTeX → v-html
  小程序端：预留 rich-text 分支（本期不实现，需后端预渲染）
-->
<template>
  <view class="formula-text" :class="`font-size-${fontSize}`">
    <!-- #ifdef H5 -->
    <view v-html="html"></view>
    <!-- #endif -->
    <!-- #ifdef MP-WEIXIN -->
    <rich-text v-if="safeHtml" :nodes="safeHtml"></rich-text>
    <text v-else>{{ content }}</text>
    <!-- #endif -->
  </view>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { renderMarkdown } from '@/utils/markdown'
import { useSettingsStore } from '@/stores/settings'

const props = defineProps<{ content: string }>()
const settings = useSettingsStore()

const html = computed(() => renderMarkdown(props.content))
const safeHtml = computed(() => '') // 小程序预留
const fontSize = computed(() => settings.fontSize)
</script>

<style scoped>
.formula-text {
  line-height: 1.8;
  word-break: break-word;
}

/* 字体三档 */
.font-size-small { font-size: 14px; }
.font-size-medium { font-size: 16px; }
.font-size-large { font-size: 18px; }

/* KaTeX 公式自适应 */
:deep(.katex-display) {
  overflow-x: auto;
  padding: 4px 0;
}
:deep(.katex) {
  font-size: 1.1em;
}

/* Markdown 元素样式 */
:deep(table) {
  border-collapse: collapse;
  width: 100%;
  margin: 8px 0;
}
:deep(th),
:deep(td) {
  border: 1px solid var(--border-color, #ddd);
  padding: 6px 12px;
  text-align: left;
}
:deep(th) {
  background: var(--bg-secondary, #f0f2f5);
}
:deep(code) {
  background: var(--bg-secondary, #f0f2f5);
  padding: 2px 6px;
  border-radius: 3px;
  font-size: 0.9em;
}
:deep(blockquote) {
  border-left: 3px solid var(--primary-color, #1e3a5f);
  margin: 8px 0;
  padding: 4px 12px;
  color: var(--text-secondary, #6b7280);
}
:deep(ol),
:deep(ul) {
  padding-left: 24px;
  margin: 8px 0;
}
:deep(p) {
  margin: 8px 0;
}
:deep(strong) {
  font-weight: 600;
}
</style>

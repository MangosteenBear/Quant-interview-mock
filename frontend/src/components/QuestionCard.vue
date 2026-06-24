<!--
  QuestionCard.vue — 题目列表项卡片
  显示题干预览（纯文本截断）+ 题型 + 难度 + 来源 + 标签
-->
<template>
  <view class="question-card" @click="onClick">
    <!-- 题干预览（纯文本，去 LaTeX 符号） -->
    <view class="stem-preview">{{ plainStem }}</view>

    <!-- 标签行 -->
    <view class="card-footer">
      <view class="tags-left">
        <DifficultyTag :level="question.difficulty" />
        <text class="type-tag">{{ typeLabel }}</text>
        <text v-if="question.book_chapter" class="chapter-tag">{{ question.book_chapter }}</text>
      </view>
      <view v-if="showFavorite" class="fav-star" @click.stop="onToggleFav">
        <text :class="{ active: isFavorited }">{{ isFavorited ? '★' : '☆' }}</text>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { QuestionListItem } from '@/types/api'
import { QUESTION_TYPE_LABELS } from '@/utils/difficulty'
import DifficultyTag from './DifficultyTag.vue'

const props = defineProps<{
  question: QuestionListItem
  showFavorite?: boolean
  isFavorited?: boolean
}>()

const emit = defineEmits<{
  click: [id: number]
  toggleFav: [id: number]
}>()

const plainStem = computed(() => {
  // 去 LaTeX 符号，纯文本截断
  return props.question.stem_markdown
    .replace(/\$+/g, '')
    .replace(/\\[a-zA-Z]+/g, '')
    .replace(/[{}]/g, '')
    .replace(/\n/g, ' ')
    .trim()
    .slice(0, 80) + (props.question.stem_markdown.length > 80 ? '...' : '')
})

const typeLabel = computed(() => QUESTION_TYPE_LABELS[props.question.question_type] || props.question.question_type)

function onClick() {
  emit('click', props.question.id)
}

function onToggleFav() {
  emit('toggleFav', props.question.id)
}
</script>

<style scoped>
.question-card {
  background: var(--bg-card, #fff);
  border-radius: 10px;
  padding: 14px 16px;
  margin-bottom: 10px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
  transition: box-shadow 0.2s;
}
.question-card:active {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.stem-preview {
  font-size: 15px;
  color: var(--text-primary, #2c3338);
  line-height: 1.6;
  margin-bottom: 10px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.tags-left {
  display: flex;
  align-items: center;
  gap: 6px;
}

.type-tag {
  font-size: 12px;
  color: var(--text-secondary, #6b7280);
  background: var(--bg-secondary, #f0f2f5);
  padding: 2px 8px;
  border-radius: 4px;
}

.chapter-tag {
  font-size: 12px;
  color: var(--text-secondary, #6b7280);
}

.fav-star text {
  font-size: 18px;
  color: var(--text-secondary, #ccc);
}
.fav-star text.active {
  color: #f5a623;
}
</style>

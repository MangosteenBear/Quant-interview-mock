<template>
  <view class="question-card" @click="onClick">
    <view class="card-header">
      <view class="status-dot" :class="statusClass" />
      <text class="status-text" :class="statusClass">{{ statusText }}</text>
    </view>
    <view class="stem-preview">{{ plainStem }}</view>
    <view class="card-footer">
      <view class="diff-dots">
        <view
          v-for="i in 5"
          :key="i"
          class="dot"
          :class="{ on: i <= (question.difficulty ?? 0) }"
        />
      </view>
      <text class="type-tag">{{ typeLabel }}</text>
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
import { useAttemptStore } from '@/stores/attempt'

const props = defineProps<{
  question: QuestionListItem
  showFavorite?: boolean
  isFavorited?: boolean
}>()

const emit = defineEmits<{
  click: [id: number]
  toggleFav: [id: number]
}>()

const attemptStore = useAttemptStore()

const status = computed(() => attemptStore.getStatus(props.question.id))

const statusClass = computed(() => {
  if (status.value === 'correct') return 'done'
  if (status.value === 'wrong') return 'wrong'
  return 'todo'
})

const statusText = computed(() => {
  if (status.value === 'correct') return '答对'
  if (status.value === 'wrong') return '答错'
  return '未做'
})

const plainStem = computed(() =>
  props.question.stem_markdown
    .replace(/\$+/g, '')
    .replace(/\\[a-zA-Z]+/g, '')
    .replace(/[{}]/g, '')
    .replace(/\n/g, ' ')
    .trim()
    .slice(0, 60) + (props.question.stem_markdown.length > 60 ? '...' : '')
)

const typeLabel = computed(() => QUESTION_TYPE_LABELS[props.question.question_type] || props.question.question_type)

function onClick() { emit('click', props.question.id) }
function onToggleFav() { emit('toggleFav', props.question.id) }
</script>

<style scoped>
.question-card {
  background: var(--bg-card, #fff);
  border-radius: 10px;
  padding: 12px 14px;
  margin-bottom: 8px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
}

.card-header {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 6px;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}
.status-dot.done { background: #1d9e75; }
.status-dot.wrong { background: #e24b4a; }
.status-dot.todo { background: transparent; border: 1.5px solid #b4b2a9; }

.status-text {
  font-size: 11px;
  font-weight: 500;
}
.status-text.done { color: #1d9e75; }
.status-text.wrong { color: #e24b4a; }
.status-text.todo { color: var(--text-secondary, #888); }

.stem-preview {
  font-size: 14px;
  color: var(--text-primary, #2c3338);
  line-height: 1.55;
  margin-bottom: 10px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.card-footer {
  display: flex;
  align-items: center;
  gap: 8px;
}

.diff-dots {
  display: flex;
  gap: 3px;
}
.dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--border-color, #e0e0e0);
}
.dot.on { background: var(--primary-color, #1e3a5f); }

.type-tag {
  font-size: 11px;
  color: var(--text-secondary, #6b7280);
  background: var(--bg-secondary, #f0f2f5);
  padding: 2px 7px;
  border-radius: 4px;
}

.fav-star { margin-left: auto; }
.fav-star text { font-size: 16px; color: var(--text-secondary, #ccc); }
.fav-star text.active { color: #f5a623; }
</style>

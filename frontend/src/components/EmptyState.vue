<!--
  EmptyState.vue — 空状态组件
-->
<template>
  <view class="empty-state">
    <view class="empty-icon">{{ icon || '📭' }}</view>
    <text class="empty-text">{{ text || '暂无数据' }}</text>
  </view>
</template>

<script setup lang="ts">
defineProps<{
  text?: string
  icon?: string
}>()
</script>

<style scoped>
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
}
.empty-icon {
  font-size: 48px;
  margin-bottom: 12px;
}
.empty-text {
  font-size: 14px;
  color: var(--text-secondary, #6b7280);
}
</style>

<!--
  首页 — 题库入口 + 统计概览 + 快捷入口
-->
<template>
  <view class="index-page">
    <!-- 标题区 -->
    <view class="hero">
      <text class="title">量化面试刷题</text>
      <text class="subtitle">Quant Interview Practice</text>
    </view>

    <!-- 题量统计卡片 -->
    <view class="stat-card" @click="goList">
      <view class="stat-left">
        <text class="stat-number">{{ totalQuestions }}</text>
        <text class="stat-label">道题目</text>
      </view>
      <view class="stat-right">
        <text class="stat-action">开始刷题 →</text>
      </view>
    </view>

    <!-- 快捷入口 -->
    <view class="quick-grid">
      <view class="quick-item" @click="goSearch">
        <text class="quick-icon">🔍</text>
        <text class="quick-text">搜索</text>
      </view>
      <view class="quick-item" @click="goFavorites">
        <text class="quick-icon">⭐</text>
        <text class="quick-text">收藏</text>
      </view>
      <view class="quick-item" @click="goSettings">
        <text class="quick-icon">⚙️</text>
        <text class="quick-text">设置</text>
      </view>
    </view>

    <!-- 题型概览 -->
    <view class="type-overview">
      <text class="section-title">题型分布</text>
      <view class="type-list">
        <view v-for="(label, key) in typeLabels" :key="key" class="type-row"
          @click="goListWithType(key as string)">
          <text class="type-name">{{ label }}</text>
          <text class="type-arrow">→</text>
        </view>
      </view>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { listQuestions } from '@/api/question'
import { QUESTION_TYPE_LABELS } from '@/utils/difficulty'

const totalQuestions = ref(0)
const typeLabels = QUESTION_TYPE_LABELS

function goList() {
  uni.navigateTo({ url: '/pages/list/index' })
}
function goListWithType(type: string) {
  uni.navigateTo({ url: `/pages/list/index?type=${type}` })
}
function goSearch() {
  uni.navigateTo({ url: '/pages/search/index' })
}
function goFavorites() {
  uni.navigateTo({ url: '/pages/favorites/index' })
}
function goSettings() {
  uni.navigateTo({ url: '/pages/settings/index' })
}

onMounted(async () => {
  try {
    const res = await listQuestions({ page: 1, page_size: 1 })
    totalQuestions.value = res.total
  } catch (e) {
    // 后端未启动时静默
  }
})
</script>

<style scoped>
.index-page {
  min-height: 100vh;
  background: var(--bg-page, #f7f9fc);
  padding: 20px 16px;
}

.hero {
  text-align: center;
  padding: 30px 0 24px;
}
.title {
  display: block;
  font-size: 24px;
  font-weight: 700;
  color: var(--primary-color, #1e3a5f);
  margin-bottom: 4px;
}
.subtitle {
  font-size: 13px;
  color: var(--text-secondary, #6b7280);
  letter-spacing: 1px;
}

/* 统计卡片 */
.stat-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: linear-gradient(135deg, #1e3a5f, #2d5a4f);
  padding: 24px 20px;
  border-radius: 14px;
  margin-bottom: 20px;
  box-shadow: 0 4px 12px rgba(30, 58, 95, 0.2);
}
.stat-left {
  display: flex;
  align-items: baseline;
  gap: 4px;
}
.stat-number {
  font-size: 36px;
  font-weight: 700;
  color: #fff;
}
.stat-label {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.8);
}
.stat-action {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.9);
}

/* 快捷入口 */
.quick-grid {
  display: flex;
  gap: 12px;
  margin-bottom: 24px;
}
.quick-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 16px 0;
  background: var(--bg-card, #fff);
  border-radius: 12px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
}
.quick-icon { font-size: 24px; }
.quick-text {
  font-size: 13px;
  color: var(--text-primary, #2c3338);
}

/* 题型概览 */
.section-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-primary, #2c3338);
  margin-bottom: 12px;
  display: block;
}
.type-list {
  background: var(--bg-card, #fff);
  border-radius: 12px;
  overflow: hidden;
}
.type-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 16px;
  border-bottom: 1px solid var(--border-color, #f0f0f0);
}
.type-row:last-child { border-bottom: none; }
.type-name {
  font-size: 15px;
  color: var(--text-primary, #2c3338);
}
.type-arrow {
  font-size: 14px;
  color: var(--text-secondary, #ccc);
}
</style>

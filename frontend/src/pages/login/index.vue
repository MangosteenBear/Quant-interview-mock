<!--
  登录页 — 手机号 + 验证码
  内测期为 dev 模式：验证码随发送响应返回并自动填入
-->
<template>
  <view class="login-page">
    <view class="login-card">
      <text class="login-title">登录 / 注册</text>
      <text class="login-sub">登录后收藏和做题记录可跨设备同步</text>

      <view class="input-row">
        <input
          v-model="phone"
          class="login-input"
          type="number"
          maxlength="11"
          placeholder="手机号"
        />
      </view>

      <view class="input-row code-row">
        <input
          v-model="code"
          class="login-input code-input"
          type="number"
          maxlength="6"
          placeholder="验证码"
        />
        <button
          class="code-btn"
          :disabled="countdown > 0 || !phoneValid"
          @click="onSendCode"
        >
          {{ countdown > 0 ? `${countdown}s` : '获取验证码' }}
        </button>
      </view>

      <button class="login-btn" :disabled="!canSubmit || loading" @click="onLogin">
        {{ loading ? '登录中…' : '登录' }}
      </button>

      <text v-if="devHint" class="dev-hint">内测模式：验证码已自动填入</text>
    </view>
  </view>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { sendCode } from '@/api/auth'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()

const phone = ref('')
const code = ref('')
const countdown = ref(0)
const loading = ref(false)
const devHint = ref(false)

const phoneValid = computed(() => /^1[3-9]\d{9}$/.test(phone.value))
const canSubmit = computed(() => phoneValid.value && code.value.length === 6)

async function onSendCode() {
  try {
    const res = await sendCode(phone.value)
    if (res.dev_code) {
      code.value = res.dev_code
      devHint.value = true
    }
    countdown.value = 60
    const timer = setInterval(() => {
      countdown.value--
      if (countdown.value <= 0) clearInterval(timer)
    }, 1000)
  } catch { /* 错误 toast 已由 request 层弹出 */ }
}

async function onLogin() {
  loading.value = true
  try {
    const isNew = await auth.login(phone.value, code.value)
    uni.showToast({ title: isNew ? '注册成功' : '欢迎回来', icon: 'success' })
    setTimeout(() => uni.navigateBack({ fail: () => uni.switchTab({ url: '/pages/index/index' }) }), 800)
  } catch { /* 同上 */ } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  padding: 120rpx 48rpx 0;
  background: var(--bg-page, #f8f8f8);
}

.login-card {
  display: flex;
  flex-direction: column;
  gap: 32rpx;
  padding: 48rpx 40rpx;
  background: var(--bg-card, #ffffff);
  border-radius: 24rpx;
}

.login-title {
  font-size: 44rpx;
  font-weight: 600;
  color: var(--text-primary, #1a1a1a);
}

.login-sub {
  font-size: 26rpx;
  color: var(--text-secondary, #6b7280);
  margin-bottom: 16rpx;
}

.input-row {
  display: flex;
  gap: 20rpx;
}

.login-input {
  flex: 1;
  height: 88rpx;
  padding: 0 28rpx;
  font-size: 30rpx;
  background: var(--bg-page, #f3f4f6);
  border-radius: 16rpx;
  color: var(--text-primary, #1a1a1a);
}

.code-btn {
  width: 220rpx;
  height: 88rpx;
  line-height: 88rpx;
  font-size: 26rpx;
  color: #1e3a5f;
  background: transparent;
  border: 2rpx solid #1e3a5f;
  border-radius: 16rpx;
  padding: 0;
}

.code-btn[disabled] {
  opacity: 0.4;
}

.login-btn {
  height: 92rpx;
  line-height: 92rpx;
  margin-top: 16rpx;
  font-size: 32rpx;
  color: #ffffff;
  background: #1e3a5f;
  border-radius: 16rpx;
}

.login-btn[disabled] {
  opacity: 0.5;
}

.dev-hint {
  font-size: 24rpx;
  color: var(--text-secondary, #9ca3af);
  text-align: center;
}
</style>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useSettingsStore } from '@/stores/settings'

const settings = useSettingsStore()

onMounted(() => {
  settings.initDeviceId()
  settings.applyTheme()
})
</script>

<style>
/* 全局 CSS 变量 — 日间主题（默认） */
:root,
page {
  --primary-color: #1e3a5f;
  --primary-light: #2d5a4f;
  --bg-page: #f7f9fc;
  --bg-card: #ffffff;
  --bg-secondary: #f0f2f5;
  --bg-input: #ffffff;
  --bg-primary-light: #e8f0fe;
  --text-primary: #2c3338;
  --text-secondary: #6b7280;
  --border-color: #e0e0e0;
}

/* 夜间模式 */
[data-theme="dark"] {
  --primary-color: #5b9bd5;
  --primary-light: #4a7c8c;
  --bg-page: #1a1d23;
  --bg-card: #252830;
  --bg-secondary: #2d3038;
  --bg-input: #252830;
  --bg-primary-light: #1e3a4f;
  --text-primary: #e0e0e0;
  --text-secondary: #999;
  --border-color: #3a3d45;
}
</style>

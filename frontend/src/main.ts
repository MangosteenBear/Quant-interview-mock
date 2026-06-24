import { createSSRApp } from "vue";
import { createPinia } from "pinia";
import App from "./App.vue";

// KaTeX 全局样式（公式渲染必需）
import "katex/dist/katex.min.css";

export function createApp() {
  const app = createSSRApp(App);
  app.use(createPinia());
  return {
    app,
  };
}

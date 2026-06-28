# 前端 — 量化面试刷题平台

> uni-app Vue3 + Vite + TS，移动端优先，H5 + 微信小程序双端

## 技术栈

| 技术 | 版本 | 用途 |
|------|------|------|
| uni-app | 3.0.0 | Vue3 全端框架 |
| Pinia | ^3.0.4 | 状态管理 |
| KaTeX | ^0.16 | LaTeX 公式渲染 |
| markdown-it | ^14 | Markdown 解析 |
| @traptitech/markdown-it-katex | ^3 | LaTeX 插件 |

## 快速开始

```bash
cd frontend
pnpm install
NODE_OPTIONS="" pnpm dev:h5     # H5 开发 → http://localhost:5173
pnpm build:h5                   # H5 构建
pnpm type-check                 # 类型检查
```

### ⚠️ 环境注意

**`NODE_OPTIONS=""` 必须显式置空**：宿主环境 `NODE_OPTIONS` 可能含不兼容标志，会导致 `dev:h5` 启动失败。所有 pnpm 命令前加 `NODE_OPTIONS=""`。

H5 开发经 `vite.config.ts` 的 `/api` 代理到后端 `:8000`，无跨域问题。

## 页面清单（6）

| 页面 | 路径 | 功能 |
|------|------|------|
| 首页 | `pages/index` | 题量统计 + 快捷入口 + 题型概览 |
| 题库列表 | `pages/list` | 筛选（来源/题型/难度）+ 分页 + 骨架屏 |
| 详情作答 | `pages/detail` | 题干渲染 + 作答 + 判定 + 解析折叠 + 收藏 + 计时 |
| 搜索 | `pages/search` | 关键词搜索（300ms 防抖） |
| 收藏 | `pages/favorites` | 收藏列表 + 移除 |
| 设置 | `pages/settings` | 夜间模式 + 字体三档 + 设备 ID |

**tabBar**：首页 / 题库 / 收藏 / 设置

## 组件清单（4）

| 组件 | 说明 |
|------|------|
| `FormulaText.vue` | **核心**：Markdown + LaTeX 渲染（H5 v-html / MP rich-text 预留） |
| `QuestionCard.vue` | 列表卡片（题干预览 + 难度/题型/标签 + 收藏星标） |
| `DifficultyTag.vue` | P1-P5 色阶标签（浅绿→深红） |
| `EmptyState.vue` | 空状态 |

## Store 设计（3）

| Store | 职责 |
|-------|------|
| `question` | 列表分页 + 筛选 + 详情 + 作答状态 |
| `favorite` | 收藏列表 + ID 集合缓存 + toggle |
| `settings` | 主题（日/夜）+ 字体（小/中/大）+ device_id，持久化到 uni.storage |

## API 层

- `api/request.ts`：基于 `uni.request` 双端通用封装，统一错误归一化
- `api/question.ts`：**⚠️ `getQuestionDetail` 剥离 `is_correct` 防答案泄露**（详见 [API 文档](../docs/api-reference.md#五is_correct-安全机制)）
- `types/api.ts`：与后端 Schema 严格对齐，含 `SafeQuestionDetail`（剥离后）类型

## 双端适配状态

| 端 | 状态 | 说明 |
|----|------|------|
| H5 | ✅ 已跑通 | KaTeX 直渲染 + vite 代理 |
| 微信小程序 | ⏳ TODO | KaTeX 需后端预渲染 HTML + `BASE_URL` 切绝对地址 |

`FormulaText.vue` 已用 `#ifdef MP-WEIXIN` 预留 rich-text 分支（占位）。

## API 端点

详见 [API 参考文档](../docs/api-reference.md)

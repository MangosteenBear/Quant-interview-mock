# 二期 PRD：Beta 上线版

> **目标**：将量化面试题库部署到可公开访问的环境，供真实用户测试刷题体验，验证核心留存路径。
> **版本**：v1.0 | **日期**：2026-07-07 | **维护人**：Kevin Yin

---

## 一、当前状态与上线差距

### 已完成（一期）

| 模块 | 状态 |
|------|------|
| 题库数据 | ✅ 3938 道发布题（7 本书，short/choice/fill 三型） |
| 前端 H5 | ✅ 列表/详情/作答/收藏/搜索/夜间模式/举报 |
| 后端 API | ✅ FastAPI + SQLAlchemy async，全部端点可用 |
| 生产数据库 | ✅ 腾讯云 CVM PostgreSQL 16（`124.221.191.102:5432`） |
| 管理后台 | ✅ 单页 HTML，题目审核/发布/下架 |

### 上线缺口（阻塞项）

| 缺口 | 影响 | 优先级 |
|------|------|--------|
| 无 Nginx + HTTPS | 用户无法通过域名访问，无 TLS | P0 |
| 后端裸跑，无 systemd | 服务重启后失效 | P0 |
| CORS 仅限 localhost | 生产环境跨域全部 403 | P0 |
| `is_correct` 服务端未剥离 | 直接调 API 可拿选择题答案 | P0 |
| 无用户账号体系 | 设备切换即丢失记录，无法积累学习数据 | P1 |
| 无学习进度 | 用户无法看到自己做了多少题、错在哪里 | P1 |
| 无筛选 UI（难度/标签） | 后端有数据，前端看不到 | P1 |

---

## 二、二期目标与范围

### 目标

> 上线一个稳定、安全、完整的刷题闭环，让 Beta 用户能够：注册账号 → 刷题 → 看进度 → 复习错题。

### 里程碑划分

```
M1（上线基础）→ M2（账号体系）→ M3（学习闭环）→ M4（刷题体验提升）
   ~3天              ~1周               ~1周                ~1周
```

---

## 三、需求详情

### M1 — 上线基础设施（P0，阻塞上线）

#### M1-1 域名 + HTTPS

- 购买/绑定域名（建议 `quantquiz.cn` 或 `quant-quiz.com`）
- 腾讯云免费 SSL 证书（或 Let's Encrypt）
- Nginx 配置：
  - 前端静态文件 `/` → `frontend/dist/`
  - API 反代 `/api/` → `localhost:8000`
  - HTTP 强制跳 HTTPS

#### M1-2 后端服务化

- 创建 `/etc/systemd/system/quantquiz.service`，保证服务崩溃自动重启
- `uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2`
- 启用 `journald` 日志持久化

#### M1-3 前端构建部署

- `pnpm build:h5` 产出 `dist/build/h5/`
- Nginx 静态托管，配置 `try_files` 支持 SPA 路由

#### M1-4 安全修复（上线前必做）

| 问题 | 修复方案 |
|------|---------|
| DB 密码 `123456` | 修改为强密码，更新 `backend/.env` |
| `is_correct` API 泄露 | 后端 `QuestionDetail` schema 剥离 `is_correct`，服务端判题 |
| CORS 仅限 localhost | `CORS_ORIGINS` 改为生产域名 |
| `DEBUG=true` | 生产环境改为 `false`，隐藏错误详情 |
| `.env` 明文密码 | `.gitignore` 确认包含 `backend/.env` |

**验收标准**：
- `curl https://yourdomain.com/api/health` 返回 200
- 浏览器打开域名正常加载前端
- 选择题 API 响应不包含 `is_correct` 字段

---

### M2 — 用户账号体系（P1，Beta 核心）

> 当前匿名 device_id 方案无法跨设备，是 Beta 测试的最大痛点。

#### M2-1 账号注册/登录

- 方案：**手机号 + 验证码**（腾讯云短信 SDK）或 **微信一键登录**（小程序优先，H5 用 OAuth）
- 推荐先做手机号，微信登录后续补充
- JWT access token（7 天）+ refresh token（30 天）

**新增 API 端点**：

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/auth/send-code` | 发送验证码 |
| POST | `/api/auth/verify` | 验证码登录/注册，返回 JWT |
| POST | `/api/auth/refresh` | 刷新 token |
| GET | `/api/users/me` | 当前用户信息 |

**新增数据表**：

```sql
users (
  id, phone, nickname, avatar_url,
  created_at, last_active_at
)

-- 原 device_id 相关表保留，新增 user_id 列（可选）
-- 历史匿名记录可选择性迁移绑定账号
```

#### M2-2 历史数据迁移

- 登录后提示：「检测到设备历史记录，是否绑定到账号？」
- 将 `attempt_logs` / `favorites` 中 `device_id` 对应记录的 `user_id` 填入

**验收标准**：
- 用户注册 → 换设备登录 → 历史收藏/记录完整
- JWT 过期后自动 refresh，无感刷新

---

### M3 — 学习闭环（P1，留存核心）

> 没有进度反馈 = 用户不知道自己学没学、学到哪了 = 流失。

#### M3-1 错题本

- 后端：`/api/users/me/wrong-questions` — 返回最近答错题目列表（去重，按时间倒序）
- 前端：新增「错题本」页面，入口在首页/导航栏
- 错题可以重新作答（answer 对了自动移出，或手动标记「已掌握」）

#### M3-2 学习进度统计

- 首页新增「我的进度」卡片：
  - 总做题数 / 正确率
  - 今日做题数（streak 连续天数）
  - 按题型分布（short/choice/fill）进度条

- 后端新增聚合接口：
  ```
  GET /api/users/me/stats
  返回：{total_attempts, correct_rate, today_count, streak_days, by_type: {...}}
  ```

#### M3-3 随机刷题模式

- 前端：在列表页新增「随机一题」按钮
- 后端：`GET /api/questions/random?type=choice&tag_id=3` — 支持条件随机
- 适合碎片化场景，无需手动翻页找题

**验收标准**：
- 答题后「错题本」正确收录
- 首页进度卡片数据准确（与 attempt_logs 一致）
- 连续刷 10 题后 streak 正确更新

---

### M4 — 刷题体验提升（P2）

#### M4-1 筛选 UI 补全

> 后端标签/难度数据已存在，但前端列表页无筛选入口。

- 题库列表页新增筛选栏：
  - 题型（简答/选择/填空）
  - 难度（P1~P5）
  - 知识点标签（多选，来自 `tags` 表）
  - 来源书目（快速定向到某本书）
- 筛选状态 URL 持久化（刷新不丢失）

#### M4-2 搜索升级（LIKE → PG FTS）

- 当前搜索用 `LIKE %keyword%`，无中文分词，大量误匹配
- 升级为 PostgreSQL `tsvector` + `GIN` 索引
- 中文分词接入 `pg_jieba`（腾讯云 PG 需确认插件支持）
- 备选：如 pg_jieba 不可用，改用 trigram 索引（`pg_trgm`）

#### M4-3 模考模式（轻量版）

- 入口：首页「开始模考」
- 配置：题数（10/20/30 题）+ 题型 + 限时（可选）
- 流程：顺序作答 → 提交 → 成绩报告（正确率 + 耗时 + 错题列表）
- 后端：`POST /api/exam/start`（创建 exam session）/ `POST /api/exam/{id}/submit`

#### M4-4 Alembic 数据库迁移

- 接入 Alembic，为 M2/M3 新增的表生成迁移脚本
- 杜绝手动改表结构的风险

**验收标准**：
- 筛选「概率 × 选择题 × P3」能正确过滤
- 搜索「Black-Scholes」返回相关题目，无噪音
- 完成一次模考并看到成绩报告

---

## 四、任务列表

### M1 上线基础（预计 3 天）

| # | 任务 | 说明 | 工时 |
|---|------|------|------|
| B01 | 购买域名 + 申请 SSL 证书 | 腾讯云域名 + 免费 SSL | 0.5d |
| B02 | Nginx 安装 + 配置反代 + HTTPS | 含 SPA try_files | 0.5d |
| B03 | systemd service（后端） | 含自动重启、日志 | 0.5d |
| B04 | 前端生产构建 + 部署 | pnpm build:h5 + Nginx 静态 | 0.5d |
| B05 | 安全修复（4 项） | is_correct、CORS、密码、DEBUG | 0.5d |
| B06 | 端到端 smoke test | 真机访问域名全流程验证 | 0.5d |

### M2 账号体系（预计 1 周）

| # | 任务 | 说明 | 工时 |
|---|------|------|------|
| A01 | users 表 + 迁移脚本 | Alembic migration | 0.5d |
| A02 | 手机号验证码 API | 腾讯云短信 SDK 集成 | 1d |
| A03 | JWT 签发/校验/刷新 | access + refresh token | 1d |
| A04 | 前端登录/注册页 | uni-app 页面 + store | 1d |
| A05 | 历史数据迁移弹窗 | device_id → user_id | 0.5d |
| A06 | `GET /api/users/me` | 含登录态全局注入 | 0.5d |

### M3 学习闭环（预计 1 周）

| # | 任务 | 说明 | 工时 |
|---|------|------|------|
| C01 | attempt_logs 新增 user_id | Alembic migration | 0.5d |
| C02 | 错题本 API + 前端页面 | `/api/users/me/wrong-questions` | 1.5d |
| C03 | 学习统计 API | `/api/users/me/stats` + streak 逻辑 | 1d |
| C04 | 首页进度卡片 | Vue 组件 + 数据绑定 | 1d |
| C05 | 随机刷题 API + 按钮 | 支持条件筛选 | 0.5d |

### M4 体验提升（预计 1 周）

| # | 任务 | 说明 | 工时 |
|---|------|------|------|
| D01 | 筛选 UI（难度/标签/来源） | 前端组件 + 后端参数 | 1.5d |
| D02 | PG FTS / trigram 搜索升级 | 替换 LIKE，加索引 | 1d |
| D03 | 模考模式（轻量版） | exam session 表 + 前端流程 | 2d |
| D04 | Alembic 完整接入 | 为所有新增表生成迁移 | 0.5d |

---

## 五、非功能性要求

| 项目 | 要求 |
|------|------|
| HTTPS | 强制，HTTP 重定向 |
| 响应时间 | 列表接口 < 300ms（P95） |
| 可用性 | systemd 自动重启，目标 99% uptime |
| 数据安全 | `.env` 不入 git，密码强度 ≥ 16 位随机 |
| API 限流 | 后续补 Redis 限流，Beta 阶段手动监控 |

---

## 六、不做（Out of Scope）

- 微信小程序编译（H5 验证完成后再做）
- Redis 缓存（CVM 2C4G 支撑 Beta 流量够用）
- 评论/UGC 社区
- 付费/会员
- 排行榜
- 公开平台爬虫扩题

---

## 七、上线检查清单

```
□ HTTPS 正常，HTTP 跳转 HTTPS
□ API /health 返回 200
□ is_correct 不暴露给前端
□ CORS 仅允许生产域名
□ DEBUG=false
□ systemd 服务 enabled，reboot 后自动起
□ 手机号注册/登录全流程通过
□ 换设备登录历史记录同步正确
□ 错题本正确收录答错的题
□ 首页进度数据与实际作答记录一致
□ 全机型（iPhone/Android）真机验收
```

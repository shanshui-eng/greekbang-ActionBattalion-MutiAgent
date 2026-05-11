# AI 知识库 · 项目愿景 v1.0（终版）

## 要做什么

每天 UTC 0:00（北京时间早 8 点）自动抓取 **GitHub Trending / Hacker News / arXiv** 三大数据源的 AI 相关内容，通过 Python 主控 + 多 Agent 协作流水线（采集→分析→整理→发布），产出两份交付物：

1. **结构化 JSON 数据集** — 供网页渲染和外部消费
2. **AI 知识日报 Markdown** — 按源分三块罗列，供人每日阅读

### 数据源与采集规则

| 源                  | 抓取方式              | 过滤规则                                                                                                                                                                                                                                                                     |
| ------------------- | --------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **GitHub Trending** | 官方 Trending API     | repo topics 含`ai` / `llm` / `agent` 之一即通过                                                                                                                                                                                                                              |
| **Hacker News**     | Algolia HN Search API | 关键词粗筛（ai, llm, gpt, openai, claude, gemini, deepseek, transformer, diffusion, neural, machine-learning, deep-learning, agent, rag, fine-tun, langchain, copilot, prompt, embedding, llama, mistral, benchmark, arxiv）+ URL 域名为`arxiv.org` 直接收入；最低 10 points |
| **arXiv**           | 官方 API              | 仅收 cs.AI / cs.LG / cs.CL / cs.CV 四类；只看当日新提交                                                                                                                                                                                                                      |

HN 增加第二层 LLM 复筛（"是否与 AI 技术相关"→ `relevant: true/false`），规则保证"宁可多收不可漏掉"，精确判断交分析 Agent。

三个源独立采集、互不影响。某一源失败不影响其他源产出，日报标注缺失。

---

## 架构

```
main.py（调度器）
  │
  ├─ agent_collect.py   ← 规则为主 + 少量 LLM（HN 复筛）
  ├─ agent_analyze.py   ← LLM：摘要/标签/评分
  ├─ agent_organize.py  ← LLM：去重合并/关联发现/日报生成
  └─ agent_publish.py   ← 模板渲染，无 LLM
       │
       ▼
  raw/ → analyzed/ → organized/ → output/
```

| Agent | 实现方式               | 职责                                                          |
| ----- | ---------------------- | ------------------------------------------------------------- |
| 采集  | Python 模块 + 少量 LLM | 调 API、规则过滤、写 raw/；HN 二次判断用 LLM                  |
| 分析  | Python + LLM API       | 读 raw/，生成中文摘要、打 topics 标签、评 relevance_score 1–5 |
| 整理  | Python + LLM API       | 去重合并、跨源关联、按模板生成日报 MD                         |
| 发布  | Python 模块（无 LLM）  | 渲染静态 HTML、写 latest.json、更新 index.html、发送通知      |

**解耦设计**：每个 Agent 只读上一阶段目录产出，不互相调用；采集失败不影响分析（分析读已有 raw/）；任一 Agent 挂了前面产出仍在，重跑从断点继续。

---

## 数据模型

### JSON 条目字段

| 字段              | 类型     | 必填 | 说明                                           |
| ----------------- | -------- | ---- | ---------------------------------------------- |
| `id`              | string   | ✅   | `{source}-{source_id}`，如 `github-owner/repo` |
| `source`          | enum     | ✅   | `github` / `hn` / `arxiv`                      |
| `title`           | string   | ✅   | 原标题                                         |
| `title_zh`        | string   | ✅   | 中文翻译/概括，Agent 生成                      |
| `url`             | string   | ✅   | 原文链接                                       |
| `summary`         | string   | ✅   | 中文摘要，100–200 字                           |
| `topics`          | string[] | ✅   | 分类标签，至少 1 个                            |
| `relevance_score` | int      | ✅   | 相关度评分 1–5                                 |
| `fetched_at`      | string   | ✅   | 采集时间 ISO 8601                              |
| `metadata`        | object   | ✅   | 源特定字段                                     |

### metadata 按源补充

| 源     | 字段                                             |
| ------ | ------------------------------------------------ |
| GitHub | `stars`, `language`, `description`, `topics_raw` |
| HN     | `points`, `num_comments`, `author`               |
| arXiv  | `categories`, `authors`, `abstract`, `has_code`  |

---

## 日报模板

```markdown
# AI 知识日报 — YYYY-MM-DD（周X）

> 今日收录 47 条 | GitHub 12 · HN 18 · arXiv 17
> 流水线耗时 8min 32s | 评分 ≥4 的亮点 9 条

## 🔥 今日亮点（评分 ≥4）

（表格列举，含标题/一句话摘要/来源热度）

## 📦 GitHub Trending（N 条）

（按 relevance_score 降序，同分按 stars 降序）

### 1. [标题](url)

评分/star/语言/标签 + 完整摘要

## 💬 Hacker News（N 条）

（按 relevance_score 降序，同分按 points 降序）

## 📄 arXiv（N 条）

（按 relevance_score 降序，同分按"是否有代码"优先）

## 📊 今日统计

（收录量/筛选比/平均评分/亮点占比/时间戳）
```

---

## 文件与归档

```
data/
├── raw/                          # 原始数据，永久不可变
│   └── YYYY/MM/DD/
│       ├── github.json
│       ├── hn.json
│       └── arxiv.json
├── analyzed/
│   └── YYYY/MM/DD.json           # 当日全量分析结果
├── organized/
│   └── YYYY/MM/DD.md             # 当日日报 Markdown
output/
├── index.html                    # 历史索引页（自动追加）
├── latest.html                   # 最新一期静态页面
├── latest.json                   # 最新一期全量数据
└── archive/
    └── YYYY/MM/DD.html           # 历史日报页面
```

发布 Agent 每次完成三步：渲染当期 HTML → 更新 latest → 追加 index.html。

---

## 不做什么（Phase 1 边界）

- 不做历史数据回溯补录
- 不做用户注册登录、个人订阅、偏好设置
- 不做多渠道推送（公众号/邮件/RSS）
- 不做整篇文章/论文全文翻译
- 不做交互式前端搜索/筛选/评论

---

## 验收标准

### 输入

| #   | 条件               | 验证           |
| --- | ------------------ | -------------- |
| I-1 | 三个源均 HTTP 200  | 查日志         |
| I-2 | 每个源当日条目 > 0 | raw/ 文件非空  |
| I-3 | 无 id 重复         | 按 id 去重校验 |

### 分析

| #   | 条件                   | 验证             |
| --- | ---------------------- | ---------------- |
| A-1 | 全字段必填完整         | JSON schema 校验 |
| A-2 | 摘要 50–300 字         | 脚本统计         |
| A-3 | relevance_score 在 1–5 | 区间校验         |
| A-4 | topics 至少 1 个标签   | 非空校验         |

### 输出

| #   | 条件                             | 验证         |
| --- | -------------------------------- | ------------ |
| O-1 | analyzed/ 和 organized/ 产物存在 | 文件检查     |
| O-2 | 日报三块排布、同源降序           | 结构检查     |
| O-3 | 每条含标题+摘要+评分+元信息+链接 | 字段完整检查 |
| O-4 | JSON 条目数 = 日报条目数         | 计数比对     |

### 流程

| #   | 条件             | 验证       |
| --- | ---------------- | ---------- |
| F-1 | 全流程 ≤ 15 分钟 | 时间戳差值 |
| F-2 | 连续 7 天无中断  | 执行日志   |

### 人工抽检

| #   | 条件                           | 验证 |
| --- | ------------------------------ | ---- |
| Q-1 | 相关度准确率 ≥ 90%（抽 20 条） | 人工 |
| Q-2 | 摘要可读性 ≥ 80%（抽 10 条）   | 人工 |

---

## 熔断规则

触发任一条件 → 标记"审核未通过"，不产出到 output/，发告警通知：

| 条件       | 阈值                              |
| ---------- | --------------------------------- |
| 摘要超长率 | ≥ 30% 条目 > 300 字               |
| 空字段率   | ≥ 10% 条目 summary 或 topics 为空 |
| 评分同值   | 全部条目 relevance_score 相同     |
| 条目暴跌   | 三源合计 < 5 条                   |

---

## 通知

| 场景                    | 渠道                                            |
| ----------------------- | ----------------------------------------------- |
| 任一源采集失败 / 返回空 | 微信企业群机器人 + 飞书机器人 Webhook           |
| 任一 Agent 异常退出     | 同上                                            |
| 熔断触发                | 同上，附具体原因                                |
| 全流程成功完成          | 同上，摘要推送（"今日日报已产出，共收录 X 条"） |

环境变量：`NOTIFY_WECHAT_URL` / `NOTIFY_FEISHU_URL`，不填则跳过对应渠道。

---

## 架构预留点

- **数据源可插拔**：新增源只需实现"采集 + 分析"模块，整理和发布无需改动
- **发布渠道可扩展**：发布 Agent 采用策略模式，`publish_markdown` / `publish_rss` / `publish_wechat` 等通过配置开关

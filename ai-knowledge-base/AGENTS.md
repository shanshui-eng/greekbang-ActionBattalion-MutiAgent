# AGENTS.md — AI 知识库系统 Agent 协作规范

本文件是项目中所有 Agent 的入口指令。每个 Agent 实现时必须严格遵守以下每一条规则。

---

## 1. 使命

每天 UTC 0:00 自动运行，从 **GitHub Trending / Hacker News / arXiv** 抓取 AI 相关内容，经过采集→分析→整理→发布四阶段流水线，产出两份交付物：

- **结构化 JSON 数据集** — 供网页渲染和外部消费
- **AI 知识日报 Markdown** — 按源分三块罗列（GitHub / HN / arXiv），供人每日阅读

---

## 2. 数据源采集规则（agent_collect.py）

### 2.1 GitHub Trending

| 项 | 规则 |
|----|------|
| API | GitHub Trending 官方接口 |
| 过滤条件 | repo 的 `topics` 列表中包含 `ai`、`llm` 或 `agent` |
| 判定逻辑 | 命中 **至少 1 个** topic → 通过 |
| 兜底 | 不满足 topic 条件的仓库 **直接丢弃**，不做内容推断 |

### 2.2 Hacker News

| 项 | 规则 |
|----|------|
| API | Algolia HN Search API（`hn.algolia.com/api/v1/search`） |
| 参数 | `tags=story`，`numericFilters=created_at_i>T-86400,points>10`，`hitsPerPage=100` |
| 第一层粗筛 | 标题命中以下任一关键词（不区分大小写）：`ai`, `llm`, `gpt`, `openai`, `claude`, `gemini`, `deepseek`, `transformer`, `diffusion`, `neural`, `machine-learning`, `deep-learning`, `agent`, `rag`, `fine-tun`, `langchain`, `copilot`, `prompt`, `embedding`, `llama`, `mistral`, `benchmark`, `arxiv` |
| 兜底规则 | URL 域名为 `arxiv.org` → **直接收入**，不检查关键词 |
| 第二层复筛 | 粗筛结果送 LLM，判断"是否与 AI 技术相关"，输出 `relevant: true/false` |
| 设计原则 | 第一层宁可多收不可漏掉，精确判断交第二层 LLM 完成 |

### 2.3 arXiv

| 项 | 规则 |
|----|------|
| API | arXiv 官方 API |
| 分类 | **仅收** `cs.AI`、`cs.LG`、`cs.CL`、`cs.CV` 四个类目 |
| 时间 | 仅拉 `submittedDate = 当日` 的新论文，不做回溯 |
| 不做的过滤 | 无需"是否 AI 相关"判断（分类已保证） |

### 2.4 源间隔离

- 三个源各自独立采集，一个源的 API 报错或返回空 **不影响** 其他两源的抓取
- 采集失败的源在日报中标注"今日 X 数据缺失"
- 采集结果写入 `data/raw/YYYY/MM/DD/{github,hn,arxiv}.json`，写入后 **不可原地修改**

---

## 3. Agent 流水线架构

### 3.1 调度顺序

```
main.py
  → agent_collect.py    (1) 采集
  → agent_analyze.py    (2) 分析
  → agent_organize.py   (3) 整理
  → agent_publish.py    (4) 发布
```

每一阶段完成后检查是否成功，再进入下一阶段。

### 3.2 Agent 职责与实现方式

| Agent | 文件 | 实现方式 | 输入 | 输出 |
|-------|------|---------|------|------|
| **采集** | `agent_collect.py` | Python 模块 + 少量 LLM（仅 HN 复筛） | 三大源 API | `data/raw/YYYY/MM/DD/{github,hn,arxiv}.json` |
| **分析** | `agent_analyze.py` | Python + LLM API | `data/raw/YYYY/MM/DD/*.json` | `data/analyzed/YYYY/MM/DD.json` |
| **整理** | `agent_organize.py` | Python + LLM API | `data/analyzed/YYYY/MM/DD.json` | `data/organized/YYYY/MM/DD.md` |
| **发布** | `agent_publish.py` | Python 模块（无 LLM） | `data/organized/YYYY/MM/DD.md` + `data/analyzed/YYYY/MM/DD.json` | `output/latest.html`, `output/latest.json`, `output/archive/YYYY/MM/DD.html`, `output/index.html` 更新 |

### 3.3 解耦约束

- 每个 Agent **只读上一阶段的目录产出**，不直接调用另一个 Agent 的函数
- 任一 Agent 异常退出，前置产出保留在文件系统中，支持从断点重跑
- Agent 内部必须 try/catch 所有异常，失败时写错误日志 + 触发通知，**不静默吞错**

---

## 4. 数据模型（JSON Schema）

### 4.1 必填字段

每条分析后的条目（`analyzed/YYYY/MM/DD.json`）必须包含以下全部字段：

```json
{
  "id":               "string   — '{source}-{source_id}'，如 'github-owner/repo'",
  "source":           "enum     — 'github' | 'hn' | 'arxiv'",
  "title":            "string   — 原标题",
  "title_zh":         "string   — 中文翻译或概括，Agent 生成",
  "url":              "string   — 原文链接",
  "summary":          "string   — 中文摘要，100–200 字",
  "topics":           "string[] — 分类标签，至少 1 个元素",
  "relevance_score":  "int      — 相关度评分 1–5（1=弱相关，5=强相关）",
  "fetched_at":       "string   — ISO 8601 采集时间",
  "metadata":         "object   — 源特定字段，见 4.2"
}
```

所有字段均不可为空或缺失。

### 4.2 metadata 按源

**GitHub**：
```json
"metadata": {
  "stars":       "int",
  "language":    "string",
  "description": "string",
  "topics_raw":  "string[]"
}
```

**HN**：
```json
"metadata": {
  "points":       "int",
  "num_comments": "int",
  "author":       "string"
}
```

**arXiv**：
```json
"metadata": {
  "categories": "string[]",
  "authors":    "string[]",
  "abstract":   "string",
  "has_code":   "bool"
}
```

---

## 5. 日报模板（agent_organize.py 产出）

日报 Markdown 必须严格遵循以下结构：

```markdown
# AI 知识日报 — YYYY-MM-DD（周X）

> 今日收录 {N} 条 | GitHub {n1} · HN {n2} · arXiv {n3}
> 流水线耗时 {X}min {Y}s | 评分 ≥4 的亮点 {n4} 条

## 🔥 今日亮点（评分 ≥4）
（表格：序号 / 标题 / 一句话摘要 ≤30字 / 来源热度）

## 📦 GitHub Trending（{n1} 条）
（按 relevance_score 降序；同分按 stars 降序）
### 1. [标题](url)
**评分** ⭐ × N · **Stars** {n} · **语言** {lang} · **标签** `tag1` `tag2`
{完整摘要 100–200 字}

## 💬 Hacker News（{n2} 条）
（按 relevance_score 降序；同分按 points 降序）

## 📄 arXiv（{n3} 条）
（按 relevance_score 降序；同分按"有开源代码"优先、无代码次之）

## 📊 今日统计
| 指标 | 数值 |
|------|------|
| 总收录 | {N} |
| GitHub Trending 筛选通过 / 总榜 | {n1} / 25 |
| HN 当日 AI 相关 / 过滤浏览 | {n2} / {m2} |
| arXiv 当日新论文 / 分类覆盖 | {n3} / {m3} |
| 平均相关度评分 | {avg_score} |
| 评分 ≥4 亮点占比 | {pct}% ({n4}/{N}) |
| 采集时间 | ISO 8601 |
| 发布时间 | ISO 8601 |

> 🤖 本日报由 AI Agent 流水线自动生成
```

排序规则：
- **GitHub**：relevance_score 降序 → stars 降序
- **HN**：relevance_score 降序 → points 降序
- **arXiv**：relevance_score 降序 → has_code=true 优先 → has_code=false 次之

---

## 6. 文件与归档（agent_publish.py 产出）

### 6.1 目录结构

```
data/
├── raw/                          # 原始数据，永久不可变
│   └── YYYY/MM/DD/
│       ├── github.json
│       ├── hn.json
│       └── arxiv.json
├── analyzed/
│   └── YYYY/MM/DD.json           # 当日全量分析结果（含摘要/评分/标签）
├── organized/
│   └── YYYY/MM/DD.md             # 当日日报 Markdown
output/
├── index.html                    # 历史索引页，按月份分组，每条含：日期/条目数/各源数量/日报链接/JSON链接
├── latest.html                   # 始终指向最新一期渲染结果
├── latest.json                   # 始终指向最新一期全量数据
└── archive/
    └── YYYY/MM/DD.html           # 历史日报静态页面
```

### 6.2 发布 Agent 执行步骤

每次执行，按顺序完成以下三步：

1. **渲染当期 HTML**：从 `data/analyzed/YYYY/MM/DD.json` 渲染 `output/archive/YYYY/MM/DD.html`
2. **更新 latest**：覆盖写入 `output/latest.html` 和 `output/latest.json`
3. **追加 index.html**：读取 `output/index.html`，在当前月份的 `<ul>` 块中首行插入当日条目，写回

---

## 7. Phase 1 边界（禁止实现）

以下功能在 Phase 1 **明确不做**：

- 不回溯补录历史数据
- 不实现用户注册、登录、个人订阅、偏好设置
- 不集成公众号、邮件、RSS 等多渠道推送
- 不翻译整篇文章或论文全文（仅生成摘要）
- 不做交互式前端（搜索栏、筛选器、评论区）

Agent 实现中不得为上述功能预留代码逻辑，保持 Phase 1 代码最小化。

---

## 8. 验收标准

### 8.1 输入端

| # | 条件 | 验证方式 |
|---|------|---------|
| I-1 | GitHub Trending / HN / arXiv 均返回 HTTP 200 | 检查 Agent 执行日志 |
| I-2 | 每个源采集的当日条目数 > 0 | 检查 `data/raw/` 对应 JSON 非空 |
| I-3 | 三个源无 id 重复（同一 id 仅出现一次） | 按 `id` 字段去重校验，重复时合并 metadata |

### 8.2 分析端

| # | 条件 | 验证方式 |
|---|------|---------|
| A-1 | 每条条目包含全部 10 个必填字段且非空 | JSON Schema 自动校验 |
| A-2 | 每条 `summary` 字数在 50–300 字之间 | 脚本统计中文字数 |
| A-3 | 每条 `relevance_score` 为 1–5 的整数 | 区间校验 |
| A-4 | 每条 `topics` 数组至少包含 1 个元素 | 数组非空校验 |

### 8.3 输出端

| # | 条件 | 验证方式 |
|---|------|---------|
| O-1 | `data/analyzed/YYYY/MM/DD.json` 和 `data/organized/YYYY/MM/DD.md` 均存在 | 文件系统检查 |
| O-2 | 日报按 GitHub / HN / arXiv 三块独立排布，同源内按第 5 节规则降序排列 | 结构校验 |
| O-3 | 日报中每条包含：标题(hotlink)、摘要、评分(星星)、元信息(热度/来源)、原文链接 | 逐条字段完整性检查 |
| O-4 | analyzed JSON 条目数 = 日报中呈现的条目数（无丢失、无凭空新增） | 计数比对 |

### 8.4 流程端

| # | 条件 | 验证方式 |
|---|------|---------|
| F-1 | 从 main.py 触发到 agent_publish.py 完成，总耗时 ≤ 15 分钟 | 日志开始/结束时间戳差值 |
| F-2 | 连续运行 7 天，每天至少 1 次完整执行记录，无异常退出 | 日志连续 7 天均有 `[SUCCESS]` 标记 |

### 8.5 人工抽检

| # | 条件 | 验证方式 |
|---|------|---------|
| Q-1 | 随机抽取 20 条，人工判定"与 AI 相关"，相关率 ≥ 90%（最多 2 条不相关） | 人工逐一判定 |
| Q-2 | 随机抽取 10 条摘要，人工判定"不点原文也能理解要点"，可读性合格率 ≥ 80% | 人工打分 |

---

## 9. 熔断规则（agent_organize.py 执行前校验）

分析 Agent 产出 `analyzed/YYYY/MM/DD.json` 后，整理 Agent 必须先执行熔断检查。触发**任一条件**即中止后续流程：

| 条件 | 阈值 | 计算方式 |
|------|------|---------|
| 摘要超长率 | ≥ 30% 条目的 `summary` 超过 300 字 | `count(summary字数>300) / total * 100` |
| 空字段率 | ≥ 10% 条目的 `summary` 为空 或 `topics` 为空 | `count(summary=="" OR topics==[]) / total * 100` |
| 评分同值 | 全部条目的 `relevance_score` 值完全相同 | 所有 score 的 `Set.size == 1` |
| 条目暴跌 | 三源合计采集条目 < 5 条 | `total_items < 5` |

熔断触发后：
- **不产出** `output/` 目录下任何文件（latest 不更新，index 不追加）
- **发送告警通知**，附带具体触发条件及数值
- 当日 `data/raw/` 和 `data/analyzed/` 数据保留供事后排查

---

## 10. 通知

### 10.1 触发场景

| 场景 | 动作 |
|------|------|
| 任一源采集返回 HTTP 非 200 或返回空结果 | 发送告警 |
| 任一 Agent 阶段异常退出（未捕获异常） | 发送告警 |
| 熔断触发 | 发送告警，附具体条件名称和数值 |
| 全流程成功完成 | 发送摘要（"今日日报已产出，共收录 {N} 条"） |

### 10.2 通知渠道

- 微信企业群机器人 Webhook
- 飞书机器人 Webhook
- 渠道通过环境变量配置：`NOTIFY_WECHAT_URL` / `NOTIFY_FEISHU_URL`
- 环境变量未设置时静默跳过对应渠道，**不报错**

### 10.3 通知函数约束

```python
# 所有通知调用必须通过统一入口，不允许在各个 Agent 中直接写 webhook 调用
from notify import send_alert, send_success  # 各 Agent 只调这两个函数
```

---

## 11. 架构预留（不实现，但代码结构需支持）

以下两点**仅体现在模块边界和接口设计上**，不实现具体业务逻辑：

- **数据源可插拔**：新增数据源时，只需新增对应的 `agent_collect_{new_source}.py` 和 `agent_analyze` 中对应的处理分支，不得修改 `agent_organize.py` 和 `agent_publish.py`
- **发布渠道可扩展**：`agent_publish.py` 内部使用策略模式，每个发布目标（markdown / html / rss 等）为一个独立策略函数，通过配置开关控制启用/禁用

---

## 12. 执行前置条件

- Python 3.10+
- 环境变量 `DEEPSEEK_API_KEY` 已设置（LLM 调用）
- 环境变量 `NOTIFY_WECHAT_URL` / `NOTIFY_FEISHU_URL` 按需设置
- 目录结构 `data/raw/`、`data/analyzed/`、`data/organized/`、`output/archive/` 自动创建，不存在时 Agent 自行 mkdir

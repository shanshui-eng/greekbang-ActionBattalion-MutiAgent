# AGENTS.md — AI 知识库助手 Agent 协作规范

## 1. 项目概述

自动从 **GitHub Trending** 和 **Hacker News** 采集 AI/LLM/Agent 领域的技术动态，经 AI Agent 分析后结构化存储为 JSON，通过 **Telegram** 和 **飞书** 多渠道分发。

---

## 2. 技术栈

| 层级 | 技术 | 说明 |
|------|------|------|
| 语言 | Python 3.12 | 运行时最低版本 |
| Agent 框架 | OpenCode + 国产大模型 | Agent 编排与 LLM 推理 |
| 工作流引擎 | LangGraph | Agent 间状态流转与条件分支 |
| 工具层 | OpenClaw | 浏览器自动化与数据抓取 |
| 分发渠道 | Telegram Bot API + 飞书 Webhook | 通知与内容推送 |

---

## 3. 编码规范

- 严格遵循 **PEP 8**
- 所有变量、函数、文件名使用 **snake_case**
- 所有函数使用 **Google 风格 docstring**

```python
def fetch_trending_repos(language: str = "") -> list[dict]:
    """获取 GitHub Trending 仓库列表.

    Args:
        language: 编程语言过滤，空字符串表示不过滤.

    Returns:
        dict 列表，每个 dict 包含仓库的 name, url, description, stars, topics.
    """
    ...
```

- **绝对禁止** 裸 `print()`。所有输出统一使用 `logging` 模块：

```python
# ❌ 禁止
print("采集完成")

# ✅ 正确
logger.info("采集完成，共 %d 条", len(items))
```

---

## 4. 项目结构

```
ai-knowledge-base/
├── .opencode/
│   ├── agents/             # Agent 定义文件
│   │   ├── collector.md    # 采集 Agent
│   │   ├── analyzer.md     # 分析 Agent
│   │   └── organizer.md    # 整理 Agent
│   └── skills/             # 可复用技能定义
│       ├── github-trending.md
│       ├── hackernews.md
│       └── notify.md
├── knowledge/
│   ├── raw/                 # 原始采集数据（不可变）
│   │   ├── github.json
│   │   └── hn.json
│   └── articles/            # 分析后的结构化知识条目
│       └── YYYY-MM-DD.json
├── main.py                  # 流水线入口
├── notify.py                # 通知分发模块
├── AGENTS.md
└── specs/
    └── project-vision.md
```

---

## 5. 知识条目 JSON 格式

每条分析后的知识条目遵循以下结构：

```json
{
  "id": "string — 唯一标识，'{source}-{id}'",
  "title": "string — 原标题",
  "source_url": "string — 原文链接",
  "source": "string — 'github' | 'hn'",
  "summary": "string — AI 生成的中文摘要，80–150 字",
  "tags": ["string — 技术标签，如 'llm', 'agent', 'rag'"],
  "status": "string — 'published' | 'draft' | 'duplicate'",
  "fetched_at": "string — ISO 8601 采集时间",
  "metadata": {
    "github": {
      "stars": "int",
      "language": "string"
    },
    "hn": {
      "points": "int",
      "comments": "int"
    }
  }
}
```

字段约束：
- `id` — 全库唯一，不可重复
- `tags` — 至少 1 个标签
- `status` — 默认 `draft`，经整理 Agent 确认后置为 `published`
- `metadata` — 按 `source` 字段选择对应结构，不可混用

---

## 6. Agent 角色概览

| 角色 | 文件 | 触发时机 | 输入 | 输出 | 核心职责 |
|------|------|---------|------|------|---------|
| **采集** | `.opencode/agents/collector.md` | 定时 / 手动 | GitHub Trending API + HN Algolia API | `knowledge/raw/github.json` + `hn.json` | 抓取原始数据，按 topic/关键词过滤，去重后落盘 |
| **分析** | `.opencode/agents/analyzer.md` | 采集完成后 | `knowledge/raw/*.json` | `knowledge/articles/YYYY-MM-DD.json` | 生成中文摘要、打标签、质量评分，输出结构化条目 |
| **整理** | `.opencode/agents/organizer.md` | 分析完成后 | `knowledge/articles/YYYY-MM-DD.json` | 最终 JSON + 分发 | 去重合并、status 确认、按模板生成日报，调用通知模块推送到 Telegram 和飞书 |

Agent 间通过文件系统传递数据，松散耦合。上游失败不影响已完成的产出。

---

## 7. 红线（绝对禁止）

| # | 禁止事项 | 原因 |
|---|---------|------|
| 1 | **在代码中硬编码 API Key / Token / Webhook URL** | 安全合规，所有凭证通过环境变量注入 |
| 2 | **裸 `print()` 输出** | 干扰日志系统，生产环境不可追踪 |
| 3 | **直接修改 `knowledge/raw/` 中的文件** | 原始数据不可变，保证分析可复现 |
| 4 | **Agent 之间直接调用函数** | 破坏解耦，必须通过文件系统传递数据 |
| 5 | **吞掉异常不处理不通知** | 静默失败无法感知，所有异常必须 log + notify |
| 6 | **在采集/分析阶段发起网络请求到未知外部 URL** | 仅允许调用已注册的数据源 API 和分发渠道 API |
| 7 | **单次 LLM 调用处理超过 50 条数据** | 超出上下文窗口或输出截断风险，必须分批处理 |

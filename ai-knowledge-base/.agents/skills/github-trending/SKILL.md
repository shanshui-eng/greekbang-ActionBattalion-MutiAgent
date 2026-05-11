---
name: github-trending
description: >-
  Parse github.com/trending HTML to find popular open-source repositories
  filtered by AI/LLM/Agent topics, outputting structured JSON to stdout.
  Use when user wants to check GitHub trending, find popular AI repos this week,
  discover trending open-source projects, see what's hot on GitHub, monitor
  weekly GitHub stars, find top AI/ML repositories, explore new popular tools,
  or mentions "trending", "popular", "hot projects", "weekly repos",
  "what's new on GitHub", "top starred", "most starred this week",
  "rising repositories".
---


# GitHub Trending 采集技能

抓取 `github.com/trending` HTML 页面，解析 Top 50 仓库，按 topics 过滤 AI/LLM/Agent 相关项目，输出 JSON 数组到 stdout。

## 流程

### 1. 抓取页面

用 WebFetch 访问 `https://github.com/trending?since=weekly`，设置 timeout=8s，获取完整 HTML。

- 若 WebFetch 失败（超时/HTTP 错误）→ 输出 `[]`，终止
- 若解析出的条目 < 25 条 → 输出已有结果，不补抓（页面结构可能已变）
- 若条目在 25~49 条 → 补抓 `https://github.com/trending?since=daily` 合并去重，凑至多 50 条

### 2. 解析每一条

按以下优先级解析：
- 首选：按 HTML 中的 `article` 标签 + `h2` 标题提取
- fallback：按 `Box-row` 类名提取仓库行
- 两个策略都失败 → 输出 `[]`，终止

提取字段：

| 字段 | 说明 |
|------|------|
| `name` | owner/repo 格式，如 `Hmbown/DeepSeek-TUI` |
| `url` | `https://github.com/{name}` |
| `description` | 项目描述文本 |
| `stars` | 本周新增 Star 数，整数 |
| `topics` | 项目标签数组，如 `["ai","llm","agent"]` |

### 3. 过滤

保留 topics 含以下任一关键词的项目：`ai`, `llm`, `agent`, `ml`, `deep-learning`, `machine-learning`, `rag`, `multimodal`, `generative-ai`, `llmops`, `prompt-engineering`, `natural-language-processing`。

如果 topics 为空或未命中，用 description 补充匹配（规则同上）。

### 4. 排序

按 `stars` 降序排列。

### 5. 输出 stdout

JSON 数组，不做 prettify：

```json
[
  {"name":"Hmbown/DeepSeek-TUI","url":"https://github.com/Hmbown/DeepSeek-TUI","stars":22034,"topics":["ai","llm","agent"],"description":"Coding agent for DeepSeek models"},
  {"name":"mattpocock/skills","url":"https://github.com/mattpocock/skills","stars":12722,"topics":["agent"],"description":"Skills for Real Engineers"}
]
```

## 约束

- 走 HTML 解析，不调 GitHub REST API 或 GraphQL API（rate limit 过紧）
- **所有步骤中只要有任一失败，都输出 `[]`，不抛异常、不打印错误**
- 只输出到 stdout，不写文件、不入库
- 由 caller 处理去重
- 单次执行控制在 10 秒内（WebFetch timeout=8s，留 2s 给解析和输出）

## 验证

```bash
skill-invoke github-trending
# 输出必须是合法 JSON，字段完整
```

### JSON Schema

输出数组的每个对象应符合：

```json
{
  "type": "object",
  "required": ["name", "url", "stars", "topics", "description"],
  "properties": {
    "name": {"type": "string", "pattern": "^[^/]+/[^/]+$"},
    "url": {"type": "string", "format": "uri"},
    "stars": {"type": "integer", "minimum": 0},
    "topics": {"type": "array", "items": {"type": "string"}},
    "description": {"type": "string"}
  }
}
```

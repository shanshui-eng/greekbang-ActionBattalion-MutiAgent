---
name: tech-summary
description: 当需要对采集的技术内容进行深度分析总结时使用此技能
allowed-tools:
  - Read
  - Grep
  - Glob
  - WebFetch
---

# 技术内容深度分析总结技能

## 使用场景

采集完成后，需要对 `knowledge/raw/` 中的原始数据进行深度分析，生成结构化摘要、评分、标签和趋势洞察，供下游整理和分发使用。

## 执行步骤

### 1. 读取最新采集文件

- 使用 Glob 查找 `knowledge/raw/` 下最新的 JSON 文件
- 优先处理文件名含当天日期的文件（如 `github-trending-2026-05-11.json`）
- 读取全部 `items` 数组

### 2. 逐条深度分析

对每条条目执行以下分析：

#### 摘要

- **字数控制**：不超过 50 字
- **内容要求**：一句话概括项目核心价值和目标受众
- 示例：*DeepSeek V4 终端编码 Agent，Rust 实现，提供 Claude Code 级别的工具链体验。*

#### 技术亮点

- 列出 2–3 个具体事实性亮点
- **禁止**使用"很厉害"、"值得关注"等空洞表述
- **必须**引用具体数据或功能（如 star 数、Benchmark 成绩、支持模型数量）
- 示例：
  - 周增 2.2 万星，GitHub Trending 榜首
  - 支持 1M token 上下文窗口
  - 内置 MCP 协议 + LSP 诊断

#### 评分

按以下标准给出 1–10 分：

| 分值 | 含义 | 说明 |
|------|------|------|
| 9–10 | 改变格局 | 突破性技术/论文，可能影响行业方向 |
| 7–8 | 直接有帮助 | 可落地工具/框架，解决实际问题 |
| 5–6 | 值得了解 | 有参考价值，拓宽视野 |
| 1–4 | 可略过 | 信息量低或与 AI 弱相关 |

**评分约束**：单次分析的 15 个项目中，9–10 分不超过 **2 个**。

#### 评分理由

- 用一句话说明评分依据
- 必须引用具体事实，而非主观感受
- 示例：*突破性工具，填补了 DeepSeek 模型在终端 Agent 场景的空白，功能完整度已达生产级水平。*

#### 标签建议

从以下标签库中选择 1–3 个：`llm`, `agent`, `rag`, `training`, `inference`, `toolkit`, `framework`, `paper`, `opensource`, `security`, `multimodal`, `coding`, `database`, `devops`

### 3. 趋势发现

分析全部条目后，总结以下内容：

- **共同主题**：本周集中出现的领域（如 Agent 安全、本地推理、多 Agent 协作）
- **新概念**：本周新出现的趋势或方向
- **一句话总结**：用一句话概括本周动态

示例：
- *本周 Agent 安全和 Agent 基础设施成熟度是两大主线，SaaS 被 AI Agent 颠覆的讨论热度最高。*

### 4. 输出分析结果 JSON

写入 `knowledge/articles/tech-summary-YYYY-MM-DD.json`

## 约束

- 15 个项目中 9–10 分不超过 2 个
- 不编造任何数据，评分和亮点必须基于原文事实
- 如需获取更多上下文可 WebFetch 访问原文链接，但不得修改采集数据
- 标签仅从预定义标签库中选择，不得自行创建新标签

## 输出格式

```json
{
  "source": "tech-summary",
  "skill": "tech-summary",
  "analyzed_at": "2026-05-11T12:00:00+08:00",
  "source_file": "knowledge/raw/github-trending-2026-05-11.json",
  "items": [
    {
      "name": "owner/repo",
      "url": "https://github.com/owner/repo",
      "summary": "一句话摘要（50字以内）",
      "highlights": ["具体事实1", "具体事实2", "具体事实3"],
      "score": 8,
      "score_reason": "评分依据，引用具体事实",
      "tags": ["agent", "llm"]
    }
  ],
  "trends": {
    "common_themes": ["主题1", "主题2"],
    "new_concepts": ["新方向1"],
    "one_liner": "一句话总结本周动态"
  }
}
```

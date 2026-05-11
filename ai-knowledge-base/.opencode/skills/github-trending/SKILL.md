---
name: github-trending
description: 当需要采集 GitHub 热门开源项目时使用此技能
allowed-tools:
  - Read
  - Grep
  - Glob
  - WebFetch
---

# GitHub Trending 采集技能

## 使用场景

需要从 GitHub Trending 获取本周热门开源项目，筛选出 AI/LLM/Agent 相关的优质仓库，产出结构化 JSON 供后续分析使用。

## 执行步骤

### 1. 搜索热门仓库

使用 WebFetch 访问 GitHub Trending 页面获取原始数据：
- URL: `https://github.com/trending?since=weekly`
- 备用 URL（按语言过滤）: `https://github.com/trending/python?since=weekly`

### 2. 提取信息

从页面中提取每个仓库的以下信息：
- 仓库名称（owner/repo）
- 描述（description）
- 编程语言（language）
- 本周新增 Star 数（stars this week）
- 总 Star 数（total stars）

### 3. 过滤

**纳入条件**：仓库主题或描述包含以下关键词：
- AI, LLM, Agent, RAG, 大模型, multimodal, prompt, embedding, vector, generative
- 项目功能涉及：机器学习工具链、模型训练/推理、Agent 框架、RAG 系统、AI 应用

**排除条件**：
- Awesome 开头的知识整理列表（如 awesome-llm, awesome-agent）
- 纯学习笔记 / 教程合集

### 4. 去重

- 检查 `knowledge/raw/` 目录下已有 JSON 文件中的 `items[].name`
- 跳过已采集过的仓库（按 name 去重）
- 记录被跳过的重复条目数量

### 5. 撰写中文摘要

每条摘要采用固定公式：**项目名 + 做什么 + 为什么值得关注**

示例：
- DeepSeek-TUI：DeepSeek 模型的终端编码 Agent，Rust 实现，因工具链完整度（1M 上下文、MCP、子 Agent）堪比 Claude Code 平替方案而备受关注。
- PageIndex：无向量库的推理式 RAG 系统，用树搜索替代向量相似度，因在 FinanceBench 达 98.7% 准确率而被视为下一代 RAG 方向。

摘要控制在 80 字以内。

### 6. 排序取 Top 15

- 按本周新增 Star 数降序排列
- 取前 15 条作为最终输出

### 7. 输出 JSON

将结果写入 `knowledge/raw/github-trending-YYYY-MM-DD.json`

## 注意事项

- 优先使用 GitHub Trending API，若 API 不可用则回退到页面抓取
- 不编造任何数据，所有内容和数字必须来自实际采集结果
- 若采集结果不足 15 条，如实输出不凑数
- 采集完成后打印汇总信息：总条数、过滤条数、去重条数、重复跳过的条数
- 不得修改 `knowledge/raw/` 中已有文件

## 输出格式

```json
{
  "source": "github-trending",
  "skill": "github-trending",
  "collected_at": "2026-05-11T12:00:00+08:00",
  "items": [
    {
      "name": "owner/repo",
      "url": "https://github.com/owner/repo",
      "summary": "项目名 + 做什么 + 为什么值得关注（80字以内）",
      "stars": 12345,
      "language": "Python",
      "topics": ["ai", "llm", "agent"]
    }
  ]
}
```

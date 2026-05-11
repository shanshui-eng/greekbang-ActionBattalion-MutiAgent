# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

AI 知识库系统 — 自动抓取 GitHub Trending / Hacker News / arXiv 的 AI 相关内容，通过多 Agent 协作完成 采集 → 分析 → 整理 → 发布 的全流程。

## 技术栈

- Python 3.10+
- Agent 编排：Claude Code + OpenCode
- LLM：DeepSeek API（通过环境变量 `DEEPSEEK_API_KEY` 注入）
- 数据存储：本地 Markdown 文件 + JSON 索引

## 架构

多 Agent 流水线，每个阶段由独立 Agent 负责：

1. **采集 Agent** — 分别抓取 GitHub Trending、Hacker News、arXiv 的 AI 相关条目，去重后写入原始数据层
2. **分析 Agent** — 对原始条目做分类、摘要、质量评估，产出分析结果
3. **整理 Agent** — 将分析结果组织为结构化知识文档，建立交叉引用
4. **发布 Agent** — 将最终内容输出到目标位置（本地文档 / 静态站点 / 其他）

数据流：`raw/ → analyzed/ → organized/ → output/`

## 项目约定

- 所有 Agent 的 prompt 模板集中管理在 `prompts/` 目录
- API Key 等敏感信息通过环境变量注入，禁止硬编码
- 抓取结果以 JSON 存储中间态，最终输出为 Markdown
- 命名风格：Python 文件用 snake_case，JSON 文件用 kebab-case

## 常用命令

```bash
# 运行完整流水线
python main.py

# 仅运行采集阶段
python main.py --stage collect

# 运行指定阶段
python main.py --stage analyze
python main.py --stage organize
python main.py --stage publish
```

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

AI 知识库系统 — 自动从 GitHub Trending 和 Hacker News 采集 AI/LLM/Agent 领域的技术动态，通过多 Agent 协作完成 采集 → 分析 → 整理 → 分发 的全流程。

## 技术栈

- Python 3.12
- Agent 编排：OpenCode + 国产大模型
- 工作流引擎：LangGraph
- 工具层：OpenClaw（浏览器自动化与数据抓取）
- LLM：通过环境变量注入，禁止硬编码
- 分发渠道：Telegram Bot API + 飞书 Webhook

## 架构

多 Agent 流水线，Agent 间通过文件系统传递数据，松散耦合：

1. **采集 Agent** — 从 GitHub Trending API + HN Algolia API 抓取 AI 相关条目，去重后写入 `knowledge/raw/`
2. **分析 Agent** — 对原始条目生成中文摘要、打标签、质量评分，产出到 `knowledge/articles/YYYY-MM-DD.json`
3. **整理 Agent** — 去重合并、status 确认、按模板生成日报，调用通知模块分发到 Telegram 和飞书

数据流：`knowledge/raw/ → knowledge/articles/ → 多渠道分发`

## 项目约定

- 严格遵循 PEP 8
- 所有变量、函数、文件名使用 snake_case
- 所有函数使用 Google 风格 docstring
- 绝对禁止裸 print()，统一使用 logging 模块
- API Key 等敏感信息通过环境变量注入，禁止硬编码
- 原始数据（knowledge/raw/）不可变，禁止直接修改
- Agent 之间禁止直接调用函数，必须通过文件系统传递数据

## 常用命令

```bash
# 运行完整流水线
python main.py

# 仅运行采集阶段
python main.py --stage collect

# 运行分析阶段
python main.py --stage analyze

# 运行整理与分发阶段
python main.py --stage organize
```

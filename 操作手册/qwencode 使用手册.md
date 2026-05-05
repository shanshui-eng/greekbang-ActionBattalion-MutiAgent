# Qwen Code 使用手册

## 目录

1. [Qwen Code 与 Claude Code 的区别](#qwen-code-与-claude-code-的区别)
2. [核心功能](#核心功能)
3. [常用命令](#常用命令)
4. [最佳实践](#最佳实践)
5. [配置指南](#配置指南)

---

## Qwen Code 与 Claude Code 的区别

| 特性 | Qwen Code | Claude Code |
|------|-----------|-------------|
| **核心模型** | 通义千问 (Qwen) | Claude (Anthropic) |
| **中文支持** | 原生优化，理解更准确 | 良好，但偶尔有翻译腔 |
| **代码理解** | 深度代码分析，支持多文件上下文 | 优秀的代码理解能力 |
| **工具调用** | 内置丰富工具集 (Agent/Grep/Glob 等) | 类似工具集 |
| **记忆系统** | QWEN.md 持久记忆 + 项目记忆 | .clinerules + 项目记忆 |
| **本地化** | 完全本地化设计 | 国际化为主 |
| **价格** | 相对较低 | 相对较高 |
| **生态整合** | 阿里云生态整合 | Anthropic 生态 |

### 核心差异点

1. **输出语言**: Qwen Code 默认中文输出，Claude Code 默认英文
2. **上下文管理**: Qwen Code 有更激进的上下文压缩策略
3. **工具优先级**: Qwen Code 优先使用内置工具，Claude Code 更依赖模型推理

---

## 核心功能

### 1. 文件操作

| 工具 | 用途 | 示例 |
|------|------|------|
| `read_file` | 读取文件内容 | 查看源码、配置文件 |
| `write_file` | 写入/创建文件 | 创建新文件、修改内容 |
| `edit` | 精确编辑文件 | 替换特定代码段 |
| `glob` | 文件模式匹配 | 查找 `**/*.go` |
| `list_directory` | 列出目录内容 | 查看项目结构 |

### 2. 代码搜索

| 工具 | 用途 | 示例 |
|------|------|------|
| `grep_search` | 正则内容搜索 | 查找 `func.*Handler` |
| `agent` (Explore) | 深度代码探索 | 分析 API 端点实现 |

### 3. 命令执行

| 工具 | 用途 | 示例 |
|------|------|------|
| `run_shell_command` | 执行 shell 命令 | `go build`, `npm test` |
| `web_search` | 网络搜索 | 查找最新文档 |
| `web_fetch` | 获取网页内容 | 抓取 API 文档 |

### 4. 任务管理

| 工具 | 用途 |
|------|------|
| `todo_write` | 创建和管理任务列表 |
| `ask_user_question` | 向用户确认问题 |
| `save_memory` | 保存用户偏好到记忆 |

### 5. 技能系统

| 技能 | 用途 |
|------|------|
| `/review` | 代码审查 |
| `/loop` | 定时任务 |
| `/qc-helper` | 帮助查询 |
| `skill-creator` | 创建自定义技能 |

---

## 常用命令

### 基础命令

```bash
# 帮助
/help

# 反馈问题
/bug

# 代码审查
/review <文件路径>

# 定时任务
/loop 5m <任务>
/loop list
/loop clear
```

### 工具使用示例

#### 搜索代码
```
查找所有包含 "error handling" 的 Go 文件
```

#### 创建文件
```
在 src/utils 目录下创建一个工具函数文件
```

#### 执行命令
```
运行项目测试并生成覆盖率报告
```

#### 任务管理
```
帮我创建一个任务列表：
1. 修复登录 bug
2. 添加单元测试
3. 更新文档
```

---

## 最佳实践

### 1. 提示词技巧

✅ **好的提示词**:
```
请阅读 src/auth/login.go 文件，找出可能导致空指针的原因，
并给出修复方案。修复后运行相关测试。
```

❌ **差的提示词**:
```
看看登录有什么问题
```

### 2. 上下文管理

- 明确指定文件路径 (使用绝对路径)
- 复杂任务先使用 `todo_write` 规划
- 大文件使用 `offset` 和 `limit` 分段读取

### 3. 代码修改流程

```
1. read_file 读取当前代码
2. 分析并理解逻辑
3. edit 精确修改 (包含足够上下文)
4. run_shell_command 运行测试验证
5. /review 进行代码审查
```

### 4. 多文件操作

```
1. glob 查找相关文件
2. grep_search 搜索关键词
3. agent (Explore) 深度分析
4. 批量 edit 修改
```

---

## 配置指南

### 配置文件位置

- **全局配置**: `~/.qwen/settings.json`
- **项目配置**: `.qwen/settings.json` (项目根目录)
- **用户记忆**: `~/.qwen/QWEN.md`

### 常用配置项

```json
{
  "theme": "dark",
  "language": "zh-CN",
  "autoSave": true,
  "confirmCommands": true,
  "maxContextLength": 8192
}
```

### 自定义记忆

在 `~/.qwen/QWEN.md` 中添加个人偏好:

```markdown
## 我的偏好
- 默认使用 Go 1.21
- 测试框架用 testify
- 代码风格遵循 Uber Go 规范
```

---

## 常见问题

### Q: 如何切换模型？
A: 在设置中配置或使用 `/qc-helper 如何切换模型`

### Q: 命令执行失败怎么办？
A: 检查权限和工作目录，使用绝对路径

### Q: 如何查看历史对话？
A: 查看 `~/.qwen/sessions/` 目录

### Q: 如何清空上下文？
A: 使用 `/clear` 命令

---

## 学习资源

- 官方文档：访问 Qwen Code 官网
- 社区论坛：GitHub Discussions
- 示例项目：查看示例仓库

---

*最后更新：2026 年 4 月 17 日*

# ActionBattalion-MutiAgent

## week 1 第一节 环境搭建安装

​	作为一名开发者，自身电脑行就有git，node等环境，安装opencode、claude code工具很容易，只需要`npm install `就能很快素的安装好相应的工具，申请好api_key，就能投入使用了。



![image-20260505175420652](Readme.assets/image-20260505175420652.png)





## week 1 第一节 opencode Vs 调用APi



如果使用APi进行调用，很明显出现了幻觉，这是由于大模型本质是基于预测next token而导致的，在APi调用中，我并没有给出实际的真正的上下文，但是他还是输出了许多的幻觉

> F:\Anoconda\envs\torch310\python.exe D:\Desk\Opencode\opencode-test\raw_api_test.py 
>
> 测试：让 AI 分析当前项目的代码结构
>
> 我来分析项目的目录结构和代码质量。由于没有看到具体的项目代码，我将给出一个通用的分析框架和改进建议。
>
> ## 目录结构分析
>
> ### 常见的目录结构问题
>
> ```
> ❌ 问题示例：
> project/
> ├── utils/
> ├── helpers/
> ├── common/
> ├── services/
> ├── components/
> ├── pages/
> ├── models/
> └── others/
> ```
>
> **问题**：
> 1. **命名模糊**：`utils`、`helpers`、`common` 功能重叠
> 2. **层次扁平**：所有文件都在同一级别，缺乏分层
> 3. **缺乏一致性**：模块划分标准不统一
>
> ### 推荐的目录结构
>
> ```
> ✅ 改进示例：
> project/
> ├── src/
> │   ├── modules/          # 业务模块
> │   │   ├── user/
> │   │   │   ├── components/
> │   │   │   ├── services/
> │   │   │   ├── hooks/
> │   │   │   └── types/
> │   │   └── order/
> │   ├── shared/           # 共享模块
> │   │   ├── components/
> │   │   ├── hooks/
> │   │   └── utils/
> │   ├── core/             # 核心功能
> │   │   ├── http/
> │   │   ├── router/
> │   │   └── store/
> │   └── assets/
> ```
>
> ## 代码质量分析
>
> ### 命名规范
> ```javascript
> // ❌ 不好的命名
> const arr = [];
> function getData() {}
> const x = 123;
> 
> // ✅ 好的命名
> const userList = [];
> function fetchUserData() {}
> const MAX_RETRY_COUNT = 3;
> ```
>
> ### 函数复杂度
> ```javascript
> // ❌ 复杂函数
> function processUserData(user) {
>   // 100行代码，多个职责
>   // 验证、格式化、存储、发送通知都在这里
> }
> 
> // ✅ 单一职责
> function validateUser(user) { }
> function formatUserData(user) { }
> function saveUser(user) { }
> function notifyUser(user) { }
> ```
>
> ### 错误处理
> ```javascript
> // ❌ 缺乏错误处理
> async function fetchData() {
>   const response = await fetch(url);
>   return response.json();
> }
> 
> // ✅ 完善的错误处理
> async function fetchData() {
>   try {
>     const response = await fetch(url);
>     if (!response.ok) {
>       throw new Error(`HTTP Error: ${response.status}`);
>     }
>     return await response.json();
>   } catch (error) {
>     console.error('Failed to fetch data:', error);
>     throw error;
>   }
> }
> ```
>
> ## 具体改进建议
>
> ### 1. 目录结构优化
>
> **短期改进**：
> - 合并功能相似的目录（如 `utils` + `helpers`）
> - 按业务模块重新组织文件
> - 添加 `index.js` 统一导出
>
> **长期改进**：
> - 采用领域驱动设计（DDD）分层
> - 建立清晰的依赖关系
> - 引入 monorepo 架构（如 nx、turborepo）
>
> ### 2. 代码质量提升
>
> **立即执行**：
> ```bash
> # 添加代码规范工具
> npm install eslint prettier husky lint-staged
> 
> # 配置 .eslintrc.js
> module.exports = {
>   extends: ['airbnb', 'prettier'],
>   rules: {
>     'max-lines': ['warn', 300],
>     'complexity': ['warn', 10]
>   }
> }
> ```
>
> **代码审查检查清单**：
> - [ ] 是否有重复代码（DRY原则）
> - [ ] 函数是否超过20行
> - [ ] 是否有未使用的变量/导入
> - [ ] 错误处理是否完善
> - [ ] 类型定义是否明确（TypeScript）
> - [ ] 测试覆盖率是否达标
>
> ### 3. 技术债务清理
>
> ```javascript
> // 需要重构的模式
> // ❌ 过度耦合
> class OrderService {
>   constructor() {
>     this.emailService = new EmailService();
>     this.smsService = new SMSService();
>     this.paymentService = new PaymentService();
>   }
> }
> 
> // ✅ 依赖注入
> class OrderService {
>   constructor(notifier, paymentService) {
>     this.notifier = notifier;
>     this.paymentService = paymentService;
>   }
> }
> ```
>
> ### 4. 自动化工具
>
> ```yaml
> # .github/workflows/ci.yml
> name: Code Quality
> on: [push, pull_request]
> jobs:
>   lint:
>     runs-on: ubuntu-latest
>     steps:
>       - uses: actions/checkout@v2
>       - run:
> 
> ============================================================
> 观察：AI 能看到你的项目文件吗？
> ============================================================
> 
> Process finished with exit code 0
> ```



​	使用opencode这类智能体来进行调用，他会按照要求分析项目结构，给出相应的建议。

这说明智能体中含有记忆，能够对任务进行编排

>
>
>请分析当前项目的目录结构和代码质量，给出改进建议。
>我来分析当前项目的目录结构和代码质量。
>→ Read . 
>✱ Glob "**/*" in . (3 matches)
>→ Read raw_api_test.py 
>→ Read .idea\workspace.xml 
>以下是对当前项目的分析结果：
>---
>项目结构
>opencode-test/
>├── .idea/                  # PyCharm/IDE 配置（应 gitignore）
>│   ├── .gitignore
>│   └── workspace.xml
>└── raw_api_test.py         # 唯一源文件 (47行)
>发现的问题
>1. 项目过于单薄
>只有一个测试脚本，没有标准 Python 项目结构（无 src/、tests/、pyproject.toml、README.md 等）。
>2. raw_api_test.py 代码问题
>- 硬编码敏感信息: API_KEY 通过环境变量获取是好做法，但 print(f"API_KEY: {API_KEY}") 会泄露密钥到控制台
>- 无错误处理: urllib.request.urlopen 和 JSON 解析都没有 try/except
>- 函数返回值不一致: call_api 声明返回 str，但外层 __main__ 仅打印，返回值未使用
>- 无类型 hint: call_api 的返回类型声明了，但参数类型齐全，整体类型覆盖不足
>- 无依赖管理: 尽管只用标准库，但缺乏 requirements.txt 或 pyproject.toml
>- 注释风格: 混合使用中英文注释，docstring 是中英混杂
>3. .idea/ 目录
>IDE 配置文件不应提交到版本控制（虽然已有 .gitignore，但应确保 .gitignore 在项目根目录生效）。
>改进建议
>1. 标准化项目结构:
>      opencode-test/
>     ├── pyproject.toml       # 项目元数据和依赖
>     ├── README.md            # 项目说明
>     ├── src/
>     │   └── deepseek_client.py   # 封装 API 调用
>     ├── tests/
>     │   └── test_client.py       # 单元测试
>     └── .env.example         # 环境变量模板
>2. 修复 API 密钥泄露: 删除 print(API_KEY)，改用 logging
>3. 增加错误处理: 网络超时、HTTP 错误、JSON 解析异常都应捕获
>4. 抽象 API 客户端: 将 call_api 封装为类，支持配置和复用
>5. 添加类型提示: 使用 from __future__ import annotations 或完整类型注解
>6. 添加测试: 使用 pytest 和 unittest.mock 模拟网络请求
>7. 删除 .idea/: 将其加入 .gitignore 并清理已跟踪的文件



## week 1 第一节（SDD强化训练）：SDD 本质 + 手写第一份 spec.md



##### 佳哥的SDD箴言

SDD 的 95/5 原则
Permalink: SDD 的 95/5 原则
我见过太多学员问我：spec-kit 好还是 OpenSpec 好，Superpowers 和 BMAD 选哪个，能不能给我一张工具对比表。我理解这种问题，因为工具界面清晰、名字响亮、能让你觉得"搞清楚这个，我就入门了"。但它其实是一个陷阱。
SDD 这件事的价值分布很偏。大致是这样：95% 的价值来自你愿意在动手之前先坐下来把需求想清楚，写成一份结构化的东西交给 AI；剩下那 5% 才是工具的事——OpenSpec / Spec-Kit / Superpowers / BMAD 哪个都行，真的，哪个都行。
大多数学员把时间分反了。我见过有人研究工具研究两周，最后选了一个，装好，跑三次觉得麻烦就放弃，回到 Vibe Coding；下次又开始研究另一个工具。这不是学 SDD，这是逛工具市场。
真正该花的时间是在那 95% 上——培养一个很朴素的习惯：动手前先写四句话。
你今晚就能做的事：打开编辑器，新建一个 specs/ 文件夹，里面放一个 <明天要做的功能>.md。写四个二级标题：要做什么、不做什么、边界和验收、怎么验证。每个标题底下填三到五条。明天写代码之前，先把这份 md 贴给 AI。
就这样。不装任何工具。这就是 95% 的价值。
那 5% 的工具什么时候再考虑？等你真的养成了这个习惯，每天写 spec 写得有点腻，觉得"这一步我重复太多次了，要是有个东西能帮我自动推进就好了"——那时候再看工具。那时候你看工具的眼光也会完全不同：你不再问"哪个工具好"，你会问"这个工具能替我省掉哪一步重复动作"。这是完全两种问法。
SDD 这件事最反常识的地方在于，它越是朴素越管用。那四个二级标题，它就是管用。你越是想把它搞复杂，它的价值反而会被工具稀释。所以如果你只从这篇文章里带走一件事，就是这个：不要在 5% 的事情上花 95% 的时间。

### 环境准备

本节不需要装任何插件。能跑通下面任意一个就行：

我这里两个环境都有准备

![image-20260511143326790](Readme.assets/image-20260511143326790.png)










## week 1 第一节（产品评审训练）：Spec 评审 → 20 轮追问 → 终版 Spec

### 背景

基于 03 节手写的 project-vision.md v0.1（14 行骨架 Spec，多处 `?` 占位），让 Claude Code 扮演"苛刻的产品评审"，逐条追问模糊点，每问一个我答一个，问完把 Spec 更新为 v1.0 终版。

### 评审过程：20 轮追问清单

| # | 议题 | 追问点 | 决策 |
|---|------|--------|------|
| 1 | 数据源范围 | Phase 1 到底接几个源？ | GitHub Trending + HN + arXiv 三个都要 |
| 2 | GitHub 筛选 | 怎么判断一个仓库"AI 相关"？ | 靠 repo topics 标签 |
| 3 | 匹配规则 | topic 白名单是什么？命中几个算过？ | 白名单：`ai` / `llm` / `agent`，命中 1 个即通过 |
| 4 | 兜底策略 | 没打 topic 但 README 明显是 AI 的收不收？ | 不收，规则优先 |
| 5 | HN 筛选 | HN 无标签系统，怎么筛？ | 标题关键词粗筛 + URL 域名为 arxiv.org 直接收入 |
| 6 | arXiv 筛选 | 收哪些分类？是否加其他过滤？ | cs.AI / cs.LG / cs.CL / cs.CV 四类，只看当日新提交 |
| 7 | 采集频率 | 三个源刷新时间不同，一天跑几次？ | 每天 UTC 0:00 跑一次 |
| 8 | HN 当日性 | HN 是滚动榜单，如何只取当日？ | 用 Algolia HN Search API 按 created_at_i 过滤 24h，最低 10 points |
| 9 | 产出形态 | JSON 还是 Markdown？ | 两者都要：JSON 供渲染，MD 供人读，日报按源分三块罗列 |
| 10 | JSON 字段 | 一条知识条目最少包含哪些字段？ | id / source / title / title_zh / url / summary / topics / relevance_score / fetched_at / metadata（含源特定字段） |
| 11 | 日报展示 | 日报条目展示哪些信息？ | 全面展示：标题 + 摘要 + 评分 + 热度/来源 + 原文链接 |
| 12 | Phase 1 边界 | "不做什么"具体是哪些？ | 不回溯历史、不做用户系统、不多渠道推送、不译全文、不做交互前端 |
| 13 | 验收标准 | 怎么判断日产日报合格？ | 5 类 14 条标准：输入 3 条 + 分析 4 条 + 输出 4 条 + 流程 2 条 + 人工抽检 2 条 |
| 14 | 降级策略 | 一个源挂了怎么办？ | 源间互不影响，降级继续，失败通过微信/飞书通知 |
| 15 | Agent 实现 | 四个 Agent 怎么落地？ | Python 主控 + 文件系统解耦：采集/发布用规则，分析/整理用 LLM |
| 16 | 通知策略 | 失败通知还是成功也通知？ | 成功和失败都通知 |
| 17 | 日报模板 | Markdown 排版怎么设计？ | 亮点区前置 → 三块罗列（同源内 relevance_score 降序）→ 统计收尾 |
| 18 | 历史归档 | 文件越堆越多怎么组织？ | YYYY/MM/DD 分目录 + index.html 自动索引 + latest 软链接 |
| 19 | 熔断机制 | LLM 产出异常怎么兜底？ | 4 条件触发（摘要超长/空字段/评分同值/条目暴跌）→ 标记"审核未通过"不产出 |
| 20 | 架构预留 | Phase 2 可能扩展哪些？ | 数据源可插拔 + 发布渠道可扩展（策略模式） |

### 产出物

- Spec 从 14 行 v0.1 扩充为完整 v1.0 终版 → `ai-knowledge-base/specs/project-vision.md`
- 项目脚手架 → `ai-knowledge-base/CLAUDE.md`、`ai-knowledge-base/VISION.md`

### 关键收获

1. **"问号驱动"的 Spec 是不可执行的**。每个 `?` 在评审中都会被追到具体决策（数字/规则/阈值），想不清楚的地方就是风险点
2. **边界先于功能**。"不做什么"应该在"要做什么"之前明确，否则范围会随讨论膨胀
3. **验收标准要可验证**。不能是"日报质量好"，必须是"摘要 50–300 字、相关度 ≥ 90%"
4. **异常路径 > 正常路径**。采集失败、LLM 抽风、条目暴跌——这些非正常情况的处理方案决定了系统是否真的能"无人值守"





## week 1 第二节 为知识库编写Agent

### 创建 3 个 Agent 定义文件

根据 AGENTS.md 中定义的 Agent 角色，在 `.opencode/agents/` 下创建了三个 Agent 定义文件：

#### 1. collector.md — 采集 Agent

- **角色**：从 GitHub Trending + Hacker News 采集 AI/LLM/Agent 技术动态
- **权限**：Read / Grep / Glob / WebFetch（只读），禁止 Write / Edit / Bash
- **职责**：搜索采集 → 提取标题/链接/热度/摘要 → 按 topic 初步筛选 → 按热度排序
- **输出**：JSON 数组写入 `knowledge/raw/{source}.json`，含 title / url / source / popularity / summary
- **质量门禁**：条目 ≥ 15 条、信息完整、不编造、无重复 URL

#### 2. analyzer.md — 分析 Agent

- **角色**：对原始数据生成中文摘要、质量评分、建议标签
- **权限**：同 collector（只读 + WebFetch 查原文），禁止 Write / Edit / Bash
- **职责**：读取 raw 数据 → 写 80–150 字中文摘要 → 提炼亮点 → 1–10 评分 → 从预定义标签库选 1–3 个标签
- **评分标准**：9–10 改变格局 / 7–8 直接有帮助 / 5–6 值得了解 / 1–4 可略过
- **输出**：以原始 id 为 key 的 JSON 对象

#### 3. organizer.md — 整理 Agent

- **角色**：去重合并、格式化标准 JSON、分类存储
- **权限**：Read / Grep / Glob / Write / Edit（有写权限），禁止 WebFetch / Bash
- **职责**：去重检查(id + URL) → 组装标准 JSON → 按 `{date}-{source}-{slug}.json` 命名写入 `knowledge/articles/` → 标记 status
- **status 规则**：已发布(published) / 草稿(draft) / 重复(duplicate)
- **红线**：禁止修改 `knowledge/raw/` 原始数据

### 三 Agent 协作流程

三个 Agent 按 `collector → analyzer → organizer` 串行执行，通过文件系统传递数据：

```
collector (只读)
  ├─ WebFetch: GitHub Trending + Hacker News
  ├─ 过滤 AI 相关条目，按热度排序
  └─ 输出 knowledge/raw/{source}.json
        │
        ▼
analyzer (只读)
  ├─ 读取 knowledge/raw/
  ├─ 写中文摘要(80-150字)、打评分(1-10)、建议标签
  └─ 输出以 id 为 key 的分析 JSON
        │
        ▼
organizer (有写权限)
  ├─ 读取分析结果
  ├─ 去重检查(id + URL)
  ├─ 格式化为标准知识条目
  └─ 写入 knowledge/articles/{date}-{source}-{slug}.json
```

**协作契约**（引用 `specs/agents-collaboration.md`）：

| 契约 | 决策 |
|------|------|
| 上游失败下游怎么办 | 每个阶段写 `.status` 文件，下游检测到 `failed` 则跳过并 warn |
| 数据怎么传 | 文件系统，不直接调用函数，不覆写 raw 数据 |
| 重跑策略 | `--force` 强制重跑指定阶段 |
| 进度追踪 | 流水线日志 + `.status` 文件 |
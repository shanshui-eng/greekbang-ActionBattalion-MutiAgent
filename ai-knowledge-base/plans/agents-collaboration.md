# 三 Agent 协作流水线 — 实施计划

> Source PRD: `specs/agents-collaboration.md`

## Architectural decisions

Durable decisions that apply across all phases:

- **Agent 边界**：collector 只读（Read/Grep/Glob/WebFetch），analyzer 只读，organizer 有写权限（Write/Edit），均禁止 Bash
- **数据传递**：Agent 间通过文件系统传递，不直接调用函数。data flow: `knowledge/raw/` → `knowledge/articles/` → 分发
- **触发方式**：CLI 入口 `python main.py --stage <collect|analyze|organize|all>`，默认 all 串行
- **状态围栏**：每个阶段产出独立的 `.status` 文件记录成功/失败/跳过，供下游决策
- **配置位置**：流水线配置集中管理于 `pyproject.toml` 的 `[tool.knowledge-base]` 段

---

## Phase 1: 单 Agent 可执行闭环

**用户故事**: 让任意一个 Agent 能独立跑通

### What to build

实现 `main.py` CLI 入口，支持 `--stage` 参数选择单个 Agent 运行。每个 Agent 封装为独立函数，接收输入路径、输出路径，返回状态码。添加 logging 配置和基础错误处理。

### Integration layers

- CLI 参数解析 → Agent 函数调用 → 文件读写 → 日志输出

### Acceptance criteria

- [ ] `python main.py --stage collect` 可以独立运行 collector，输出到 `knowledge/raw/`
- [ ] `python main.py --stage analyze` 可以独立运行 analyzer，读取 raw 输出分析结果
- [ ] `python main.py --stage organize` 可以独立运行 organizer，读取分析结果输出到 `knowledge/articles/`
- [ ] 每个 Agent 运行时有 INFO 级别的起止日志
- [ ] 非法 `--stage` 参数时有清晰的报错提示

---

## Phase 2: 三 Agent 串行流水线

**用户故事**: collector → analyzer → organizer 串起来

### What to build

在 Phase 1 基础上实现 `--stage all` 全量流水线模式。每个阶段完成后写入 `.status` 文件（`{stage}.status`），下游通过检查上游 `.status` 决定是否执行。添加总进度日志（Phase 1/3 → Phase 2/3 → Phase 3/3）。

### Integration layers

- Pipeline 编排逻辑 → 状态文件读写 → 阶段间条件跳转 → 聚合日志

### Acceptance criteria

- [ ] `python main.py --stage all` 按 collector → analyzer → organizer 顺序执行
- [ ] 每个阶段成功后在根目录写入对应的 `.status` 文件
- [ ] 下游阶段启动时检查上游 `.status`，不存在则跳过并 warn
- [ ] 控制台输出 `[1/3] Collecting...` / `[2/3] Analyzing...` / `[3/3] Organizing...` 进度信息
- [ ] 流水线完成后输出汇总日志（各阶段耗时、状态）

---

## Phase 3: 错误恢复 & 重跑策略

**用户故事**: 上游失败下游怎么办、重跑策略

### What to build

在每个 Agent 函数外层包 try/except，捕获异常后：1）写 `{stage}.status` 为 `failed`；2）记录异常详情到日志；3）下游检测到上游 failed 后跳过并说明原因。实现 `--stage` 重新指定已失败的阶段重跑，`--force` 强制覆盖已有结果。

### Integration layers

- 异常捕获 → 状态持久化 → 条件跳转 → CLI 参数扩展

### Acceptance criteria

- [ ] 任意 Agent 抛出异常时，流水线不会崩溃，下游 Agent 正常跳过
- [ ] 失败的阶段写入 `{stage}.status` 内容为 `failed` + 错误信息
- [ ] `python main.py --stage collect` 成功重跑后，下游可再次执行
- [ ] `python main.py --stage all --force` 忽略已有状态强制全量重跑
- [ ] 所有异常都被记录到日志文件，无静默失败

---

## Phase 4: 协作规范定稿

**用户故事**: 数据怎么传、协作契约文档化

### What to build

将实施过程中确认的协作规则写回 AGENTS.md：明确 `.status` 契约格式、数据文件命名规范、重跑策略、错误处理约定。在 `specs/` 下新增维护文档 `流水线运维手册`。添加验收检查清单。

### Integration layers

- 文档更新 → 配置同步 → 验收测试

### Acceptance criteria

- [ ] AGENTS.md 中补充流水线编排章节（CLI 参数、状态契约、错误策略）
- [ ] `specs/runbook.md` 包含：启动方式、重跑步骤、常见故障排查
- [ ] 文档中的命令示例与实际代码一致
- [ ] 验收检查清单可在 CI 或手动执行时逐条确认

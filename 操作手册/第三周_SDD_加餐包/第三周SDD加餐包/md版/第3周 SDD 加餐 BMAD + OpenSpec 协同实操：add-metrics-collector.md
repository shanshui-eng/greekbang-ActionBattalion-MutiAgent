>**背景**：Week 2 我们已经跑通过一次 `add-analyzer-retry-policy` 端到端，知道 `/opsx:*` 节奏的学员。
>**目标**：用 **BMAD 把架构想清楚** → 用 **OpenSpec 把 spec 钉死** → 用 `/opsx:apply`**生成代码改动**。这是多 Agent 场景下的标准 SDD 流程。
>**代码仓**：https://github.com/huangjia2019/sdd-in-action/tree/master/week3/code

---
## 0 · 为什么这节要引入 BMAD

Week 2 你一个人 + grill-me 就能把 retry change 想透——因为 retry 是**单一职责**的增强，边界在一个函数里。


Week 3 的场景变了。N 个 Agent 协作，新加一个 Agent 要同时考虑：

* 插在拓扑图的哪里（Architect 视角）

* 谁看 dashboard、要什么指标（PM 视角）

* 怎么测、QA 怎么验（QA 视角）

* 单个 Agent 的 runtime 设计（Dev 视角）

* 

**一个人戴 4 顶帽子讨论**，脑子会糊。BMAD 的 12+ 角色系统不是让你真请 4 个人，是让**同一个 AI 用 4 个不同的 persona 跟你对话**，每次只戴一顶帽子想一个问题。


相比 Week 2 单人 grill-me，Week 3 的改进：

|维度|Week 2 单 Agent|Week 3 多 Agent|
|:----|:----|:----|
|复杂度|低 · 一个函数|中 · 涉及 7 节点拓扑|
|视角数|1 · grill-me 挑刺|4 · PM / Architect / Dev / QA|
|工具链|OpenSpec · grill-me|**BMAD · OpenSpec · grill-me**|
|产物|spec + code|**PRD + Architecture doc + spec + code**|
|耗时|40 min|60 min|


---

## 1 · 要做什么

给 V3 workflow 加一个 `⑧ Metrics Collector` —— 在每个节点完成后记录 `latency / cost / status / iterations`，输出 JSON 可以接 Grafana。


>**咖哥发言**： **在工作流里加一个“统一记账员 / 观测员”组件**，每当某个节点执行完，它就顺手把这一步的关键运行信息记下来，最后产出一份结构化 JSON，方便后面接到 **Grafana / Prometheus / Loki / ELK** 这类监控系统里做可视化、告警和分析。


**几个关键约束**：

* 不能破坏现有 3 路条件边（`review → organize / revise / human_flag`）。

* 不能让每个 Agent 都写 metrics 代码（那会污染所有 7 个文件）。

* 不能引入第二个 LLM 调用（会致使成本翻倍）。

* 观察者模式 ， 最小侵入。


**这就是为什么需要 Architect**——这 4 条约束哪条优先、怎么取舍，PM 不懂、Dev 也说不清。


---

## 2 · Week 3 自身环境自检

注意 · **Week 2 和 Week 3 是同仓库下两套独立代码** · `week2/code/openspec/` 和 `week3/code/openspec/` 互不相关 ，Week 2 跑没跑完不影响这里。


要自检的是 **Week 3 自己的环境**：

```plain
cd /home/huangj2/sdd-in-action/week3/code

# ① Week 3 OpenSpec 已初始化？
ls openspec/
# 期望 · 看到 config.yaml + project.md + specs/

# ② Week 3 specs/ 是不是空的？
ls openspec/specs/
# 期望 · 空（Week 3 起点 · 还没有任何 archived spec）
# 这意味着 · 这次 change 是 greenfield ADDED only · 不会有 MODIFIED delta

# ③ V3 7 节点拓扑能 build？
python3 -c "from workflows.graph import build_graph; g = build_graph(); print(sorted(g.nodes.keys()))"
# 期望 · ['analyze', 'collect', 'human_flag', 'organize', 'plan', 'review', 'revise']

# ④ Week 3 已有的 tests 跑得通？
python3 tests/cost_guard.py && python3 tests/security.py
# 期望 · 看到"所有测试通过！"
```
**任意一条不过，都不要往下走，**补完再来。


---

## 3 · Stage 0 准备


### 步骤 1 · 进 Week 3 工作目录 + 装 BMAD（在 week3/code/ 内）

```plain
cd /home/huangj2/sdd-in-action/week3/code
git checkout master              # 基线 · 7 个 Agent 都在
git pull                          # 拉最新
```


### 为什么 BMAD 装在“项目级别”而不是“系统级别”

咖哥当时的第一反应是，装一次系统级别的，所有项目都能用，多省事？——这个直觉对 npm 包是对的，对 BMAD 是错的。下面讲清楚为什么。

**类比要换一下**：

* `npm install -g typescript` · 装的是**编译器**（一段中立的代码），跟你写什么项目无关 · 全局共享合理

* `npx bmad-method install` ，装的是**方法论配置**（PM/Architect 的对话 prompt、PRD 模板、checklists），跟“这个项目要解决什么问题”强相关。如果共享，反而错位。


打个具体的比方，想象你是产品经理。

* 给知识库项目写 PRD，重点是采集质量、入库率、成本。

* 给电商项目写 PRD，重点是转化率、客单价、退款率。

你能让一份PM 模板同时服务这两个项目吗？可以，但每次都要回头改，这样很累。


**BMAD 是把“项目方法论”变成代码资产**。一个项目一份 `.bmad-core/`（PM persona、Architect 偏好、QA 风格）跟项目代码一起进 git，跟项目一起演进，跟项目一起被 review。这才是**Docs-as-Code** 的精神。


回到本课程，4 周的设计，也是 **4 个独立的 SDD 项目**（只是物理上放在一个仓库做教学）：

|Week|项目特性|PM persona 应该侧重|
|:----|:----|:----|
|Week 2|单 Agent，retry 改造|函数边界、回退策略|
|Week 3|多 Agent，协作演进|用户视角、4 视角切换、metrics|
|Week 4|平台化，生产部署|交付节奏、上线门、回滚预案|

如果共用一份 `.bmad-core/agents/pm.md`，要么承载不下这些差异，要么变成万能但平庸的模板。

**每周独立 BMAD = 每个 SDD 项目独立方法论 = 与项目同生共死的配置资产**。


显然，这样也有代价，Week 4 还要再装一次。但：

* `npx bmad-method install` 第二次以后有 npm 缓存，1-2 分钟搞定。

* “装 BMAD”是端到端 SDD 体验的一部分，行动营练习中你能每周走一遍 ，心理记忆更深。


**核心思想：工具是全局的，方法论是项目的。BMAD 是方法论，不是工具——所以它跟着项目走，不跟着用户走。**


---
```plain
# 装 BMAD v6（一次性 · 装在 week3/code/ 内）
npx bmad-method install
# Installation directory · 默认就是 /home/huangj2/sdd-in-action/week3/code · 直接回车
# 选 claude-code 或 cursor
# 模块只勾前两个绿点（Core + Agile-AI Driven Development）· 其他全跳过

# 验证（v6 装在 _bmad/ 和 .agents/skills/）
ls .agents/skills/ | grep bmad-agent-
# 期望 · 看到 bmad-agent-pm / bmad-agent-architect / bmad-agent-dev / bmad-agent-analyst /
#       bmad-agent-tech-writer / bmad-agent-ux-designer

# OpenSpec 已经在 Week 2 装过 · 全局命令
openspec --version
```


截图如下。


![图片](第3周 SDD 加餐 BMAD + OpenSpec 协同实操：add-metrics-collector/1.png)


![图片](第3周 SDD 加餐 BMAD + OpenSpec 协同实操：add-metrics-collector/2.png)

![图片](第3周 SDD 加餐 BMAD + OpenSpec 协同实操：add-metrics-collector/3.png)

![图片](第3周 SDD 加餐 BMAD + OpenSpec 协同实操：add-metrics-collector/4.png)

![图片](第3周 SDD 加餐 BMAD + OpenSpec 协同实操：add-metrics-collector/5.png)

![图片](第3周 SDD 加餐 BMAD + OpenSpec 协同实操：add-metrics-collector/6.png)

```plain
# 开 feature 分支
git checkout -b feature/add-metrics-collector-local
mkdir -p _bmad-output/planning-artifacts  # 保存本周 BMAD 产出
```
### BMAD v6 命令体系

v6 命令分三类，本节实操按这个映射使用。

|类型|命令前缀|实际作用|本节 Stage 用哪个|
|:----|:----|:----|:----|
|**Persona 对话**|/bmad-agent-{role}|打开 chat 和某 persona 聊（PM 叫 John · Architect 叫 Winston）|Stage 1 用 pm · Stage 2 用 architect|
|**Task 工作流**|/bmad-create-{artifact}|按结构化流程产出某文档（PRD / Architecture / Story）|进阶用法 · 本节走 Persona 路线|
|**Review 工作流**|/bmad-review-*|对抗审查 / 边缘 case 猎人 / E2E 测试生成|**Stage 5 替代旧版@qa**（v6 没 qa-agent）|


---

## 4 · Stage 1 ：BMAD PM 写 PRD（10 分钟）

**为什么先 PM 不是 Architect**？不知道谁看、看什么，架构无从设计。PM 先把 **who / what / when** 定死。


**在 IDE 新开一个 chat 窗口**，跑 BMAD v6 真实命令：

```plain
/bmad-agent-pm
```
![图片](第3周 SDD 加餐 BMAD + OpenSpec 协同实操：add-metrics-collector/7.png)

![图片](第3周 SDD 加餐 BMAD + OpenSpec 协同实操：add-metrics-collector/8.png)

v6 把 PM persona 起名 **John**，开 chat 后直接输入 “Hi John”，唤醒你的产品经理Agent角色。


注意，不是 `@pm` 也不是 `/bmad:pm` ，是 `/bmad-agent-pm`（slash 命令 · `agent-` 中缀）。

```plain
> /bmad-agent-pm

Hi John · 我是知识库项目 Tech Lead · 想给 V3 workflow 加 metrics collection。

背景：
- V3 7 节点已经在生产跑 · 每天采集 20 条分析 + 审核 + 入库
- 目前没法回答 "昨晚 pipeline 卡在哪一步" "review 平均几次能通过" "哪个 Agent 最烧钱"
- 业务方（内容运营）要看知识库健康度 dashboard

请帮我起草一份 PRD（简洁版 · 1 页）· 包含：
1. Problem Statement
2. Users（谁看 dashboard）
3. Must-have Metrics（MVP · 5 个以内）
4. Nice-to-have
5. Success Criteria
6. Out of Scope
```


![图片](第3周 SDD 加餐 BMAD + OpenSpec 协同实操：add-metrics-collector/9.png)

**BMAD PM 会回你一份结构化 PRD，把它存起来。**可以指示：

```plain
PRD写完后请存到 _bmad-output/planning-artifacts/metrics-collector-prd.md
```
### PM 产出的典型内容（供你参考）

```plain
# PRD · Metrics Collector for V3 Pipeline

## Problem
V3 pipeline 跑完没人知道跑得怎么样。事故 MTTR 靠猜。业务方要看健康度。

## Users
- Tech Lead · 事故分析 · "昨晚挂在哪"
- 内容运营 · 业务健康 · "今天入库几条 / 降级几条"
- Finance · 成本账 · "每次 pipeline 花多少"

## Must-have Metrics (MVP)
1. 每个节点的 latency_ms
2. 每个节点的 llm_tokens（分 prompt / completion）
3. review 节点的 iterations 分布
4. human_flag 触发次数（degraded items）
5. pipeline 总成本 ¥

## Nice-to-have
- Prometheus 导出格式
- 每 Agent 的成功率时间序列

## Success Criteria
- Dashboard 可以回答 "昨晚 pipeline 哪一步慢"
- 所有 Must-have metrics 自动落到 JSON · 格式对齐 Grafana

## Out of Scope
- 实时告警 · 下个季度
- 分布式 tracing · OpenTelemetry 集成下季度
- 预算熔断联动 · CostGuard 已经有了
```
### ![图片](第3周 SDD 加餐 BMAD + OpenSpec 协同实操：add-metrics-collector/10.png)

### commit 目前的**BMAD**产出

```plain
git add _bmad-output/
git commit -m "docs(bmad): PM draft PRD for metrics-collector"

---
```


## 5 · Stage 2 BMAD Architect · 架构决策（15 分钟，这是本节核心）

BMAD 铁律——fresh chat，防止 PM 和 Architect 的角色混淆。


所以我们**新开一个 chat**，调用 architect persona：

```plain
/bmad-agent-architect
```


BMAD v6 Architect persona 叫 **Winston**，创建新的对话，还是从打招呼环节 “Hi Winston”开始，引出 Winston 完成下述任务。

```plain
> /bmad-agent-architect

Hi Winston · 我有一个 V3 Multi-Agent pipeline · 7 个节点 · LangGraph StateGraph。
拓扑图（贴 AGENTS.md 的架构图）。

PM 给的 PRD · _bmad-output/planning-artifacts/prd-metrics-collection.md
约束：
- 不破坏现有 3 路条件边
- 不污染每个 Agent 文件（观察者模式）
- 不引入第二次 LLM 调用
- 最小侵入

请你作为架构师 · 给我 3 个候选方案 · 权衡 · 推荐。
（注意 · LangGraph 没有 graph.compile(callbacks=...) 这种 graph 级 callback 注册 API · 
方案要基于 LangGraph 真实支持的能力提）
```



![图片](第3周 SDD 加餐 BMAD + OpenSpec 协同实操：add-metrics-collector/11.png)


Architect 典型回复（3 方案权衡）。出具体方案之前，会先进行多步骤的引导和提问。


![图片](第3周 SDD 加餐 BMAD + OpenSpec 协同实操：add-metrics-collector/12.png)
![图片](第3周 SDD 加餐 BMAD + OpenSpec 协同实操：add-metrics-collector/13.png)

![图片](第3周 SDD 加餐 BMAD + OpenSpec 协同实操：add-metrics-collector/14.png)

![图片](第3周 SDD 加餐 BMAD + OpenSpec 协同实操：add-metrics-collector/15.png)


他会一直磨磨唧唧地问来问去，不需要的就直接选择最简单的路径。



![图片](第3周 SDD 加餐 BMAD + OpenSpec 协同实操：add-metrics-collector/16.png)

![图片](第3周 SDD 加餐 BMAD + OpenSpec 协同实操：add-metrics-collector/17.png)

![图片](第3周 SDD 加餐 BMAD + OpenSpec 协同实操：add-metrics-collector/18.png)

![图片](第3周 SDD 加餐 BMAD + OpenSpec 协同实操：add-metrics-collector/19.png)

一系列架构级别的决策，佳哥不堪重负。


![图片](第3周 SDD 加餐 BMAD + OpenSpec 协同实操：add-metrics-collector/20.png)

![图片](第3周 SDD 加餐 BMAD + OpenSpec 协同实操：add-metrics-collector/21.png)

![图片](第3周 SDD 加餐 BMAD + OpenSpec 协同实操：add-metrics-collector/22.png)



![图片](第3周 SDD 加餐 BMAD + OpenSpec 协同实操：add-metrics-collector/23.png)


![图片](第3周 SDD 加餐 BMAD + OpenSpec 协同实操：add-metrics-collector/24.png)


![图片](第3周 SDD 加餐 BMAD + OpenSpec 协同实操：add-metrics-collector/25.png)

![图片](第3周 SDD 加餐 BMAD + OpenSpec 协同实操：add-metrics-collector/26.png)

![图片](第3周 SDD 加餐 BMAD + OpenSpec 协同实操：add-metrics-collector/27.png)

### 最后才出方案

```plain
方案 A · In-graph Node · 每个节点之后插一个 metrics 节点
  ✅ 符合 LangGraph 原生 pattern
  ❌ 图膨胀 · 7 节点变 14 节点 · 可读性差
  ❌ 破坏现有 routing（每条边都要改）

方案 B · 装饰器 wrap 每个 node 函数
  ✅ 零图结构改动
  ⚠️ 7 个文件都要改（加 @track_metrics import）
  ✅ 性能零开销
  ❌ 不是真观察者模式 · 仍属侵入

方案 C · LangChain BaseCallbackHandler + invoke-time config  ✅ 零文件改动 · 调用 graph.invoke(state, config={"callbacks":[handler]})
  ✅ 真观察者模式 · LangGraph 官方支持
  ✅ on_chain_start / on_chain_end 天然按节点触发
  ⚠️ 拿 token usage 要从 on_llm_end 读 · 需要按 run_id 关联
  ✅ 天然对接 LangSmith / LangFuse / OpenTelemetry

推荐：C · 满足"零文件改动"约束 · 是 LangGraph 真实支持的官方机制
新增文件：workflows/metrics.py（1 个 BaseCallbackHandler 子类）
修改文件：graph.py 的 entry point（invoke 时传 config · +5 行）
```



![图片](第3周 SDD 加餐 BMAD + OpenSpec 协同实操：add-metrics-collector/28.png)

如果BMAD没存，可以**手工把这段架构决策存到这里**。

```plain
_bmad-output/planning-artifacts/architecture.md
```
### commit BMAD 产出

```plain
git add _bmad-output/
git commit -m "docs(bmad): Architect proposes BaseCallbackHandler design (3 options weighed)"

---
```


## 6 · Stage 3 OpenSpec：把 PRD + Architecture 翻译成 spec（15 分钟）

### 步骤 1 · 在新 chat 开 OpenSpec 流程

**再新开一个 chat**（和 BMAD chat 分开）：

```plain
> /opsx:new add-metrics-collector
```
>如果 `/opsx:new` 在你的 OpenSpec 版本里不可用 ，就跳过 ， 直接手写 proposal.md（步骤 3）就行，scaffold 已经建好。

![图片](第3周 SDD 加餐 BMAD + OpenSpec 协同实操：add-metrics-collector/29.png)

![图片](第3周 SDD 加餐 BMAD + OpenSpec 协同实操：add-metrics-collector/30.png)




![图片](第3周 SDD 加餐 BMAD + OpenSpec 协同实操：add-metrics-collector/31.png)


![图片](第3周 SDD 加餐 BMAD + OpenSpec 协同实操：add-metrics-collector/32.png)

![图片](第3周 SDD 加餐 BMAD + OpenSpec 协同实操：add-metrics-collector/33.png)
### 步骤 2 · 可以手写 proposal.md ，把 BMAD 决策精炼进去

我是没这么做，你可以试试看。

```plain
# add-metrics-collector

## Why

V3 pipeline 跑完没有可观测性。事故 MTTR 靠猜 · 业务方看不到健康度。
PRD 见 `_bmad-output/planning-artifacts/prd-metrics-collection.md`（BMAD v6 自动以 `prd-` 前缀落盘）

## What

新增 `workflows/metrics.py` · 通过 **LangChain BaseCallbackHandler** 记录每节点的：

- `latency_ms`（毫秒）
- `llm_tokens`（prompt + completion）
- `status`（success / failed / degraded）
- `review_iterations`（仅 review 节点）
- `total_cost_yuan`（仅 end node）

输出 · `_metrics/run-{timestamp}.json`

**架构决策**：采用方案 C（BaseCallbackHandler · invoke-time config）· 不改任何现有 Agent 文件 · 只改 graph 入口 5 行。
架构文档见 `_bmad-output/planning-artifacts/architecture.md`（实施只看 v0.2 章节 · 即第 905 行起 · v0.1 是反例保留）

## Out of scope

- Prometheus 导出 · 下季度
- 实时告警 · 下季度
- OpenTelemetry · 下季度
- 预算熔断联动 · CostGuard 已做
- 修改现有 7 个 Agent 的任何代码
```


### 步骤 3 · 按 Continue 推进 · 不需要 ff 等子命令

OpenSpec v6/v7 用一个 `/opsx-new` 命令**自动驱动**整个工作流，你只需要在 IDE 里按 **Continue** 推进。


**我们审视一下v5到v6的简化**：v5 时代有 `/opsx-ff`（fast-forward 生成 spec 首稿）等子命令，v6 已合并到 `/opsx-new` 的工作流里。讲义只用到 `/opsx-new` / `/opsx-apply` / `/opsx-archive` / `/opsx-validate` 四个命令。



![图片](第3周 SDD 加餐 BMAD + OpenSpec 协同实操：add-metrics-collector/34.png)

![图片](第3周 SDD 加餐 BMAD + OpenSpec 协同实操：add-metrics-collector/35.png)

![图片](第3周 SDD 加餐 BMAD + OpenSpec 协同实操：add-metrics-collector/36.png)

![图片](第3周 SDD 加餐 BMAD + OpenSpec 协同实操：add-metrics-collector/37.png)


### 步骤 4 · 验证 4 个 artifacts 不为空

```plain
cd /home/huangj2/sdd-in-action/week3/code
find openspec/changes/add-metrics-collector -type f -exec wc -l {} \;
```
**期望**：4 个文件**都有 20+ 行**：
* `proposal.md` ~25 行（Why / What / Capabilities / Impact）

* `design.md` ~100 行（Context / Decisions / Risks）

* `tasks.md` ~30 行（细粒度 task 清单）

* `specs/metrics-collection/spec.md` ~60 行（ADDED Requirements + Scenarios）


**任何文件 0 行**，都说明OpenSpec 没跑完工作流，需要回 chat 让它续完，可以提醒它“继续把空文件填完”。

### 步骤 5 · 接受方案漂移 · 但验证 5 条硬约束闭环

OpenSpec 可能给出**跟 architecture.md v0.2 不一样的方案，** 这是正常的。

V3 实操真实出现过两种“漂移变体”：

* **变体 1**：OpenSpec 选 `with_metrics` wrapper（不是 BaseCallbackHandler）

* **变体 2**：OpenSpec 选 `track_metrics` decorator + 终点 `flush_metrics_node`


我的看法是，**只要满足 5 条硬约束**（7 Agent 文件 0 变动 / OOS 严格 / 命名合理 / API 真实 / 不引入新概念），任何变体都可接受。

>**核心思路**：Architect 提炼架构方向，OpenSpec 实现 spec 时允许变体——重要的是约束闭环 ，不是方案完全一致。这是 SDD 协作的真实样貌，不是漏洞。
### 步骤 6 · Greenfield delta 形态确认

**注意，Week 3 是 greenfield（起点 specs/ 为空）**。本次 change 只有 ADDED delta · 不会有 MODIFIED 或 REMOVED。这跟 Week 2 一样，Week 2 的 `analyzer-retry-policy` 在 `week2/code/openspec/` 下，与 Week 3 的 openspec 是两套独立 spec 仓库， 不互相依赖。


**真正的 brownfield 体验**要等到：

* 本次 change archive 之后 · Week 3 自己的 openspec/specs/ 会有 `metrics-collection`。

* **下一次** 在 Week 3 做 change（比如 add-prometheus-export）· 那时候才会出现 MODIFIED metrics-collection。

* 或 Week 4 实操，基于本周已 archived 的 spec 演进。

### 步骤 7 · grill-me 拷问

```plain
> @grill-me 审 specs/metrics-collection/spec.md · 重点：

1. callback 注册失败时 pipeline 会怎样（要不要 block）
2. metrics 记录自己也消耗时间 · 算不算 latency
3. 如果 metrics.py 抛异常 · 主流程要不要继续（建议：try/except 包住所有 callback 内部 · 永远 swallow exception）
4. JSON 输出文件巨大时怎么办（retention policy · 留最近 100 次）
5. 多并发 invoke 时 · MetricsCollector 实例能复用吗（建议：每次 invoke 新建 · run_id 隔离）
```
### 步骤 8 · commit

```plain
git add openspec/changes/add-metrics-collector/
git commit -m "docs(openspec): proposal + spec for add-metrics-collector"


---
```


## 7 · Stage 4 · `/opsx:apply` 生成代码（10 分钟）

下一阶段进入代码生成环节。

```plain
> /opsx:apply
```


![图片](第3周 SDD 加餐 BMAD + OpenSpec 协同实操：add-metrics-collector/38.png)


**期望 apply 产出**（下面展示了参考形态 ，不保证一次完全对）：

* `workflows/metrics.py`（新文件 · `MetricsCollector(BaseCallbackHandler)` + JSON dump 方法）

* `workflows/graph.py` 入口函数（修改 5 行 · `app.invoke(state, config={"callbacks": [collector]})`）

* `tests/test_metrics.py`（新文件 · 单测）

* **不改** workflows/planner.py / collector.py / analyzer.py / reviewer.py / reviser.py / organizer.py / human_flag.py 的任何一个（验证架构决策生效）


**如果 AI 把 callback 写成了**`compile(callbacks=...)` ，立刻打回。这是 V1 踩过的坑。给它看：



![图片](第3周 SDD 加餐 BMAD + OpenSpec 协同实操：add-metrics-collector/39.png)

```plain
LangGraph 的 compile() 不接受 callbacks 参数。callbacks 在 invoke/stream 时通过 config 传入。
```
>`参考：https://langchain-ai.github.io/langgraph/concepts/streaming/`
### `/opsx:verify` 要求

```plain
> /opsx:verify
```
verify 会发现 · 如果 apply 不小心改了现有 Agent 文件，会 flag 违反“不污染现有 Agent”的架构决策。**这就是 BMAD Architect 方案写进 spec 之后的价值，让spec 变成质量闸门**。
### 手工抽查

verify 自动化只覆盖 spec 约束。加两条手工抽查。

```plain
# ① 7 个 Agent 文件应该 0 字节变动
git diff --stat workflows/{planner,collector,analyzer,reviewer,reviser,organizer,human_flag}.py
# 期望 · 输出为空

# ② metrics.py 内部不能 import workflows 里任何 Agent
grep -E "from workflows\.(planner|collector|analyzer|reviewer|reviser|organizer|human_flag)" workflows/metrics.py
# 期望 · 输出为空（callback 只看 run_id · 不需要知道 Agent 实现）

---
```


## 8 · Stage 5 · BMAD QA · 测试评审（5 分钟）

**再开 fresh chat** ，用于跑 v6 对抗审查命令：

```plain
/bmad-review-adversarial-general
```


**BMAD** **v6 没有**`bmad-agent-qa`！QA 工作被拆成更细粒度：

>`/bmad-review-adversarial-general` · 对抗式审查
>`/bmad-review-edge-case-hunter` · 边缘 case 猎人
>`/bmad-qa-generate-e2e-tests` · 生成 E2E 测试
>
>当前Stage 用 adversarial-general，它会以“挑刺者”身份审查你的方案。

![图片](第3周 SDD 加餐 BMAD + OpenSpec 协同实操：add-metrics-collector/40.png)

```plain
> /bmad-review-adversarial-general
> 这份 change 的 PRD + Architecture + spec + 代码见：
> - _bmad-output/planning-artifacts/prd-metrics-collection.md
> - _bmad-output/planning-artifacts/architecture.md
> - openspec/changes/add-metrics-collector/
>
> 请从 QA / 对抗审查视角审：
> 1. 哪些测试场景 apply 没覆盖
> 2. 边界条件（callback 抛异常 / 文件写失败 / disk full）
> 3. 性能回归 · BaseCallbackHandler 会不会让 pipeline 慢 2×
```
### QA 典型反馈

```plain
覆盖充分 · 3 点补测建议：
1. callback 抛异常时 · pipeline 仍能完成（需要测 graceful degradation）
2. 大批量（100 items）跑一次 · 确认 metrics 文件没撑爆磁盘
3. 并发 invoke 隔离 · 两个 MetricsCollector 实例不能串数据
```
把这些回传给 `@grill-me` 补到 spec ，然后 `/opsx:apply` 补测试。

---

## 9 · Stage 6 · commit + PR + archive（5 分钟）

```plain
pytest tests/test_metrics.py -v

git add workflows/metrics.py workflows/graph.py tests/test_metrics.py \
        openspec/changes/add-metrics-collector/ _bmad-output/
git commit -m "feat(workflow): add metrics collection via BaseCallbackHandler"

git push -u origin feature/add-metrics-collector-local
```
### archive

```plain
# merge 之后：
git checkout master && git pull
/opsx:archive add-metrics-collector

---
```


## 10 · BMAD 最佳实践总结

|最佳实际原则|说明|体现|
|:----|:----|:----|
|**Docs-as-code** |PRD / Architecture 先于代码 ，全部 commit 进仓库|Stage 1-2 · _bmad-output/ 全 git tracked|
|**Fresh chat per role**|PM / Architect / Dev / QA 各用独立 chat，避免角色混淆|每个 Stage 都强调“新开 chat”|
|**Role-scoped questioning**|问 Architect 不要问业务，问 PM 不要问技术选型|Stage 1 只问 users/metrics · Stage 2 只问 3 方案权衡|
|**Control Manifest** |spec 是 architect 决策的落盘 ，将其变成质量闸门|Stage 3 proposal 里引用 architecture doc 作为决策依据|
|**Git workflow integration**|每个 stage 单独 commit ，让决策过程可追溯|每个 Stage 结尾 commit|
|**Multi-layered review** |QA 是单独的一个stage，很重要|Stage 5  独立 QA|
|**API 真实性约束**|给 Architect 提示真实 API 边界 ，防止产生“概念正确但 API 不存在“的方案。这点我们在 V2 新增了。|Stage 2 强提示 “LangGraph 没有 compile(callbacks=...)”|

### BMAD 的四个 anti-pattern

|Anti-pattern|如果犯了会发生|怎么防|
|:----|:----|:----|
|**Context overload**  所有文件 paste 给 AI|幻觉 · AI 忽略指令|Stage 2 Architect 只给 AGENTS.md + PRD，不 paste 所有代码|
|**Role overstepping**  让 Dev 改架构|技术债爆炸|Stage 4 apply 只改 metrics.py + graph.py 入口 ，不改 Agent 文件|
|**Skipping QA**  跳过 QA 直接 merge|上线回归|Stage 5 强制 QA review，即使只有 3 条反馈|
|**API hallucination**  AI 推荐“理论上对但 API 不存在”的方案|apply 阶段代码跑不通|Stage 2 强约束，必要时给 AI 看官方文档链接|


---

## 11 · 终点清单

跑完本 tutorial ，仓库新增了以下内容。

### BMAD 产出

```plain
_bmad-output/planning-artifacts/
├── prd-metrics-collection.md              ← PM 产出
└── architecture.md     ← Architect 产出（3 方案权衡）
```
### OpenSpec 产出

```plain
openspec/changes/archive/{date}-add-metrics-collector/
├── proposal.md
├── design.md
├── tasks.md
└── specs/metrics-collection/spec.md  (ADDED only · greenfield)

openspec/specs/metrics-collection/      ← archive 后合入主规范（Week 3 specs/ 第一份）
```
### 代码产出

```plain
workflows/metrics.py                    ← 新文件 · MetricsCollector(BaseCallbackHandler)
workflows/graph.py                      ← +5 行 · invoke 时传 config
tests/test_metrics.py                   ← 新文件 · 单测（含异常 / 并发 / 大批量）
_metrics/run-{timestamp}.json           ← 跑一次 pipeline 后产生
```
### **不改**（验证架构决策）

```plain
workflows/planner.py / collector.py / analyzer.py / reviewer.py /
workflows/reviser.py / organizer.py / human_flag.py / state.py
→ 全部 0 字节变动

---
```


## 13 · 总结

**OpenSpec 管“how to ship”，BMAD 管“who thinks about what”**。


* 单 Agent change（Week 2），grill-me 一个视角足够。

* 多 Agent change（Week 3），需要 PM（用户视角）+ Architect（架构视角）+ QA（风险视角）三个不同 chat 独立审查。。

* **角色隔离 = 认知隔离**：fresh chat 强制 AI 切换 persona，可以避免一个 AI 自我说服

* **API 真实性闸门**，Architect 阶段给 AI 划定真实 API 边界，否则 apply 必踩坑。


**跑完这份 tutorial，你就知道真实大项目里 SDD 工作流长什么样，动手试试看看吧**。


---

## Sources · BMAD 最佳实践参考

* [BMAD-METHOD GitHub](https://github.com/bmad-code-org/BMAD-METHOD)

* [BMAD Applied (Benny's Mind Hack)](https://bennycheung.github.io/bmad-reclaiming-control-in-ai-dev)

* [BMAD Method Guide (redreamality)](https://redreamality.com/garden/notes/bmad-method-guide/)

* [BMAD DeepWiki](https://deepwiki.com/bmad-code-org/BMAD-METHOD)

* [LangGraph Streaming & Callbacks 官方文档](https://langchain-ai.github.io/langgraph/concepts/streaming/)

* [LangChain BaseCallbackHandler 接口](https://python.langchain.com/api_reference/core/callbacks/langchain_core.callbacks.base.BaseCallbackHandler.html)


---



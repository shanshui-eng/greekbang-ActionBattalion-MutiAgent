这个实操指南，清晰地列出了通过 OpenSpec 做 SDD 增量开发的全流程，目的是让大家轻松地一步步上手OpenSpec。我是以 Week2 的现有代码为基线，增添一个新功能。


从头这么跑一遍OpenSpec，第一遍我大概花了一两个小时的时间。如果步骤顺畅的话可能45分钟就可以搞定吧。


**场景：**Week2 代码，基本上已经跑起来了。现在，我们要增加一个小change，是`add-analyzer-retry-policy`给 analyzer 加指数退避重试。


>**咖哥发言**：什么是指数退避重试（Exponential Backoff Retry）。就是LLM API调用失败了后不要马上重试，每次重试**等待时间翻倍**，再加一点随机抖动。

下面，列出清晰的基于OpenSpec的实操步骤以及我的过程截屏。


让大家跟着一起感受通过OpenSpec做SDD增量开发的全流程。


```plain
Stage 0 · /opsx-explore 先聊不落盘（5 问 5 答）
Stage 1 · /opsx-new add-analyzer-retry-policy（看到 4 份空模板）
Stage 2 · 手写 proposal.md（主体 + 动作 + 对象 + 边界）
Stage 3 · /opsx-ff 生成首稿 + 15 秒自检（capability 名绑业务）
Stage 4 · grill-me 拷问 5 个边界（贴完整问答）
Stage 5 · /opsx-apply 生成代码（看到 workflows/analyzer.py 新增 retry + 测试）
Stage 6 · /opsx-verify 反向对照（看到每条 spec 都有对应实现）
Stage 7 · commit + PR + /opsx-archive（spec → archive/ 下半年可追溯）
```


好，现在开船了。


## OpenSpec 环境准备

先准备OpenSpec环境。

```plain
npm install -g @fission-ai/openspec@latest
openspec --version

cd ~/ai-knowledge-base/v2-automation
openspec init
# ✓ openspec/project/  · 全局上下文
# ✓ openspec/changes/  · 进行中的变更
# ✓ openspec/archive/  · 归档的变更
```


![图片](第二周（加餐-2）OpenSpec实操指南/1.png)

![图片](第二周（加餐-2）OpenSpec实操指南/2.png)

![图片](第二周（加餐-2）OpenSpec实操指南/3.png)

![图片](第二周（加餐-2）OpenSpec实操指南/4.png)

init了之后，项目中将出现一系列的openspec目录，尤其是项目配置相关的config.yaml，可以手写（或者让AI写）一些项目相关的说明。


![图片](第二周（加餐-2）OpenSpec实操指南/5.png)


```plain
# ⚠️ 关键 · 启用 expanded 命令（默认 core 只有 4 条 · 本周用不够）
# v1.3.0 没有 expanded 预设 · 直接编辑全局 config
openspec config path
# 输出 ~/.config/openspec/config.json · 把 workflows 数组改成：
# ["propose","explore","apply","archive","new","continue","ff","verify","sync","bulk-archive","onboard"]

openspec update
# ✓ Updated OpenCode (v1.3.0)
```


![图片](第二周（加餐-2）OpenSpec实操指南/6.png)


改完记得**重启 OpenCode / Claude Code**，否则 `/opsx-new` 找不到。



## 0· 项目准备

### clone & checkout master（这是基线状态）

```plain
git clone git@github.com:huangjia2019/sdd-in-action.git
cd sdd-in-action/week2/code
git checkout master        # master 就是"还没加 retry"的基线
```
### 看看基线状态

```plain
ls
# AGENTS.md  .env.example  knowledge/  openspec/  pipeline/  requirements.txt  tests/
#  .claude/  .opencode/

cat pipeline/model_client.py | head -30
# 看到的是 chat() 直接调 OpenAI SDK · 没有 retry
```
**当前**`pipeline/pipeline.py::step_analyze()`**的痛点**：
```plain
# pipeline/pipeline.py · 精简
def step_analyze(items):
    for i, item in enumerate(items, 1):
        # ⚠️ 这里调 chat 会抛异常 · 没有 retry · 直接 propagate
        #    pipeline 会在第 i 条挂掉 · 前 i-1 条的成本沉没
        response = chat(prompt)
        ...
```
假设某天出现这样情况，深夜跑定时，采集 50 条 GitHub，分析跑到第 23 条 timeout 了一次，脚本退出：
* 已花 tokens 成本 ¥0.04

* 入库 articles 0 条

* 当天知识库空的

因此，要解决这个情况，需要修改程序，增加Retry限制。

### 装依赖 + 配 .env

```plain
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# 编辑 .env 填入真实的 LLM_API_KEY（DeepSeek / Qwen / OpenAI 任选）
```
### 环境自检

```plain
openspec --version          # 期望 v1.3.0 或更新
ls openspec/                # 期望看到 project.md + changes/ + specs/
```
**在 OpenCode / Claude Code 里敲**`/op`**看命令补全**。应该至少看到：`new · ff · apply · verify · sync · archive · onboard · continue · explore · bulk-archive · propose`。如果没有看到，回到OpenSpec的准备工作。

### 开分支（关键步）

```plain
git checkout -b feature/add-analyzer-retry-policy
```
**之后一切改动在这个分支上**。想 diff 对照 before/after 就切回 master：
```plain
git diff master..feature/add-analyzer-retry-policy    # 看你改了什么
```
跑完整个 tutorial，这个 feature 分支会有 8-10 个 commit，最后 PR merge 回 master。


## 1 · 确定要改什么

加一个 `with_retry` 装饰器，给 LLM 调用加**指数退避重试**。


**不是随便重试**，要区分：

* **该重试**：timeout / rate limit / connection error（瞬时故障 · 重试大概率能好）

* **不该重试**：JSON 解析失败 / KeyError（内容问题 · 重试只会浪费钱）


为什么不直接 vibe 让 AI 给你 `@retry(max_attempts=3)`：

* 半年后 retry 到底最多几次？base_delay 多少？你不记得了。

* 新人问“为什么不重试 JSONDecodeError”，你没地方查。

* 业务上要区分“白天重试 3 次/夜里重试 1 次”，spec 没写边界，AI 又要重猜。

* 

走 OpenSpec 就是把这些“一时想清楚就够了”的决策**刻进仓库里**。


## 2 · Stage 0 · `/opsx-explore` · 先聊不落盘

### **为什么先 explore 不直接 new**？


你脑子里现在想的 retry 其实有 5 个模糊点还没想清楚。直接 `new` + 手写 proposal 会把模糊写进 spec，后面 apply 出来的代码也会带着这些模糊点跑。

### 在 IDE 里

```plain
> /opsx-explore
我要给 sdd-in-action/week2/code 的 pipeline 加一个 retry 机制。

背景：
- analyzer 在 pipeline/pipeline.py 的 step_analyze() 里
- LLM 调用入口是 pipeline/model_client.py::chat()
- 调的 provider 是 OpenAI 兼容端点（DeepSeek / Qwen / OpenAI）
- 采集 50 条分析跑到一半挂过 · 前面的 tokens 浪费

范围：
- 只加 LLM 调用这一层的 retry
- 不改 step_collect / step_organize / step_save

不做：
- 不做 provider 级 fallback（OpenAI 挂了切 DeepSeek）· 那是未来
- 不做 circuit breaker
- 不做 async / 并发

先帮我列出 5 个最容易搞错边界的问题 · 我回答完你再帮我起草 proposal。

```
### ![图片](第二周（加餐-2）OpenSpec实操指南/7.png)

![图片](第二周（加餐-2）OpenSpec实操指南/8.png)

AI 返回一系列的问题。

```plain
┌─ opencode ─────────────────────────────────────────────────────────────┐
│  Good. Before we draft the proposal, here are 5 boundary questions    │
│  you should nail down. Each of them will end up as a clause in         │
│  your spec:                                                            │
│                                                                        │
│  Q1 · 哪些异常重试 · 哪些不重试?                                        │
│     (APITimeoutError / RateLimitError / APIConnectionError ·           │
│      httpx.TimeoutException · httpx.ConnectError · 还是别的?)          │
│                                                                        │
│  Q2 · 最多重试几次 · delay 怎么算?                                      │
│     (3 次 + 指数退避 1s/2s/4s? 要 jitter 吗? max_delay 封顶?)           │
│                                                                        │
│  Q3 · rate limit 的 429 特殊处理吗?                                     │
│     (有些 provider 返回 Retry-After: 30 · 吃这个值还是统一走 exp?)      │
│                                                                        │
│  Q4 · retry 期间的成本怎么算?                                           │
│     (失败的重试要不要算进 cost_tracker?)                                │
│                                                                        │
│  Q5 · 全部重试完还是 fail · pipeline 怎么办?                            │
│     (沿用现有 fallback 降级 summary? 整个 pipeline 退出?)               │
│                                                                        │
│  回答完我们再起草。                                                     │
└────────────────────────────────────────────────────────────────────────┘
```


![图片](第二周（加餐-2）OpenSpec实操指南/9.png)


你逐个回答（示例 · 根据你的实际情况填）

```plain
A1 · 重试这些:
     APITimeoutError, APIConnectionError, RateLimitError,
     httpx.TimeoutException, httpx.ConnectError
    NOT 重试:
     json.JSONDecodeError, KeyError, ValueError
     (内容层错误重试无效 · 浪费钱)

A2 · max_attempts=3
     base_delay=1s · exp backoff 1 → 2 → 4
     max_delay=20s 封顶
     jitter 1.0-1.5× 只加不减（防雪崩 · 标准做法）

A3 · 暂时统一走 exponential backoff · 不吃 Retry-After
     (实现简单优先 · 以后可以升级)

A4 · 每次真调 API 都记 cost_tracker · 包括失败的重试
     失败的 tokens=0 · 成功的记 response.usage.tokens
     方便事后 debug 看哪次 retry 把预算烧了

A5 · 全部重试失败 → 沿用降级路径(默认 summary)
     该 item 的 status 字段标记 "degraded"
     pipeline 继续跑 · 不整体退出
```
### AI 确认

```plain
┌─ opencode ─────────────────────────────────────────────────────────────┐
│  Excellent. All 5 boundaries nailed. Two things to note before         │
│  you /opsx-new:                                                        │
│                                                                        │
│  1 · "retry 失败后 fallback degraded" 是一个**有状态的行为** —         │
│     spec 里要把 status="degraded" 这条明确写进 DEGRADATION             │
│     requirement · 否则后面 verify 会发现实现有但 spec 没写             │
│                                                                        │
│  2 · 你列的 5 个可重试异常里 · 漏了 5xx HTTP 状态码                     │
│     (provider 容量紧张时会返 APIStatusError with status_code >= 500)   │
│     建议加上                                                            │
│                                                                        │
│  Ready when you are. 下一步 /opsx-new add-analyzer-retry-policy        │
└────────────────────────────────────────────────────────────────────────┘
```
这 5 问 5 答就是你下一步 `proposal.md` 的底稿。如果**不 explore 直接跳 proposal，你能想到 2 个问题，有些问题会在 apply 之后的 verify 阶段才发现，代价就是重跑。**

### ![图片](第二周（加餐-2）OpenSpec实操指南/10.png)



## 3 · Stage 1 · `/opsx-new` · 创建 change 目录

### 创建change目录

```plain
> /opsx-new add-analyzer-retry-policy
```
AI 响应
![图片](第二周（加餐-2）OpenSpec实操指南/11.png)
![图片](第二周（加餐-2）OpenSpec实操指南/12.png)

AI会创建出来Change目录openspec/changes/add-analyzer-retry-policy/，未来所期待的一些Artifacts如下。


OpenCode会问你要不要继续生成第一个工件，如果你说继续，就会生成proposal.md。


```plain
┌─ opencode ─────────────────────────────────────────────────────────────┐
│  Creating new change 'add-analyzer-retry-policy'...                    │
│                                                                        │
│  ✓ openspec/changes/add-analyzer-retry-policy/                         │
│    ├── proposal.md    (template · 待你手写)                            │
│    ├── design.md      (/opsx-ff 之后生成)                                       │
│    ├── tasks.md       (/opsx-ff 之后生成)                                       │
│    └── specs/         (空 · /opsx-ff 之后生成)                         │
│                                                                        │
│  Next · 打开 proposal.md 按 Why / What / Out of scope 三段结构          │
│       写完主语明确的草稿 · 然后跑 /opsx-ff                          │
└────────────────────────────────────────────────────────────────────────┘
```
终端确认。
```plain
ls -la openspec/changes/add-analyzer-retry-policy/
# proposal.md  design.md  tasks.md  specs/

cat openspec/changes/add-analyzer-retry-policy/proposal.md
```


注意，如果没有出现proposal.md，就自己创建一个。


我让在OpenCode中人工指示AI，帮我创建了一个新的 proposal.md。


![图片](第二周（加餐-2）OpenSpec实操指南/13.png)



![图片](第二周（加餐-2）OpenSpec实操指南/14.png)

**看到的内容**（template · 空的）：

```plain
# <change-name>

## Why

<why we need this change>

## What

<what we're changing>

## Out of scope

- <explicit non-goals>
```
###  命名规则快检查

`add-analyzer-retry-policy`：`analyzer`（业务对象）+ `retry-policy`（策略）

|❌ 错误命名|为什么错|
|:----|:----|
|add-retry-decorator|绑实现（decorator 是怎么做的）|
|add-retry-handler|绑实现（handler）|
|add-chat-retry|chat 不是业务对象 · analyzer 才是|
|add-backoff-module|连"retry"这个目的都没体现|



![图片](第二周（加餐-2）OpenSpec实操指南/15.png)

现在拥有了AI生成的proposal.md，不过这个纯AI生成的proposal.md，我们需要手工修改。


### 提交第一个 commit

```plain
git add openspec/changes/add-analyzer-retry-policy/
git commit -m "chore(openspec): new change add-analyzer-retry-policy (templates)"
```



## 4 · Stage 2 · 手写 `proposal.md`（关键步）


### 手写`proposal.md`

打开 `openspec/changes/add-analyzer-retry-policy/proposal.md`，把 template 删掉。


**然后按下面这个结构写**（这份模板你值得收藏）：

```plain
# add-analyzer-retry-policy

## Why

sdd-in-action/week2/code 的 analyzer（`pipeline/pipeline.py::step_analyze`）在 LLM API
调用层没有重试逻辑。历史事故：采集 50 条跑到第 23 条 timeout，脚本退出，前 22 条的
token 成本 ¥0.04 沉没，当天知识库空。LLM API 的瞬时故障（timeout / rate limit /
connection reset / 5xx）是常态，pipeline 必须自己扛住这一层抖动。

## What

在 `pipeline/model_client.py` 新增 `with_retry` 装饰器，套在 `chat()` 上实现指数
退避重试：

- **可重试异常**：`APITimeoutError`、`APIConnectionError`、`RateLimitError`、
  `httpx.TimeoutException`、`httpx.ConnectError`、`APIStatusError where status_code >= 500`
- **不可重试异常**：`json.JSONDecodeError`、`KeyError`、`ValueError`
  （内容层错误 · 重试无效）
- **重试策略**：max_attempts=3，base_delay=1s，指数退避 1s → 2s → 4s，
  max_delay=20s 封顶，jitter 1.0-1.5× 只加不减（防雪崩）
- **成本追踪**：每次 API 调用（包括失败的重试）都记一次 cost_tracker，
  失败的 tokens=0，成功的按 response.usage 记
- **终极失败**：max_attempts 用完仍失败 → 沿用现有 fallback（降级 summary），
  该 item 的 `status` 字段标记 `"degraded"`，pipeline 继续跑完其他 items

## Out of scope

- 不做 provider 级 fallback（OpenAI 挂了切 DeepSeek）—— 未来迭代
- 不做 circuit breaker（连续失败 N 次后停止调用）—— ROI 不够
- 不做 async / 并发重试 —— 保持同步简单
- 不吃 `Retry-After` header —— 统一走 exp backoff 简化实现
- 不改 step_collect / step_organize / step_save —— 作用域就这一个函数
```
这份 proposal 的几个细节。
|句子|为什么这么写|
|:----|:----|
|*"历史事故：..."*|给 AI 一个**具体的 pain** · AI 会知道不是抽象需求 · 策略会往"省钱"方向倾斜|
|明确列**可重试 vs 不可重试**|你 explore 得到的结论 · 直接落到 proposal · AI 不用再猜|
|*"pipeline 继续跑完其他 items"*|这句决定 apply 出来是 try/except 还是 abort 风格 · 漏写会默认 abort|
|**Out of scope 列 5 条**|后面 /opsx-ff 不会多生成 provider fallback / circuit breaker · 作用域干净|

后面这三条**不要做：**

1. **写成 user story**：`As a developer, I want retries so that...` ← 这是 Jira ticket，不是 spec

2. **只写 What 不写 Why**：AI 没有动机感，出来的 spec 干涩

3. **Out of scope 留空**：会多出 3 个你不想要的 capability



### 为什么不用 `/opsx-propose`来自动生成proposal ？

`/opsx-propose` 会让 AI 直接生成 proposal —— 快是快，但 AI 经常把**主语写歪**（你想"给 analyzer 加 retry"，AI 生成"build resilient error handling system"）。主语偏差一毫米，后面 spec/代码/测试全歪一公里。


本 tutorial 走 `/opsx-new`**→ 手写 proposal →**`/opsx-ff` 这条路：

* `new` 只创目录，不写内容

* 手写 proposal 强迫你把主语钉死（5 分钟投资回报最高）

* `ff` 检测到 `proposal.md` 已存在就用你的，跳过生成步骤，只补 spec/design/tasks


什么时候可以偷懒用 `/opsx-propose`？change 本身只动 10 行代码 + 主语已经极其明确（比如 “rename variable X to Y in file Z”），propose 一把梭也不会错。


本 tutorial 的 retry 不算简单 change（5 个 requirement 边界要想透），值得花那 5 分钟手写。


### commit

```plain
git add openspec/changes/add-analyzer-retry-policy/proposal.md
git commit -m "docs(openspec): write proposal for add-analyzer-retry-policy"
```


![图片](第二周（加餐-2）OpenSpec实操指南/16.png)


## 5 · Stage 3 · `/opsx-ff` · 生成首稿 + 15 秒自检

### 生成Change工件

下面开始生成Change工件。

```plain
> /opsx-ff
```


AI 响应如下。


![图片](第二周（加餐-2）OpenSpec实操指南/17.png)

![图片](第二周（加餐-2）OpenSpec实操指南/18.png)
![图片](第二周（加餐-2）OpenSpec实操指南/19.png)

工件创建成功，除了之前手工创建的proposal.md，还有design.md, tasks.md等等规范。


![图片](第二周（加餐-2）OpenSpec实操指南/20.png)

![图片](第二周（加餐-2）OpenSpec实操指南/21.png)


### 更重要的当然是Spec

看看下面输出的东西。

```plain
ls openspec/changes/add-analyzer-retry-policy/specs/
```
**期望输出**：
```plain
analyzer-retry-policy/
```



![图片](第二周（加餐-2）OpenSpec实操指南/22.png)

**只有 1 个目录 · 名字是**`analyzer-retry-policy`**（业务词）** → ✅ 继续 Stage 4。


**如果看到下面任何一个**，可以按照诊断做相应处置。

|你看到的|诊断|
|:----|:----|
|retry-handler/|❌ 跑偏到实现词。回 Stage 2 改 proposal，强调"analyzer 的能力"|
|decorator-utility/|❌ 更严重跑偏|
|retry-policy/ + exception-filter/ + cost-tracker/ 3 个目录|❌ AI 过度拆分。回 Stage 2 明确 "all in one capability"|
|openspec-config/|❌ AI 把 retry 理解成给 openspec 自己加 retry 了。回 Stage 2 · proposal 第一段必须先说清楚项目是什么|

**跑偏的唯一修复方式**：

```plain
rm -rf openspec/changes/add-analyzer-retry-policy
# 回 Stage 2 改 proposal · 主语写得更死
/opsx-new add-analyzer-retry-policy
```
别舍不得那 2 分钟写好的 proposal，**用错误的 proposal 继续 grill-me 只会错上加错**。
### 看看生成的 spec

```plain
cat openspec/changes/add-analyzer-retry-policy/specs/analyzer-retry-policy/spec.md
```
**期望内容**：
```plain
# analyzer-retry-policy

## ADDED Requirements

### Requirement: RETRY-POLICY

The `chat()` function in `pipeline/model_client.py` MUST retry on transient
LLM API failures.

#### Scenario: Transient timeout triggers retry
- **WHEN** `chat()` raises `APITimeoutError`
- **THEN** the call MUST be retried up to `max_attempts=3` times
- **AND** the delay between attempts MUST follow exponential backoff
  (base=1s, factor=2, max=20s, with 1.0-1.5× jitter)

#### Scenario: Rate limit triggers retry
- **WHEN** `chat()` raises `RateLimitError`
- **THEN** same retry policy as above

#### Scenario: Connection error triggers retry
- **WHEN** `chat()` raises `APIConnectionError` or `httpx.TimeoutException`
  or `httpx.ConnectError`
- **THEN** same retry policy as above

### Requirement: EXCEPTION-REGISTRY

The module MUST distinguish retryable from non-retryable exceptions.

#### Scenario: Non-retryable exceptions propagate immediately
- **WHEN** `chat()` raises `json.JSONDecodeError`, `KeyError`, or `ValueError`
- **THEN** the exception MUST propagate immediately without retry
- **AND** no additional cost_tracker entries MUST be recorded

### Requirement: COST-TRACKING

All retry attempts (including failures) MUST be recorded in cost_tracker.

#### Scenario: Retry attempts are billable
- **WHEN** a retry occurs
- **THEN** cost_tracker MUST log each API call with status="retry"
  or status="success"
- **AND** token counts MUST include partial responses from failed attempts

### Requirement: DEGRADATION

When all retries fail, the pipeline MUST continue with degraded output.

#### Scenario: Max retries exhausted
- **WHEN** max_attempts consecutive retries all fail
- **THEN** the item MUST fall back to the existing default summary
- **AND** the item's status field MUST be set to "degraded"
- **AND** the pipeline MUST continue processing remaining items

### Requirement: CONCURRENCY-OFF

Retries MUST be synchronous and sequential per item.

#### Scenario: No concurrent retries
- **WHEN** a retry happens
- **THEN** no other item is processed in parallel
```
**首稿基本能用**，但仔细看 COST-TRACKING 的 *“partial responses from failed attempts”*，**这句是AI 编的**，httpx 超时的时候压根没有 partial response。grill-me 就是要把这种偷偷编出来的东西揪出来。
### commit

```plain
git add openspec/changes/add-analyzer-retry-policy/
git commit -m "docs(openspec): opsx:ff first draft · 5 requirements 70% correct"
```



## 6 · Stage 4 · `grill-me` 拷问 spec

grill-me 是 Week 1 你练过的 agent。现在让它对着 `specs/analyzer-retry-policy/spec.md` 拷问。

### 使用grill-me检验

在 IDE 里输入

```plain
> @grill-me 请批判视角审这份 spec:
> openspec/changes/add-analyzer-retry-policy/specs/analyzer-retry-policy/spec.md
>
> 重点拷问:
> 1. 是否有无法实现的条款?
> 2. 是否有内部矛盾?
> 3. 是否遗漏了边界?
> 4. 条款的可测试性?
```
### grill-me 可能的回应（AI给的示例）

```plain
┌─ grill-me ─────────────────────────────────────────────────────────────┐
│  审完了。5 个问题 · 从严重到次要:                                       │
│                                                                        │
│  🔴 [BLOCKING] COST-TRACKING 条款自相矛盾                               │
│                                                                        │
│   > "token counts MUST include partial responses from failed attempts" │
│                                                                        │
│   httpx 的 TimeoutException 在请求未完成时触发 · 此时压根没有 response │
│   谈不上 partial。建议改为:                                             │
│                                                                        │
│     - WHEN a retry attempt raises a retryable exception                │
│     - THEN cost_tracker MUST log the attempt with tokens=0             │
│           and status="retry_failed"                                    │
│     - WHEN a retry attempt succeeds                                    │
│     - THEN cost_tracker MUST log tokens from response.usage            │
│                                                                        │
│  ───────────────────────────────────────────────────────────────────  │
│                                                                        │
│  🟡 [SERIOUS] DEGRADATION 没说 degraded 条目还要不要入库                │
│                                                                        │
│   > "item's status field MUST be set to 'degraded'"                    │
│                                                                        │
│   status=degraded 的条目继续流到 step_organize 入库 · 还是在 analyze   │
│   阶段就丢掉? spec 没写。Out of scope 也没排除。实现时 AI 会猜。       │
│                                                                        │
│   建议追加:                                                            │
│                                                                        │
│     #### Scenario: Degraded items skip articles output                 │
│     - WHEN an item is marked status="degraded"                         │
│     - THEN it MUST still be passed to step_organize                    │
│     - AND step_organize MUST skip degraded items from articles/        │
│           (but keep in knowledge/raw/ for debug)                       │
│                                                                        │
│  ───────────────────────────────────────────────────────────────────  │
│                                                                        │
│  🟠 [MODERATE] EXCEPTION-REGISTRY 漏了 5xx HTTP 错误                    │
│                                                                        │
│   OpenAI/DeepSeek 容量紧张时返 500/502/503 · 它们是 APIStatusError     │
│   不是 APITimeoutError · 现在的 spec 会漏掉这类错误直接 raise 出去。   │
│                                                                        │
│   建议追加到可重试列表: APIStatusError where status_code >= 500        │
│                                                                        │
│  ───────────────────────────────────────────────────────────────────  │
│                                                                        │
│  🟠 [MODERATE] RETRY-POLICY 没说失败的"最后一次"要不要记 cost          │
│                                                                        │
│   attempt 3 (最后一次) 失败时 · COST-TRACKING 的条款说"retry 要记" ·   │
│   但 attempt 3 不是 retry (后面没 retry 了) · 应该单独说清楚。         │
│                                                                        │
│   建议: "the final failed attempt (attempt = max_attempts) MUST ALSO   │
│          be logged with tokens=0 and status='retry_failed'"           │
│                                                                        │
│  ───────────────────────────────────────────────────────────────────  │
│                                                                        │
│  🟢 [MINOR] CONCURRENCY-OFF 冗余                                        │
│                                                                        │
│   你 proposal 的 Out of scope 已经排除了 async/并发。再在 spec 里      │
│   写 CONCURRENCY-OFF 一个 requirement 略冗余。建议合并进 RETRY-POLICY  │
│   的描述行("retries are synchronous and sequential") · 省一个 req。   │
│                                                                        │
│  ───────────────────────────────────────────────────────────────────  │
│                                                                        │
│  总结 · 5 问题 · 1 blocking · 2 serious · 1 moderate · 1 minor        │
│  blocking 必须改才能 apply · serious 最好改 · minor 看你口味。         │
└────────────────────────────────────────────────────────────────────────┘
```
### 回应 grill-me（把有效反馈落回 spec）

```plain
> 🔴 按你建议改 COST-TRACKING
> 🟡 degraded 条目流向 · 选"流到 step_organize 但 skip articles 输出"
> 🟠 加 APIStatusError where status_code >= 500 到 EXCEPTION-REGISTRY
> 🟠 最后一次失败也记 cost_tracker
> 🟢 合并 CONCURRENCY-OFF 进 RETRY-POLICY
>
> 请直接改 spec.md · 显示 diff
```
### grill-me 返回 diff（Mock）

```plain
 ### Requirement: RETRY-POLICY

 The `chat()` function in `pipeline/model_client.py` MUST retry on transient
-LLM API failures.
+LLM API failures. Retries MUST be synchronous and sequential per item.

 #### Scenario: Connection error triggers retry
 - **WHEN** `chat()` raises `APIConnectionError` or `httpx.TimeoutException`
   or `httpx.ConnectError`
+- **OR** `APIStatusError` where `status_code >= 500`
 - **THEN** same retry policy as above

 ### Requirement: COST-TRACKING

-All retry attempts (including failures) MUST be recorded in cost_tracker.
+Every attempt (success or retryable-failure) MUST be recorded in cost_tracker.

 #### Scenario: Retry attempts are billable
-- **WHEN** a retry occurs
-- **THEN** cost_tracker MUST log each API call with status="retry"
-  or status="success"
-- **AND** token counts MUST include partial responses from failed attempts
+- **WHEN** a retry attempt raises a retryable exception
+- **THEN** cost_tracker MUST log the attempt with tokens=0
+  and status="retry_failed"
+- **WHEN** a retry attempt succeeds (including first attempt)
+- **THEN** cost_tracker MUST log the attempt with tokens from
+  response.usage and status="success"
+- **WHEN** the final attempt (attempt == max_attempts) fails
+- **THEN** cost_tracker MUST log tokens=0 and status="retry_failed"

 ### Requirement: DEGRADATION
 #### Scenario: Max retries exhausted
 - **WHEN** max_attempts consecutive retries all fail
 - **THEN** the item MUST fall back to the existing default summary
 - **AND** the item's `status` field MUST be set to "degraded"
 - **AND** the pipeline MUST continue processing remaining items

+#### Scenario: Degraded items skip articles output
+- **WHEN** an item is marked `status="degraded"`
+- **THEN** step_organize MUST skip it from `knowledge/articles/`
+  (keeping only in `knowledge/raw/` for debug)

-### Requirement: CONCURRENCY-OFF
-
-Retries MUST be synchronous and sequential per item.
-
-#### Scenario: No concurrent retries
-...
```
改完 6 处。**spec 现在 apply-ready**。
### grill-me 自检清单

保存前自己再看一遍：

* [x] 每个 Requirement 能用代码实现

* [x] 每个 Scenario 能写成测试（WHEN 明确、THEN 可检查）

* [x] 没有内部矛盾

* [x] 边界都列了（retryable / non-retryable / 5xx / final-attempt / degraded-flow）

* [x] Out of scope 里列的确实没进 spec


**过了这一轮，apply 出来的代码基本不大需要返工**。（但是因为我图快，回答的问题不仔细，也不准确，后续还是返工了。）

### commit

```plain
git add openspec/changes/add-analyzer-retry-policy/
git commit -m "docs(openspec): grill-me pass · fix 5 spec issues (1 blocking · 2 serious · 2 moderate)"

```


下面是我拷问过程的一系列截图。


![图片](第二周（加餐-2）OpenSpec实操指南/23.png)

![图片](第二周（加餐-2）OpenSpec实操指南/24.png)

![图片](第二周（加餐-2）OpenSpec实操指南/25.png)

![图片](第二周（加餐-2）OpenSpec实操指南/26.png)


![图片](第二周（加餐-2）OpenSpec实操指南/27.png)


![图片](第二周（加餐-2）OpenSpec实操指南/28.png)


![图片](第二周（加餐-2）OpenSpec实操指南/29.png)


![图片](第二周（加餐-2）OpenSpec实操指南/30.png)


![图片](第二周（加餐-2）OpenSpec实操指南/31.png)




![图片](第二周（加餐-2）OpenSpec实操指南/32.png)






![图片](第二周（加餐-2）OpenSpec实操指南/33.png)

## 7 · Stage 5 · `/opsx-apply` · 生成代码

### AI根据Spec驱动来生成代码

```plain
> /opsx-apply
```
![图片](第二周（加餐-2）OpenSpec实操指南/34.png)
![图片](第二周（加餐-2）OpenSpec实操指南/35.png)




![图片](第二周（加餐-2）OpenSpec实操指南/36.png)

![图片](第二周（加餐-2）OpenSpec实操指南/37.png)


![图片](第二周（加餐-2）OpenSpec实操指南/38.png)


### 看 model_client.py 的修改

```plain
git diff master -- pipeline/model_client.py | head -80
```
**期望看到的 diff**：
```plain
+import logging
+import random
+import time
+from functools import wraps
+from typing import Callable, TypeVar
+
+import httpx
+from openai import (
+    APIConnectionError,
+    APIStatusError,
+    APITimeoutError,
+    RateLimitError,
+)
+
+logger = logging.getLogger(__name__)
+T = TypeVar("T")
+
+# ── Exception Registry (spec: EXCEPTION-REGISTRY) ─────────────────
+RETRYABLE_EXCEPTIONS: tuple[type[BaseException], ...] = (
+    APITimeoutError,
+    APIConnectionError,
+    RateLimitError,
+    httpx.TimeoutException,
+    httpx.ConnectError,
+)
+
+
+def _is_retryable(exc: BaseException) -> bool:
+    if isinstance(exc, RETRYABLE_EXCEPTIONS):
+        return True
+    # spec: 5xx HTTP status codes are retryable
+    if isinstance(exc, APIStatusError) and 500 <= exc.status_code < 600:
+        return True
+    return False
+
+
+def with_retry(
+    max_attempts: int = 3,
+    base_delay: float = 1.0,
+    max_delay: float = 20.0,
+    cost_tracker: Callable[[str, int], None] | None = None,
+):
+    """指数退避重试装饰器 · spec: analyzer-retry-policy"""
+    def decorator(fn: Callable[..., T]) -> Callable[..., T]:
+        @wraps(fn)
+        def wrapper(*args, **kwargs) -> T:
+            last_exc: BaseException | None = None
+            for attempt in range(1, max_attempts + 1):
+                try:
+                    result = fn(*args, **kwargs)
+                    if cost_tracker:
+                        cost_tracker("success", _tokens_of(result))
+                    return result
+                except Exception as e:
+                    if not _is_retryable(e):
+                        raise  # spec EXCEPTION-REGISTRY · non-retryable
+                    last_exc = e
+                    if cost_tracker:
+                        cost_tracker("retry_failed", 0)
+                    if attempt == max_attempts:
+                        raise
+                    delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
+                    delay *= 1.0 + random.random() * 0.5  # jitter 1.0-1.5×
+                    logger.warning(
+                        "[retry] %s attempt %d/%d failed: %s · sleep %.1fs",
+                        fn.__name__, attempt, max_attempts, type(e).__name__, delay,
+                    )
+                    time.sleep(delay)
+            assert last_exc is not None
+            raise last_exc
+        return wrapper
+    return decorator
+
+
+def _tokens_of(result: ChatResponse) -> int:
+    try:
+        return (result.prompt_tokens or 0) + (result.completion_tokens or 0)
+    except AttributeError:
+        return 0
+
+
-def chat(prompt: str, system: str = "...", ...):
+@with_retry(max_attempts=3, base_delay=1.0, max_delay=20.0)
+def chat(prompt: str, system: str = "...", ...):
     """调用 LLM · 返回 ChatResponse"""
     ...
```
### 看 pipeline.py 的修改

```plain
git diff master -- pipeline/pipeline.py
```
**期望 diff 如下**：
```plain
 def step_analyze(items):
     for i, item in enumerate(items, 1):
         ...
-        response = chat(prompt)
+        try:
+            response = chat(prompt)
+        except Exception as e:
+            # retry 用完仍失败 · spec DEGRADATION
+            logger.error("analyze failed after all retries · %s · %s",
+                         item['title'], e)
+            analyzed.append({
+                **item,
+                "summary": item.get("description", "")[:200],
+                "tags": ["degraded"],
+                "relevance_score": 0.0,
+                "category": "unknown",
+                "status": "degraded",
+                "analyzed_at": datetime.now(timezone.utc).isoformat(),
+            })
+            continue
         ...


 def step_organize(items, min_score=0.6):
     for item in items:
+        # spec DEGRADATION · skip degraded items from articles
+        if item.get("status") == "degraded":
+            continue
         if item.get("relevance_score", 0) < min_score:
             continue
         ...
```
### 看 tests/test_retry.py

```plain
cat tests/test_retry.py | head -40
"""Unit tests for analyzer-retry-policy · spec coverage"""

import pytest
from unittest.mock import MagicMock
from openai import APITimeoutError, RateLimitError, APIStatusError

from pipeline.model_client import with_retry, _is_retryable


def test_retryable_exceptions():
    """spec: EXCEPTION-REGISTRY"""
    assert _is_retryable(APITimeoutError("timeout"))
    assert _is_retryable(RateLimitError("429", response=None, body=None))
    # 5xx HTTP
    err503 = APIStatusError("503", response=MagicMock(status_code=503), body=None)
    assert _is_retryable(err503)
    # 4xx should NOT retry
    err404 = APIStatusError("404", response=MagicMock(status_code=404), body=None)
    assert not _is_retryable(err404)


def test_non_retryable_exceptions():
    """spec: EXCEPTION-REGISTRY · negative"""
    from json import JSONDecodeError
    assert not _is_retryable(JSONDecodeError("x", "y", 0))
    assert not _is_retryable(KeyError("missing"))
    assert not _is_retryable(ValueError("bad"))


def test_retry_with_eventual_success():
    """spec: RETRY-POLICY · 第 3 次成功"""
    calls = []
    @with_retry(max_attempts=3, base_delay=0.01)
    def flaky():
        calls.append(1)
        if len(calls) < 3:
            raise APITimeoutError("timeout")
        return MagicMock(prompt_tokens=100, completion_tokens=50)
    flaky()
    assert len(calls) == 3

# ... 还有 7 个测试（含 cost_tracker 记录、degraded、jitter 上限等）
```
**注意**：每个测试的 docstring 都指向对应的 spec requirement ID。这不是巧合，这是 apply 出来的代码**自带 traceability**。等下 verify 就靠这个做反向对照。
### 跑一下单测

```plain
cd ~/sdd-in-action/week2/code
pytest tests/test_retry.py -v
```
**期望输出**：
```plain
============================= test session starts ==============================
collected 10 items

tests/test_retry.py::test_retryable_exceptions PASSED                   [ 10%]
tests/test_retry.py::test_non_retryable_exceptions PASSED               [ 20%]
tests/test_retry.py::test_retry_with_eventual_success PASSED            [ 30%]
tests/test_retry.py::test_retry_exhausts_and_raises PASSED              [ 40%]
tests/test_retry.py::test_jitter_respects_max_delay PASSED              [ 50%]
tests/test_retry.py::test_cost_tracker_logs_retry_failed PASSED         [ 60%]
tests/test_retry.py::test_cost_tracker_logs_success PASSED              [ 70%]
tests/test_retry.py::test_final_attempt_failure_logged PASSED           [ 80%]
tests/test_retry.py::test_degraded_item_status PASSED                   [ 90%]
tests/test_retry.py::test_degraded_item_skipped_in_organize PASSED      [100%]

========================= 10 passed in 0.45s ==================================
```
### commit

```plain
git add pipeline/model_client.py pipeline/pipeline.py tests/test_retry.py \
        openspec/changes/add-analyzer-retry-policy/
git commit -m "feat(analyzer): implement retry policy via /opsx-apply

Spec: openspec/changes/add-analyzer-retry-policy/
- model_client.py: with_retry decorator + exception registry
- pipeline.py: degraded status handling + organize filter
- 10 unit tests covering all 5 requirements"
```


这个过程经过了一下反复的调试，才真正跑通，有错误就让AI解决，过程展示如下。



![图片](第二周（加餐-2）OpenSpec实操指南/39.png)

![图片](第二周（加餐-2）OpenSpec实操指南/40.png)


![图片](第二周（加餐-2）OpenSpec实操指南/41.png)


![图片](第二周（加餐-2）OpenSpec实操指南/42.png)



![图片](第二周（加餐-2）OpenSpec实操指南/43.png)

要小心它自己修改测试脚本让自己通过，因此我们还是要知道它测试的是什么。

![图片](第二周（加餐-2）OpenSpec实操指南/44.png)


![图片](第二周（加餐-2）OpenSpec实操指南/45.png)


![图片](第二周（加餐-2）OpenSpec实操指南/46.png)




![图片](第二周（加餐-2）OpenSpec实操指南/47.png)


![图片](第二周（加餐-2）OpenSpec实操指南/48.png)

最终成功通过测试。


![图片](第二周（加餐-2）OpenSpec实操指南/49.png)

## 8 · Stage 6 · `/opsx-verify` · 反向对照

### 启动Verify

```plain
> /opsx-verify
```
### ![图片](第二周（加餐-2）OpenSpec实操指南/50.png)

![图片](第二周（加餐-2）OpenSpec实操指南/51.png)
### 可能有响应 warning

决定接受还是改。

```plain
> 关于 cost_tracker optional 的 warning · 我的判断是保持 optional · 理由:
> - 生产调用点 step_analyze 总是传 tracker · 行为满足 spec
> - 作为通用装饰器允许 None 方便单测（不用 mock tracker）
> - 这个判断记到 design.md 的 Decision Log
>
> 请把这条 append 到 design.md
```


如调整，AI 会在 design.md 加一段修改：

```plain
## Decision Log

### 2026-04-12 · cost_tracker 参数保持 optional

- **Context**: /opsx-verify warned that spec says "MUST log" but decorator
  allows cost_tracker=None.
- **Decision**: 保持 optional。
- **Rationale**: 实际调用点（step_analyze 调 chat）总是传 tracker · MUST
  约束在调用层成立。装饰器层允许 None 便于单测不 mock tracker。
- **Alternative rejected**: 强制 required 参数 → 单测代码臃肿 · 实际安全性无提升。
```
### ![图片](第二周（加餐-2）OpenSpec实操指南/52.png)

### commit

```plain
git add openspec/changes/add-analyzer-retry-policy/design.md
git commit -m "docs(openspec): record verify decision · cost_tracker stays optional"
```



## 9 · Stage 7 · PR + merge + `/opsx-archive`

### push feature 分支

```plain
git push -u origin feature/add-analyzer-retry-policy
```
### 在 GitHub 创建 PR

**PR 标题**：`feat(analyzer): add retry policy with exponential backoff`


**PR body**（粘 proposal 的 Why + What）：

```plain
## Summary
Adds retry logic to LLM calls in `pipeline/model_client.py::chat()` to handle
transient API failures (timeout / rate limit / 5xx / connection errors).

## Why
采集 50 条跑到第 23 条 timeout → 脚本崩 → 前 22 条的 tokens 成本沉没。

## What
- `with_retry` 装饰器 + exception registry
- max_attempts=3 · exp backoff 1→2→4s · jitter 1.0-1.5× · max_delay=20s
- cost_tracker 区分 success / retry_failed
- 终极失败降级 status="degraded" · organize 跳过不入库

## Spec
See `openspec/changes/add-analyzer-retry-policy/`

## Test plan
- [x] `pytest tests/test_retry.py -v` · 10/10 passed
- [x] `/opsx-verify` · 5/5 requirements covered
- [ ] 跑一次真实 pipeline（reviewer 在合并前自己跑）
```
### merge 之后回 master

```plain
# PR merge 后
git checkout master
git pull origin master
```
### 启动`/opsx-archive`

```plain
> /opsx-archive add-analyzer-retry-policy
```


### 验证归档

```plain
ls openspec/changes/
# 期望 · archive/（只剩这一个）

ls openspec/changes/archive/
# 期望 · 2026-04-12-add-analyzer-retry-policy/

cat openspec/specs/analyzer-retry-policy.md | head -10
# 期望 · 主规范里已合并 retry-policy 的 5 个 requirement
```
###  最后一次 commit + push master

```plain
git add openspec/
git commit -m "chore(openspec): archive add-analyzer-retry-policy after merge"
git push

```


截屏展示如下

![图片](第二周（加餐-2）OpenSpec实操指南/53.png)

![图片](第二周（加餐-2）OpenSpec实操指南/54.png)


![图片](第二周（加餐-2）OpenSpec实操指南/55.png)



![图片](第二周（加餐-2）OpenSpec实操指南/56.png)

## 10 · 终点清单

跑完全程后，仓库应该有：

### 代码侧（master 分支）

```plain
week2/code/
├── pipeline/
│   ├── model_client.py    ← 新增 with_retry 装饰器 · RETRYABLE_EXCEPTIONS
│   └── pipeline.py        ← step_analyze 处理 degraded · step_organize 过滤
└── tests/
    └── test_retry.py      ← ✨ 新增 · 10 个单测
```
### OpenSpec 侧（master 分支）

```plain
week2/code/openspec/
├── changes/
│   └── archive/
│       └── 2026-04-12-add-analyzer-retry-policy/   ← ✨ 归档
│           ├── proposal.md      ← Why + What + Out of scope
│           ├── design.md        ← 含 Decision Log (cost_tracker optional)
│           ├── tasks.md         ← 6 个 task · 全 ☑️
│           └── specs/
│               └── analyzer-retry-policy/
│                   └── spec.md  ← 5 req · 10 scenario
└── specs/
    └── analyzer-retry-policy.md  ← ✨ 主规范 · archive 时自动 sync
```
### git 侧

```plain
* master (合并后)
|\
| * feature/add-analyzer-retry-policy (8 commits)
|   ├─ chore: opsx:new templates
|   ├─ docs: write proposal
|   ├─ docs: opsx:ff first draft
|   ├─ docs: grill-me pass · fix 5 issues
|   ├─ feat: implement retry policy via opsx:apply
|   ├─ docs: record verify decision
|   └─ (merge commit)
* chore: archive after merge
```


![图片](第二周（加餐-2）OpenSpec实操指南/57.png)

好，终于成功了！


总的来说，对于这样的一个change，比起自己去分析需求写代码，可能还是还是用SDD的比较快；但是如果说是只需要改一两行的那种bug，当然我觉得还是自己去改比较好了。


那么，面对一个新任务，或者一个修改的时候，在下面这几个选项里：

* 自己手写代码

* Vibe Coding

* OpenSpec驱动的SDD开发


针对于各种规模的项目，你会决定选择哪一种开发方式？大家可以积极探讨。


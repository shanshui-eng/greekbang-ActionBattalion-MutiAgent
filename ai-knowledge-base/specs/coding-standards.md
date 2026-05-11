# AI 知识库 · 编码规范 v0.2

## 要做什么

- Python 用 black 格式化（`pyproject.toml` 中配置 line-length=88）
- 所有公开函数必须有 Google 风格 docstring（参考 AGENTS.md §3）
- 所有变量、函数、文件名使用 snake_case
- 所有输出使用 logging 模块，禁止裸 print()
- API Key / Token 等敏感信息通过环境变量注入

## 不做什么

- 不允许魔法字符串——所有字面量必须定义为模块顶层常量（`SCREAMING_SNAKE_CASE`），pre-commit 用 `flake8-blind-except` + 自定义规则检查
- 不允许 TODO / FIXME 提交到 main——pre-commit hook + CI 均用 `grep` 拦截

## 边界 & 验收

- 单测要求（statement coverage）：
  - 核心模块（`main.py`、各 Agent pipeline）：≥ 90%
  - 工具模块（`utils/`、`notify.py`）：≥ 80%
  - 豁免：`__init__.py`、`config.py`

## 怎么验证

```bash
# 本地运行
black --check .
ruff check .
pytest --cov --cov-fail-under=80

# CI 额外拦截 TODO
! grep -rn "TODO\|FIXME" --include="*.py" .
```

配置文件引用：`pyproject.toml`（black/ruff/pytest 配置均集中在此）

## 红线（追加）

- 禁止直接修改 `knowledge/raw/` 中的文件
- 禁止 Agent 之间直接调用函数
- 禁止单次 LLM 调用处理超过 50 条数据

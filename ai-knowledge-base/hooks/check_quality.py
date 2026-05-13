"""知识条目 5 维度质量评分工具.

用法:
    python hooks/check_quality.py <json_file> [json_file2 ...]
    python hooks/check_quality.py knowledge/articles/*.json

评分维度:
    1. 摘要质量 (25 分): 长度 + 技术关键词奖励
    2. 技术深度 (25 分): score 字段 1-10 映射
    3. 格式规范 (20 分): id/title/url/status/timestamp 各 4 分
    4. 标签精度 (15 分): 1-3 个合法标签最佳
    5. 空洞词检测 (15 分): 中英文黑名单匹配

等级: A >= 80, B >= 60, C < 60
退出码: 存在 C 级 → 1, 全 A/B → 0
"""

import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

# ── 常量 ───────────────────────────────────────────

EXIT_SUCCESS = 0
EXIT_FAILURE = 1

VALID_TAGS = {
    "llm", "agent", "rag", "training", "inference", "toolkit",
    "framework", "paper", "opensource", "security", "multimodal",
    "coding", "database", "devops",
}

VALID_STATUSES = {"draft", "review", "published", "archived"}

TECH_KEYWORDS = [
    "大模型", "LLM", "Agent", "RAG", "推理", "训练", "开源",
    "框架", "工具", "模型", "API", "向量", "检索", "微调",
    "部署", "transformer", "diffusion", "embedding", "dataset",
    "benchmark", "SOTA", "GPU", "量化", "分布式", "多模态",
    "fine-tuning", "prompt", "RLHF", "MoE", "LoRA", "QLoRA",
    "attention", "token", "inference", "scaling",
]

CN_BUZZWORDS = [
    "赋能", "抓手", "闭环", "打通", "全链路", "底层逻辑",
    "颗粒度", "对齐", "拉通", "沉淀", "强大的", "革命性的",
]

EN_BUZZWORDS = [
    "groundbreaking", "revolutionary", "game-changing",
    "cutting-edge", "best-in-class", "world-class", "disruptive",
    "next-generation", "unprecedented", "paradigm shift",
    "state-of-the-art", "synergy", "ecosystem", "holistic",
]

ID_PATTERN = re.compile(r"^[a-z][a-z0-9-]*-\d{8}-\d{3,}$")
URL_PATTERN = re.compile(r"^https?://[^\s/$.?#].[^\s]*$")
TIMESTAMP_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")


# ── 数据结构 ───────────────────────────────────────

@dataclass
class DimensionScore:
    """单个维度的评分结果."""

    name: str
    score: float
    max_score: float
    details: str = ""


@dataclass
class QualityReport:
    """单条知识条目的质量报告."""

    label: str
    total_score: float = 0.0
    grade: str = "-"
    dimensions: list[DimensionScore] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


# ── 评分函数 ───────────────────────────────────────

def score_summary(summary: str) -> DimensionScore:
    """摘要质量评分 (25 分).

    长度 >= 50 字得 20 分, >= 20 字得 10 分, 技术关键词最多 +5 奖励.
    """
    if not isinstance(summary, str):
        return DimensionScore("摘要质量", 0, 25, "summary 不是字符串 (+0)")

    length = len(summary)
    parts: list[str] = []

    if length >= 50:
        base = 20
        parts.append(f"长度 {length} 字, 满分档 (+{base})")
    elif length >= 20:
        base = 10
        parts.append(f"长度 {length} 字, 基本档 (+{base})")
    else:
        base = 0
        parts.append(f"长度仅 {length} 字, 不足 20 (+0)")

    summary_lower = summary.lower()
    kw_hits = [kw for kw in TECH_KEYWORDS if kw.lower() in summary_lower]
    bonus = min(len(kw_hits), 5)
    if bonus > 0:
        parts.append(f"命中技术关键词 {len(kw_hits)} 个: {', '.join(kw_hits[:5])} (+{bonus})")

    return DimensionScore("摘要质量", base + bonus, 25, "; ".join(parts))


def score_tech_depth(item: dict) -> DimensionScore:
    """技术深度评分 (25 分), 基于原始 score 字段 1-10 → 0-25 线性映射."""
    raw = item.get("score")
    if isinstance(raw, (int, float)) and not isinstance(raw, bool):
        if 1 <= raw <= 10:
            mapped = round(raw * 2.5, 1)
            return DimensionScore("技术深度", mapped, 25, f"原始评分 {raw}/10 → {mapped}/25")
        else:
            return DimensionScore("技术深度", 0, 25, f"原始评分 {raw} 超出 [1,10] (+0)")
    return DimensionScore("技术深度", 0, 25, "缺少有效 score 字段 (+0)")


def score_format(item: dict) -> DimensionScore:
    """格式规范评分 (20 分), id/title/url/status/timestamp 各 4 分."""
    score = 0
    checks: list[str] = []

    id_val = item.get("id", "")
    if isinstance(id_val, str) and ID_PATTERN.match(id_val):
        score += 4
        checks.append("id ✓")
    else:
        checks.append("id ✗")

    title = item.get("title", "")
    if isinstance(title, str) and len(title.strip()) > 0:
        score += 4
        checks.append("title ✓")
    else:
        checks.append("title ✗")

    url = item.get("source_url", "")
    if isinstance(url, str) and URL_PATTERN.match(url):
        score += 4
        checks.append("url ✓")
    else:
        checks.append("url ✗")

    status = item.get("status", "")
    if isinstance(status, str) and status in VALID_STATUSES:
        score += 4
        checks.append("status ✓")
    else:
        checks.append("status ✗")

    ts = item.get("fetched_at", "")
    if isinstance(ts, str) and TIMESTAMP_PATTERN.match(ts):
        score += 4
        checks.append("ts ✓")
    else:
        checks.append("ts ✗")

    return DimensionScore("格式规范", score, 20, " ".join(checks))


def score_tags(item: dict) -> DimensionScore:
    """标签精度评分 (15 分).

    1-3 个标签且全部在标准库中 → 满分.
    """
    tags = item.get("tags", [])
    if not isinstance(tags, list):
        return DimensionScore("标签精度", 0, 15, "tags 不是数组 (+0)")

    valid = [t for t in tags if isinstance(t, str) and t in VALID_TAGS]
    invalid = len(tags) - len(valid)

    if 1 <= len(valid) <= 3 and invalid == 0:
        return DimensionScore("标签精度", 15, 15, f"{len(valid)} 个标签全合法 (+15)")
    elif len(valid) >= 1:
        return DimensionScore("标签精度", 10, 15,
                              f"{len(valid)} 合法 / {invalid} 非法 (+10)")
    else:
        return DimensionScore("标签精度", 0, 15, "无合法标签 (+0)")


def score_buzzwords(item: dict) -> DimensionScore:
    """空洞词检测评分 (15 分), 每个空洞词 -3 分, 最低 0."""
    parts: list[str] = []
    for field in ("title", "summary"):
        val = item.get(field, "")
        if isinstance(val, str):
            parts.append(val)
    combined = " ".join(parts)

    found: list[str] = []
    for bw in CN_BUZZWORDS:
        if bw in combined:
            found.append(bw)
    combined_lower = combined.lower()
    for bw in EN_BUZZWORDS:
        if bw in combined_lower:
            found.append(bw)

    penalty = len(found) * 3
    final = max(0, 15 - penalty)

    if found:
        return DimensionScore("空洞词检测", final, 15,
                              f"发现 {len(found)} 个: {', '.join(found)} (-{penalty})")
    return DimensionScore("空洞词检测", 15, 15, "未检测到空洞词 (+15)")


# ── 渲染 ───────────────────────────────────────────

BAR_WIDTH = 20


def _render_bar(score: float, max_score: float) -> str:
    """渲染得分进度条."""
    ratio = min(score / max_score, 1.0) if max_score > 0 else 0.0
    filled = int(ratio * BAR_WIDTH)
    empty = BAR_WIDTH - filled
    bar = "█" * filled + "░" * empty
    return f"{bar} {score:4.0f}/{max_score:.0f}"


def _grade_color(grade: str) -> str:
    """等级对应的显示前缀."""
    return {"A": "  ✅", "B": "  ⚠️", "C": "  ❌"}.get(grade, "  ?")


def print_report(report: QualityReport) -> None:
    """打印单条条目的质量报告."""
    print(f"\n{'─' * 50}")
    print(f"  {report.label}")
    print(f"{'─' * 50}")

    if report.errors:
        for err in report.errors:
            print(f"  [ERROR] {err}")
        return

    for dim in report.dimensions:
        bar = _render_bar(dim.score, dim.max_score)
        print(f"  {dim.name:<8s}  {bar}  {dim.details}")

    total_bar = _render_bar(report.total_score, 100)
    print(f"  {'─' * 40}")
    print(f"  {'总分':<8s}  {total_bar}  等级: {report.grade}")


def print_final_summary(reports: list[QualityReport]) -> None:
    """打印汇总统计."""
    total = len(reports)
    a_count = sum(1 for r in reports if r.grade == "A")
    b_count = sum(1 for r in reports if r.grade == "B")
    c_count = sum(1 for r in reports if r.grade == "C")
    avg_score = (
        sum(r.total_score for r in reports if r.grade != "-") / max(total, 1)
    )

    print(f"\n{'=' * 50}")
    print(f"  汇总统计")
    print(f"{'=' * 50}")
    print(f"  条目总数: {total}")
    print(f"  A (≥80): {a_count}  |  B (≥60): {b_count}  |  C (<60): {c_count}")
    print(f"  平均分: {avg_score:.1f}")
    print(f"{'=' * 50}")


# ── 核心逻辑 ───────────────────────────────────────

def analyze_file(filepath: Path) -> list[QualityReport]:
    """分析单个 JSON 文件, 返回所有条目的质量报告."""
    if filepath.suffix.lower() != ".json":
        return [QualityReport(str(filepath), errors=[f"非 JSON 文件, 跳过"])]

    try:
        text = filepath.read_text(encoding="utf-8")
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        return [QualityReport(str(filepath), errors=[f"JSON 解析失败: {exc}"])]
    except OSError as exc:
        return [QualityReport(str(filepath), errors=[f"文件读取失败: {exc}"])]

    items: list[tuple[int | None, object]] = []
    if isinstance(data, dict):
        items.append((None, data))
    elif isinstance(data, list):
        items.extend((i, item) for i, item in enumerate(data))
    else:
        return [QualityReport(str(filepath), errors=["根节点不是 dict 或 list"])]

    reports: list[QualityReport] = []
    for idx, item in items:
        label = str(filepath) if idx is None else f"{filepath}[#{idx}]"

        if not isinstance(item, dict):
            reports.append(QualityReport(label, errors=["条目不是 object"]))
            continue

        dimensions = [
            score_summary(item.get("summary", "")),
            score_tech_depth(item),
            score_format(item),
            score_tags(item),
            score_buzzwords(item),
        ]
        total = sum(d.score for d in dimensions)
        grade = "A" if total >= 80 else "B" if total >= 60 else "C"
        reports.append(QualityReport(label, total, grade, dimensions))

    return reports


def main() -> int:
    """入口函数."""
    args = sys.argv[1:]
    if not args:
        print(
            "用法: python hooks/check_quality.py <json_file> [json_file2 ...]",
            file=sys.stderr,
        )
        return EXIT_FAILURE

    files_to_check: list[Path] = []
    for arg in args:
        path = Path(arg)
        if path.is_file():
            files_to_check.append(path)
        else:
            globbed = sorted(path.parent.glob(path.name))
            if not globbed:
                print(f"[WARN] 未匹配到文件: {arg}", file=sys.stderr)
            files_to_check.extend(globbed)

    if not files_to_check:
        print("[ERROR] 没有找到可评分的文件", file=sys.stderr)
        return EXIT_FAILURE

    all_reports: list[QualityReport] = []
    for fpath in files_to_check:
        reports = analyze_file(fpath)
        all_reports.extend(reports)
        for report in reports:
            print_report(report)

    print_final_summary(all_reports)

    has_c = any(r.grade == "C" for r in all_reports)
    return EXIT_FAILURE if has_c else EXIT_SUCCESS


if __name__ == "__main__":
    sys.exit(main())

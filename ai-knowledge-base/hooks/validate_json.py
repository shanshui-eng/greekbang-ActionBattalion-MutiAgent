"""校验知识条目 JSON 文件.

用法:
    python hooks/validate_json.py <json_file> [json_file2 ...]
    python hooks/validate_json.py knowledge/articles/*.json

校验项:
    1. JSON 解析
    2. 必填字段存在性与类型
    3. ID 格式: {source}-{YYYYMMDD}-{NNN}
    4. status 取值范围
    5. URL 格式
    6. 摘要长度 >= 20 字
    7. 标签数量 >= 1
    8. score (可选) 1-10
    9. audience (可选) beginner/intermediate/advanced
"""

import json
import re
import sys
from pathlib import Path


EXIT_SUCCESS = 0
EXIT_FAILURE = 1

ID_PATTERN = re.compile(r"^[a-z][a-z0-9-]*-\d{8}-\d{3,}$")
URL_PATTERN = re.compile(r"^https?://[^\s/$.?#].[^\s]*$")
VALID_STATUSES = {"draft", "review", "published", "archived"}
VALID_AUDIENCES = {"beginner", "intermediate", "advanced"}

REQUIRED_FIELDS: dict[str, type] = {
    "id": str,
    "title": str,
    "source_url": str,
    "summary": str,
    "tags": list,
    "status": str,
}


def validate_file(filepath: Path) -> list[str]:
    """校验单个 JSON 文件，返回错误列表."""
    errors: list[str] = []

    if not filepath.suffix.lower() == ".json":
        errors.append(f"[SKIP] 非 JSON 文件: {filepath}")
        return errors

    try:
        text = filepath.read_text(encoding="utf-8")
    except Exception as exc:
        errors.append(f"[IO_ERROR] 读取失败: {filepath} — {exc}")
        return errors

    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        errors.append(f"[PARSE_ERROR] JSON 解析失败: {filepath} — {exc}")
        return errors

    if isinstance(data, dict):
        _validate_item(data, filepath, errors)
    elif isinstance(data, list):
        for idx, item in enumerate(data):
            _validate_item(item, filepath, errors, index=idx)
    else:
        errors.append(f"[TYPE_ERROR] JSON 根节点类型错误 (期待 dict 或 list): {filepath}")

    return errors


def _validate_item(
    item: object,
    filepath: Path,
    errors: list[str],
    index: int | None = None,
) -> None:
    """校验单个条目."""
    prefix = f"#{index}" if index is not None else "item"
    loc = f"{filepath}[{prefix}]"

    if not isinstance(item, dict):
        errors.append(f"[TYPE_ERROR] {loc} — 不是 object")
        return

    # 1. 必填字段
    for field, expected_type in REQUIRED_FIELDS.items():
        if field not in item:
            errors.append(f"[MISSING] {loc} — 缺少字段: '{field}'")
        elif not isinstance(item[field], expected_type):
            actual = type(item[field]).__name__
            errors.append(
                f"[TYPE_ERROR] {loc}.{field} — 期待 {expected_type.__name__}, "
                f"实际 {actual}"
            )

    # 2. ID 格式: {source}-{YYYYMMDD}-{NNN}
    id_val = item.get("id")
    if isinstance(id_val, str) and not ID_PATTERN.match(id_val):
        errors.append(f"[FORMAT] {loc}.id — 格式无效 '{id_val}', 期待 {{source}}-{{YYYYMMDD}}-{{NNN}}")

    # 3. status 范围
    status_val = item.get("status")
    if isinstance(status_val, str) and status_val not in VALID_STATUSES:
        errors.append(
            f"[VALUE] {loc}.status — 无效值 '{status_val}', "
            f"期待 {VALID_STATUSES}"
        )

    # 4. URL 格式
    url_val = item.get("source_url")
    if isinstance(url_val, str) and not URL_PATTERN.match(url_val):
        errors.append(f"[FORMAT] {loc}.source_url — 无效 URL: '{url_val}'")

    # 5. 摘要长度
    summary_val = item.get("summary")
    if isinstance(summary_val, str) and len(summary_val) < 20:
        errors.append(
            f"[LENGTH] {loc}.summary — 过短 ({len(summary_val)} 字), "
            f"最少需要 20 字"
        )

    # 6. 标签数量
    tags_val = item.get("tags")
    if isinstance(tags_val, list) and len(tags_val) < 1:
        errors.append(f"[LENGTH] {loc}.tags — 至少需要 1 个标签")

    if isinstance(tags_val, list):
        for t_idx, tag in enumerate(tags_val):
            if not isinstance(tag, str):
                errors.append(
                    f"[TYPE_ERROR] {loc}.tags[{t_idx}] — "
                    f"期待 str, 实际 {type(tag).__name__}"
                )

    # 7. score (可选)
    score_val = item.get("score")
    if score_val is not None:
        if not isinstance(score_val, (int, float)):
            errors.append(
                f"[TYPE_ERROR] {loc}.score — 期待 int/float, "
                f"实际 {type(score_val).__name__}"
            )
        elif not (1 <= score_val <= 10):
            errors.append(
                f"[VALUE] {loc}.score — {score_val} 超出范围 [1, 10]"
            )

    # 8. audience (可选)
    audience_val = item.get("audience")
    if audience_val is not None:
        if not isinstance(audience_val, str):
            errors.append(
                f"[TYPE_ERROR] {loc}.audience — 期待 str, "
                f"实际 {type(audience_val).__name__}"
            )
        elif audience_val not in VALID_AUDIENCES:
            errors.append(
                f"[VALUE] {loc}.audience — 无效值 '{audience_val}', "
                f"期待 {VALID_AUDIENCES}"
            )


def _print_summary(
    file_stats: dict[str, tuple[int, int]],
    total_errors: int,
    total_warnings: int,
    total_files: int,
) -> None:
    """打印汇总统计."""
    print(f"\n{'=' * 50}")
    print(f"  汇总统计")
    print(f"{'=' * 50}")
    for filepath, (passed, failed) in sorted(file_stats.items()):
        status = "PASS" if failed == 0 else "FAIL"
        print(f"  {status:4s}  {filepath}  ({passed} ok, {failed} errors)")
    print(f"{'-' * 50}")
    print(f"  总文件: {total_files}")
    print(f"  总错误: {total_errors}")
    print(f"  总警告: {total_warnings}")
    print(f"{'=' * 50}")


def main() -> int:
    """入口函数."""
    args = sys.argv[1:]
    if not args:
        print("用法: python hooks/validate_json.py <json_file> [json_file2 ...]", file=sys.stderr)
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
        print("[ERROR] 没有找到可校验的文件", file=sys.stderr)
        return EXIT_FAILURE

    total_errors = 0
    total_warnings = 0
    total_files = len(files_to_check)
    file_stats: dict[str, tuple[int, int]] = {}

    for fpath in files_to_check:
        errors = validate_file(fpath)
        n_warnings = sum(1 for e in errors if e.startswith("[WARN]") or e.startswith("[SKIP]"))
        n_errors = len(errors) - n_warnings

        total_errors += n_errors
        total_warnings += n_warnings
        file_stats[str(fpath)] = (0, n_errors)

        for err in errors:
            print(err)

    _print_summary(file_stats, total_errors, total_warnings, total_files)

    return EXIT_SUCCESS if total_errors == 0 else EXIT_FAILURE


if __name__ == "__main__":
    sys.exit(main())

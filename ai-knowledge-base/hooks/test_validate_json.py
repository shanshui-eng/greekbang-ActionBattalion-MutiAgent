"""validate_json.py 测试用例.

用法:
    python -m unittest hooks/test_validate_json.py
    pytest hooks/test_validate_json.py
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

# 将被测模块加入搜索路径
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from hooks.validate_json import (  # noqa: E402
    EXIT_FAILURE,
    EXIT_SUCCESS,
    ID_PATTERN,
    REQUIRED_FIELDS,
    URL_PATTERN,
    VALID_AUDIENCES,
    VALID_STATUSES,
    _validate_item,
    main,
    validate_file,
)


# ── 辅助函数 ──────────────────────────────────────

def _make_temp_file(data, suffix=".json"):
    """创建临时 JSON 文件，返回 Path 对象."""
    tmp = tempfile.NamedTemporaryFile(
        suffix=suffix, delete=False, mode="w", encoding="utf-8"
    )
    if isinstance(data, str):
        tmp.write(data)
    else:
        json.dump(data, tmp, ensure_ascii=False)
    tmp.close()
    return Path(tmp.name)


def _minimal_item(**overrides):
    """构建一个合法的极简条目，可用 overrides 覆盖任意字段."""
    item = {
        "id": "github-20260513-001",
        "title": "Test Repository",
        "source_url": "https://github.com/test/repo",
        "source": "github",
        "summary": "这是一个测试条目的摘要，长度超过二十个字符以确保通过最短校验",
        "tags": ["llm", "opensource"],
        "status": "draft",
        "fetched_at": "2026-05-13T08:00:00Z",
    }
    item.update(overrides)
    return item


# ── 常量校验 ──────────────────────────────────────

class TestREQUIRED_FIELDS(unittest.TestCase):
    """校验 REQUIRED_FIELDS 字典的正确性."""

    def test_all_fields_present(self):
        """6 个必填字段全部存在."""
        expected = {"id", "title", "source_url", "summary", "tags", "status"}
        self.assertEqual(set(REQUIRED_FIELDS.keys()), expected)

    def test_field_types(self):
        """每个字段的类型声明正确."""
        self.assertIs(REQUIRED_FIELDS["id"], str)
        self.assertIs(REQUIRED_FIELDS["title"], str)
        self.assertIs(REQUIRED_FIELDS["source_url"], str)
        self.assertIs(REQUIRED_FIELDS["summary"], str)
        self.assertIs(REQUIRED_FIELDS["tags"], list)
        self.assertIs(REQUIRED_FIELDS["status"], str)


class TestIDPattern(unittest.TestCase):
    """校验 ID_PATTERN 正则表达式."""

    def test_valid_github_id(self):
        self.assertIsNotNone(ID_PATTERN.match("github-20260513-001"))

    def test_valid_hn_id(self):
        self.assertIsNotNone(ID_PATTERN.match("hn-20260101-999"))

    def test_valid_arxiv_id(self):
        self.assertIsNotNone(ID_PATTERN.match("arxiv-20261231-00001"))

    def test_valid_long_serial(self):
        self.assertIsNotNone(ID_PATTERN.match("github-20260513-000123"))

    def test_old_format_rejected(self):
        """旧格式 github-repo-name 应被拒绝."""
        self.assertIsNone(ID_PATTERN.match("github-deepseek-tui"))

    def test_no_date_rejected(self):
        """缺少日期段应被拒绝."""
        self.assertIsNone(ID_PATTERN.match("github-001"))

    def test_no_serial_rejected(self):
        """缺少序号段应被拒绝."""
        self.assertIsNone(ID_PATTERN.match("github-20260513"))

    def test_wrong_date_format_rejected(self):
        """日期不是 8 位数字应被拒绝."""
        self.assertIsNone(ID_PATTERN.match("github-2026-05-13-001"))

    def test_source_must_start_with_letter(self):
        """source 段必须以小写字母开头."""
        self.assertIsNone(ID_PATTERN.match("123github-20260513-001"))


class TestURLPattern(unittest.TestCase):
    """校验 URL_PATTERN 正则表达式."""

    def test_https_url(self):
        self.assertIsNotNone(URL_PATTERN.match("https://github.com/user/repo"))

    def test_http_url(self):
        self.assertIsNotNone(URL_PATTERN.match("http://arxiv.org/abs/2605.12345"))

    def test_ftp_rejected(self):
        self.assertIsNone(URL_PATTERN.match("ftp://files.example.com/repo"))

    def test_plain_text_rejected(self):
        self.assertIsNone(URL_PATTERN.match("not-a-url"))

    def test_empty_rejected(self):
        self.assertIsNone(URL_PATTERN.match(""))


class TestConstants(unittest.TestCase):
    """校验枚举常量的值."""

    def test_valid_statuses(self):
        self.assertEqual(VALID_STATUSES, {"draft", "review", "published", "archived"})

    def test_valid_audiences(self):
        self.assertEqual(VALID_AUDIENCES, {"beginner", "intermediate", "advanced"})


# ── _validate_item 单元测试 ──────────────────────

class TestValidateItem(unittest.TestCase):
    """测试 _validate_item() 各条校验规则."""

    def setUp(self):
        self.filepath = Path("fake.json")
        self.errors: list[str] = []

    # ── 正向 ──

    def test_minimal_valid_item_passes(self):
        _validate_item(_minimal_item(), self.filepath, self.errors)
        self.assertEqual(self.errors, [])

    def test_valid_item_with_optional_fields(self):
        item = _minimal_item(score=8, audience="advanced")
        _validate_item(item, self.filepath, self.errors)
        self.assertEqual(self.errors, [])

    def test_boundary_summary_20_chars(self):
        item = _minimal_item(summary="A" * 20)
        _validate_item(item, self.filepath, self.errors)
        self.assertFalse(any("summary" in e for e in self.errors))

    def test_boundary_score_1(self):
        item = _minimal_item(score=1)
        _validate_item(item, self.filepath, self.errors)
        self.assertFalse(any("score" in e for e in self.errors))

    def test_boundary_score_10(self):
        item = _minimal_item(score=10)
        _validate_item(item, self.filepath, self.errors)
        self.assertFalse(any("score" in e for e in self.errors))

    # ── 缺失字段 ──

    def test_missing_id_reported(self):
        item = _minimal_item()
        del item["id"]
        _validate_item(item, self.filepath, self.errors)
        self.assertTrue(any("MISSING" in e and "id" in e for e in self.errors))

    def test_missing_title_reported(self):
        item = _minimal_item()
        del item["title"]
        _validate_item(item, self.filepath, self.errors)
        self.assertTrue(any("MISSING" in e and "title" in e for e in self.errors))

    def test_missing_source_url_reported(self):
        item = _minimal_item()
        del item["source_url"]
        _validate_item(item, self.filepath, self.errors)
        self.assertTrue(any("MISSING" in e and "source_url" in e for e in self.errors))

    def test_missing_summary_reported(self):
        item = _minimal_item()
        del item["summary"]
        _validate_item(item, self.filepath, self.errors)
        self.assertTrue(any("MISSING" in e and "summary" in e for e in self.errors))

    def test_missing_tags_reported(self):
        item = _minimal_item()
        del item["tags"]
        _validate_item(item, self.filepath, self.errors)
        self.assertTrue(any("MISSING" in e and "tags" in e for e in self.errors))

    def test_missing_status_reported(self):
        item = _minimal_item()
        del item["status"]
        _validate_item(item, self.filepath, self.errors)
        self.assertTrue(any("MISSING" in e and "status" in e for e in self.errors))

    # ── 类型错误 ──

    def test_id_wrong_type(self):
        item = _minimal_item(id=12345)
        _validate_item(item, self.filepath, self.errors)
        self.assertTrue(any("TYPE_ERROR" in e and "id" in e for e in self.errors))

    def test_tags_wrong_type_string(self):
        item = _minimal_item(tags="llm")
        _validate_item(item, self.filepath, self.errors)
        self.assertTrue(any("TYPE_ERROR" in e and "tags" in e for e in self.errors))

    def test_summary_wrong_type(self):
        item = _minimal_item(summary=123)
        _validate_item(item, self.filepath, self.errors)
        self.assertTrue(any("TYPE_ERROR" in e and "summary" in e for e in self.errors))

    def test_status_wrong_type(self):
        item = _minimal_item(status=1)
        _validate_item(item, self.filepath, self.errors)
        self.assertTrue(any("TYPE_ERROR" in e and "status" in e for e in self.errors))

    def test_non_dict_item_reported(self):
        _validate_item("not a dict", self.filepath, self.errors)
        self.assertTrue(any("TYPE_ERROR" in e for e in self.errors))

    # ── ID 格式 ──

    def test_old_id_format_reported(self):
        item = _minimal_item(id="github-deepseek-tui")
        _validate_item(item, self.filepath, self.errors)
        self.assertTrue(any("FORMAT" in e and "id" in e for e in self.errors))

    def test_id_without_date_reported(self):
        item = _minimal_item(id="github-001")
        _validate_item(item, self.filepath, self.errors)
        self.assertTrue(any("FORMAT" in e and "id" in e for e in self.errors))

    # ── status 范围 ──

    def test_invalid_status_reported(self):
        item = _minimal_item(status="deleted")
        _validate_item(item, self.filepath, self.errors)
        self.assertTrue(any("VALUE" in e and "status" in e for e in self.errors))

    def test_duplicate_status_reported(self):
        """duplicate 不在新的 4 值枚举中，应报无效."""
        item = _minimal_item(status="duplicate")
        _validate_item(item, self.filepath, self.errors)
        self.assertTrue(any("VALUE" in e and "status" in e for e in self.errors))

    # ── URL 格式 ──

    def test_invalid_url_reported(self):
        item = _minimal_item(source_url="ftp://example.com/repo")
        _validate_item(item, self.filepath, self.errors)
        self.assertTrue(any("FORMAT" in e and "source_url" in e for e in self.errors))

    def test_plain_text_url_reported(self):
        item = _minimal_item(source_url="not-a-url")
        _validate_item(item, self.filepath, self.errors)
        self.assertTrue(any("FORMAT" in e and "source_url" in e for e in self.errors))

    # ── 摘要长度 ──

    def test_short_summary_reported(self):
        item = _minimal_item(summary="太短")
        _validate_item(item, self.filepath, self.errors)
        self.assertTrue(any("LENGTH" in e and "summary" in e for e in self.errors))

    def test_summary_19_chars_reported(self):
        item = _minimal_item(summary="A" * 19)
        _validate_item(item, self.filepath, self.errors)
        self.assertTrue(any("LENGTH" in e and "summary" in e for e in self.errors))

    # ── 标签数量 ──

    def test_empty_tags_reported(self):
        item = _minimal_item(tags=[])
        _validate_item(item, self.filepath, self.errors)
        self.assertTrue(any("LENGTH" in e and "tags" in e for e in self.errors))

    def test_tag_elements_type_checked(self):
        item = _minimal_item(tags=["llm", 123, None])
        _validate_item(item, self.filepath, self.errors)
        type_errors = [e for e in self.errors if "TYPE_ERROR" in e and "tags[" in e]
        self.assertEqual(len(type_errors), 2)

    # ── score 范围 ──

    def test_score_below_1_reported(self):
        item = _minimal_item(score=0)
        _validate_item(item, self.filepath, self.errors)
        self.assertTrue(any("VALUE" in e and "score" in e for e in self.errors))

    def test_score_above_10_reported(self):
        item = _minimal_item(score=99)
        _validate_item(item, self.filepath, self.errors)
        self.assertTrue(any("VALUE" in e and "score" in e for e in self.errors))

    def test_score_wrong_type_reported(self):
        item = _minimal_item(score="high")
        _validate_item(item, self.filepath, self.errors)
        self.assertTrue(any("TYPE_ERROR" in e and "score" in e for e in self.errors))

    def test_score_none_skipped(self):
        """score 为 None 时跳过检查（等同于不存在）."""
        item = _minimal_item(score=None)
        _validate_item(item, self.filepath, self.errors)
        self.assertFalse(any("score" in e for e in self.errors))

    # ── audience 范围 ──

    def test_invalid_audience_reported(self):
        item = _minimal_item(audience="expert")
        _validate_item(item, self.filepath, self.errors)
        self.assertTrue(any("VALUE" in e and "audience" in e for e in self.errors))

    def test_audience_wrong_type_reported(self):
        item = _minimal_item(audience=123)
        _validate_item(item, self.filepath, self.errors)
        self.assertTrue(any("TYPE_ERROR" in e and "audience" in e for e in self.errors))

    def test_audience_none_skipped(self):
        item = _minimal_item(audience=None)
        _validate_item(item, self.filepath, self.errors)
        self.assertFalse(any("audience" in e for e in self.errors))

    # ── 多错误累积 ──

    def test_multiple_errors_accumulated(self):
        """单条目触发多项错误时，全部记录而非遇错即停."""
        item = _minimal_item(
            id="bad",
            status="invalid",
            source_url="not-a-url",
            summary="X",
            tags=[],
            score=99,
            audience="genius",
        )
        _validate_item(item, self.filepath, self.errors)
        categories = {e.split("]")[0].lstrip("[") for e in self.errors}
        self.assertIn("FORMAT", categories)
        self.assertIn("VALUE", categories)
        self.assertIn("LENGTH", categories)
        self.assertGreaterEqual(len(self.errors), 5)


# ── validate_file 集成测试 ───────────────────────

class TestValidateFile(unittest.TestCase):
    """测试 validate_file() 函数对各种文件输入的响应."""

    # ── 正向 ──

    def test_valid_single_dict_passes(self):
        fpath = _make_temp_file(_minimal_item())
        try:
            errors = validate_file(fpath)
            self.assertEqual(errors, [])
        finally:
            fpath.unlink(missing_ok=True)

    def test_valid_list_passes(self):
        fpath = _make_temp_file([
            _minimal_item(id="github-20260513-001"),
            _minimal_item(id="hn-20260513-002", source="hn"),
            _minimal_item(id="arxiv-20260513-003", source="arxiv"),
        ])
        try:
            errors = validate_file(fpath)
            self.assertEqual(errors, [])
        finally:
            fpath.unlink(missing_ok=True)

    def test_valid_with_optional_fields_passes(self):
        fpath = _make_temp_file(_minimal_item(score=8, audience="intermediate"))
        try:
            errors = validate_file(fpath)
            self.assertEqual(errors, [])
        finally:
            fpath.unlink(missing_ok=True)

    # ── 反向 ──

    def test_broken_json_reports_parse_error(self):
        fpath = _make_temp_file("{ this is not valid json }")
        try:
            errors = validate_file(fpath)
            self.assertTrue(any("PARSE_ERROR" in e for e in errors))
        finally:
            fpath.unlink(missing_ok=True)

    def test_non_dict_non_list_root_reported(self):
        # 写入合法的 JSON 字符串值（带引号），解析后为 str 而非 dict/list
        tmp = tempfile.NamedTemporaryFile(
            suffix=".json", delete=False, mode="w", encoding="utf-8"
        )
        json.dump("just a bare string", tmp, ensure_ascii=False)
        tmp.close()
        fpath = Path(tmp.name)
        try:
            errors = validate_file(fpath)
            self.assertTrue(any("TYPE_ERROR" in e for e in errors),
                            f"Expected TYPE_ERROR, got: {errors}")
        finally:
            fpath.unlink(missing_ok=True)

    def test_non_json_file_skipped(self):
        fpath = _make_temp_file("hello world", suffix=".txt")
        try:
            errors = validate_file(fpath)
            self.assertTrue(any("SKIP" in e for e in errors))
        finally:
            fpath.unlink(missing_ok=True)

    def test_list_of_mixed_items(self):
        """列表中混入非 dict 条目时，该项报错但合法项通过."""
        item = _minimal_item(id="github-20260513-001")
        fpath = _make_temp_file([item, "not a dict", item])
        try:
            errors = validate_file(fpath)
            type_errors = [e for e in errors if "TYPE_ERROR" in e]
            self.assertEqual(len(type_errors), 1)
        finally:
            fpath.unlink(missing_ok=True)

    def test_empty_list_passes(self):
        fpath = _make_temp_file([])
        try:
            errors = validate_file(fpath)
            self.assertEqual(errors, [])
        finally:
            fpath.unlink(missing_ok=True)

    def test_list_with_index_labeling(self):
        """列表中条目的错误信息包含正确的 #index."""
        bad_item = _minimal_item(id="bad-id", status="invalid", summary="X", tags=[])
        fpath = _make_temp_file([
            _minimal_item(id="github-20260513-001"),
            bad_item,
        ])
        try:
            errors = validate_file(fpath)
            self.assertTrue(any("#1" in e for e in errors))
        finally:
            fpath.unlink(missing_ok=True)


# ── main() CLI 集成测试 ──────────────────────────

class TestMain(unittest.TestCase):
    """测试 main() 命令行入口的输入处理和退出码."""

    def _run_main(self, *args):
        """执行 main() 并返回 (exit_code, stdout, stderr)."""
        import io

        old_argv = sys.argv
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        try:
            sys.argv = ["validate_json.py"] + list(args)
            sys.stdout = io.StringIO()
            sys.stderr = io.StringIO()
            exit_code = main()
            return exit_code, sys.stdout.getvalue(), sys.stderr.getvalue()
        finally:
            sys.argv = old_argv
            sys.stdout = old_stdout
            sys.stderr = old_stderr

    def test_no_args_prints_usage_and_exit_1(self):
        exit_code, stdout, stderr = self._run_main()
        self.assertEqual(exit_code, EXIT_FAILURE)
        self.assertIn("用法", stderr)

    def test_valid_file_exit_0(self):
        fpath = _make_temp_file(_minimal_item())
        try:
            exit_code, stdout, _ = self._run_main(str(fpath))
            self.assertEqual(exit_code, EXIT_SUCCESS)
            self.assertIn("PASS", stdout)
        finally:
            fpath.unlink(missing_ok=True)

    def test_invalid_file_exit_1(self):
        item = _minimal_item(id="bad")
        fpath = _make_temp_file(item)
        try:
            exit_code, stdout, _ = self._run_main(str(fpath))
            self.assertEqual(exit_code, EXIT_FAILURE)
            self.assertIn("FAIL", stdout)
        finally:
            fpath.unlink(missing_ok=True)

    def test_mixed_files_exit_1(self):
        """一个有效 + 一个无效 = exit 1."""
        good = _make_temp_file(_minimal_item(id="github-20260513-001"))
        bad = _make_temp_file(_minimal_item(id="bad"))
        try:
            exit_code, stdout, _ = self._run_main(str(good), str(bad))
            self.assertEqual(exit_code, EXIT_FAILURE)
            self.assertIn("PASS", stdout)
            self.assertIn("FAIL", stdout)
        finally:
            good.unlink(missing_ok=True)
            bad.unlink(missing_ok=True)

    def test_glob_pattern_expands(self):
        """通配符模式自动展开为文件列表."""
        import os

        d = Path(tempfile.mkdtemp())
        try:
            f1 = d / "a.json"
            f2 = d / "b.json"
            f1.write_text(json.dumps(_minimal_item(id="github-20260513-001")), encoding="utf-8")
            f2.write_text(json.dumps(_minimal_item(id="hn-20260513-002")), encoding="utf-8")
            glob_arg = str(d / "*.json")
            exit_code, stdout, _ = self._run_main(glob_arg)
            self.assertEqual(exit_code, EXIT_SUCCESS)
            self.assertIn("总文件: 2", stdout)
        finally:
            for f in d.iterdir():
                f.unlink(missing_ok=True)
            d.rmdir()

    def test_warn_on_no_match(self):
        exit_code, _, stderr = self._run_main("/nonexistent/path/*.json")
        self.assertIn("WARN", stderr)

    def test_no_files_found_exit_1(self):
        exit_code, _, stderr = self._run_main("/nonexistent/path/*.json")
        self.assertEqual(exit_code, EXIT_FAILURE)
        self.assertIn("没有找到", stderr)

    def test_non_json_file_skipped_in_main(self):
        """非 JSON 文件 SKIP 算警告不算错误，exit 0."""
        fpath = _make_temp_file("hello", suffix=".txt")
        try:
            exit_code, stdout, _ = self._run_main(str(fpath))
            self.assertEqual(exit_code, EXIT_SUCCESS)
            self.assertIn("SKIP", stdout)
        finally:
            fpath.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)

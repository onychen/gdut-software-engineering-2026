import contextlib
import io
import runpy
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from main import (
    SimilarityError,
    main,
    normalize_text,
    read_text_file,
    run,
    similarity_rate,
    write_rate_file,
)


class NormalizeTextTests(unittest.TestCase):
    def test_removes_punctuation_and_whitespace(self):
        self.assertEqual(normalize_text("今天， 天气！\n晴。"), "今天天气晴")

    def test_normalizes_width_and_case(self):
        self.assertEqual(normalize_text("ＡＢＣ １２３"), "abc123")


class SimilarityRateTests(unittest.TestCase):
    def test_identical_text_is_one(self):
        self.assertEqual(similarity_rate("论文查重算法", "论文查重算法"), 1.0)

    def test_candidate_contained_in_source_is_one(self):
        self.assertEqual(similarity_rate("甲乙丙丁戊己", "丙丁戊"), 1.0)

    def test_added_unmatched_content_lowers_score(self):
        score = similarity_rate("今天是星期天", "今天是星期天明天要考试")
        self.assertGreater(score, 0.0)
        self.assertLess(score, 1.0)

    def test_empty_candidate_is_zero(self):
        self.assertEqual(similarity_rate("有内容", ""), 0.0)

    def test_empty_source_is_zero(self):
        self.assertEqual(similarity_rate("", "有内容"), 0.0)

    def test_both_empty_is_zero(self):
        self.assertEqual(similarity_rate("", ""), 0.0)

    def test_unrelated_text_is_zero(self):
        self.assertEqual(similarity_rate("甲乙丙丁", "戊己庚辛"), 0.0)

    def test_punctuation_and_spacing_do_not_change_score(self):
        self.assertEqual(similarity_rate("今天是星期天。天气晴！", "今天 是 星期天天气晴"), 1.0)

    def test_single_character_text_uses_unigrams(self):
        self.assertEqual(similarity_rate("你", "你"), 1.0)

    def test_repeated_candidate_grams_cannot_overconsume_source(self):
        self.assertAlmostEqual(similarity_rate("哈哈", "哈哈哈哈"), 1 / 3)

    def test_shared_character_without_shared_bigram_is_not_counted(self):
        self.assertEqual(similarity_rate("甲乙丙", "甲丁丙"), 0.0)

    def test_score_is_directional_to_candidate_length(self):
        short_copy = similarity_rate("甲乙丙丁", "甲乙")
        expanded_copy = similarity_rate("甲乙丙丁", "甲乙戊己庚辛")
        self.assertGreater(short_copy, expanded_copy)


class FileAndCliTests(unittest.TestCase):
    def test_reads_utf8_bom(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bom.txt"
            path.write_bytes("\ufeff中文".encode("utf-8"))
            self.assertEqual(read_text_file(path), "中文")

    def test_reads_gb18030(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "gb.txt"
            path.write_bytes("中文论文".encode("gb18030"))
            self.assertEqual(read_text_file(path), "中文论文")

    def test_missing_file_raises_clear_error(self):
        with tempfile.TemporaryDirectory() as directory, self.assertRaisesRegex(
            SimilarityError, "无法读取文件"
        ):
            read_text_file(Path(directory) / "missing.txt")

    def test_invalid_text_encoding_raises_clear_error(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "invalid.txt"
            path.write_bytes(b"\x81")
            with self.assertRaisesRegex(SimilarityError, "不是有效的"):
                read_text_file(path)

    def test_unwritable_answer_path_raises_clear_error(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "missing-parent" / "answer.txt"
            with self.assertRaisesRegex(SimilarityError, "无法写入答案文件"):
                write_rate_file(path, 0.5)

    def test_run_writes_two_decimal_answer(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "original.txt").write_text("论文查重", encoding="utf-8")
            (root / "copy.txt").write_text("论文查重", encoding="utf-8")
            answer = root / "answer.txt"
            self.assertEqual(run(str(root / "original.txt"), str(root / "copy.txt"), str(answer)), 1.0)
            self.assertEqual(answer.read_text(encoding="utf-8"), "1.00\n")

    def test_cli_missing_input_returns_nonzero_without_answer(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            answer = root / "answer.txt"
            with contextlib.redirect_stderr(io.StringIO()):
                result = main([
                    str(root / "missing.txt"),
                    str(root / "copy.txt"),
                    str(answer),
                ])
            self.assertEqual(result, 1)
            self.assertFalse(answer.exists())

    def test_cli_requires_three_paths(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(
            SystemExit
        ) as raised:
            main(["only-one-path"])
        self.assertEqual(raised.exception.code, 2)

    def test_script_entrypoint_runs_successfully(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            original = root / "original.txt"
            copied = root / "copied.txt"
            answer = root / "answer.txt"
            original.write_text("课程作业", encoding="utf-8")
            copied.write_text("课程作业", encoding="utf-8")
            script = Path(__file__).resolve().parents[1] / "main.py"
            arguments = [str(script), str(original), str(copied), str(answer)]
            with patch.object(sys, "argv", arguments), contextlib.redirect_stdout(
                io.StringIO()
            ), self.assertRaises(SystemExit) as raised:
                runpy.run_path(str(script), run_name="__main__")
            self.assertEqual(raised.exception.code, 0)
            self.assertEqual(answer.read_text(encoding="utf-8"), "1.00\n")


if __name__ == "__main__":
    unittest.main()

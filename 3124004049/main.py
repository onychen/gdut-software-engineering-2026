"""Command-line Chinese/English text similarity checker for the course assignment."""

from __future__ import annotations

import argparse
import sys
import unicodedata
from collections import Counter
from collections.abc import Iterable
from pathlib import Path


class SimilarityError(Exception):
    """Raised when an input or output file cannot be processed."""


def normalize_text(text: str) -> str:
    """Normalize width/case and discard whitespace, punctuation, and symbols."""
    normalized = unicodedata.normalize("NFKC", text).casefold()
    return "".join(char for char in normalized if char.isalnum())


def _gram_codes(text: str, size: int) -> Iterable[int]:
    """Yield compact, collision-free integer encodings of adjacent character grams."""
    if size == 1:
        return (ord(char) for char in text)
    # Unicode code points fit in 21 bits, so packing two points is reversible.
    return (
        (ord(text[index]) << 21) | ord(text[index + 1])
        for index in range(len(text) - 1)
    )


def similarity_rate(original: str, plagiarized: str) -> float:
    """Return the copied fraction of the candidate text, in the range [0, 1].

    We compare a multiset of adjacent character bigrams. Each source bigram can
    match only as many times as it occurs in the source. For texts shorter than
    two normalized characters, single characters are used instead.
    """
    source = normalize_text(original)
    candidate = normalize_text(plagiarized)
    if not source or not candidate:
        return 0.0

    gram_size = 1 if min(len(source), len(candidate)) < 2 else 2
    source_counts = Counter(_gram_codes(source, gram_size))
    total_candidate_grams = 0
    matched_grams = 0

    # Consume source counts in place: this enforces multiset matching without
    # allocating a second Counter for the candidate.
    for code in _gram_codes(candidate, gram_size):
        total_candidate_grams += 1
        available = source_counts.get(code, 0)
        if available:
            matched_grams += 1
            source_counts[code] = available - 1

    return matched_grams / total_candidate_grams


def read_text_file(path: str | Path) -> str:
    """Read UTF-8 (including BOM) or fall back to GB18030 for Chinese files."""
    file_path = Path(path)
    try:
        content = file_path.read_bytes()
    except OSError as exc:
        detail = exc.strerror or str(exc)
        raise SimilarityError(f"无法读取文件 {file_path}: {detail}") from exc

    for encoding in ("utf-8-sig", "gb18030"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise SimilarityError(f"文件不是有效的 UTF-8 或 GB18030 文本: {file_path}")


def write_rate_file(path: str | Path, rate: float) -> None:
    """Write a decimal rate with exactly two fractional digits."""
    file_path = Path(path)
    try:
        file_path.write_text(f"{rate:.2f}\n", encoding="utf-8", newline="\n")
    except OSError as exc:
        detail = exc.strerror or str(exc)
        raise SimilarityError(f"无法写入答案文件 {file_path}: {detail}") from exc


def run(original_path: str, plagiarized_path: str, answer_path: str) -> float:
    """Read both inputs, compute the score, and write only the requested output."""
    original = read_text_file(original_path)
    plagiarized = read_text_file(plagiarized_path)
    rate = similarity_rate(original, plagiarized)
    write_rate_file(answer_path, rate)
    return rate


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="计算原文与待检测论文的字符二元组重复率。"
    )
    parser.add_argument("original", help="原文文件的路径")
    parser.add_argument("plagiarized", help="待检测论文文件的路径")
    parser.add_argument("answer", help="答案文件的路径")
    args = parser.parse_args(argv)

    try:
        run(args.original, args.plagiarized, args.answer)
    except SimilarityError as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

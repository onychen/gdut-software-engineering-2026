"""Compare a naive pairwise matcher with the production Counter matcher."""

from __future__ import annotations

import statistics
import sys
import timeit
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from main import normalize_text, similarity_rate


def pairwise_reference(source: str, candidate: str) -> float:
    """Simple O(N*M) prototype retained only for the performance comparison."""
    source = normalize_text(source)
    candidate = normalize_text(candidate)
    if not source or not candidate:
        return 0.0
    if min(len(source), len(candidate)) < 2:
        source_grams = list(source)
        candidate_grams = list(candidate)
    else:
        source_grams = [source[i : i + 2] for i in range(len(source) - 1)]
        candidate_grams = [candidate[i : i + 2] for i in range(len(candidate) - 1)]

    used = bytearray(len(source_grams))
    matches = 0
    for candidate_gram in candidate_grams:
        for index, source_gram in enumerate(source_grams):
            if not used[index] and candidate_gram == source_gram:
                used[index] = 1
                matches += 1
                break
    return matches / len(candidate_grams) if candidate_grams else 0.0


def main() -> None:
    source = "甲乙" * 1_200
    candidate = "丙丁" * 1_200

    pairwise_seconds = statistics.median(
        timeit.repeat(lambda: pairwise_reference(source, candidate), number=1, repeat=5)
    )
    counter_seconds = statistics.median(
        timeit.repeat(lambda: similarity_rate(source, candidate), number=1, repeat=5)
    )

    print(f"Input sizes: source={len(source)}, candidate={len(candidate)} characters")
    print(f"Pairwise prototype median (5 runs): {pairwise_seconds:.6f} seconds")
    print(f"Counter implementation median (5 runs): {counter_seconds:.6f} seconds")
    if counter_seconds > 0:
        print(f"Observed speedup: {pairwise_seconds / counter_seconds:.1f}x")


if __name__ == "__main__":
    main()

"""Run cProfile against an in-memory synthetic document; writes nothing to disk."""

import cProfile
import io
import pstats
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from main import similarity_rate


def main() -> None:
    source = ("软件工程要求分析设计实现测试持续改进。" * 20_000)
    inserted_text = "独立新增内容ABCxyz0123456789。" * 1_000
    candidate = source[:120_000] + inserted_text + source[120_000:]

    profiler = cProfile.Profile()
    score = profiler.runcall(similarity_rate, source, candidate)
    output = io.StringIO()
    pstats.Stats(profiler, stream=output).strip_dirs().sort_stats("tottime").print_stats(12)

    print(f"Source length: {len(source)} characters")
    print(f"Candidate length: {len(candidate)} characters")
    print(f"Similarity rate: {score:.2f}")
    print(output.getvalue())


if __name__ == "__main__":
    main()

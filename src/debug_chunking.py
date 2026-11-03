
from pathlib import Path
import json

from chunking_experiments import (
    MAX_TOKENS,
    tokenizer,
    token_count,
    fixed_size_chunk,
    recursive_chunk
)


def find_overlap(first, second):
    """Find exact shared suffix/prefix between two chunks."""

    max_length = min(len(first), len(second))

    for length in range(max_length, 0, -1):
        if first.endswith(second[:length]):
            return second[:length]

    return ""


def inspect_overlaps(name, chunks):
    """Inspect overlap and possible duplication between chunks."""

    print(f"\n========== {name} OVERLAP CHECKS ==========")

    if len(chunks) < 2:
        print("Only one chunk. No overlap to inspect.")
        return

    for i in range(len(chunks) - 1):

        first = chunks[i]
        second = chunks[i + 1]

        shared = find_overlap(first, second)

        print(f"\nChunks {i + 1} -> {i + 2}")

        print("Shared characters:", len(shared))
        print("Shared tokens:", token_count(shared))

        print(
            "Next chunk entirely contained in previous:",
            second in first
        )

        print("\nPrevious chunk ending:")
        print(repr(first[-200:]))

        print("\nNext chunk beginning:")
        print(repr(second[:200]))

        print("-" * 60)


ROOT = Path(__file__).resolve().parents[1]

INPUT_DIR = ROOT / "data" / "processed" / "curated"

print("MAX_TOKENS:", MAX_TOKENS)
print("Tokenizer max length:", tokenizer.model_max_length)
print("Backend truncation:", tokenizer.backend_tokenizer.truncation)

print("\n========== PAGE-LEVEL DEBUG ==========")

for filename in [
    "CERTIN_2023.jsonl",
    "NIST_800_61R3.jsonl"
]:

    path = INPUT_DIR / filename

    with path.open("r", encoding="utf-8") as file:

        for line in file:

            record = json.loads(line)

            if record["page"] not in [3, 4, 5, 10]:
                continue

            text = record["text"]

            print("\n" + "=" * 65)
            print("Document:", filename)
            print("Page:", record["page"])
            print("Characters:", len(text))
            print("Original tokens:", token_count(text))

            fixed = fixed_size_chunk(text)
            recursive = recursive_chunk(text)

            # Inspect fixed-size chunking
            inspect_overlaps("FIXED", fixed)

            # Inspect recursive chunking
            inspect_overlaps("RECURSIVE", recursive)

            # Print chunk statistics
            print("\n========== CHUNK STATISTICS ==========")

            print("Fixed chunks:", len(fixed))
            print(
                "Fixed chunk sizes:",
                [token_count(x) for x in fixed]
            )

            print("\nRecursive chunks:", len(recursive))
            print(
                "Recursive chunk sizes:",
                [token_count(x) for x in recursive]
            )

            print("=" * 65)

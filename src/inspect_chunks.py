
from pathlib import Path
import json
import statistics

ROOT = Path(__file__).resolve().parents[1]

CHUNK_DIR = ROOT / "data" / "processed" / "chunks"

STRATEGIES = [
    "fixed",
    "recursive"
]


def load_chunks(strategy):

    path = CHUNK_DIR / f"{strategy}_chunks.jsonl"
    chunks = []

    with path.open("r", encoding="utf-8") as file:
        for line in file:
            chunks.append(json.loads(line))

    return chunks


def inspect_strategy(strategy):

    chunks = load_chunks(strategy)

    if not chunks:
        print(f"No chunks found for {strategy}")
        return

    lengths = [
        chunk["token_count"] for chunk in chunks
    ]

    print("\n" + "=" * 75)
    print("STRATEGY:", strategy.upper())
    print("=" * 75)

    print("Total chunks:", len(chunks))
    print("Average:", round(statistics.mean(lengths), 2))
    print("Median:", statistics.median(lengths))
    print("Chunks below 40 tokens:", sum(x < 40 for x in lengths))

    print("\n--- FIRST 5 CHUNKS ---")

    for chunk in chunks[:5]:

        print("\nSource:", chunk["source_id"])
        print("Page:", chunk["page"])
        print("Tokens:", chunk["token_count"])
        print("Text:", chunk["text"][:400])

    print("\n--- 5 SMALLEST CHUNKS ---")

    smallest = sorted(
        chunks,
        key=lambda x: x["token_count"]
    )[:5]

    for chunk in smallest:

        print("\nSource:", chunk["source_id"])
        print("Page:", chunk["page"])
        print("Tokens:", chunk["token_count"])
        print("Text:", repr(chunk["text"]))


def main():

    for strategy in STRATEGIES:
        inspect_strategy(strategy)


if __name__ == "__main__":
    main()

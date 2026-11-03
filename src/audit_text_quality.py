
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROCESSED = ROOT / "data" / "processed"

STAGES = {
    "extracted": PROCESSED / "extracted",
    "cleaned": PROCESSED / "cleaned",
    "curated": PROCESSED / "curated",
    "fixed": PROCESSED / "chunks",
    "recursive": PROCESSED / "chunks",
}

# Known suspicious phrases from retrieval results.
# These are diagnostic examples, not automatic corrections.
PHRASES = [
    "beendesignated",
    "aswell",
    "UsePwned",
    "Passwordsto",
    "previouslybreached",
]

def load_records(path):
    records = []

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))

    return records


def inspect(stage, path):
    if not path.exists():
        print(f"\n{stage}: File not found: {path}")
        return

    records = load_records(path)
    print(f"\n{'=' * 65}")
    print(f"STAGE: {stage.upper()} | {path.name}")
    print("=" * 65)

    found = 0

    for record in records:
        content = record.get("text", "")

        for phrase in PHRASES:
            pos = content.lower().find(phrase.lower())

            if pos == -1:
                continue

            found += 1

            start = max(0, pos - 90)
            end = min(len(content), pos + len(phrase) + 90)

            print(f"\nPhrase: {phrase}")
            print("Source:", record.get("source_id"))
            print("Page:", record.get("page"))
            print("Chunk:", record.get("chunk_id", "N/A"))
            print("Context:", repr(content[start:end]))

    if found == 0:
        print("No known suspicious phrases found.")


def main():
    sources = ["CERTIN_2023", "OWASP_AUTH"]

    for source in sources:
        for stage in ["extracted", "cleaned", "curated"]:
            inspect(stage, STAGES[stage] / f"{source}.jsonl")

    inspect(
        "fixed",
        STAGES["fixed"] / "fixed_chunks.jsonl"
    )

    inspect(
        "recursive",
        STAGES["recursive"] / "recursive_chunks.jsonl"
    )


if __name__ == "__main__":
    main()

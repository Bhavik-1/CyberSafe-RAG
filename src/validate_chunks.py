
from pathlib import Path
import json
from collections import Counter

from chunking_experiments import token_count, MAX_TOKENS

ROOT = Path(__file__).resolve().parents[1]
CHUNK_DIR = ROOT / "data" / "processed" / "chunks"

for strategy in ["fixed", "recursive"]:

    path = CHUNK_DIR / f"{strategy}_chunks.jsonl"

    print("\n" + "=" * 55)
    print(f"VALIDATING {strategy.upper()} CHUNKS")
    print("=" * 55)

    records = []
    ids = set()
    pages = set()
    errors = []

    with path.open("r", encoding="utf-8") as file:

        for line_number, line in enumerate(file, start=1):

            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                errors.append(f"Invalid JSON at line {line_number}")
                continue

            chunk_id = record.get("chunk_id")
            text = record.get("text", "")

            if not chunk_id:
                errors.append(f"Missing ID at line {line_number}")

            elif chunk_id in ids:
                errors.append(f"Duplicate ID: {chunk_id}")

            ids.add(chunk_id)

            if not text.strip():
                errors.append(f"Empty chunk: {chunk_id}")

            actual_tokens = token_count(text)

            if actual_tokens > MAX_TOKENS:
                errors.append(
                    f"Oversized chunk: {chunk_id} "
                    f"({actual_tokens} tokens)"
                )

            if actual_tokens != record.get("token_count"):
                errors.append(
                    f"Token metadata mismatch: {chunk_id}"
                )

            pages.add((record["source_id"], record["page"]))
            records.append(record)

    print("Total chunks:", len(records))
    print("Unique chunk IDs:", len(ids))
    print("Unique source-page combinations:", len(pages))
    print("Maximum actual tokens:", max(
        (token_count(r["text"]) for r in records),
        default=0
    ))

    print("Errors:", len(errors))

    for error in errors[:20]:
        print("ERROR:", error)

    if not errors:
        print("RESULT: PASSED")

    else:
        print("RESULT: FAILED")

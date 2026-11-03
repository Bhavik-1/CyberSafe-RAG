
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]

INPUT_DIR = ROOT / "data" / "processed" / "cleaned"
OUTPUT_DIR = ROOT / "data" / "processed" / "curated"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Physical PDF page numbers (1-indexed)
SKIP_PAGES = {
    "CERTIN_2023": {1, 2},
    "CERTIN_2024": {1, 2, 3},
    "CERTIN_2025": {1, 2}
}


def main():

    total_kept = 0
    total_skipped = 0

    for file_path in sorted(INPUT_DIR.glob("*.jsonl")):

        records_kept = 0
        records_skipped = 0

        source_id = file_path.stem
        excluded = SKIP_PAGES.get(source_id, set())

        output_path = OUTPUT_DIR / file_path.name

        with file_path.open(
            "r", encoding="utf-8"
        ) as source:

            with output_path.open(
                "w", encoding="utf-8"
            ) as output:

                for line in source:

                    record = json.loads(line)

                    if record["page"] in excluded:
                        records_skipped += 1
                        continue

                    record["curated"] = True

                    output.write(
                        json.dumps(
                            record,
                            ensure_ascii=False
                        ) + "\n"
                    )

                    records_kept += 1

        total_kept += records_kept
        total_skipped += records_skipped

        print(f"\n{file_path.name}")
        print("Kept:", records_kept)
        print("Skipped:", records_skipped)

    print("\n========== CURATION SUMMARY ==========")
    print("Pages retained:", total_kept)
    print("Pages excluded:", total_skipped)
    print("Output:", OUTPUT_DIR)


if __name__ == "__main__":
    main()

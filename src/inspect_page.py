
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

FILES = {
    "EXTRACTED": ROOT / "data/processed/extracted/OWASP_AUTH.jsonl",
    "CLEANED": ROOT / "data/processed/cleaned/OWASP_AUTH.jsonl",
}

TARGET_PAGE = 4

for stage, path in FILES.items():
    print("\n" + "=" * 70)
    print(stage)
    print("=" * 70)

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            record = json.loads(line)

            if record.get("page") == TARGET_PAGE:
                print(record.get("text", ""))
                break

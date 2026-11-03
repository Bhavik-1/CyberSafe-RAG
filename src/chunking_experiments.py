
from pathlib import Path
import json
import re
import statistics

from transformers import AutoTokenizer


# ==========================================
# 1. CONFIGURATION
# ==========================================

ROOT = Path(__file__).resolve().parents[1]

INPUT_DIR = ROOT / "data" / "processed" / "curated"
OUTPUT_DIR = ROOT / "data" / "processed" / "chunks"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

MAX_TOKENS = 180
OVERLAP = 30

tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

if not tokenizer.is_fast:
    raise RuntimeError("A fast tokenizer is required.")

# Disable hidden backend truncation.
tokenizer.backend_tokenizer.no_truncation()


# ==========================================
# 2. TOKEN UTILITIES
# ==========================================

def token_count(text):
    """
    Count all tokens without truncation or padding.
    """

    if not text:
        return 0

    encoded = tokenizer(
        text,
        add_special_tokens=False,
        truncation=False,
        padding=False
    )

    return len(encoded["input_ids"])


def token_offsets(text):
    """
    Return token character offsets in original text.
    """

    if not text:
        return []

    encoding = tokenizer(
        text,
        add_special_tokens=False,
        truncation=False,
        padding=False,
        return_offsets_mapping=True
    )

    return encoding["offset_mapping"]


def tail_by_tokens(text, n_tokens):
    """
    Return the last n tokens while preserving original text.
    """

    if not text or n_tokens <= 0:
        return ""

    offsets = token_offsets(text)

    if not offsets:
        return ""

    if len(offsets) <= n_tokens:
        return text.strip()

    start_char = offsets[-n_tokens][0]

    return text[start_char:].strip()


def validate_chunks(chunks, strategy):
    """
    Validate token limits and empty chunks.
    """

    for index, chunk in enumerate(chunks, start=1):

        if not chunk.strip():
            raise ValueError(
                f"{strategy}: Empty chunk at position {index}"
            )

        count = token_count(chunk)

        if count > MAX_TOKENS:
            raise ValueError(
                f"{strategy}: Chunk {index} has {count} tokens. "
                f"Maximum allowed is {MAX_TOKENS}."
            )

    return True


# ==========================================
# 3. STRATEGY 1: FIXED-SIZE CHUNKING
# ==========================================

def fixed_size_chunk(text):
    """
    Split text into token-based chunks.

    Target:
    - Maximum 180 tokens.
    - Approximately 30 tokens overlap.
    - Preserve original capitalization and wording.
    """

    if not text or not text.strip():
        return []

    offsets = token_offsets(text)

    if not offsets:
        return []

    chunks = []

    total_tokens = len(offsets)
    start = 0

    while start < total_tokens:

        end = min(start + MAX_TOKENS, total_tokens)

        # Extract the corresponding original text.
        while end > start:

            char_start = offsets[start][0]
            char_end = offsets[end - 1][1]

            chunk = text[char_start:char_end].strip()

            if token_count(chunk) <= MAX_TOKENS:
                break

            end -= 1

        if end <= start:
            raise ValueError(
                "Unable to create a valid fixed-size chunk."
            )

        chunks.append(chunk)

        # All tokens have been processed.
        if end >= total_tokens:
            break

        # Move forward while retaining overlap.
        next_start = end - OVERLAP

        # Guarantee progress.
        if next_start <= start:
            next_start = start + 1

        start = next_start

    validate_chunks(chunks, "FIXED")

    return chunks


# ==========================================
# 4. STRATEGY 2: RECURSIVE CHUNKING
# ==========================================

def split_long_unit(text):
    """
    Split oversized paragraphs or sentences
    using fixed-size chunking.
    """

    if token_count(text) <= MAX_TOKENS:
        return [text.strip()]

    return fixed_size_chunk(text)


def recursive_chunk(text):
    """
    Recursive-style chunking:

    1. Split by paragraphs.
    2. Split paragraphs by sentence boundaries.
    3. Split oversized sentences using fixed chunking.
    4. Combine related units.
    5. Add overlap while respecting the token limit.
    """

    if not text or not text.strip():
        return []

    # Split on paragraph and sentence boundaries.
    units = re.split(
        r"\n{2,}|(?<=[.!?])\s+",
        text
    )

    units = [
        unit.strip()
        for unit in units
        if unit.strip()
    ]

    # Split oversized units.
    prepared_units = []

    for unit in units:
        prepared_units.extend(
            split_long_unit(unit)
        )

    chunks = []
    current = ""

    for unit in prepared_units:

        unit_count = token_count(unit)

        if unit_count > MAX_TOKENS:
            raise ValueError(
                f"Recursive unit exceeds limit: {unit_count}"
            )

        candidate = (
            current + "\n" + unit
            if current else unit
        )

        # If it fits, continue building the current chunk.
        if token_count(candidate) <= MAX_TOKENS:
            current = candidate
            continue

        # Save the previous chunk.
        if current:
            chunks.append(current)

        # Determine overlap from the previous chunk.
        overlap_size = min(
            OVERLAP,
            token_count(current)
        ) if current else 0

        overlap_text = ""

        # Reduce overlap until the next chunk fits.
        while overlap_size > 0:

            overlap_text = tail_by_tokens(
                current,
                overlap_size
            )

            candidate = overlap_text + "\n" + unit

            if token_count(candidate) <= MAX_TOKENS:
                break

            overlap_size -= 1

        # If no overlap fits, use the unit alone.
        if overlap_size == 0:
            candidate = unit

        if token_count(candidate) > MAX_TOKENS:
            raise ValueError(
                "Recursive chunk exceeded maximum token count."
            )

        current = candidate

    if current:
        chunks.append(current)

    validate_chunks(chunks, "RECURSIVE")

    return chunks


# ==========================================
# 5. STRATEGY REGISTRY
# ==========================================

STRATEGIES = {
    "fixed": fixed_size_chunk,
    "recursive": recursive_chunk
}


# ==========================================
# 6. CHUNK METADATA
# ==========================================

def create_chunk_record(record, strategy, index, text):

    count = token_count(text)

    if count > MAX_TOKENS:
        raise ValueError(
            f"Chunk has {count} tokens; "
            f"maximum allowed is {MAX_TOKENS}."
        )

    return {
        "chunk_id": (
            f"{record['source_id']}_"
            f"P{record['page']}_"
            f"{strategy.upper()}_{index:03d}"
        ),
        "source_id": record["source_id"],
        "source_title": record["source_title"],
        "issuer": record["issuer"],
        "category": record["category"],
        "page": record["page"],
        "strategy": strategy,
        "token_count": count,
        "text": text
    }


# ==========================================
# 7. PROCESS EACH STRATEGY
# ==========================================

def process_strategy(strategy, chunk_function):

    output_path = (
        OUTPUT_DIR / f"{strategy}_chunks.jsonl"
    )

    total_chunks = 0
    token_counts = []
    small_chunks = 0
    total_pages = 0

    with output_path.open(
        "w",
        encoding="utf-8"
    ) as output:

        for file_path in sorted(
            INPUT_DIR.glob("*.jsonl")
        ):

            with file_path.open(
                "r",
                encoding="utf-8"
            ) as source:

                for line in source:

                    record = json.loads(line)
                    total_pages += 1

                    texts = chunk_function(
                        record["text"]
                    )

                    for index, text in enumerate(
                        texts,
                        start=1
                    ):

                        if not text.strip():
                            continue

                        chunk = create_chunk_record(
                            record,
                            strategy,
                            index,
                            text
                        )

                        output.write(
                            json.dumps(
                                chunk,
                                ensure_ascii=False
                            ) + "\n"
                        )

                        total_chunks += 1

                        token_counts.append(
                            chunk["token_count"]
                        )

                        if chunk["token_count"] < 40:
                            small_chunks += 1

    print("\n" + "=" * 50)
    print(f"STRATEGY: {strategy.upper()}")
    print("=" * 50)

    print("Pages processed:", total_pages)
    print("Total chunks:", total_chunks)

    if token_counts:

        print(
            "Average tokens:",
            round(statistics.mean(token_counts), 2)
        )

        print(
            "Median tokens:",
            statistics.median(token_counts)
        )

        print("Maximum tokens:", max(token_counts))
        print("Minimum tokens:", min(token_counts))

        print(
            "Chunks below 40 tokens:",
            small_chunks
        )

    print("Saved:", output_path)

    return {
        "strategy": strategy,
        "total_pages": total_pages,
        "total_chunks": total_chunks,
        "average_tokens": (
            round(statistics.mean(token_counts), 2)
            if token_counts else 0
        ),
        "median_tokens": (
            statistics.median(token_counts)
            if token_counts else 0
        ),
        "min_tokens": min(token_counts, default=0),
        "max_tokens": max(token_counts, default=0),
        "small_chunks": small_chunks
    }


# ==========================================
# 8. MAIN EXPERIMENT
# ==========================================

def main():

    if not any(INPUT_DIR.glob("*.jsonl")):
        raise FileNotFoundError(
            f"No curated JSONL files found in {INPUT_DIR}"
        )

    print("MODEL:", MODEL_NAME)
    print("MAX TOKENS:", MAX_TOKENS)
    print("OVERLAP:", OVERLAP)
    print("TOKENIZER MAX LENGTH:", tokenizer.model_max_length)
    print(
        "BACKEND TRUNCATION:",
        tokenizer.backend_tokenizer.truncation
    )

    results = []

    for strategy, function in STRATEGIES.items():

        result = process_strategy(
            strategy,
            function
        )

        results.append(result)

    report_path = (
        OUTPUT_DIR / "chunking_comparison.json"
    )

    with report_path.open(
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            results,
            file,
            indent=4
        )

    print("\n========== CHUNKING COMPARISON ==========")

    for result in results:
        print(result)

    print("\nComparison saved:", report_path)


if __name__ == "__main__":
    main()

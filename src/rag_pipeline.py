
import os
import re
import json
import pickle
import time
import argparse
from pathlib import Path
from datetime import datetime, timezone

import faiss
from dotenv import load_dotenv
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer, CrossEncoder
from google import genai


# ============================================================
# 1. CONFIGURATION
# ============================================================

ROOT = Path(__file__).resolve().parents[1]

VECTOR_DIR = ROOT / "vector_store"
CHUNK_DIR = ROOT / "data" / "processed" / "chunks"
EVALUATION_DIR = ROOT / "evaluation"

OUTPUT_FILE = EVALUATION_DIR / "pipeline_results.json"

load_dotenv(ROOT / ".env", override=True)

API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"

DENSE_TOP_K = 10
BM25_TOP_K = 10
RRF_K = 60
CANDIDATE_K = 10
FINAL_TOP_K = 5

MAX_OUTPUT_TOKENS = 700
THINKING_LEVEL = "low"

DEFAULT_STRATEGY = "fixed"

QUERIES = [
    "What should I do if I receive a phishing email?",
    "How can I protect my online accounts using multi-factor authentication?",
    "How should passwords be stored securely?",
    "What are the steps involved in responding to a cybersecurity incident?",
    "What should I do if my account has been compromised?"
]


SYSTEM_INSTRUCTION = """
You are CyberSafe RAG, an evidence-grounded cybersecurity
awareness and incident response assistant.

Your purpose is to provide clear, practical and reliable
cybersecurity guidance using the supplied evidence.

STRICT EVIDENCE RULES:

1. Answer using ONLY the supplied evidence.
2. Never invent facts, procedures, statistics or recommendations.
3. If evidence is insufficient, explicitly say so.
4. Every factual claim must have a supporting citation.
5. Use the exact citation format: [Evidence N, p. X].
6. Each citation must contain ONLY ONE evidence number
   and ONE page number.
7. NEVER combine multiple evidence references inside
   a single pair of square brackets.
8. When multiple sources support the same claim, write
   separate citations next to each other.
9. Never create citations or page numbers that are not supplied.
10. List only sources actually cited in your answer.
11. If sources disagree, explain the disagreement and
    identify the relevant source context.

CITATION FORMATTING:

Correct:
- Phishing emails may contain suspicious links
  [Evidence 1, p. 4].
- Multiple sources support this recommendation
  [Evidence 1, p. 4] [Evidence 4, p. 4].

Incorrect:
- [Evidence 1, p. 4, Evidence 4, p. 4]
- [Evidence 1, Evidence 4, p. 4]
- [Evidence 1, p. 4; Evidence 4, p. 4]

Every citation must be a separate bracketed reference.
Never put multiple Evidence references inside one bracket.

ANSWER QUALITY:

12. Start with a direct answer to the user's question.
13. Use numbered steps for procedures and bullet points
    for lists of signs, risks or recommendations.
14. Combine repetitive recommendations.
15. Prefer concise, actionable language.
16. Explain technical terms in simple language when needed.
17. Do not repeat the same recommendation in multiple steps.
18. Do not add unnecessary introductions or conclusions.

CYBERSECURITY SAFETY:

19. Never encourage clicking suspicious links or opening
    suspicious attachments.
20. Never instruct users to click, open, expand or visit
    suspicious or shortened URLs to verify them.
21. Do not suggest clicking a link after checking its
    displayed URL or sender address.
22. Recommend inspecting suspicious URLs without opening
    them and verifying websites through trusted official
    channels or approved security tools.
23. Never ask users to share passwords, OTPs, PINs or
    authentication secrets.
24. Never claim to scan or verify a real device, link
    or account.

SCOPE AND CONTEXT:

25. Distinguish individual-user advice from organizational
    incident response procedures.
26. Do not present organizational security controls as
    actions an ordinary individual can perform.
27. Do not invent platform-specific account recovery steps.
28. Do not invent reporting portals, phone numbers or URLs.
29. Clearly identify what information is missing when
    the supplied evidence does not cover a question.

ABSTENTION:

30. If evidence does not directly answer the question,
    clearly state that the available evidence is insufficient.
31. You may provide partial guidance only when supported
    by evidence, and must identify the missing information.
32. Never fill evidence gaps using assumptions or general
    cybersecurity knowledge.

SOURCES FORMAT:

At the end of the answer, include:

Sources:
- Source title | Issuer | Page X

Include only sources cited in the answer.
Use the exact source title, issuer and page metadata
provided with the retrieved evidence.

STRICT SOURCE LIST RULES:

39. Include a source entry only when that exact source
    and page are cited in the answer.
40. Never list every retrieved document automatically.
41. The source page must exactly match the page number
    associated with the cited Evidence reference.
42. Never infer, estimate or invent a page number.
43. If Evidence 2 is cited on page 10, the corresponding
    source entry must identify page 10.
44. Compare every source entry against the citations
    actually used before completing the answer.
45. Remove all unused or uncited source entries.
46. If a source cannot be matched confidently, do not
    guess its title, issuer or page.

CLAIM ACCURACY AND QUALIFICATIONS:

47. Do not make absolute claims unless the supplied
    evidence explicitly supports that absolute statement.
48. Preserve exceptions, limitations and qualifications
    stated by the original source.
49. Do not turn a general recommendation into an absolute rule.
50. Do not omit important conditions attached to a recommendation.
51. When describing technical security guidance, preserve
    the original source's intended context.
52. If a source says a practice is recommended in most
    circumstances, do not rewrite it as mandatory in
    every circumstance.

PASSWORD STORAGE ACCURACY:

66. When discussing password storage, distinguish
    password hashing from encryption accurately.

67. Explain that passwords should generally be stored
    using strong, adaptive password-hashing algorithms
    such as Argon2id, bcrypt or PBKDF2, when supported
    by the supplied evidence.

68. Do not claim that passwords must NEVER be encrypted
    under all circumstances.

69. Preserve the OWASP exception: encrypted password
    storage may be necessary in situations where an
    application genuinely needs to recover the original
    plaintext password to authenticate with another
    system that does not support a modern alternative.

70. Explain that this is an exception, not the preferred
    approach. Wherever possible, recommend an alternative
    architecture that avoids storing recoverable passwords.

71. Do not confuse password hashing with encryption:
    hashing is designed to be one-way, while encryption
    allows data to be recovered using the appropriate key.

72. When discussing PBKDF2 work factors, preserve the
    source's conditions, including its FIPS-140 compliance
    context where applicable. Do not present a conditional
    work-factor recommendation as universally mandatory.

73. Do not omit exceptions or conditions simply to make
    an answer shorter.

EXAMPLE OF PRESERVING SOURCE QUALIFICATIONS:

Question:
How should passwords be securely stored?

Incorrect:
"Passwords must never be encrypted."

Correct:
"Passwords should generally be stored using strong,
adaptive password-hashing algorithms such as Argon2id,
bcrypt or PBKDF2 rather than encryption.

However, OWASP acknowledges limited situations where
encrypted storage may be necessary, such as when an
application must recover the original password to
authenticate with another system that does not support
a modern alternative. Wherever possible, an alternative
architecture should be used to avoid storing recoverable
passwords."

The answer must cite the retrieved evidence supporting
both the general recommendation and the exception.

ABSTENTION RESPONSE QUALITY:

53. When evidence is insufficient, keep the response direct.
54. Do not add unrelated facts merely to make an abstention
    answer appear more informative.
55. Do not speculate about the answer to an unanswerable
    question.
56. Explain briefly what the supplied evidence cannot establish.

FINAL SELF-CHECK BEFORE RESPONDING:

57. Check every citation individually.
58. Confirm that every citation follows [Evidence N, p. X].
59. Confirm that no bracket contains multiple Evidence references.
60. Confirm that every cited evidence number and page exists
    in the supplied context.
61. Confirm that every listed source was actually cited.
62. Confirm that every listed source page matches its citation.
63. Confirm that no factual statement overstates the evidence.
64. Confirm that no important qualification has been removed.
65. If a citation cannot be formatted correctly, do not
    invent or guess it. State that the evidence reference
    could not be verified.
"""




# ============================================================
# 2. LOAD MODELS
# ============================================================

def load_models():

    print("\nLoading embedding model...")

    embedding_model = SentenceTransformer(EMBEDDING_MODEL)

    print("Embedding model loaded.")

    print("\nLoading cross-encoder...")

    reranker = CrossEncoder(RERANKER_MODEL)

    print("Cross-encoder loaded.")

    return embedding_model, reranker


# ============================================================
# 3. TOKENIZATION
# ============================================================

def tokenize(text):

    return re.findall(r"[a-zA-Z0-9]+", text.lower())


# ============================================================
# 4. LOAD VECTOR STORE
# ============================================================

def load_vector_store(strategy):

    index_path = VECTOR_DIR / f"{strategy}_index.faiss"
    metadata_path = VECTOR_DIR / f"{strategy}_metadata.pkl"

    if not index_path.exists() or not metadata_path.exists():
        raise FileNotFoundError(
            f"Vector store missing for strategy: {strategy}"
        )

    index = faiss.read_index(str(index_path))

    with open(metadata_path, "rb") as file:
        metadata = pickle.load(file)

    if index.ntotal != len(metadata):
        raise ValueError("FAISS index and metadata size mismatch.")

    return index, metadata


# ============================================================
# 5. LOAD BM25
# ============================================================

def load_bm25(strategy):

    chunk_path = CHUNK_DIR / f"{strategy}_chunks.jsonl"

    if not chunk_path.exists():
        raise FileNotFoundError(
            f"Chunk file missing: {chunk_path}"
        )

    chunks = []

    with open(chunk_path, "r", encoding="utf-8") as file:

        for line in file:

            if line.strip():
                chunks.append(json.loads(line))

    corpus = [
        tokenize(chunk.get("text", ""))
        for chunk in chunks
    ]

    bm25 = BM25Okapi(corpus)

    return bm25, chunks


# ============================================================
# 6. PREPARE RETRIEVAL COMPONENTS
# ============================================================

def prepare_retrieval(strategy, embedding_model):

    print(f"\nPreparing {strategy.upper()} retrieval...")

    index, metadata = load_vector_store(strategy)

    bm25, chunks = load_bm25(strategy)

    if index.ntotal != len(chunks):
        raise ValueError(
            "FAISS and BM25 chunk counts do not match."
        )

    if index.ntotal == 0:
        raise ValueError("Vector store is empty.")

    if len(metadata) != len(chunks):
        raise ValueError(
            "FAISS metadata and BM25 chunks do not match."
        )

    print("FAISS vectors:", index.ntotal)
    print("BM25 chunks:", len(chunks))

    return {
        "index": index,
        "metadata": metadata,
        "bm25": bm25,
        "chunks": chunks,
        "embedding_model": embedding_model
    }


# ============================================================
# 7. DENSE RETRIEVAL
# ============================================================

def retrieve_dense(query, components):

    index = components["index"]
    metadata = components["metadata"]
    model = components["embedding_model"]

    embedding = model.encode(
        [query],
        convert_to_numpy=True,
        normalize_embeddings=True
    )

    scores, indices = index.search(
        embedding.astype("float32"),
        min(DENSE_TOP_K, index.ntotal)
    )

    results = []

    for score, idx in zip(scores[0], indices[0]):

        if idx < 0:
            continue

        chunk = metadata[idx]

        results.append({
            "score": float(score),
            "chunk_id": chunk["chunk_id"],
            "source_id": chunk["source_id"],
            "source_title": chunk["source_title"],
            "issuer": chunk.get("issuer"),
            "page": chunk["page"],
            "text": chunk["text"]
        })

    return results


# ============================================================
# 8. BM25 RETRIEVAL
# ============================================================

def retrieve_bm25(query, components):

    bm25 = components["bm25"]
    chunks = components["chunks"]

    scores = bm25.get_scores(tokenize(query))

    indices = sorted(
        range(len(scores)),
        key=lambda i: scores[i],
        reverse=True
    )[:min(BM25_TOP_K, len(scores))]

    results = []

    for idx in indices:

        chunk = chunks[idx]

        results.append({
            "score": float(scores[idx]),
            "chunk_id": chunk["chunk_id"],
            "source_id": chunk["source_id"],
            "source_title": chunk["source_title"],
            "issuer": chunk.get("issuer"),
            "page": chunk["page"],
            "text": chunk["text"]
        })

    return results


# ============================================================
# 9. RECIPROCAL RANK FUSION
# ============================================================

def reciprocal_rank_fusion(dense_results, bm25_results):

    fused_scores = {}
    details = {}

    for result_list in [dense_results, bm25_results]:

        for rank, result in enumerate(result_list, start=1):

            chunk_id = result["chunk_id"]

            if chunk_id not in fused_scores:

                fused_scores[chunk_id] = 0.0
                details[chunk_id] = result.copy()

            fused_scores[chunk_id] += (
                1.0 / (RRF_K + rank)
            )

    ranked_ids = sorted(
        fused_scores,
        key=lambda chunk_id: fused_scores[chunk_id],
        reverse=True
    )

    results = []

    for chunk_id in ranked_ids:

        item = details[chunk_id].copy()

        item.pop("score", None)
        item["rrf_score"] = fused_scores[chunk_id]

        results.append(item)

    return results


# ============================================================
# 10. CROSS-ENCODER RERANKING
# ============================================================

def rerank_candidates(query, candidates, reranker):

    pairs = [
        (query, item["text"])
        for item in candidates
    ]

    scores = reranker.predict(
        pairs,
        batch_size=16,
        show_progress_bar=False
    )

    results = []

    for candidate, score in zip(candidates, scores):

        item = candidate.copy()
        item["cross_encoder_score"] = float(score)

        results.append(item)

    results.sort(
        key=lambda item: item["cross_encoder_score"],
        reverse=True
    )

    return results


# ============================================================
# 11. BUILD EVIDENCE CONTEXT
# ============================================================

def clean_text(text):

    return re.sub(r"\s+", " ", str(text)).strip()


def build_context(chunks):

    blocks = []

    for number, chunk in enumerate(chunks, start=1):

        blocks.append(
            f"[EVIDENCE {number}]\n"
            f"Source: {chunk.get('source_title', 'Unknown')}\n"
            f"Issuer: {chunk.get('issuer', 'Unknown')}\n"
            f"Source ID: {chunk.get('source_id', 'Unknown')}\n"
            f"Page: {chunk.get('page', 'Unknown')}\n"
            f"Content: {clean_text(chunk.get('text', ''))}"
        )

    return "\n\n---\n\n".join(blocks)


# ============================================================
# 11.5 CITATION VALIDATION
# ============================================================

def validate_citations(answer, chunks):
    """Validate citation references and the Sources list structurally.

    This checks evidence indices, page numbers, and source-list consistency.
    It does NOT establish whether a cited passage semantically supports a claim.
    """
    citation_pattern = re.compile(
    r"\[Evidence (\d+), p\. (\d+)\]"
)
    citation_like_pattern = re.compile(r"\[Evidence[^\]]*\]", re.IGNORECASE)

    citations = citation_pattern.findall(answer or "")
    citation_like = citation_like_pattern.findall(answer or "")
    evidence_map = {
        number: chunk for number, chunk in enumerate(chunks or [], start=1)
    }

    errors = []
    valid_citations = []
    cited_evidence_numbers = set()

    for evidence_number_text, page_number_text in citations:
        evidence_number = int(evidence_number_text)
        page_number = int(page_number_text)
        chunk = evidence_map.get(evidence_number)

        if chunk is None:
            errors.append(f"Invalid evidence number: Evidence {evidence_number}.")
            continue

        try:
            actual_page = int(chunk["page"])
        except (KeyError, TypeError, ValueError):
            errors.append(f"Evidence {evidence_number} has invalid page metadata.")
            continue

        if page_number != actual_page:
            errors.append(
                f"Page mismatch: Evidence {evidence_number} cites page {page_number}, "
                f"but retrieved evidence is page {actual_page}."
            )
            continue

        valid_citations.append((evidence_number, page_number))
        cited_evidence_numbers.add(evidence_number)

    # Catch malformed Evidence references, including references with wrong syntax.
    normalized_valid = {
        (number, page) for number, page in valid_citations
    }
    for citation_text in citation_like:
        match = citation_pattern.fullmatch(citation_text.strip())
        if not match:
            errors.append(f"Malformed citation: {citation_text}")
            continue
        pair = (int(match.group(1)), int(match.group(2)))
        if pair not in normalized_valid:
            # A validly formatted but invalid reference was already reported above.
            pass

    sources_match = re.search(
        r"^Sources\s*:\s*\n([\s\S]*)",
        answer or "",
        re.IGNORECASE | re.MULTILINE
    )

    if not sources_match:
    # A concise abstention with no citations does not require a Sources section.
        if citations:
            errors.append("Sources section is missing.")

        source_lines = []
    else:
        source_lines = [
            line.strip()[1:].strip()
            for line in sources_match.group(1).splitlines()
            if line.strip().startswith(("-", "*"))
        ]

    expected_sources = set()
    for evidence_number in cited_evidence_numbers:
        chunk = evidence_map[evidence_number]
        expected_sources.add((
            str(chunk.get("source_title") or "Unknown").strip().casefold(),
            str(chunk.get("issuer") or "Unknown").strip().casefold(),
            str(chunk.get("page", "Unknown")).strip()
        ))

    actual_sources = set()
    for line in source_lines:
        parts = [part.strip() for part in line.split("|")]
        if len(parts) != 3:
            errors.append(f"Malformed source entry: {line}")
            continue

        page_text = re.sub(r"^page\s+", "", parts[2], flags=re.IGNORECASE).strip()
        actual_sources.add((
            parts[0].casefold(),
            parts[1].casefold(),
            page_text
        ))

    for source in sorted(expected_sources - actual_sources):
        errors.append(
            f"Missing source entry: {source[0]} | {source[1]} | Page {source[2]}"
        )

    for source in sorted(actual_sources - expected_sources):
        errors.append(
            f"Uncited or unknown source listed: "
            f"{source[0]} | {source[1]} | Page {source[2]}"
        )

    return {
        "valid": len(errors) == 0,
        "citation_count": len(citations),
        "valid_citation_count": len(valid_citations),
        "errors": errors
    }

def rebuild_sources_section(answer, chunks):
    """
    Rebuild the Sources section using only citations
    actually present in the answer.

    Source metadata is obtained directly from retrieved chunks.
    Invalid citations are not silently corrected.
    """

    if not answer:
        return answer

    # Remove any existing Sources section.
    answer_body = re.split(
        r"^Sources\s*:",
        answer,
        maxsplit=1,
        flags=re.IGNORECASE | re.MULTILINE
    )[0].strip()

    citation_pattern = re.compile(
        r"\[Evidence\s+(\d+),\s*p\.\s*(\d+)\]",
        re.IGNORECASE
    )

    evidence_map = {
        number: chunk
        for number, chunk in enumerate(chunks or [], start=1)
    }

    # Collect unique source/page combinations from citations.
    cited_sources = {}

    for evidence_number_text, page_number_text in (
        citation_pattern.findall(answer_body)
    ):

        evidence_number = int(evidence_number_text)
        cited_page = int(page_number_text)

        chunk = evidence_map.get(evidence_number)

        if chunk is None:
            continue

        try:
            actual_page = int(chunk.get("page"))
        except (TypeError, ValueError):
            continue

        # Do not silently repair an incorrect citation.
        if cited_page != actual_page:
            continue

        source_title = str(
            chunk.get("source_title") or "Unknown"
        ).strip()

        issuer = str(
            chunk.get("issuer") or "Unknown"
        ).strip()

        key = (
            source_title.casefold(),
            issuer.casefold(),
            actual_page
        )

        cited_sources[key] = (
            source_title,
            issuer,
            actual_page
        )

    # Build the Sources section.
    if not cited_sources:
        return answer_body

    source_lines = ["", "Sources:"]

    for source_title, issuer, page in sorted(
        cited_sources.values(),
        key=lambda item: (
            item[0].casefold(),
            item[2]
        )
    ):
        source_lines.append(
            f"- {source_title} | {issuer} | Page {page}"
        )

    return answer_body + "\n" + "\n".join(source_lines)


# ============================================================
# 11.6 CLAIM-LEVEL CITATION VERIFICATION
# ============================================================

def _extract_json_object(text):
    """Extract JSON from the verifier response."""

    if not text:
        raise ValueError("Verifier returned an empty response.")

    cleaned = text.strip()
    cleaned = re.sub(
        r"^```(?:json)?\s*", "", cleaned,
        flags=re.IGNORECASE
    )
    cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        parsed = json.loads(cleaned)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{[\s\S]*\}", cleaned)

    if not match:
        raise ValueError("No JSON object found.")

    parsed = json.loads(match.group(0))

    if not isinstance(parsed, dict):
        raise ValueError("Expected a JSON object.")

    return parsed



def verify_claim_support(answer, chunks, client):
    """
    Verify individual factual claims using sentence-level
    citation mapping.

    Python determines which citations belong to each sentence.
    Gemini evaluates semantic support but cannot assign citations
    from other sentences.
    """

    if not answer or not chunks:
        return {
            "status": "not_run",
            "claim_count": 0,
            "supported_count": 0,
            "partially_supported_count": 0,
            "unsupported_count": 0,
            "missing_citation_count": 0,
            "claims": [],
            "error": "Answer or evidence is empty."
        }

    # ========================================================
    # 1. EXTRACT ANSWER WITHOUT SOURCES SECTION
    # ========================================================

    answer_body = re.split(
        r"^Sources\s*:",
        answer,
        maxsplit=1,
        flags=re.IGNORECASE | re.MULTILINE
    )[0].strip()

    citation_pattern = re.compile(
        r"\[Evidence\s+(\d+),\s*p\.\s*(\d+)\]",
        re.IGNORECASE
    )

    # ========================================================
    # 2. SPLIT ANSWER INTO SENTENCES
    # ========================================================

    lines = [
        line.strip()
        for line in answer_body.splitlines()
        if line.strip()
    ]

    sentences = []

    for line in lines:

        # Protect the period inside citation notation:
        # [Evidence 1, p. 10]
        protected_line = re.sub(
            r"(\[Evidence\s+\d+,\s*)p\.",
            r"\1p<DOT>",
            line,
            flags=re.IGNORECASE
        )

        # Protect common abbreviations.
        protected_line = re.sub(
            r"\b(e\.g|i\.e|etc|Mr|Mrs|Dr|vs)\.",
            lambda match: match.group(0).replace(".", "<DOT>"),
            protected_line,
            flags=re.IGNORECASE
        )

        # Keep citations attached to the preceding sentence.
        parts = re.split(
            r"(?<=[.!?])\s+(?!\[Evidence\s+\d+,\s*p)"
            r"(?=(?:[A-Z0-9*#\-\[]|[\"']))",
            protected_line,
            flags=re.IGNORECASE
        )

        for part in parts:

            part = part.replace("<DOT>", ".").strip()

            if part:
                sentences.append(part)

    # ========================================================
    # 3. CREATE SENTENCE-LEVEL CITATION MAP
    # ========================================================

    sentence_map = {}

    for sentence_id, sentence in enumerate(sentences, start=1):

        sentence_citations = [
            (int(evidence_number), int(page_number))
            for evidence_number, page_number
            in citation_pattern.findall(sentence)
        ]

        sentence_map[sentence_id] = {
            "text": sentence,
            "citations": list(set(sentence_citations))
        }

    print("\n========== SENTENCE CITATION MAP ==========")

    for sentence_id, data in sentence_map.items():

        print(
            f"Sentence {sentence_id}: {data['text']}",
            flush=True
        )

        print(
            "Citations:",
            data["citations"],
            flush=True
        )

    print("===========================================\n")

    # ========================================================
    # 4. BUILD RETRIEVED EVIDENCE CONTEXT
    # ========================================================

    evidence_blocks = []

    for number, chunk in enumerate(chunks, start=1):

        evidence_blocks.append(
            f"[EVIDENCE {number}]\n"
            f"Source: {chunk.get('source_title', 'Unknown')}\n"
            f"Issuer: {chunk.get('issuer', 'Unknown')}\n"
            f"Page: {chunk.get('page', 'Unknown')}\n"
            f"Content: {clean_text(chunk.get('text', ''))}"
        )

    evidence_context = "\n\n---\n\n".join(evidence_blocks)

    # ========================================================
    # 5. PREPARE SENTENCES FOR GEMINI
    # ========================================================

    sentence_context = []

    for sentence_id, data in sentence_map.items():

        sentence_context.append({
            "segment_id": sentence_id,
            "sentence": data["text"]
        })

    sentence_context_json = json.dumps(
        sentence_context,
        indent=2,
        ensure_ascii=False
    )

    # ========================================================
    # 6. CLAIM-LEVEL VERIFICATION PROMPT
    # ========================================================

    verification_prompt = f"""
You are a strict claim-level evidence verifier.

TASK:

1. Examine each supplied sentence independently.
2. Split sentences containing multiple factual claims
   into individual claims.
3. Preserve the original wording of each claim.
4. Return the segment_id of the sentence from which
   each claim was extracted.
5. Assess each claim ONLY against citations attached
   to its original sentence.
6. Do not borrow citations from other sentences.
7. Do not use outside knowledge.
8. Do not assume a recommendation is correct merely
   because it is common cybersecurity advice.

CLASSIFICATION:

SUPPORTED:
The cited passage directly supports the entire claim.

PARTIALLY_SUPPORTED:
The passage supports only part of the claim, or the
claim is broader or more specific than the evidence.

UNSUPPORTED:
The cited passage does not support or contradicts
the claim.

MISSING_CITATION:
The original sentence has no citation.

IMPORTANT:

- Python independently determines which citations
  belong to each sentence.
- Do not invent citation references.
- Do not assign citations from another sentence.
- Do not use uncited evidence to rescue a claim.
- Multiple claims from one sentence may share that
  sentence's citations.
- Preserve the original claim wording.
- Give a short explanation based on the evidence.
- Ignore headings and non-factual content.
- Do not include claims from the Sources section.

Return ONLY valid JSON in this format:

{{
  "claims": [
    {{
      "segment_id": 1,
      "claim": "Original factual claim",
      "status": "SUPPORTED",
      "reason": "Explanation based on the evidence."
    }}
  ]
}}

If there are no factual claims, return:
{{"claims": []}}

ORIGINAL SENTENCES:

{sentence_context_json}

RETRIEVED EVIDENCE:

{evidence_context}
"""

    try:

        # ====================================================
        # 7. CALL GEMINI
        # ====================================================

        verification = client.interactions.create(
            model=GEMINI_MODEL,
            system_instruction=(
                "You are a strict evidence verifier. "
                "Use only supplied evidence. "
                "Do not invent citations or segment IDs. "
                "Return valid JSON only."
            ),
            input=verification_prompt,
            generation_config={
                "max_output_tokens": 1200,
                "thinking_level": THINKING_LEVEL
            }
        )

        parsed = _extract_json_object(
            getattr(verification, "output_text", "") or ""
        )

        raw_claims = parsed.get("claims", [])

        if not isinstance(raw_claims, list):
            raise ValueError("'claims' must be a list.")

        # ====================================================
        # 8. PREPARE LOCAL VALIDATION
        # ====================================================

        evidence_map = {
            number: chunk
            for number, chunk in enumerate(chunks, start=1)
        }

        allowed_statuses = {
            "SUPPORTED",
            "PARTIALLY_SUPPORTED",
            "UNSUPPORTED",
            "MISSING_CITATION"
        }

        checked_claims = []

        # ====================================================
        # 9. VALIDATE EACH CLAIM
        # ====================================================

        for item in raw_claims:

            if not isinstance(item, dict):
                continue

            claim_text = str(
                item.get("claim", "")
            ).strip()

            if not claim_text:
                continue

            # Validate original sentence ID.
            try:
                segment_id = int(item.get("segment_id"))
            except (TypeError, ValueError):
                segment_id = None

            segment = sentence_map.get(segment_id)

            status = str(
                item.get("status", "UNSUPPORTED")
            ).upper().strip()

            if status not in allowed_statuses:
                status = "UNSUPPORTED"

            checked_citations = []
            citation_errors = []

            # =================================================
            # 10. GET CITATIONS ONLY FROM ORIGINAL SENTENCE
            # =================================================

            if segment is None:

                citation_errors.append(
                    "Invalid or missing segment ID returned by verifier."
                )

            else:

                original_sentence_citations = segment["citations"]

                for evidence_number, page_number in original_sentence_citations:

                    chunk = evidence_map.get(evidence_number)

                    if chunk is None:
                        citation_errors.append(
                            f"Unknown Evidence {evidence_number} "
                            "in original sentence."
                        )
                        continue

                    try:
                        actual_page = int(chunk.get("page"))

                    except (TypeError, ValueError):
                        citation_errors.append(
                            f"Invalid page metadata for Evidence "
                            f"{evidence_number}."
                        )
                        continue

                    if page_number != actual_page:
                        citation_errors.append(
                            f"Page mismatch for Evidence "
                            f"{evidence_number}."
                        )
                        continue

                    checked_citations.append({
                        "evidence_number": evidence_number,
                        "page": page_number,
                        "source_title": chunk.get(
                            "source_title", "Unknown"
                        ),
                        "issuer": chunk.get("issuer", "Unknown")
                    })

            # =================================================
            # 11. ENFORCE CITATION STATUS LOCALLY
            # =================================================

            if not checked_citations:

                status = "MISSING_CITATION"

                citation_errors.append(
                    "No valid citation was attached to the "
                    "original sentence containing this claim."
                )

            # =================================================
            # 12. SAVE VERIFIED CLAIM
            # =================================================

            checked_claims.append({
                "claim": claim_text,
                "segment_id": segment_id,
                "original_sentence": (
                    segment["text"] if segment else None
                ),
                "citations": checked_citations,
                "status": status,
                "reason": str(
                    item.get("reason", "")
                ).strip(),
                "validation_errors": citation_errors
            })

        # ====================================================
        # 13. CALCULATE FINAL COUNTS
        # ====================================================

        counts = {
            status: sum(
                claim["status"] == status
                for claim in checked_claims
            )
            for status in allowed_statuses
        }

        return {
            "status": "completed",
            "claim_count": len(checked_claims),
            "supported_count": counts["SUPPORTED"],
            "partially_supported_count": counts[
                "PARTIALLY_SUPPORTED"
            ],
            "unsupported_count": counts["UNSUPPORTED"],
            "missing_citation_count": counts[
                "MISSING_CITATION"
            ],
            "claims": checked_claims,
            "method": (
                "LLM-assisted semantic verification with "
                "Python sentence-level citation mapping; "
                "requires human validation"
            )
        }

    except Exception as error:

        print(
            "\nClaim-level verification error:",
            str(error)
        )

        return {
            "status": "failed",
            "claim_count": 0,
            "supported_count": 0,
            "partially_supported_count": 0,
            "unsupported_count": 0,
            "missing_citation_count": 0,
            "claims": [],
            "error": str(error),
            "method": (
                "LLM-assisted semantic verification with "
                "sentence-level citation mapping"
            )
        }


# ============================================================
# 12. GENERATE ANSWER
# ============================================================

def generate_answer(query, chunks, client):

    if not chunks:
        return {
            "answer": "Insufficient evidence found.",
            "status": "no_evidence",
            "api_latency": 0.0
        }

    context = build_context(chunks)

    prompt = f"""
QUESTION:
{query}

EVIDENCE:
{context}

Provide an evidence-grounded answer.

Use this format:

Answer:
[Your answer]

Sources:
- Source title | Issuer | Page

Keep the answer concise but complete.
"""

    start = time.perf_counter()

    try:

        interaction = client.interactions.create(
            model=GEMINI_MODEL,
            system_instruction=SYSTEM_INSTRUCTION,
            input=prompt,
            generation_config={
                "max_output_tokens": MAX_OUTPUT_TOKENS,
                "thinking_level": THINKING_LEVEL
            }
        )

        answer = interaction.output_text or (
            "The model returned an empty response."
        )

        status = "success"

    except Exception as error:

        message = str(error)

        print("\nGemini API error:", message)

        if "429" in message or "RESOURCE_EXHAUSTED" in message:

            answer = "Gemini API rate limit or quota exceeded."
            status = "rate_limited"

        else:

            answer = "Generation failed. Check the API error above."
            status = "failed"

    latency = time.perf_counter() - start

    
    answer = answer.strip()

# Rebuild Sources from citations actually used.
    answer = rebuild_sources_section(answer, chunks)

# Validate the final answer.
    citation_validation = validate_citations(
        answer, chunks
    )

    verification_start = time.perf_counter()

    claim_verification = (
        verify_claim_support(answer, chunks, client)
        if status == "success"
        else {
            "status": "not_run",
            "claims": [],
            "claim_count": 0
        }
    )

    verification_latency = round(
        time.perf_counter() - verification_start,
        2
    )

    return {
        "answer": answer,
        "status": status,
        "api_latency": round(latency, 2),
        "citation_validation": citation_validation,
        "claim_verification": claim_verification,
        "verification_latency": verification_latency
    }





def generate_answer_stream(query, chunks, client):
    """Stream Gemini output and measure time to first text token."""

    if not chunks:
        yield {
            "type": "complete",
            "answer": "Insufficient evidence found.",
            "status": "no_evidence",
            "api_latency": 0.0,
            "ttft": 0.0,
            "citation_validation": {},
            "claim_verification": {
                "status": "not_run",
                "claims": [],
                "claim_count": 0
            },
            "verification_latency": 0.0
        }
        return

    context = build_context(chunks)

    prompt = f"""
QUESTION:
{query}

EVIDENCE:
{context}

Provide an evidence-grounded answer.

Use this format:

Answer:
[Your answer]

Sources:
- Source title | Issuer | Page

Keep the answer concise but complete.
"""

    start = time.perf_counter()
    first_token_time = None
    answer_parts = []
    status = "success"

    try:
        stream = client.interactions.create(
            model=GEMINI_MODEL,
            system_instruction=SYSTEM_INSTRUCTION,
            input=prompt,
            generation_config={
                "max_output_tokens": MAX_OUTPUT_TOKENS,
                "thinking_level": THINKING_LEVEL,
            },
            stream=True,
        )

        for event in stream:
            event_type = getattr(event, "event_type", None)

            if event_type == "step.start":
                step = getattr(event, "step", None)
                step_type = getattr(step, "type", "unknown")
                elapsed = time.perf_counter() - start

                print(
                    f"[GEMINI] Step started: {step_type} "
                    f"at {elapsed:.2f}s",
                    flush=True,
                )

                if step_type == "thought":
                    yield {
                        "type": "status",
                        "text": "Analysing evidence..."
                    }

                elif step_type == "model_output":
                    yield {
                        "type": "status",
                        "text": "Writing answer..."
                    }

            elif event_type == "step.delta":
                delta = getattr(event, "delta", None)
                delta_type = getattr(delta, "type", None)

                if delta_type == "text":
                    text_delta = getattr(delta, "text", "")

                    if text_delta:
                        if first_token_time is None:
                            first_token_time = (
                                time.perf_counter() - start
                            )

                            print(
                                f"[GEMINI] FIRST TEXT TOKEN: "
                                f"{first_token_time:.2f}s",
                                flush=True,
                            )

                        answer_parts.append(text_delta)

                        yield {
                            "type": "token",
                            "text": text_delta
                        }

        answer = "".join(answer_parts).strip()

        if not answer:
            answer = "The model returned an empty response."

    except Exception as error:
        message = str(error)

        print(
            "\nGemini streaming API error:",
            message,
            flush=True
        )

        if "429" in message or "RESOURCE_EXHAUSTED" in message:
            answer = "Gemini API rate limit or quota exceeded."
            status = "rate_limited"

        else:
            answer = "Generation failed. Check the API error above."
            status = "failed"

        if not answer_parts:
            yield {
                "type": "token",
                "text": answer
            }

        else:
            yield {
                "type": "replace",
                "text": answer
            }

    # ========================================================
    # 1. GENERATION LATENCY
    # ========================================================

    latency = time.perf_counter() - start

    # ========================================================
    # 2. STRUCTURAL CITATION VALIDATION
    # ========================================================

    # Rebuild Sources from citations actually used.
    answer = rebuild_sources_section(answer, chunks)

# Validate the final answer.
    citation_validation = validate_citations(
      answer,
      chunks
    )

    print("\n========== CITATION VALIDATION ==========")

    print(
        json.dumps(
            citation_validation,
            indent=4,
            ensure_ascii=False
        ),
        flush=True
    )

    print("=========================================\n")

    # ========================================================
    # 3. CLAIM-LEVEL SEMANTIC VERIFICATION
    # ========================================================

    verification_start = time.perf_counter()

    if status == "success":

        claim_verification = verify_claim_support(
            answer,
            chunks,
            client
        )

    else:

        claim_verification = {
            "status": "not_run",
            "claim_count": 0,
            "supported_count": 0,
            "partially_supported_count": 0,
            "unsupported_count": 0,
            "missing_citation_count": 0,
            "claims": []
        }

    verification_latency = round(
        time.perf_counter() - verification_start,
        2
    )

    # ========================================================
    # 4. PRINT CLAIM VERIFICATION RESULTS
    # ========================================================

    print("\n========== CLAIM VERIFICATION ==========")

    print(
        json.dumps(
            claim_verification,
            indent=4,
            ensure_ascii=False
        ),
        flush=True
    )

    print(
        "\nVerification latency:",
        verification_latency,
        "seconds",
        flush=True
    )

    print("========================================\n")

    # ========================================================
    # 5. SEND FINAL RESPONSE TO FRONTEND
    # ========================================================

    yield {
        "type": "complete",
        "answer": answer,
        "status": status,
        "api_latency": round(latency, 2),
        "ttft": (
            round(first_token_time, 2)
            if first_token_time else None
        ),
        "citation_validation": citation_validation,
        "claim_verification": claim_verification,
        "verification_latency": verification_latency
    }



# ============================================================
# 13. RUN ONE QUERY
# ============================================================

def run_query(query, components, reranker, client=None):

    total_start = time.perf_counter()

    dense = retrieve_dense(query, components)
    bm25 = retrieve_bm25(query, components)

    hybrid = reciprocal_rank_fusion(dense, bm25)

    candidates = hybrid[:CANDIDATE_K]

    reranked = rerank_candidates(
        query,
        candidates,
        reranker
    )

    final_chunks = reranked[:FINAL_TOP_K]

    result = {
        "query": query,
        "dense_count": len(dense),
        "bm25_count": len(bm25),
        "candidate_count": len(candidates),
        "results": final_chunks
    }

    if client is not None:

        generation = generate_answer(
            query,
            final_chunks,
            client
        )

        result.update(generation)

    result["total_time"] = round(
        time.perf_counter() - total_start,
        2
    )

    return result


# ============================================================
# 14. SAVE RESULTS
# ============================================================

def save_results(results, strategy):

    EVALUATION_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    output = {
        "strategy": strategy,
        "embedding_model": EMBEDDING_MODEL,
        "reranker_model": RERANKER_MODEL,
        "gemini_model": GEMINI_MODEL if API_KEY else None,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "results": results
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as file:

        json.dump(
            output,
            file,
            indent=4,
            ensure_ascii=False
        )

    print("\nResults saved to:", OUTPUT_FILE)


# ============================================================
# 15. MAIN
# ============================================================

def main():

    parser = argparse.ArgumentParser(
        description="CyberSafe RAG unified pipeline"
    )

    parser.add_argument(
        "--strategy",
        choices=["fixed", "recursive"],
        default=DEFAULT_STRATEGY
    )

    parser.add_argument(
        "--no-generation",
        action="store_true",
        help="Run retrieval and reranking without Gemini"
    )

    parser.add_argument(
        "--query",
        type=str,
        help="Run a single custom question"
    )

    args = parser.parse_args()

    if not args.no_generation and not API_KEY:
        raise ValueError(
            "GEMINI_API_KEY missing from .env. "
            "Use --no-generation to test retrieval only."
        )

    print("\n" + "=" * 75)
    print("CYBERSAFE RAG - UNIFIED PIPELINE")
    print("=" * 75)

    print("Strategy:", args.strategy)
    print("Generation:", not args.no_generation)

    embedding_model, reranker = load_models()

    components = prepare_retrieval(
        args.strategy,
        embedding_model
    )

    client = None

    if not args.no_generation:
        client = genai.Client(api_key=API_KEY)

    queries = [args.query] if args.query else QUERIES

    all_results = []

    for number, query in enumerate(queries, start=1):

        print("\n" + "=" * 75)
        print(f"QUESTION {number}/{len(queries)}")
        print("=" * 75)
        print(query)

        result = run_query(
            query,
            components,
            reranker,
            client
        )

        print("\nTOP RETRIEVED EVIDENCE:")

        for rank, item in enumerate(result["results"], start=1):

            print(
                f"\n{rank}. {item['source_id']} | "
                f"Page {item['page']} | "
                f"Cross-encoder: "
                f"{item['cross_encoder_score']:.4f}"
            )

            print(item["text"][:350])

        if not args.no_generation:

            print("\nGENERATED ANSWER:\n")
            print(result["answer"])
            print("\nStatus:", result["status"])
            print("API latency:", result["api_latency"], "seconds")

            if result["status"] == "rate_limited":
                all_results.append(result)
                print("\nStopping because API quota was exceeded.")
                break

        print("\nTotal query time:", result["total_time"], "seconds")

        all_results.append(result)

    save_results(all_results, args.strategy)

    print("\nPIPELINE COMPLETED.")


if __name__ == "__main__":
    main()


import sys
import csv
import json
import time
import threading
from collections import OrderedDict

from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from backend.evaluation import router as evaluation_router

# ============================================================
# 1. PROJECT CONFIGURATION
# ============================================================

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"

sys.path.insert(0, str(SRC))

import rag_pipeline as rag


MANIFEST_PATH = ROOT / "data" / "manifests" / "sources.csv"

CHUNK_FILES = {
    "fixed": ROOT / "data" / "processed" / "chunks" / "fixed_chunks.jsonl",
    "recursive": ROOT / "data" / "processed" / "chunks" / "recursive_chunks.jsonl",
}


# ============================================================
# 2. SHARED MODEL STATE
# ============================================================

pipeline_state = {
    "embedding_model": None,
    "reranker": None,
    "components": None,
    "client": None,
    "ready": False,
}


# ============================================================
# 2A. IN-MEMORY RESPONSE CACHE
# ============================================================

CACHE_TTL_SECONDS = 24 * 60 * 60  # 24 hours
CACHE_MAX_SIZE = 128

response_cache = OrderedDict()
cache_lock = threading.Lock()

cache_stats = {
    "hits": 0,
    "misses": 0,
    "expired": 0,
}


def normalize_cache_key(message: str) -> str:
    """Normalize whitespace and casing for repeat-question caching."""
    return " ".join(message.strip().lower().split())


def get_cached_response(message: str):
    """Return an unexpired cached response, if available."""
    key = normalize_cache_key(message)
    now = time.monotonic()

    with cache_lock:
        entry = response_cache.get(key)

        if entry is None:
            cache_stats["misses"] += 1
            return None

        if now - entry["created_at"] >= CACHE_TTL_SECONDS:
            del response_cache[key]
            cache_stats["expired"] += 1
            cache_stats["misses"] += 1
            return None

        response_cache.move_to_end(key)
        cache_stats["hits"] += 1
        return entry["response"]


def store_cached_response(message: str, response):
    """Store a successful response and enforce the cache size limit."""
    key = normalize_cache_key(message)

    with cache_lock:
        response_cache[key] = {
            "response": response,
            "created_at": time.monotonic(),
        }
        response_cache.move_to_end(key)

        while len(response_cache) > CACHE_MAX_SIZE:
            response_cache.popitem(last=False)


def clear_response_cache():
    """Clear all cached responses."""
    with cache_lock:
        response_cache.clear()



# ============================================================
# 3. LOAD MODELS ONCE WHEN BACKEND STARTS
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):

    print("\n" + "=" * 60)
    print("STARTING CYBERSAFE FASTAPI BACKEND")
    print("=" * 60)

    try:

        if not rag.API_KEY:
            raise RuntimeError(
                "GEMINI_API_KEY is missing from the project .env file."
            )

        print("\nLoading embedding model...")

        embedding_model, reranker = rag.load_models()

        print("\nPreparing retrieval components...")

        components = rag.prepare_retrieval(
            "fixed",
            embedding_model
        )

        print("\nConnecting to Gemini...")

        client = rag.genai.Client(
            api_key=rag.API_KEY
        )

        pipeline_state["embedding_model"] = embedding_model
        pipeline_state["reranker"] = reranker
        pipeline_state["components"] = components
        pipeline_state["client"] = client
        pipeline_state["ready"] = True

        print("\nCyberSafe backend is ready!")

    except Exception:
        pipeline_state["ready"] = False
        print("\nFailed to initialize CyberSafe backend.")
        raise

    yield

    pipeline_state["ready"] = False

    print("\nCyberSafe backend stopped.")


# ============================================================
# 4. CREATE FASTAPI APPLICATION
# ============================================================

app = FastAPI(
    title="CyberSafe RAG API",
    description=(
        "Evidence-grounded cybersecurity awareness "
        "and incident response assistant."
    ),
    version="1.0.0",
    lifespan=lifespan,
)


# ============================================================
# 5. CORS CONFIGURATION
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://cyber-safe-rag.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(evaluation_router)

# ============================================================
# 6. REQUEST AND RESPONSE SCHEMAS
# ============================================================

class ChatRequest(BaseModel):

    message: str = Field(
        min_length=1,
        max_length=5000
    )


class EvidenceItem(BaseModel):

    number: int
    title: str
    issuer: str
    page: str
    score: float
    text: str


class ChatResponse(BaseModel):

    answer: str
    evidence: list[EvidenceItem]
    latency: float
    status: str
    cache_hit: bool = False
    total_latency: float = 0.0
    citation_validation: dict = Field(default_factory=dict)
    claim_verification: dict = Field(default_factory=dict)

# ============================================================
# 7. KNOWLEDGE BASE HELPER FUNCTIONS
# ============================================================

def load_source_manifest():

    if not MANIFEST_PATH.exists():
        raise HTTPException(
            status_code=500,
            detail="Source manifest file not found."
        )

    with open(
        MANIFEST_PATH,
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as file:

        return list(csv.DictReader(file))


def load_chunk_records(strategy: str):

    if strategy not in CHUNK_FILES:
        raise HTTPException(
            status_code=400,
            detail="Strategy must be fixed or recursive."
        )

    path = CHUNK_FILES[strategy]

    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Chunk file not found: {path.name}"
        )

    records = []

    with open(
        path,
        "r",
        encoding="utf-8"
    ) as file:

        for line in file:

            if line.strip():
                records.append(json.loads(line))

    return records


# ============================================================
# 8. HEALTH CHECK
# ============================================================

@app.get("/")
def root():

    return {
        "application": "CyberSafe RAG API",
        "status": (
            "ready"
            if pipeline_state["ready"]
            else "initializing"
        ),
    }


@app.get("/api/health")
def health():

    return {
        "status": (
            "healthy"
            if pipeline_state["ready"]
            else "not_ready"
        ),
        "pipeline_loaded": pipeline_state["ready"],
    }


# ============================================================
# 9. CHAT ENDPOINT
# ============================================================

@app.post(
    "/api/chat",
    response_model=ChatResponse
)
def chat(request: ChatRequest):

    request_start = time.perf_counter()

    if not pipeline_state["ready"]:
        raise HTTPException(
            status_code=503,
            detail="RAG pipeline is not ready."
        )

    message = request.message.strip()

    if not message:
        raise HTTPException(
            status_code=400,
            detail="Message cannot be empty."
        )

    try:
        print("\\n" + "=" * 60)
        print("NEW CYBERSAFE QUERY")
        print("=" * 60)
        print("Question:", message)

        # 1. Check the 24-hour response cache.
        cached_response = get_cached_response(message)

        if cached_response is not None:
            total_latency_ms = (
                time.perf_counter() - request_start
            ) * 1000

            print("\\nCACHE HIT - Gemini generation skipped.")
            print("Response time:", round(total_latency_ms, 2), "ms")

            return cached_response.model_copy(
                update={
                    "cache_hit": True,
                    "total_latency": round(total_latency_ms, 2),
                }
            )

        print("\\nCACHE MISS - Running RAG pipeline...")

        # 2. Run the existing retrieval and generation pipeline.
        result = rag.run_query(
            message,
            pipeline_state["components"],
            pipeline_state["reranker"],
            pipeline_state["client"]
        )

        answer = result.get(
            "answer",
            "No answer was generated."
        )
        retrieved = result.get("results", [])

        evidence = []

        for index, item in enumerate(retrieved, start=1):
            try:
                score = float(
                    item.get("cross_encoder_score", 0)
                )
            except (TypeError, ValueError):
                score = 0.0

            evidence.append(
                EvidenceItem(
                    number=index,
                    title=str(
                        item.get("source_title", "Unknown source")
                    ),
                    issuer=str(
                        item.get("issuer", "Unknown")
                    ),
                    page=str(
                        item.get("page", "Unknown")
                    ),
                    score=score,
                    text=str(
                        item.get("text", "")
                    )
                )
            )

        latency = float(result.get("api_latency", 0))
        total_latency_ms = (
            time.perf_counter() - request_start
        ) * 1000

        response = ChatResponse(
            answer=answer,
            evidence=evidence,
            latency=latency,
            status="success",
            cache_hit=False,
            total_latency=round(total_latency_ms, 2),
            citation_validation=result.get("citation_validation", {}),
            claim_verification=result.get("claim_verification", {}),
        )

        # Cache only successful answers with supporting evidence.
        if answer.strip() and evidence:
            store_cached_response(message, response)
            print("\\nResponse stored in 24-hour cache.")

        print("\\nAnswer generated successfully.")
        print("Evidence items:", len(evidence))
        print("Gemini latency:", latency, "seconds")
        print("Total request latency:", round(total_latency_ms, 2), "ms")

        return response

    except Exception as error:
        print("\\nRAG ERROR:", repr(error))
        raise HTTPException(
            status_code=500,
            detail="Unable to process the cybersecurity question."
        ) from error


# ============================================================
# 9A. STREAMING CHAT ENDPOINT
# ============================================================

def sse_event(event_name: str, payload: dict) -> str:
    """Format one Server-Sent Event."""
    return f"event: {event_name}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


def stream_chat_response(message: str):
    """
    Stream evidence metadata first, followed by Gemini text deltas.
    Completed successful responses are stored in the existing 24-hour cache.
    """
    request_start = time.perf_counter()

    try:
        cached_response = get_cached_response(message)

        if cached_response is not None:
            total_latency_ms = (time.perf_counter() - request_start) * 1000

            yield sse_event(
                "meta",
                {
                    "evidence": [
                        item.model_dump() for item in cached_response.evidence
                    ],
                    "cache_hit": True,
                    "latency": cached_response.latency,
                },
            )
            # Send cached answer as one chunk; no Gemini request is made.
            yield sse_event("token", {"text": cached_response.answer})
            yield sse_event(
                "complete",
                {
                    "answer": cached_response.answer,
                    "status": cached_response.status,
                    "latency": cached_response.latency,
                    "total_latency": round(total_latency_ms, 2),
                    "cache_hit": True,
                    "citation_validation": cached_response.citation_validation,
                },
            )
            return

        if not pipeline_state["ready"]:
            yield sse_event(
                "error",
                {"message": "RAG pipeline is not ready."},
            )
            return

        # Retrieval and reranking are completed before Gemini starts.
        components = pipeline_state["components"]
        dense = rag.retrieve_dense(message, components)
        bm25 = rag.retrieve_bm25(message, components)
        hybrid = rag.reciprocal_rank_fusion(dense, bm25)
        candidates = hybrid[:rag.CANDIDATE_K]
        reranked = rag.rerank_candidates(
            message,
            candidates,
            pipeline_state["reranker"],
        )
        final_chunks = reranked[:rag.FINAL_TOP_K]

        evidence = []
        for index, item in enumerate(final_chunks, start=1):
            try:
                score = float(item.get("cross_encoder_score", 0))
            except (TypeError, ValueError):
                score = 0.0

            evidence.append(
                EvidenceItem(
                    number=index,
                    title=str(item.get("source_title", "Unknown source")),
                    issuer=str(item.get("issuer", "Unknown")),
                    page=str(item.get("page", "Unknown")),
                    score=score,
                    text=str(item.get("text", "")),
                )
            )

        # Send evidence to React as soon as retrieval is finished.
        yield sse_event(
            "meta",
            {
                "evidence": [item.model_dump() for item in evidence],
                "cache_hit": False,
                "latency": 0.0,
            },
        )

        final_generation = None
        for update in rag.generate_answer_stream(
            message,
            final_chunks,
            pipeline_state["client"],
        ):
            if update["type"] == "token":
                yield sse_event("token", {"text": update["text"]})
            elif update["type"] == "replace":
                yield sse_event("replace", {"text": update["text"]})
            elif update["type"] == "complete":
                final_generation = update
            elif update["type"] == "status":
                yield sse_event("status", {"text": update["text"]})

        if final_generation is None:
            raise RuntimeError("Gemini stream ended without a completion event.")

        answer = final_generation["answer"]
        latency = float(final_generation.get("api_latency", 0.0))
        total_latency_ms = (time.perf_counter() - request_start) * 1000
        status = final_generation.get("status", "success")

        response = ChatResponse(
            answer=answer,
            evidence=evidence,
            latency=latency,
            status=status,
            cache_hit=False,
            total_latency=round(total_latency_ms, 2),
            citation_validation=final_generation.get("citation_validation", {}),
            claim_verification=final_generation.get("claim_verification", {}),
        )

        if status == "success" and answer.strip() and evidence:
            store_cached_response(message, response)

        yield sse_event(
            "complete",
            {
                "answer": answer,
                "status": status,
                "latency": latency,
                "total_latency": round(total_latency_ms, 2),
                "cache_hit": False,
                "citation_validation": final_generation.get("citation_validation", {}),
                "claim_verification": final_generation.get("claim_verification", {}),
            },
        )

    except Exception as error:
        print("\nStreaming RAG error:", repr(error))
        yield sse_event(
            "error",
            {"message": "Unable to process the cybersecurity question."},
        )


@app.post("/api/chat/stream")
def chat_stream(request: ChatRequest):
    message = request.message.strip()

    if not message:
        raise HTTPException(
            status_code=400,
            detail="Message cannot be empty.",
        )

    return StreamingResponse(
        stream_chat_response(message),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ============================================================
# 9A. CACHE MONITORING
# ============================================================

@app.get("/api/cache/stats")
def get_cache_stats():

    now = time.monotonic()

    with cache_lock:
        # Remove expired entries before reporting the current size.
        expired_keys = [
            key
            for key, entry in response_cache.items()
            if now - entry["created_at"] >= CACHE_TTL_SECONDS
        ]

        for key in expired_keys:
            del response_cache[key]

        cache_stats["expired"] += len(expired_keys)

        hits = cache_stats["hits"]
        misses = cache_stats["misses"]

        return {
            "cache_entries": len(response_cache),
            "maximum_entries": CACHE_MAX_SIZE,
            "ttl_seconds": CACHE_TTL_SECONDS,
            "ttl_hours": CACHE_TTL_SECONDS / 3600,
            "hits": hits,
            "misses": misses,
            "expired": cache_stats["expired"],
            "hit_rate_percent": round(
                hits / max(hits + misses, 1) * 100,
                2
            ),
        }


@app.delete("/api/cache")
def delete_cache():

    clear_response_cache()

    return {
        "status": "success",
        "message": "Response cache cleared.",
    }


# ============================================================
# 10. KNOWLEDGE BASE STATISTICS
# ============================================================

@app.get("/api/knowledge/stats")
def knowledge_stats():

    manifest = load_source_manifest()

    fixed_chunks = load_chunk_records("fixed")
    recursive_chunks = load_chunk_records("recursive")

    issuers = sorted({
        item["issuer"]
        for item in manifest
        if item.get("issuer")
    })

    categories = sorted({
        item["category"]
        for item in manifest
        if item.get("category")
    })

    return {
        "total_documents": len(manifest),
        "fixed_chunks": len(fixed_chunks),
        "recursive_chunks": len(recursive_chunks),
        "issuers": issuers,
        "categories": categories,
        "strategies": ["fixed", "recursive"],
    }


# ============================================================
# 11. GET AND SEARCH DOCUMENTS
# ============================================================

@app.get("/api/knowledge")
def get_knowledge(
    search: str = "",
    issuer: str = "all",
    strategy: str = "fixed",
):

    manifest = load_source_manifest()
    chunks = load_chunk_records(strategy)

    search = search.strip().lower()

    grouped = {}

    for chunk in chunks:

        source_id = chunk["source_id"]

        if source_id not in grouped:
            grouped[source_id] = []

        grouped[source_id].append(chunk)

    documents = []

    for source in manifest:

        source_id = source["source_id"]
        source_chunks = grouped.get(source_id, [])

        title = source.get("title", "")
        source_issuer = source.get("issuer", "")

        searchable_text = (
            title + " " +
            source_issuer + " " +
            source_id + " " +
            source.get("category", "")
        ).lower()

        if search and search not in searchable_text:
            continue

        if issuer.lower() != "all":

            if source_issuer.lower() != issuer.lower():
                continue

        pages = {
            int(chunk["page"])
            for chunk in source_chunks
            if chunk.get("page") is not None
        }

        documents.append({

            "source_id": source_id,

            "title": title,

            "issuer": source_issuer,

            "category": source.get("category", ""),

            "audience": source.get("audience", ""),

            "jurisdiction": source.get("jurisdiction", ""),

            "publication_date": source.get(
                "publication_date", ""
            ),

            "source_url": source.get("source_url", ""),

            "total_chunks": len(source_chunks),

            "total_pages": len(pages),

            "total_tokens": sum(
                int(chunk.get("token_count", 0))
                for chunk in source_chunks
            ),

        })

    return {
        "strategy": strategy,
        "total": len(documents),
        "documents": documents,
    }


# ============================================================
# 12. GET CHUNKS FOR AN INDIVIDUAL DOCUMENT
# ============================================================

@app.get("/api/knowledge/{source_id}/chunks")
def get_document_chunks(
    source_id: str,
    strategy: str = "fixed",
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
):

    manifest = load_source_manifest()

    source = next(
        (
            item for item in manifest
            if item["source_id"] == source_id
        ),
        None
    )

    if source is None:
        raise HTTPException(
            status_code=404,
            detail="Document not found."
        )

    chunks = load_chunk_records(strategy)

    document_chunks = [

        {
            "chunk_id": item["chunk_id"],
            "source_id": item["source_id"],
            "source_title": item["source_title"],
            "issuer": item["issuer"],
            "category": item["category"],
            "page": item["page"],
            "strategy": item["strategy"],
            "token_count": item["token_count"],
            "text": item["text"],
        }

        for item in chunks

        if item["source_id"] == source_id

    ]

    start = (page - 1) * limit
    end = start + limit

    return {
        "source": source,
        "strategy": strategy,
        "total_chunks": len(document_chunks),
        "page": page,
        "limit": limit,
        "chunks": document_chunks[start:end],
    }

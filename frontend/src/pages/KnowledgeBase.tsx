import { useCallback, useEffect, useState } from "react";
import {
  Search,
  Database,
  FileText,
  Layers,
  ChevronRight,
  ChevronDown,
  ExternalLink,
  X,
  LoaderCircle,
  BookOpen,
  Shield,
  Filter,
  ArrowLeft,
  CalendarDays,
  Globe,
} from "lucide-react";

const API_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

type Strategy = "fixed" | "recursive";

type DocumentItem = {
  source_id: string;
  title: string;
  issuer: string;
  category: string;
  audience: string;
  jurisdiction: string;
  publication_date: string;
  source_url: string;
  total_chunks: number;
  total_pages: number;
  total_tokens: number;
};

type Chunk = {
  chunk_id: string;
  source_id: string;
  source_title: string;
  issuer: string;
  category: string;
  page: number;
  strategy: string;
  token_count: number;
  text: string;
};

type Stats = {
  total_documents: number;
  fixed_chunks: number;
  recursive_chunks: number;
  issuers: string[];
  categories: string[];
  strategies: string[];
};

const issuerColors: Record<string, string> = {
  "CERT-In": "text-cyan-300 bg-cyan-400/10 border-cyan-400/20",
  NIST: "text-violet-300 bg-violet-400/10 border-violet-400/20",
  OWASP: "text-amber-300 bg-amber-400/10 border-amber-400/20",
};

const formatCategory = (category: string) => category.replaceAll("_", " ");

export default function KnowledgeBase() {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [search, setSearch] = useState("");
  const [issuer, setIssuer] = useState("all");
  const [strategy, setStrategy] = useState<Strategy>("fixed");

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [selectedDocument, setSelectedDocument] = useState<DocumentItem | null>(
    null,
  );

  const [chunks, setChunks] = useState<Chunk[]>([]);
  const [chunkLoading, setChunkLoading] = useState(false);
  const [chunkError, setChunkError] = useState("");
  const [chunkPage, setChunkPage] = useState(1);
  const [totalChunks, setTotalChunks] = useState(0);
  const [expandedChunks, setExpandedChunks] = useState<string[]>([]);

  const CHUNKS_PER_PAGE = 8;

  // =====================================================
  // LOAD KNOWLEDGE BASE STATISTICS
  // =====================================================

  useEffect(() => {
    const loadStats = async () => {
      try {
        const response = await fetch(`${API_URL}/api/knowledge/stats`);

        if (!response.ok) {
          throw new Error("Could not load knowledge base statistics.");
        }

        const data: Stats = await response.json();
        setStats(data);
      } catch (err) {
        console.error(err);
      }
    };

    loadStats();
  }, []);

  // =====================================================
  // LOAD DOCUMENTS
  // =====================================================

  const loadDocuments = useCallback(async () => {
    setLoading(true);
    setError("");

    try {
      const params = new URLSearchParams({
        search,
        issuer,
        strategy,
      });

      const response = await fetch(
        `${API_URL}/api/knowledge?${params.toString()}`,
      );

      if (!response.ok) {
        throw new Error("Unable to load documents.");
      }

      const data = await response.json();
      setDocuments(data.documents || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
    } finally {
      setLoading(false);
    }
  }, [search, issuer, strategy]);

  useEffect(() => {
    const timeout = window.setTimeout(() => {
      loadDocuments();
    }, 250);

    return () => window.clearTimeout(timeout);
  }, [loadDocuments]);

  // =====================================================
  // LOAD CHUNKS FOR SELECTED DOCUMENT
  // =====================================================

  const loadChunks = async (document: DocumentItem, page: number) => {
    setChunkLoading(true);
    setChunkError("");

    try {
      const params = new URLSearchParams({
        strategy,
        page: String(page),
        limit: String(CHUNKS_PER_PAGE),
      });

      const response = await fetch(
        `${API_URL}/api/knowledge/${encodeURIComponent(
          document.source_id,
        )}/chunks?${params.toString()}`,
      );

      if (!response.ok) {
        throw new Error("Unable to load document chunks.");
      }

      const data = await response.json();

      setChunks(data.chunks || []);
      setTotalChunks(data.total_chunks || 0);
      setChunkPage(page);
      setExpandedChunks([]);
    } catch (err) {
      setChunkError(
        err instanceof Error ? err.message : "Unable to load chunks.",
      );
    } finally {
      setChunkLoading(false);
    }
  };

  const openDocument = (document: DocumentItem) => {
    setSelectedDocument(document);
    setChunks([]);
    setChunkPage(1);
    setExpandedChunks([]);
    loadChunks(document, 1);
  };

  const closeDocument = () => {
    setSelectedDocument(null);
    setChunks([]);
    setChunkError("");
  };

  const toggleChunk = (chunkId: string) => {
    setExpandedChunks((previous) =>
      previous.includes(chunkId)
        ? previous.filter((id) => id !== chunkId)
        : [...previous, chunkId],
    );
  };

  // Reload selected document's chunks when strategy changes.
  useEffect(() => {
    if (selectedDocument) {
      loadChunks(selectedDocument, 1);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [strategy]);

  // =====================================================
  // DOCUMENT DETAILS VIEW
  // =====================================================

  if (selectedDocument) {
    const document = selectedDocument;
    const totalPages = Math.max(1, Math.ceil(totalChunks / CHUNKS_PER_PAGE));

    return (
      <div className="space-y-6">
        <button
          onClick={closeDocument}
          className="flex items-center gap-2 text-sm text-slate-400 hover:text-cyan-400 transition"
        >
          <ArrowLeft size={17} />
          Back to Knowledge Base
        </button>

        <section className="rounded-2xl border border-slate-800 bg-[#101a2c] p-6">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div className="flex gap-4">
              <div className="w-12 h-12 rounded-xl bg-cyan-400/10 flex items-center justify-center shrink-0">
                <FileText className="text-cyan-400" size={24} />
              </div>

              <div>
                <div className="flex flex-wrap items-center gap-2 mb-2">
                  <span
                    className={`text-xs px-2.5 py-1 rounded-full border ${
                      issuerColors[document.issuer] ||
                      "text-slate-300 bg-slate-800 border-slate-700"
                    }`}
                  >
                    {document.issuer}
                  </span>

                  <span className="text-xs text-slate-500">
                    {document.source_id}
                  </span>
                </div>

                <h2 className="text-xl font-bold">{document.title}</h2>

                <p className="text-sm text-slate-500 mt-1 capitalize">
                  {formatCategory(document.category)}
                </p>
              </div>
            </div>

            {document.source_url && (
              <a
                href={document.source_url}
                target="_blank"
                rel="noreferrer"
                className="flex items-center gap-2 text-sm text-cyan-400 hover:text-cyan-300"
              >
                Original source
                <ExternalLink size={15} />
              </a>
            )}
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-7">
            {[
              ["Indexed chunks", document.total_chunks],
              ["Indexed pages", document.total_pages],
              ["Tokens", document.total_tokens.toLocaleString()],
              ["Publication", document.publication_date || "Not specified"],
            ].map(([label, value]) => (
              <div
                key={String(label)}
                className="rounded-xl bg-slate-900/80 border border-slate-800 p-4"
              >
                <p className="text-xs text-slate-500 mb-2">{label}</p>
                <p className="text-lg font-bold text-white">{value}</p>
              </div>
            ))}
          </div>

          <div className="flex flex-wrap items-center justify-between gap-3 mt-6 pt-5 border-t border-slate-800">
            <div>
              <h3 className="font-semibold">Indexed text chunks</h3>
              <p className="text-xs text-slate-500 mt-1">
                Inspect the exact text used by the retrieval system.
              </p>
            </div>

            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-500">Strategy</span>

              <select
                value={strategy}
                onChange={(e) => setStrategy(e.target.value as Strategy)}
                className="bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white outline-none focus:border-cyan-400"
              >
                <option value="fixed">Fixed-size</option>
                <option value="recursive">Recursive</option>
              </select>
            </div>
          </div>
        </section>

        {/* CHUNK LIST */}

        {chunkError && (
          <div className="rounded-xl border border-red-400/20 bg-red-400/5 p-4 text-sm text-red-300">
            {chunkError}
          </div>
        )}

        {chunkLoading ? (
          <div className="flex items-center justify-center py-20 text-slate-400 gap-3">
            <LoaderCircle className="animate-spin text-cyan-400" />
            Loading indexed chunks...
          </div>
        ) : (
          <div className="space-y-3">
            {chunks.map((chunk, index) => {
              const expanded = expandedChunks.includes(chunk.chunk_id);

              return (
                <div
                  key={chunk.chunk_id}
                  className="rounded-xl border border-slate-800 bg-[#101a2c] overflow-hidden"
                >
                  <button
                    onClick={() => toggleChunk(chunk.chunk_id)}
                    className="w-full flex flex-wrap items-center gap-3 p-4 text-left hover:bg-slate-900/70 transition"
                  >
                    {expanded ? (
                      <ChevronDown size={17} className="text-cyan-400" />
                    ) : (
                      <ChevronRight size={17} className="text-cyan-400" />
                    )}

                    <span className="text-xs font-bold text-cyan-400">
                      CHUNK{" "}
                      {String(
                        (chunkPage - 1) * CHUNKS_PER_PAGE + index + 1,
                      ).padStart(2, "0")}
                    </span>

                    <span className="text-sm font-medium flex-1 min-w-0 truncate">
                      {chunk.chunk_id}
                    </span>

                    <span className="text-xs text-slate-500">
                      Page {chunk.page}
                    </span>

                    <span className="text-xs text-slate-500">
                      {chunk.token_count} tokens
                    </span>
                  </button>

                  {expanded && (
                    <div className="px-5 pb-5">
                      <div className="border-t border-slate-800 pt-4">
                        <div className="flex flex-wrap gap-2 mb-4">
                          <span className="text-xs rounded-full bg-cyan-400/10 text-cyan-300 px-2.5 py-1">
                            {chunk.issuer}
                          </span>

                          <span className="text-xs rounded-full bg-slate-800 text-slate-300 px-2.5 py-1">
                            Page {chunk.page}
                          </span>

                          <span className="text-xs rounded-full bg-slate-800 text-slate-300 px-2.5 py-1">
                            {chunk.token_count} tokens
                          </span>
                        </div>

                        <pre className="text-sm text-slate-300 leading-7 whitespace-pre-wrap break-words font-sans">
                          {chunk.text}
                        </pre>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}

            {chunks.length === 0 && !chunkLoading && (
              <div className="text-center py-12 text-slate-500">
                No chunks found for this document.
              </div>
            )}
          </div>
        )}

        {/* PAGINATION */}

        {totalChunks > CHUNKS_PER_PAGE && (
          <div className="flex items-center justify-between rounded-xl border border-slate-800 bg-[#101a2c] p-4">
            <p className="text-xs text-slate-500">
              Showing{" "}
              {Math.min((chunkPage - 1) * CHUNKS_PER_PAGE + 1, totalChunks)}
              {" - "}
              {Math.min(chunkPage * CHUNKS_PER_PAGE, totalChunks)}
              {" of "}
              {totalChunks} chunks
            </p>

            <div className="flex gap-2">
              <button
                disabled={chunkPage <= 1 || chunkLoading}
                onClick={() => loadChunks(document, chunkPage - 1)}
                className="px-3 py-2 text-xs rounded-lg border border-slate-700 disabled:opacity-40 hover:bg-slate-800"
              >
                Previous
              </button>

              <span className="px-3 py-2 text-xs text-slate-400">
                {chunkPage} / {totalPages}
              </span>

              <button
                disabled={chunkPage >= totalPages || chunkLoading}
                onClick={() => loadChunks(document, chunkPage + 1)}
                className="px-3 py-2 text-xs rounded-lg border border-slate-700 disabled:opacity-40 hover:bg-slate-800"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>
    );
  }

  // =====================================================
  // MAIN KNOWLEDGE BASE VIEW
  // =====================================================

  return (
    <div className="space-y-7">
      {/* PAGE HEADER */}

      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="text-xs text-slate-500 mb-2">
            Workspace / Knowledge Base
          </div>

          <h1 className="text-2xl font-bold">Knowledge Base</h1>

          <p className="text-sm text-slate-500 mt-1">
            Explore the trusted cybersecurity documents powering CyberSafe.
          </p>
        </div>

        <div className="flex items-center gap-2 rounded-xl border border-emerald-400/20 bg-emerald-400/5 px-3 py-2">
          <span className="w-2 h-2 rounded-full bg-emerald-400" />
          <span className="text-xs text-emerald-300">
            Knowledge base indexed
          </span>
        </div>
      </div>

      {/* STATISTICS */}

      <div className="grid grid-cols-2 xl:grid-cols-4 gap-4">
        {[
          {
            label: "Knowledge documents",
            value: stats?.total_documents ?? "—",
            icon: Database,
            color: "text-cyan-400",
          },
          {
            label: "Fixed-size chunks",
            value: stats?.fixed_chunks ?? "—",
            icon: Layers,
            color: "text-violet-400",
          },
          {
            label: "Recursive chunks",
            value: stats?.recursive_chunks ?? "—",
            icon: FileText,
            color: "text-amber-400",
          },
          {
            label: "Trusted issuers",
            value: stats?.issuers.length ?? "—",
            icon: Shield,
            color: "text-emerald-400",
          },
        ].map((item) => {
          const Icon = item.icon;

          return (
            <div
              key={item.label}
              className="rounded-2xl border border-slate-800 bg-[#101a2c] p-5"
            >
              <div className="flex items-center justify-between mb-4">
                <p className="text-xs text-slate-500">{item.label}</p>

                <Icon size={20} className={item.color} />
              </div>

              <p className="text-2xl font-bold">{item.value}</p>
            </div>
          );
        })}
      </div>

      {/* SEARCH AND FILTERS */}

      <section className="rounded-2xl border border-slate-800 bg-[#101a2c] p-5">
        <div className="flex items-center gap-2 mb-4">
          <Filter size={17} className="text-cyan-400" />
          <h3 className="font-semibold text-sm">Find documents</h3>
        </div>

        <div className="grid md:grid-cols-[minmax(0,1fr)_190px_190px] gap-3">
          <div className="relative">
            <Search
              size={17}
              className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500"
            />

            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search by document, issuer or category..."
              className="w-full bg-slate-900 border border-slate-800 rounded-xl pl-11 pr-4 py-3 text-sm outline-none focus:border-cyan-400/50 placeholder:text-slate-600"
            />

            {search && (
              <button
                onClick={() => setSearch("")}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-white"
              >
                <X size={16} />
              </button>
            )}
          </div>

          <select
            value={issuer}
            onChange={(e) => setIssuer(e.target.value)}
            className="bg-slate-900 border border-slate-800 rounded-xl px-4 py-3 text-sm outline-none focus:border-cyan-400/50"
          >
            <option value="all">All issuers</option>
            <option value="CERT-In">CERT-In</option>
            <option value="NIST">NIST</option>
            <option value="OWASP">OWASP</option>
          </select>

          <select
            value={strategy}
            onChange={(e) => setStrategy(e.target.value as Strategy)}
            className="bg-slate-900 border border-slate-800 rounded-xl px-4 py-3 text-sm outline-none focus:border-cyan-400/50"
          >
            <option value="fixed">Fixed-size chunks</option>
            <option value="recursive">Recursive chunks</option>
          </select>
        </div>
      </section>

      {/* DOCUMENT LIST */}

      <div>
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="font-semibold">Indexed documents</h2>

            <p className="text-xs text-slate-500 mt-1">
              {documents.length} documents found
            </p>
          </div>

          <span className="text-xs text-slate-500 capitalize">
            {strategy} strategy
          </span>
        </div>

        {error && (
          <div className="rounded-xl border border-red-400/20 bg-red-400/5 p-4 text-sm text-red-300 mb-4">
            {error}
          </div>
        )}

        {loading ? (
          <div className="flex items-center justify-center py-20 text-slate-400 gap-3">
            <LoaderCircle className="animate-spin text-cyan-400" />
            Loading knowledge base...
          </div>
        ) : documents.length === 0 ? (
          <div className="rounded-2xl border border-slate-800 bg-[#101a2c] py-16 text-center">
            <Search size={28} className="mx-auto text-slate-600 mb-3" />

            <p className="font-semibold">No documents found</p>

            <p className="text-sm text-slate-500 mt-1">
              Try a different search term or issuer.
            </p>
          </div>
        ) : (
          <div className="grid lg:grid-cols-2 gap-4">
            {documents.map((document) => (
              <button
                key={document.source_id}
                onClick={() => openDocument(document)}
                className="group text-left rounded-2xl border border-slate-800 bg-[#101a2c] p-5 hover:border-cyan-400/40 hover:bg-[#132139] transition"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex gap-3 min-w-0">
                    <div className="w-11 h-11 shrink-0 rounded-xl bg-cyan-400/10 flex items-center justify-center">
                      <FileText size={21} className="text-cyan-400" />
                    </div>

                    <div className="min-w-0">
                      <h3 className="font-semibold text-sm leading-5 group-hover:text-cyan-300 transition">
                        {document.title}
                      </h3>

                      <p className="text-xs text-slate-500 mt-1">
                        {document.issuer} · {document.source_id}
                      </p>
                    </div>
                  </div>

                  <ChevronRight
                    size={19}
                    className="text-slate-600 group-hover:text-cyan-400 shrink-0"
                  />
                </div>

                <div className="flex flex-wrap gap-2 mt-5">
                  <span
                    className={`text-[11px] rounded-full px-2.5 py-1 border ${
                      issuerColors[document.issuer] ||
                      "text-slate-300 bg-slate-800 border-slate-700"
                    }`}
                  >
                    {document.issuer}
                  </span>

                  <span className="text-[11px] rounded-full px-2.5 py-1 bg-slate-800 text-slate-300 capitalize">
                    {formatCategory(document.category)}
                  </span>

                  <span className="text-[11px] rounded-full px-2.5 py-1 bg-slate-800 text-slate-300">
                    {document.audience.replaceAll("_", " ")}
                  </span>
                </div>

                <div className="grid grid-cols-3 gap-3 mt-5 pt-4 border-t border-slate-800">
                  <div>
                    <p className="text-lg font-bold">{document.total_chunks}</p>
                    <p className="text-[11px] text-slate-500">Chunks</p>
                  </div>

                  <div>
                    <p className="text-lg font-bold">{document.total_pages}</p>
                    <p className="text-[11px] text-slate-500">Indexed pages</p>
                  </div>

                  <div>
                    <p className="text-lg font-bold">
                      {document.total_tokens.toLocaleString()}
                    </p>
                    <p className="text-[11px] text-slate-500">Tokens</p>
                  </div>
                </div>

                <div className="flex items-center justify-between mt-4 text-xs text-slate-500">
                  <span className="flex items-center gap-1.5">
                    <Globe size={13} />
                    {document.jurisdiction}
                  </span>

                  <span className="flex items-center gap-1.5">
                    <CalendarDays size={13} />
                    {document.publication_date || "Date not specified"}
                  </span>
                </div>
              </button>
            ))}
          </div>
        )}
      </div>

      <div className="rounded-xl border border-cyan-400/15 bg-cyan-400/5 p-4 flex gap-3">
        <BookOpen size={19} className="text-cyan-400 shrink-0" />
        <p className="text-xs text-slate-400 leading-relaxed">
          CyberSafe retrieves information from indexed cybersecurity reference
          documents. Select any document to inspect the exact chunks available
          to the retrieval system.
        </p>
      </div>
    </div>
  );
}

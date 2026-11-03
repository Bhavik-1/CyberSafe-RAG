import { useState } from "react";
import ReactMarkdown from "react-markdown";

import {
  Shield,
  Send,
  Plus,
  Trash2,
  Mail,
  Lock,
  Bug,
  ShieldAlert,
  BookOpen,
  FileText,
  ChevronDown,
  ChevronRight,
  Sparkles,
  LoaderCircle,
  Clock,
  AlertCircle,
} from "lucide-react";
import remarkBreaks from "remark-breaks";
const API_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

const suggestions = [
  {
    title: "Phishing attacks",
    description: "Identify suspicious emails and links",
    icon: Mail,
    question: "What should I do if I receive a phishing email?",
  },
  {
    title: "Account security",
    description: "Protect accounts with passwords and MFA",
    icon: Lock,
    question: "How can I protect my accounts using MFA?",
  },
  {
    title: "Malware",
    description: "Understand malware and cyber threats",
    icon: Bug,
    question: "What are common signs of malware infection?",
  },
  {
    title: "Incident response",
    description: "Understand cybersecurity incident response",
    icon: ShieldAlert,
    question: "What are the main steps in incident response?",
  },
];

type Evidence = {
  number: number;
  title: string;
  issuer: string;
  page: string;
  score: number;
  text: string;
};

type CitationValidation = {
  valid?: boolean;
  citation_count?: number;
  valid_citation_count?: number;
  errors?: string[];
};

type ClaimItem = Record<string, unknown>;

type ClaimVerification = {
  status?: string;
  claim_count?: number;
  claims?: ClaimItem[];
  [key: string]: unknown;
};

type Message = {
  role: "user" | "assistant";
  content: string;
  latency?: number;
  citationValidation?: CitationValidation;
  claimVerification?: ClaimVerification;
};

export default function Assistant() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [question, setQuestion] = useState("");
  const [evidence, setEvidence] = useState<Evidence[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [expandedEvidence, setExpandedEvidence] = useState<number[]>([]);
  const [, setStreamStatus] = useState("Retrieving evidence...");
  // =====================================================
  // SEND MESSAGE TO FASTAPI
  // =====================================================

  const sendMessage = async (text?: string) => {
    const userQuestion = (text ?? question).trim();

    if (!userQuestion || loading) return;

    setQuestion("");
    setError("");
    setEvidence([]);
    setExpandedEvidence([]);

    // Add the user message and an empty assistant message. The assistant
    // message is updated as Gemini sends text deltas.
    setMessages((previous) => [
      ...previous,
      { role: "user", content: userQuestion },
      { role: "assistant", content: "" },
    ]);

    setLoading(true);

    const updateAssistantMessage = (updater: (current: Message) => Message) => {
      setMessages((previous) => {
        if (previous.length === 0) return previous;
        const next = [...previous];
        const last = next[next.length - 1];
        if (last.role === "assistant") {
          next[next.length - 1] = updater(last);
        }
        return next;
      });
    };

    try {
      const response = await fetch(`${API_URL}/api/chat/stream`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "text/event-stream",
        },
        body: JSON.stringify({ message: userQuestion }),
      });

      if (!response.ok) {
        let detail = "The server could not process your question.";
        try {
          const errorData = await response.json();
          detail = errorData.detail || detail;
        } catch {
          // Keep the default error message.
        }
        throw new Error(detail);
      }

      if (!response.body) {
        throw new Error("Streaming is not supported by this browser response.");
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let streamError = "";

      const handleEvent = (rawEvent: string) => {
        const lines = rawEvent.split(/\r?\n/);
        let eventName = "message";
        const dataLines: string[] = [];

        for (const line of lines) {
          if (line.startsWith("event:")) {
            eventName = line.slice(6).trim();
          } else if (line.startsWith("data:")) {
            dataLines.push(line.slice(5).trim());
          }
        }

        if (dataLines.length === 0) return;

        const payload = JSON.parse(dataLines.join("\n"));

        if (eventName === "meta") {
          setEvidence(payload.evidence || []);
        } else if (eventName === "token") {
          updateAssistantMessage((current) => ({
            ...current,
            content: current.content + (payload.text || ""),
          }));
        } else if (eventName === "replace") {
          updateAssistantMessage((current) => ({
            ...current,
            content: payload.text || "",
          }));
        } else if (eventName === "complete") {
          updateAssistantMessage((current) => ({
            ...current,
            latency: Number(payload.latency || 0),
            citationValidation: payload.citation_validation || undefined,
            claimVerification: payload.claim_verification || undefined,
          }));
        } else if (eventName === "status") {
          setStreamStatus(payload.text || "Generating answer...");
        } else if (eventName === "error") {
          streamError = payload.message || "The streaming request failed.";
        }
      };

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        buffer = buffer.replace(/\r\n/g, "\n");

        let boundary = buffer.indexOf("\n\n");
        while (boundary !== -1) {
          const rawEvent = buffer.slice(0, boundary);
          buffer = buffer.slice(boundary + 2);
          if (rawEvent.trim()) handleEvent(rawEvent);
          boundary = buffer.indexOf("\n\n");
        }
      }

      buffer += decoder.decode();
      if (buffer.trim()) handleEvent(buffer);

      if (streamError) {
        throw new Error(streamError);
      }
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Something went wrong.";

      setError(message);
      updateAssistantMessage((current) => ({
        ...current,
        content: current.content || "I couldn't complete that request.",
      }));
    } finally {
      setLoading(false);
    }
  };

  // =====================================================
  // CLEAR CHAT
  // =====================================================

  const clearChat = () => {
    if (loading) return;

    setMessages([]);
    setEvidence([]);
    setError("");
    setQuestion("");
    setExpandedEvidence([]);
  };

  // =====================================================
  // EXPAND / COLLAPSE EVIDENCE
  // =====================================================

  const toggleEvidence = (index: number) => {
    setExpandedEvidence((previous) =>
      previous.includes(index)
        ? previous.filter((item) => item !== index)
        : [...previous, index],
    );
  };

  // =====================================================
  // RENDER
  // =====================================================

  return (
    <div className="h-full min-h-[calc(100vh-80px)] flex flex-col">
      {/* HEADER */}

      <div className="flex flex-wrap items-center justify-between gap-4 mb-7">
        <div>
          <h1 className="text-2xl font-bold">AI Assistant</h1>

          <p className="text-sm text-slate-500 mt-1">
            Evidence-grounded cybersecurity guidance
          </p>
        </div>

        <button
          onClick={clearChat}
          disabled={loading || messages.length === 0}
          className="flex items-center gap-2 px-4 py-2.5 rounded-xl border border-slate-700 text-sm text-slate-300 hover:bg-slate-800 disabled:opacity-40 disabled:cursor-not-allowed transition"
        >
          <Trash2 size={16} />
          Clear conversation
        </button>
      </div>

      {/* MAIN WORKSPACE */}

      <div className="flex-1 grid grid-cols-1 xl:grid-cols-[minmax(0,1fr)_340px] gap-5">
        {/* CHAT AREA */}

        <section className="rounded-2xl border border-slate-800 bg-[#101a2c] flex flex-col min-h-[650px] overflow-hidden">
          {/* CHAT HEADER */}

          <div className="flex items-center justify-between px-5 py-4 border-b border-slate-800">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-xl bg-cyan-400/10">
                <Shield className="text-cyan-400" size={21} />
              </div>

              <div>
                <p className="font-semibold text-sm">CyberSafe Assistant</p>

                <p className="text-xs text-emerald-400 mt-1">
                  ●{" "}
                  {loading ? "Processing your question..." : "Ready to assist"}
                </p>
              </div>
            </div>

            <span className="text-xs text-slate-500">Gemini powered</span>
          </div>

          {/* MESSAGES */}

          <div className="flex-1 overflow-y-auto p-5">
            {messages.length === 0 && !loading ? (
              <div className="max-w-2xl mx-auto py-8">
                <div className="w-14 h-14 rounded-2xl bg-cyan-400/10 flex items-center justify-center mx-auto mb-5">
                  <Sparkles className="text-cyan-400" size={28} />
                </div>

                <h2 className="text-2xl font-bold text-center mb-3">
                  How can I help you stay safe online?
                </h2>

                <p className="text-sm text-slate-400 text-center mb-9">
                  Ask a question about cybersecurity. I'll retrieve relevant
                  evidence from trusted sources.
                </p>

                <div className="grid sm:grid-cols-2 gap-3">
                  {suggestions.map((item) => {
                    const Icon = item.icon;

                    return (
                      <button
                        key={item.title}
                        onClick={() => sendMessage(item.question)}
                        disabled={loading}
                        className="text-left rounded-xl border border-slate-800 bg-slate-900/70 p-4 hover:border-cyan-400/40 hover:bg-cyan-400/5 transition"
                      >
                        <Icon className="text-cyan-400 mb-3" size={21} />

                        <p className="text-sm font-semibold mb-1">
                          {item.title}
                        </p>

                        <p className="text-xs text-slate-500">
                          {item.description}
                        </p>
                      </button>
                    );
                  })}
                </div>
              </div>
            ) : (
              <div className="space-y-6">
                {messages.map((message, index) => (
                  <div
                    key={index}
                    className={`flex gap-3 ${
                      message.role === "user" ? "justify-end" : "justify-start"
                    }`}
                  >
                    {message.role === "assistant" && (
                      <div className="w-9 h-9 shrink-0 rounded-xl bg-cyan-400/10 flex items-center justify-center">
                        <Shield size={19} className="text-cyan-400" />
                      </div>
                    )}

                    <div
                      className={`max-w-[90%] min-w-0 rounded-2xl p-4 ${
                        message.role === "user"
                          ? "bg-cyan-400/10 border border-cyan-400/20"
                          : "bg-slate-900 border border-slate-800"
                      }`}
                    >
                      {message.role === "assistant" ? (
                        <>
                          <div className="rounded-xl bg-[#0b1424] border border-slate-800 p-5 sm:p-6">
                            <div
                              className="
      prose prose-invert max-w-none
      prose-p:text-slate-200
      prose-p:leading-8
      prose-p:my-3
      prose-strong:text-cyan-300
      prose-ul:my-4
      prose-ul:space-y-3
      prose-li:text-slate-200
      prose-li:leading-7
      prose-li:marker:text-cyan-400
      prose-headings:text-cyan-300
      prose-headings:font-semibold
      prose-hr:border-slate-700
      text-[14px] sm:text-[15px]
    "
                            >
                              <ReactMarkdown remarkPlugins={[remarkBreaks]}>
                                {message.content}
                              </ReactMarkdown>
                            </div>
                          </div>

                          {message.citationValidation && (
                            <div
                              className={`mt-4 rounded-xl border p-3 text-xs ${
                                message.citationValidation.valid
                                  ? "border-emerald-400/20 bg-emerald-400/5 text-emerald-300"
                                  : "border-amber-400/20 bg-amber-400/5 text-amber-300"
                              }`}
                            >
                              <div className="flex items-center gap-2 font-semibold">
                                {message.citationValidation.valid ? (
                                  <Shield size={15} />
                                ) : (
                                  <AlertCircle size={15} />
                                )}
                                {message.citationValidation.valid
                                  ? "Citation structure valid"
                                  : "Citation issues found"}
                              </div>
                              <p className="mt-1 text-slate-400">
                                {message.citationValidation
                                  .valid_citation_count ?? 0}{" "}
                                of{" "}
                                {message.citationValidation.citation_count ?? 0}{" "}
                                citations passed structural checks.
                              </p>
                              {!!message.citationValidation.errors?.length && (
                                <ul className="mt-2 list-disc pl-5 space-y-1 text-amber-200">
                                  {message.citationValidation.errors.map(
                                    (item, errorIndex) => (
                                      <li key={errorIndex}>{item}</li>
                                    ),
                                  )}
                                </ul>
                              )}
                              <p className="mt-2 text-slate-500">
                                This checks citation references and source
                                metadata, not whether the cited text fully
                                supports each claim.
                              </p>
                            </div>
                          )}

                          {message.claimVerification && (
                            <div className="mt-4 rounded-xl border border-slate-700 bg-slate-800/40 p-3 text-xs">
                              <div className="flex items-center justify-between gap-3">
                                <div className="flex items-center gap-2 font-semibold text-slate-200">
                                  <Shield size={15} className="text-cyan-400" />
                                  Claim-level verification
                                </div>
                                <span
                                  className={`rounded-full px-2 py-1 text-[10px] font-semibold ${
                                    message.claimVerification.status ===
                                    "completed"
                                      ? "bg-emerald-400/10 text-emerald-300"
                                      : "bg-amber-400/10 text-amber-300"
                                  }`}
                                >
                                  {message.claimVerification.status ||
                                    "Available"}
                                </span>
                              </div>

                              <p className="mt-2 text-slate-400">
                                {typeof message.claimVerification
                                  .claim_count === "number"
                                  ? `${message.claimVerification.claim_count} claims checked against retrieved evidence.`
                                  : `${message.claimVerification.claims?.length ?? 0} claims checked against retrieved evidence.`}
                              </p>

                              {Array.isArray(
                                message.claimVerification.claims,
                              ) &&
                                message.claimVerification.claims.length > 0 && (
                                  <div className="mt-3 space-y-2">
                                    {message.claimVerification.claims.map(
                                      (claim, claimIndex) => {
                                        const claimStatus = String(
                                          claim.status ??
                                            claim.classification ??
                                            claim.support_status ??
                                            "Unclassified",
                                        );
                                        const claimText = String(
                                          claim.claim ??
                                            claim.text ??
                                            claim.original_sentence ??
                                            "Claim details unavailable.",
                                        );
                                        const normalizedStatus =
                                          claimStatus.toLowerCase();
                                        const statusStyle =
                                          normalizedStatus.includes(
                                            "support",
                                          ) &&
                                          !normalizedStatus.includes("partial")
                                            ? "text-emerald-300"
                                            : normalizedStatus.includes(
                                                  "partial",
                                                )
                                              ? "text-amber-300"
                                              : normalizedStatus.includes(
                                                    "unsupported",
                                                  ) ||
                                                  normalizedStatus.includes(
                                                    "missing",
                                                  )
                                                ? "text-rose-300"
                                                : "text-slate-300";

                                        return (
                                          <div
                                            key={claimIndex}
                                            className="rounded-lg border border-slate-700/70 bg-slate-900/60 p-2.5"
                                          >
                                            <div className="mb-1 flex items-center justify-between gap-2">
                                              <span className="text-slate-500">
                                                Claim {claimIndex + 1}
                                              </span>
                                              <span
                                                className={`font-semibold ${statusStyle}`}
                                              >
                                                {claimStatus.replaceAll(
                                                  "_",
                                                  " ",
                                                )}
                                              </span>
                                            </div>
                                            <p className="leading-relaxed text-slate-300">
                                              {claimText}
                                            </p>
                                          </div>
                                        );
                                      },
                                    )}
                                  </div>
                                )}

                              <p className="mt-3 text-slate-500">
                                LLM-assisted assessment of whether answer claims
                                are supported by the retrieved evidence; it is
                                not a guarantee of factual correctness.
                              </p>
                            </div>
                          )}

                          {message.latency !== undefined && (
                            <div className="flex items-center gap-2 mt-5 pt-3 border-t border-slate-800 text-xs text-slate-500">
                              <Clock size={13} />
                              Generation latency: {message.latency.toFixed(
                                2,
                              )}{" "}
                              seconds
                            </div>
                          )}
                        </>
                      ) : (
                        <p className="text-sm leading-relaxed whitespace-pre-wrap">
                          {message.content}
                        </p>
                      )}
                    </div>
                  </div>
                ))}

                {/* LOADING INDICATOR */}

                {loading && (
                  <div className="flex gap-3">
                    <div className="w-9 h-9 shrink-0 rounded-xl bg-cyan-400/10 flex items-center justify-center">
                      <Shield size={19} className="text-cyan-400" />
                    </div>

                    <div className="rounded-2xl bg-slate-900 border border-slate-800 p-4">
                      <div className="flex items-center gap-3 text-sm text-slate-300">
                        <LoaderCircle
                          className="animate-spin text-cyan-400"
                          size={18}
                        />
                        Retrieving evidence and streaming your answer...
                      </div>

                      <p className="text-xs text-slate-500 mt-2">
                        Evidence will appear first, followed by the answer as
                        Gemini generates it.
                      </p>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* ERROR */}

            {error && (
              <div className="mt-5 rounded-xl border border-red-400/20 bg-red-400/5 p-4">
                <div className="flex items-center gap-2 text-red-300 font-semibold text-sm mb-2">
                  <AlertCircle size={17} />
                  Request failed
                </div>

                <p className="text-sm text-slate-400">{error}</p>

                <p className="text-xs text-slate-500 mt-2">
                  Check that your FastAPI server is running and try again.
                </p>
              </div>
            )}
          </div>

          {/* INPUT */}

          <div className="border-t border-slate-800 p-4">
            <form
              onSubmit={(event) => {
                event.preventDefault();
                sendMessage();
              }}
              className="flex items-end gap-3"
            >
              <div className="flex-1 relative">
                <textarea
                  value={question}
                  onChange={(event) => setQuestion(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" && !event.shiftKey) {
                      event.preventDefault();
                      sendMessage();
                    }
                  }}
                  placeholder="Ask about phishing, malware, passwords..."
                  rows={2}
                  disabled={loading}
                  className="w-full resize-none rounded-xl bg-[#17263d] border border-slate-700 p-4 pr-12 text-sm text-white placeholder:text-slate-500 outline-none focus:border-cyan-400/50 transition disabled:opacity-60"
                />

                <button
                  type="button"
                  onClick={() => setQuestion("")}
                  disabled={loading}
                  className="absolute right-3 top-3 text-slate-500 hover:text-white disabled:opacity-40"
                  title="Clear input"
                >
                  <Plus size={17} className="rotate-45" />
                </button>
              </div>

              <button
                type="submit"
                disabled={!question.trim() || loading}
                className="h-12 w-12 shrink-0 rounded-xl bg-cyan-400 text-slate-950 flex items-center justify-center hover:bg-cyan-300 disabled:opacity-40 disabled:cursor-not-allowed transition"
                title="Send message"
              >
                {loading ? (
                  <LoaderCircle className="animate-spin" size={19} />
                ) : (
                  <Send size={19} />
                )}
              </button>
            </form>

            <p className="text-[11px] text-slate-600 text-center mt-3">
              CyberSafe provides evidence-grounded cybersecurity guidance.
            </p>
          </div>
        </section>

        {/* EVIDENCE SIDEBAR */}

        <aside className="rounded-2xl border border-slate-800 bg-[#101a2c] p-5 h-fit">
          <div className="flex items-center gap-2 mb-2">
            <BookOpen size={20} className="text-cyan-400" />

            <h3 className="font-semibold">Retrieved Evidence</h3>
          </div>

          <p className="text-xs text-slate-500 mb-5">
            Documents retrieved to generate the latest answer.
          </p>

          {evidence.length > 0 ? (
            <div className="space-y-3">
              {evidence.map((item) => (
                <div
                  key={item.number}
                  className="rounded-xl border border-slate-800 bg-slate-900/70 overflow-hidden"
                >
                  <button
                    onClick={() => toggleEvidence(item.number)}
                    className="w-full flex items-center gap-2 p-3 text-left hover:bg-slate-800/70 transition"
                  >
                    {expandedEvidence.includes(item.number) ? (
                      <ChevronDown
                        size={15}
                        className="text-cyan-400 shrink-0"
                      />
                    ) : (
                      <ChevronRight
                        size={15}
                        className="text-cyan-400 shrink-0"
                      />
                    )}

                    <span className="text-xs font-bold text-cyan-400">
                      {String(item.number).padStart(2, "0")}
                    </span>

                    <span className="text-xs font-semibold flex-1 min-w-0">
                      {item.title}
                    </span>
                  </button>

                  <div className="px-3 pb-3">
                    <div className="flex flex-wrap gap-2 text-[11px] text-slate-500">
                      <span>{item.issuer}</span>
                      <span>·</span>
                      <span>Page {item.page}</span>
                    </div>

                    <p className="text-[11px] text-cyan-400 mt-2">
                      Cross-encoder score: {item.score.toFixed(3)}
                    </p>

                    {expandedEvidence.includes(item.number) && (
                      <div className="mt-3 pt-3 border-t border-slate-800">
                        <p className="text-xs text-slate-300 leading-relaxed whitespace-pre-wrap">
                          {item.text}
                        </p>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="py-7 text-center">
              <FileText size={27} className="text-slate-600 mx-auto mb-3" />

              <p className="text-xs text-slate-500">
                {loading
                  ? "Retrieving relevant documents..."
                  : "Ask a question to see its retrieved evidence."}
              </p>
            </div>
          )}

          <div className="mt-6 rounded-xl bg-emerald-400/5 border border-emerald-400/15 p-4">
            <div className="flex items-center gap-2 mb-2">
              <Shield className="text-emerald-400" size={17} />

              <p className="text-xs font-semibold text-emerald-300">
                Evidence First
              </p>
            </div>

            <p className="text-xs text-slate-500 leading-relaxed">
              Answers are grounded in retrieved documents. The assistant may
              abstain when evidence is insufficient.
            </p>
          </div>
        </aside>
      </div>
    </div>
  );
}

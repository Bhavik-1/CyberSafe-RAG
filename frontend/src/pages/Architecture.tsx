import { useState } from "react";
import {
  FileText,
  FileSearch,
  Scissors,
  BrainCircuit,
  Database,
  Search,
  GitMerge,
  ArrowDown,
  Sparkles,
  ShieldCheck,
  Layers,
  Code2,
  ChevronDown,
  CheckCircle2,
  Workflow,
  Zap,
} from "lucide-react";

type Stage = {
  id: number;
  title: string;
  subtitle: string;
  technology: string[];
  description: string;
  implementation: string;
  output: string;
  icon: typeof FileText;
  color: string;
  bg: string;
};

const stages: Stage[] = [
  {
    id: 1,
    title: "Document Ingestion",
    subtitle: "Collect trusted cybersecurity sources",
    technology: ["CERT-In", "NIST", "OWASP", "PDF"],
    description:
      "Cybersecurity reference documents are collected from trusted sources. Each document is assigned source metadata such as its title, issuer, category, publication date and jurisdiction.",
    implementation:
      "Documents are organized into source-specific folders. A source manifest maintains document identity and metadata.",
    output: "PDF documents and source manifest",
    icon: FileText,
    color: "text-cyan-400",
    bg: "bg-cyan-400/10",
  },
  {
    id: 2,
    title: "Text Extraction & Cleaning",
    subtitle: "Convert documents into usable text",
    technology: ["PyMuPDF", "Python", "Unicode normalization"],
    description:
      "Text is extracted page by page from PDF documents. Cleaning removes unwanted formatting characters, normalizes whitespace and handles line-break hyphenation while preserving meaningful content.",
    implementation:
      "PyMuPDF extracts page-level text. A cleaning pipeline normalizes the extracted content and retains source and page metadata.",
    output: "Cleaned page-level text records",
    icon: FileSearch,
    color: "text-cyan-400",
    bg: "bg-cyan-400/10",
  },
  {
    id: 3,
    title: "Text Chunking",
    subtitle: "Divide documents into retrieval units",
    technology: [
      "Fixed-size",
      "Recursive",
      "180-token limit",
      "30-token overlap",
    ],
    description:
      "Long documents are divided into smaller text chunks so that relevant passages can be retrieved independently. Two chunking strategies are evaluated.",
    implementation:
      "Fixed-size chunking uses a maximum of 180 tokens and approximately 30 tokens of overlap. Recursive chunking attempts to preserve paragraph and sentence boundaries while respecting the token limit.",
    output: "430 fixed-size chunks and 465 recursive chunks",
    icon: Scissors,
    color: "text-violet-400",
    bg: "bg-violet-400/10",
  },
  {
    id: 4,
    title: "Embedding Generation",
    subtitle: "Represent text as numerical vectors",
    technology: ["Sentence Transformers", "all-MiniLM-L6-v2", "384 dimensions"],
    description:
      "Each chunk is transformed into a dense numerical representation. Similarity between a query and document chunks can then be measured in vector space.",
    implementation:
      "The all-MiniLM-L6-v2 Sentence Transformer generates 384-dimensional embeddings. Embeddings are normalized before FAISS indexing.",
    output: "Normalized 384-dimensional vectors",
    icon: BrainCircuit,
    color: "text-violet-400",
    bg: "bg-violet-400/10",
  },
  {
    id: 5,
    title: "Hybrid Retrieval",
    subtitle: "Combine semantic and keyword search",
    technology: ["FAISS", "BM25", "Dense retrieval", "Sparse retrieval"],
    description:
      "The system retrieves candidate chunks using two complementary approaches. Dense retrieval captures semantic similarity, while BM25 identifies keyword-based relevance.",
    implementation:
      "FAISS uses normalized embeddings with an inner-product index. BM25 performs lexical retrieval using tokenized chunk text. Both retrieve candidate lists for the same query.",
    output: "Dense and BM25 candidate rankings",
    icon: Database,
    color: "text-cyan-400",
    bg: "bg-cyan-400/10",
  },
  {
    id: 6,
    title: "Reciprocal Rank Fusion",
    subtitle: "Combine the retrieval rankings",
    technology: ["RRF", "Rank fusion", "K = 60"],
    description:
      "Dense and BM25 rankings are combined using Reciprocal Rank Fusion. This uses each candidate's position in the result lists rather than directly comparing incompatible raw retrieval scores.",
    implementation:
      "The fusion score is calculated as the sum of 1/(K + rank) across retrieval lists, with K = 60. The highest-ranked candidates form the hybrid result set.",
    output: "Fused hybrid candidate ranking",
    icon: GitMerge,
    color: "text-amber-400",
    bg: "bg-amber-400/10",
  },
  {
    id: 7,
    title: "Cross-Encoder Reranking",
    subtitle: "Improve the ordering of retrieved evidence",
    technology: ["Cross-Encoder", "ms-marco-MiniLM-L-6-v2"],
    description:
      "A cross-encoder evaluates each query-candidate pair jointly. It assigns a relevance score that is used to reorder the retrieved candidates.",
    implementation:
      "The top 10 hybrid candidates are scored by the cross-encoder and sorted by relevance. The top 5 chunks are selected as generation context.",
    output: "Top 5 reranked evidence chunks",
    icon: Layers,
    color: "text-amber-400",
    bg: "bg-amber-400/10",
  },
  {
    id: 8,
    title: "Answer Generation",
    subtitle: "Generate responses grounded in evidence",
    technology: [
      "Gemini API",
      "gemini-3.5-flash-lite",
      "Evidence-only prompting",
    ],
    description:
      "The selected evidence chunks are passed to Gemini with instructions to answer using the supplied material, distinguish missing information and avoid unsupported claims.",
    implementation:
      "The Gemini Interactions API receives the user question, retrieved evidence and system instructions. The generation process includes explicit abstention rules.",
    output: "Evidence-grounded generated answer",
    icon: Sparkles,
    color: "text-emerald-400",
    bg: "bg-emerald-400/10",
  },
  {
    id: 9,
    title: "Citations & Response",
    subtitle: "Present transparent and traceable answers",
    technology: ["Evidence references", "Source metadata", "Page numbers"],
    description:
      "The final answer is displayed alongside its supporting evidence. Citations identify the source and page associated with the retrieved information.",
    implementation:
      "The FastAPI backend returns the generated answer and retrieved evidence. The React interface displays expandable evidence cards with source titles, issuers and page numbers.",
    output: "Answer with evidence and source citations",
    icon: ShieldCheck,
    color: "text-emerald-400",
    bg: "bg-emerald-400/10",
  },
  {
    id: 10,
    title: "Claim-level Verification",
    subtitle: "Check individual claims against retrieved evidence",
    technology: [
      "Gemini-assisted verification",
      "Claim extraction",
      "Citation checks",
      "Human review",
    ],
    description:
      "Individual factual claims in the generated answer are assessed against the retrieved evidence. Each claim is classified as SUPPORTED, PARTIALLY_SUPPORTED, UNSUPPORTED or MISSING_CITATION.",
    implementation:
      "The backend sends the answer and retrieved chunks to a verification step. The verifier assesses claim support and checks evidence references and page numbers. This is an LLM-assisted assessment, not a guarantee of factual correctness.",
    output: "Claim-level verification results and status labels",
    icon: ShieldCheck,
    color: "text-emerald-400",
    bg: "bg-emerald-400/10",
  },
];

const evaluationMethods = [
  {
    name: "Precision@5",
    description:
      "Measures the proportion of the top five retrieved chunks that are relevant.",
  },
  {
    name: "Recall@5",
    description:
      "Measures how many of the known relevant chunks appear in the top five.",
  },
  {
    name: "MRR",
    description: "Measures how highly the first relevant result is ranked.",
  },
  {
    name: "NDCG@5",
    description:
      "Measures the quality of the ranking while accounting for result positions.",
  },
];

function StageCard({
  stage,
  expanded,
  onClick,
}: {
  stage: Stage;
  expanded: boolean;
  onClick: () => void;
}) {
  const Icon = stage.icon;

  return (
    <div className="overflow-hidden rounded-2xl border border-slate-800 bg-[#101a2c] transition hover:border-slate-700">
      <button
        onClick={onClick}
        aria-expanded={expanded}
        className="flex w-full items-center gap-4 p-4 text-left md:p-5"
      >
        <div
          className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-xl ${stage.bg} ${stage.color}`}
        >
          <Icon size={23} />
        </div>

        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs font-semibold text-slate-500">
              STEP {String(stage.id).padStart(2, "0")}
            </span>
            <h3 className="font-semibold text-white">{stage.title}</h3>
          </div>
          <p className="mt-1 text-sm text-slate-400">{stage.subtitle}</p>
        </div>

        <ChevronDown
          size={19}
          className={`shrink-0 text-slate-500 transition-transform ${expanded ? "rotate-180" : ""}`}
        />
      </button>

      {expanded && (
        <div className="border-t border-slate-800 px-5 pb-5 pt-4 md:pl-[84px]">
          <p className="text-sm leading-7 text-slate-300">
            {stage.description}
          </p>

          <div className="mt-5">
            <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-500">
              Technologies and components
            </p>
            <div className="flex flex-wrap gap-2">
              {stage.technology.map((technology) => (
                <span
                  key={technology}
                  className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-1.5 text-xs text-slate-300"
                >
                  {technology}
                </span>
              ))}
            </div>
          </div>

          <div className="mt-5 grid gap-3 md:grid-cols-2">
            <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
              <div className="mb-2 flex items-center gap-2 text-xs font-semibold text-cyan-400">
                <Code2 size={15} />
                Implementation
              </div>
              <p className="text-xs leading-6 text-slate-400">
                {stage.implementation}
              </p>
            </div>

            <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
              <div className="mb-2 flex items-center gap-2 text-xs font-semibold text-emerald-400">
                <CheckCircle2 size={15} />
                Output
              </div>
              <p className="text-xs leading-6 text-slate-300">{stage.output}</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function Architecture() {
  const [expandedStage, setExpandedStage] = useState<number | null>(1);

  return (
    <div className="mx-auto max-w-[1500px] space-y-8 p-5 text-slate-100 md:p-8">
      {/* Header */}
      <section className="flex flex-col justify-between gap-4 md:flex-row md:items-center">
        <div>
          <div className="mb-2 flex items-center gap-2 text-xs font-medium uppercase tracking-[0.18em] text-cyan-400">
            <Workflow size={15} />
            System methodology
          </div>
          <h1 className="text-3xl font-bold tracking-tight text-white">
            RAG Architecture
          </h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-400">
            Explore how CyberSafe transforms trusted cybersecurity documents
            into evidence-grounded AI responses through hybrid retrieval and
            reranking.
          </p>
        </div>

        <div className="inline-flex items-center gap-2 self-start rounded-xl border border-emerald-400/20 bg-emerald-400/10 px-3 py-2 text-xs font-medium text-emerald-300">
          <CheckCircle2 size={15} />
          Pipeline implemented
        </div>
      </section>

      {/* Architecture summary */}
      <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {[
          {
            label: "Knowledge documents",
            value: "8",
            detail: "CERT-In, NIST and OWASP",
            icon: FileText,
            color: "text-cyan-400",
          },
          {
            label: "Chunk records",
            value: "895",
            detail: "430 fixed + 465 recursive",
            icon: Scissors,
            color: "text-violet-400",
          },
          {
            label: "Embedding dimensions",
            value: "384",
            detail: "all-MiniLM-L6-v2",
            icon: BrainCircuit,
            color: "text-amber-400",
          },
          {
            label: "Generation model",
            value: "Gemini",
            detail: "gemini-3.5-flash-lite",
            icon: Sparkles,
            color: "text-emerald-400",
          },
        ].map((item) => {
          const Icon = item.icon;
          return (
            <div
              key={item.label}
              className="rounded-2xl border border-slate-800 bg-[#101a2c] p-5"
            >
              <div className="mb-4 flex items-center justify-between">
                <p className="text-sm text-slate-400">{item.label}</p>
                <Icon size={20} className={item.color} />
              </div>
              <h3 className="text-3xl font-bold text-white">{item.value}</h3>
              <p className="mt-2 text-xs text-slate-500">{item.detail}</p>
            </div>
          );
        })}
      </section>

      {/* Main pipeline */}
      <section>
        <div className="mb-5">
          <h2 className="text-xl font-semibold text-white">
            End-to-end RAG pipeline
          </h2>
          <p className="mt-1 text-sm text-slate-500">
            Select any stage to explore its implementation and output.
          </p>
        </div>

        <div className="space-y-2">
          {stages.map((stage, index) => (
            <div key={stage.id}>
              <StageCard
                stage={stage}
                expanded={expandedStage === stage.id}
                onClick={() =>
                  setExpandedStage(expandedStage === stage.id ? null : stage.id)
                }
              />
              {index !== stages.length - 1 && (
                <div className="flex justify-center py-2">
                  <ArrowDown size={19} className="text-slate-600" />
                </div>
              )}
            </div>
          ))}
        </div>
      </section>

      {/* Hybrid retrieval explanation */}
      <section>
        <div className="mb-5">
          <h2 className="text-xl font-semibold text-white">
            Why hybrid retrieval?
          </h2>
          <p className="mt-1 text-sm text-slate-500">
            Two retrieval techniques complement each other.
          </p>
        </div>

        <div className="grid gap-4 md:grid-cols-2">
          <div className="rounded-2xl border border-cyan-400/15 bg-[#101a2c] p-6">
            <div className="mb-4 flex h-11 w-11 items-center justify-center rounded-xl bg-cyan-400/10 text-cyan-400">
              <BrainCircuit size={23} />
            </div>
            <h3 className="text-lg font-semibold text-white">
              Dense retrieval
            </h3>
            <p className="mt-2 text-sm leading-6 text-slate-400">
              Uses semantic embeddings to find passages with similar meaning,
              even when the query and document use different words.
            </p>
            <div className="mt-4 rounded-xl bg-slate-900/70 p-3 text-xs text-cyan-300">
              Technology: Sentence Transformers + FAISS
            </div>
          </div>

          <div className="rounded-2xl border border-amber-400/15 bg-[#101a2c] p-6">
            <div className="mb-4 flex h-11 w-11 items-center justify-center rounded-xl bg-amber-400/10 text-amber-400">
              <Search size={23} />
            </div>
            <h3 className="text-lg font-semibold text-white">
              Sparse retrieval
            </h3>
            <p className="mt-2 text-sm leading-6 text-slate-400">
              Uses keyword matching and term importance to find passages
              containing relevant words and technical terminology.
            </p>
            <div className="mt-4 rounded-xl bg-slate-900/70 p-3 text-xs text-amber-300">
              Technology: BM25
            </div>
          </div>
        </div>

        <div className="mt-4 rounded-2xl border border-violet-400/15 bg-violet-400/[0.04] p-5">
          <div className="flex items-center gap-3">
            <GitMerge size={23} className="text-violet-400" />
            <h3 className="font-semibold text-white">Reciprocal Rank Fusion</h3>
          </div>
          <p className="mt-3 text-sm leading-6 text-slate-400">
            RRF combines the ranked outputs of dense and BM25 retrieval. It uses
            ranking positions instead of comparing raw scores from different
            retrieval systems.
          </p>
          <div className="mt-4 overflow-x-auto rounded-xl bg-slate-950/70 p-4 text-center">
            <code className="whitespace-nowrap text-sm text-violet-300">
              RRF(d) = Σ 1 / (K + rank(d))
            </code>
            <p className="mt-2 text-xs text-slate-500">
              K = 60 in the current implementation
            </p>
          </div>
        </div>
      </section>

      {/* Reranking */}
      <section className="rounded-2xl border border-amber-400/15 bg-[#101a2c] p-6">
        <div className="flex items-start gap-4">
          <div className="rounded-xl bg-amber-400/10 p-3 text-amber-400">
            <Zap size={23} />
          </div>
          <div>
            <h2 className="text-lg font-semibold text-white">
              Cross-Encoder Reranking
            </h2>
            <p className="mt-2 text-sm leading-6 text-slate-400">
              After hybrid retrieval produces its candidate set, a cross-encoder
              jointly processes the query and each candidate passage. It
              provides a more focused relevance ranking before generation.
            </p>
            <div className="mt-4 flex flex-wrap gap-2">
              {[
                "Top 10 hybrid candidates",
                "Cross-encoder scoring",
                "Top 5 context chunks",
              ].map((item) => (
                <span
                  key={item}
                  className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-slate-300"
                >
                  {item}
                </span>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Generation and safety */}
      <section className="grid gap-4 lg:grid-cols-2">
        <div className="rounded-2xl border border-emerald-400/15 bg-[#101a2c] p-6">
          <div className="mb-4 flex items-center gap-3">
            <Sparkles size={22} className="text-emerald-400" />
            <h3 className="font-semibold text-white">
              Evidence-grounded generation
            </h3>
          </div>
          <p className="text-sm leading-6 text-slate-400">
            Gemini receives the question and selected evidence chunks. Its
            instructions prioritize source-grounded answers, appropriate
            citations and explicit acknowledgement of missing information.
          </p>
        </div>

        <div className="rounded-2xl border border-emerald-400/15 bg-[#101a2c] p-6">
          <div className="mb-4 flex items-center gap-3">
            <ShieldCheck size={22} className="text-emerald-400" />
            <h3 className="font-semibold text-white">Safety and abstention</h3>
          </div>
          <p className="text-sm leading-6 text-slate-400">
            The assistant must not invent platform-specific recovery steps,
            contact details or procedures. When retrieved evidence is
            insufficient, it should say so rather than present guesses as facts.
          </p>
        </div>
      </section>

      {/* Evaluation methodology */}
      <section>
        <div className="mb-5">
          <h2 className="text-xl font-semibold text-white">
            How the pipeline is evaluated
          </h2>
          <p className="mt-1 text-sm text-slate-500">
            Retrieval quality and generated-answer quality are assessed
            separately.
          </p>
        </div>

        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          {evaluationMethods.map((method) => (
            <div
              key={method.name}
              className="rounded-xl border border-slate-800 bg-[#101a2c] p-4"
            >
              <h3 className="font-semibold text-cyan-300">{method.name}</h3>
              <p className="mt-2 text-xs leading-6 text-slate-400">
                {method.description}
              </p>
            </div>
          ))}
        </div>

        <div className="mt-4 rounded-xl border border-slate-800 bg-slate-900/60 p-4">
          <p className="text-sm leading-6 text-slate-400">
            Answer evaluation additionally checks expected-point coverage,
            citation reference validity, abstention behaviour, generation
            latency and manual ratings for factual correctness, faithfulness,
            citation support, relevance and clarity.
          </p>
        </div>
      </section>

      <footer className="border-t border-slate-800 pt-5 text-xs text-slate-600">
        CyberSafe RAG · Architecture and methodology
      </footer>
    </div>
  );
}

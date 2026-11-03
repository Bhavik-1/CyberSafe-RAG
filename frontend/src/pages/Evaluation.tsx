import { useEffect, useMemo, useState } from "react";
import {
  Activity,
  Award,
  BarChart3,
  CheckCircle2,
  ChevronDown,
  Clock3,
  FileCheck2,
  Info,
  ShieldCheck,
  Target,
  TrendingUp,
} from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  PolarAngleAxis,
  PolarGrid,
  Radar,
  RadarChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

const API_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

type RetrievalRow = {
  strategy: string;
  method: string;
  query_count: number;
  precision_at_5: number;
  recall_at_5: number;
  mrr: number;
  ndcg_at_5: number;
};

type RetrievalDetail = {
  query: string;
  strategy: string;
  method: string;
  relevant_chunk_count: number;
  retrieved_chunk_count: number;
  precision_at_5: number;
  recall_at_5: number;
  mrr: number;
  ndcg_at_5: number;
};

type AnswerQuestion = {
  query: string;
  point_coverage: number;
  covered_points: number;
  total_points: number;
  citation_accuracy: number;
  valid_citations: number;
  invalid_citations: number;
  total_citations: number;
  expected_abstention: boolean;
  detected_abstention: boolean;
  abstention_correct: boolean;
  latency_seconds: number;
};

type ManualRatings = {
  factual_correctness: number | null;
  faithfulness: number | null;
  citation_support: number | null;
  answer_relevance: number | null;
  clarity: number | null;
};

type ManualRow = {
  question: string;
  ratings: ManualRatings;
  average_score: number | null;
  unsupported_claims: string;
  abstention_appropriate: string;
  review_comments: string;
};

type DashboardData = {
  retrieval: {
    summary: RetrievalRow[];
    details: RetrievalDetail[];
  };
  automated_answers: {
    evaluation_type: string;
    notes: string[];
    summary: {
      total_questions: number;
      average_point_coverage: number;
      average_question_citation_accuracy: number;
      overall_citation_accuracy: number;
      abstention_accuracy: number;
      average_generation_latency_seconds: number;
      total_citations: number;
      valid_citations: number;
    };
    questions: AnswerQuestion[];
  };
  manual_review: {
    total_questions: number;
    reviewed_questions: number;
    criteria_averages: Record<string, number | null>;
    overall_average: number | null;
    rows: ManualRow[];
    scale: string;
  };
};

const METHODS = ["Dense", "BM25", "Hybrid RRF", "Hybrid + Cross-Encoder"];

const METRICS = [
  { key: "precision_at_5", label: "Precision@5" },
  { key: "recall_at_5", label: "Recall@5" },
  { key: "mrr", label: "MRR" },
  { key: "ndcg_at_5", label: "NDCG@5" },
] as const;

const CRITERIA = [
  { key: "factual_correctness", label: "Factual correctness" },
  { key: "faithfulness", label: "Faithfulness" },
  { key: "citation_support", label: "Citation support" },
  { key: "answer_relevance", label: "Answer relevance" },
  { key: "clarity", label: "Clarity" },
];

const COLORS = ["#8b5cf6", "#06b6d4", "#f59e0b", "#10b981"];

const formatPercent = (value: number | null | undefined) =>
  value == null ? "—" : `${(value * 100).toFixed(1)}%`;

const formatScore = (value: number | null | undefined) =>
  value == null ? "—" : value.toFixed(3);

const shortQuestion = (question: string) => {
  if (question.includes("phishing")) return "Phishing email";
  if (question.includes("multi-factor")) return "MFA protection";
  if (question.includes("passwords")) return "Password storage";
  if (question.includes("incident")) return "Incident response";
  if (question.includes("compromised")) return "Compromised account";
  return question.length > 35 ? `${question.slice(0, 35)}...` : question;
};

function MetricCard({
  label,
  value,
  description,
  icon: Icon,
  accent,
}: {
  label: string;
  value: string;
  description: string;
  icon: React.ElementType;
  accent: string;
}) {
  return (
    <div className="rounded-2xl border border-white/[0.07] bg-[#151923] p-5 transition hover:border-white/15">
      <div className="flex items-center justify-between">
        <p className="text-sm text-gray-400">{label}</p>
        <div className={`rounded-xl p-2 ${accent}`}>
          <Icon size={19} />
        </div>
      </div>
      <p className="mt-4 text-3xl font-semibold tracking-tight text-white">
        {value}
      </p>
      <p className="mt-2 text-xs text-gray-500">{description}</p>
    </div>
  );
}

function SectionHeading({
  title,
  subtitle,
  icon: Icon,
}: {
  title: string;
  subtitle: string;
  icon: React.ElementType;
}) {
  return (
    <div className="mb-5 flex items-start gap-3">
      <div className="rounded-xl bg-violet-500/10 p-2.5 text-violet-400">
        <Icon size={20} />
      </div>
      <div>
        <h2 className="text-lg font-semibold text-white">{title}</h2>
        <p className="mt-1 text-sm text-gray-500">{subtitle}</p>
      </div>
    </div>
  );
}

function Panel({
  children,
  className = "",
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={`rounded-2xl border border-white/[0.07] bg-[#151923] p-5 ${className}`}
    >
      {children}
    </div>
  );
}

export default function Evaluation() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [strategy, setStrategy] = useState("fixed");
  const [selectedMetric, setSelectedMetric] =
    useState<(typeof METRICS)[number]["key"]>("ndcg_at_5");
  const [selectedQuestion, setSelectedQuestion] = useState<number | null>(null);

  useEffect(() => {
    let active = true;

    const loadDashboard = async () => {
      try {
        setLoading(true);
        setError("");

        const response = await fetch(`${API_URL}/api/evaluation/dashboard`);

        if (!response.ok) {
          throw new Error(`API returned ${response.status}`);
        }

        const result: DashboardData = await response.json();

        if (active) setData(result);
      } catch (err) {
        if (active) {
          setError(
            err instanceof Error
              ? err.message
              : "Unable to load evaluation data.",
          );
        }
      } finally {
        if (active) setLoading(false);
      }
    };

    loadDashboard();

    return () => {
      active = false;
    };
  }, []);

  const retrievalRows = useMemo(
    () =>
      data?.retrieval.summary.filter((row) => row.strategy === strategy) ?? [],
    [data, strategy],
  );

  const selectedMetricLabel =
    METRICS.find((metric) => metric.key === selectedMetric)?.label ?? "NDCG@5";

  const retrievalChartData = retrievalRows.map((row) => ({
    method: row.method,
    value: row[selectedMetric],
  }));

  const strategyComparison = useMemo(() => {
    if (!data) return [];

    return METHODS.map((method) => {
      const fixed = data.retrieval.summary.find(
        (row) => row.strategy === "fixed" && row.method === method,
      );
      const recursive = data.retrieval.summary.find(
        (row) => row.strategy === "recursive" && row.method === method,
      );

      return {
        method,
        fixed: fixed?.ndcg_at_5 ?? 0,
        recursive: recursive?.ndcg_at_5 ?? 0,
      };
    });
  }, [data]);

  const radarData = CRITERIA.map((criterion) => ({
    criterion: criterion.label,
    score: data?.manual_review.criteria_averages[criterion.key] ?? 0,
    fullMark: 5,
  }));

  // Latest eight-case end-to-end regression benchmark (Gemini answer
  // generation plus claim-level verification). These are saved benchmark
  // measurements, not live request timings.
  const regressionLatencies: Record<string, number> = {
    "Phishing email": 13.61,
    "MFA protection": 11.62,
    "Password storage": 13.22,
    "Incident response": 21.96,
    Malware: 11.96,
    "Out of scope": 10.42,
    "Insufficient evidence": 10.61,
    "Account security": 12.07,
  };

  const latencyData = Object.entries(regressionLatencies).map(
    ([question, latency]) => ({ question, latency }),
  );

  const averageEndToEndLatency =
    latencyData.reduce((sum, item) => sum + item.latency, 0) /
    latencyData.length;

  const answerSummary = data?.automated_answers.summary;
  const manual = data?.manual_review;

  if (loading) {
    return (
      <div className="flex min-h-[55vh] flex-col items-center justify-center gap-4">
        <div className="h-10 w-10 animate-spin rounded-full border-2 border-violet-500 border-t-transparent" />
        <p className="text-sm text-gray-400">Loading evaluation results...</p>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="rounded-2xl border border-red-500/20 bg-red-500/5 p-8">
        <h2 className="text-lg font-semibold text-white">
          Unable to load evaluation dashboard
        </h2>
        <p className="mt-2 text-sm text-gray-400">
          {error || "No evaluation data was returned."}
        </p>
        <p className="mt-3 text-xs text-gray-500">
          Make sure the FastAPI backend is running on port 8000.
        </p>
        <button
          onClick={() => window.location.reload()}
          className="mt-5 rounded-xl bg-violet-600 px-4 py-2 text-sm font-medium text-white hover:bg-violet-500"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-8 pb-10 text-gray-200">
      {/* Header */}
      <div className="flex flex-col justify-between gap-4 md:flex-row md:items-center">
        <div>
          <div className="mb-2 flex items-center gap-2 text-xs font-medium uppercase tracking-[0.18em] text-violet-400">
            <Activity size={14} />
            Performance analytics
          </div>
          <h1 className="text-3xl font-bold tracking-tight text-white">
            Evaluation Dashboard
          </h1>
          <p className="mt-2 max-w-2xl text-sm text-gray-400">
            Measure retrieval quality, answer reliability and human-reviewed
            response quality across your CyberSafe RAG experiments.
          </p>
        </div>

        <div className="flex items-center gap-2 self-start rounded-xl border border-emerald-500/20 bg-emerald-500/10 px-3 py-2 text-xs font-medium text-emerald-400">
          <CheckCircle2 size={15} />
          Evaluation data loaded
        </div>
      </div>

      {/* Top metric cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard
          label="Retrieval experiments"
          value={String(data.retrieval.details.length)}
          description="Across 5 questions, 2 strategies and 4 methods"
          icon={BarChart3}
          accent="bg-violet-500/10 text-violet-400"
        />
        <MetricCard
          label="Manual review score"
          value={
            manual?.overall_average != null
              ? `${manual.overall_average.toFixed(2)}/5`
              : "—"
          }
          description={`${manual?.reviewed_questions ?? 0} answers manually reviewed`}
          icon={Award}
          accent="bg-amber-500/10 text-amber-400"
        />
        <MetricCard
          label="Average end-to-end latency"
          value={`${averageEndToEndLatency.toFixed(2)}s`}
          description="8 regression tests, including claim verification"
          icon={Clock3}
          accent="bg-cyan-500/10 text-cyan-400"
        />
        <MetricCard
          label="Valid citations"
          value={
            answerSummary
              ? `${answerSummary.valid_citations}/${answerSummary.total_citations}`
              : "—"
          }
          description="Automated citation reference validation"
          icon={FileCheck2}
          accent="bg-emerald-500/10 text-emerald-400"
        />
      </div>

      {/* Retrieval evaluation */}
      <section>
        <SectionHeading
          title="Retrieval performance"
          subtitle="Compare retrieval algorithms using Precision@5, Recall@5, MRR and NDCG@5."
          icon={Target}
        />

        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div className="flex rounded-xl border border-white/[0.08] bg-[#151923] p-1">
            {["fixed", "recursive"].map((item) => (
              <button
                key={item}
                onClick={() => setStrategy(item)}
                className={`rounded-lg px-4 py-2 text-sm capitalize transition ${
                  strategy === item
                    ? "bg-violet-600 text-white"
                    : "text-gray-400 hover:text-white"
                }`}
              >
                {item === "fixed" ? "Fixed-size" : "Recursive"}
              </button>
            ))}
          </div>

          <div className="relative">
            <select
              value={selectedMetric}
              onChange={(event) =>
                setSelectedMetric(event.target.value as typeof selectedMetric)
              }
              className="appearance-none rounded-xl border border-white/[0.08] bg-[#151923] py-2.5 pl-3 pr-9 text-sm text-gray-200 outline-none focus:border-violet-500"
            >
              {METRICS.map((metric) => (
                <option key={metric.key} value={metric.key}>
                  {metric.label}
                </option>
              ))}
            </select>
            <ChevronDown
              size={15}
              className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-gray-400"
            />
          </div>
        </div>

        <Panel>
          <div className="mb-5">
            <h3 className="font-semibold text-white">
              {selectedMetricLabel} by retrieval method
            </h3>
            <p className="mt-1 text-xs text-gray-500">
              Strategy: {strategy} · Evaluation cutoff: 5 retrieved chunks
            </p>
          </div>
          <div className="h-[310px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={retrievalChartData}
                margin={{ top: 10, right: 12, left: -15, bottom: 10 }}
              >
                <CartesianGrid
                  strokeDasharray="3 3"
                  stroke="#ffffff12"
                  vertical={false}
                />
                <XAxis
                  dataKey="method"
                  tick={{ fill: "#9ca3af", fontSize: 11 }}
                  axisLine={false}
                  tickLine={false}
                  interval={0}
                  angle={-10}
                  textAnchor="end"
                  height={55}
                />
                <YAxis
                  domain={[0, 1]}
                  tick={{ fill: "#9ca3af", fontSize: 11 }}
                  axisLine={false}
                  tickLine={false}
                  tickFormatter={(value) => `${(value * 100).toFixed(0)}%`}
                />
                <Tooltip
                  cursor={{ fill: "#ffffff08" }}
                  contentStyle={{
                    background: "#202635",
                    border: "1px solid #ffffff18",
                    borderRadius: 12,
                    color: "#fff",
                  }}
                  formatter={(value) => [
                    `${(Number(value) * 100).toFixed(1)}%`,
                    selectedMetricLabel,
                  ]}
                />
                <Bar dataKey="value" radius={[7, 7, 0, 0]} maxBarSize={65}>
                  {retrievalChartData.map((_, index) => (
                    <Cell key={index} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Panel>

        <Panel className="mt-4">
          <h3 className="mb-4 font-semibold text-white">
            Retrieval metric breakdown
          </h3>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[650px] text-left text-sm">
              <thead>
                <tr className="border-b border-white/[0.07] text-xs text-gray-500">
                  <th className="pb-3 font-medium">Method</th>
                  <th className="pb-3 text-right font-medium">Precision@5</th>
                  <th className="pb-3 text-right font-medium">Recall@5</th>
                  <th className="pb-3 text-right font-medium">MRR</th>
                  <th className="pb-3 text-right font-medium">NDCG@5</th>
                </tr>
              </thead>
              <tbody>
                {retrievalRows.map((row) => (
                  <tr
                    key={`${row.strategy}-${row.method}`}
                    className="border-b border-white/[0.05] last:border-0"
                  >
                    <td className="py-4 font-medium text-white">
                      {row.method}
                    </td>
                    <td className="py-4 text-right tabular-nums">
                      {formatPercent(row.precision_at_5)}
                    </td>
                    <td className="py-4 text-right tabular-nums">
                      {formatPercent(row.recall_at_5)}
                    </td>
                    <td className="py-4 text-right tabular-nums">
                      {formatScore(row.mrr)}
                    </td>
                    <td className="py-4 text-right tabular-nums">
                      {formatScore(row.ndcg_at_5)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Panel>
      </section>

      {/* Strategy comparison */}
      <section>
        <SectionHeading
          title="Chunking strategy comparison"
          subtitle="Compare fixed-size and recursive chunking using NDCG@5 across retrieval methods."
          icon={TrendingUp}
        />

        <Panel>
          <div className="mb-4 flex flex-wrap gap-5 text-xs text-gray-400">
            <span className="flex items-center gap-2">
              <span className="h-2.5 w-2.5 rounded-sm bg-violet-500" />
              Fixed-size
            </span>
            <span className="flex items-center gap-2">
              <span className="h-2.5 w-2.5 rounded-sm bg-cyan-500" />
              Recursive
            </span>
          </div>
          <div className="h-[310px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={strategyComparison}
                margin={{ top: 10, right: 12, left: -15, bottom: 10 }}
              >
                <CartesianGrid
                  strokeDasharray="3 3"
                  stroke="#ffffff12"
                  vertical={false}
                />
                <XAxis
                  dataKey="method"
                  tick={{ fill: "#9ca3af", fontSize: 11 }}
                  axisLine={false}
                  tickLine={false}
                  interval={0}
                  angle={-10}
                  textAnchor="end"
                  height={55}
                />
                <YAxis
                  domain={[0, 1]}
                  tick={{ fill: "#9ca3af", fontSize: 11 }}
                  axisLine={false}
                  tickLine={false}
                />
                <Tooltip
                  contentStyle={{
                    background: "#202635",
                    border: "1px solid #ffffff18",
                    borderRadius: 12,
                  }}
                />
                <Legend />
                <Bar
                  dataKey="fixed"
                  name="Fixed-size"
                  fill="#8b5cf6"
                  radius={[5, 5, 0, 0]}
                />
                <Bar
                  dataKey="recursive"
                  name="Recursive"
                  fill="#06b6d4"
                  radius={[5, 5, 0, 0]}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <p className="mt-3 text-xs text-gray-500">
            NDCG@5 measures the ranking quality of the top five retrieved
            chunks. Higher values indicate better ranked relevance.
          </p>
        </Panel>
      </section>

      {/* Automated evaluation */}
      <section>
        <SectionHeading
          title="Automated answer evaluation"
          subtitle="Heuristic checks for expected answer points, citation references and abstention behaviour."
          icon={ShieldCheck}
        />

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <MetricCard
            label="Point coverage"
            value={formatPercent(answerSummary?.average_point_coverage)}
            description="Average expected-point coverage"
            icon={Target}
            accent="bg-violet-500/10 text-violet-400"
          />
          <MetricCard
            label="Question citation accuracy"
            value={formatPercent(
              answerSummary?.average_question_citation_accuracy,
            )}
            description="Average per-question citation validity"
            icon={FileCheck2}
            accent="bg-cyan-500/10 text-cyan-400"
          />
          <MetricCard
            label="Abstention accuracy"
            value={formatPercent(answerSummary?.abstention_accuracy)}
            description="Expected vs detected abstention"
            icon={ShieldCheck}
            accent="bg-emerald-500/10 text-emerald-400"
          />
          <MetricCard
            label="Total citations"
            value={`${answerSummary?.valid_citations ?? 0}/${answerSummary?.total_citations ?? 0}`}
            description="Valid evidence index and page references"
            icon={CheckCircle2}
            accent="bg-amber-500/10 text-amber-400"
          />
        </div>

        <Panel className="mt-4">
          <h3 className="mb-4 font-semibold text-white">
            End-to-end latency by test case
          </h3>
          <div className="h-[280px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={latencyData}
                margin={{ top: 10, right: 12, left: -15, bottom: 10 }}
              >
                <CartesianGrid
                  strokeDasharray="3 3"
                  stroke="#ffffff12"
                  vertical={false}
                />
                <XAxis
                  dataKey="question"
                  tick={{ fill: "#9ca3af", fontSize: 11 }}
                  axisLine={false}
                  tickLine={false}
                  interval={0}
                  angle={-10}
                  textAnchor="end"
                  height={55}
                />
                <YAxis
                  tick={{ fill: "#9ca3af", fontSize: 11 }}
                  axisLine={false}
                  tickLine={false}
                  unit="s"
                />
                <Tooltip
                  contentStyle={{
                    background: "#202635",
                    border: "1px solid #ffffff18",
                    borderRadius: 12,
                  }}
                  formatter={(value) => [
                    `${Number(value).toFixed(2)} seconds`,
                    "End-to-end latency",
                  ]}
                />
                <Bar
                  dataKey="latency"
                  fill="#06b6d4"
                  radius={[6, 6, 0, 0]}
                  maxBarSize={65}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <p className="mt-3 text-xs text-gray-500">
            Average measured end-to-end latency across 8 regression tests:{" "}
            <strong className="text-gray-300">
              {averageEndToEndLatency.toFixed(2)} seconds
            </strong>
          </p>
        </Panel>

        <Panel className="mt-4">
          <h3 className="mb-4 font-semibold text-white">
            Question-wise automated results
          </h3>
          <div className="space-y-3">
            {data.automated_answers.questions.map((question, index) => (
              <button
                key={question.query}
                onClick={() =>
                  setSelectedQuestion(selectedQuestion === index ? null : index)
                }
                className="w-full rounded-xl border border-white/[0.06] bg-white/[0.015] p-4 text-left transition hover:border-white/15"
              >
                <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-white">
                      {shortQuestion(question.query)}
                    </p>
                    <p className="mt-1 text-xs text-gray-500">
                      {question.covered_points}/{question.total_points} expected
                      points covered · {question.valid_citations}/
                      {question.total_citations} valid citations
                    </p>
                  </div>
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="rounded-lg bg-violet-500/10 px-2.5 py-1.5 text-xs text-violet-300">
                      {formatPercent(question.point_coverage)} coverage
                    </span>
                    <span className="rounded-lg bg-cyan-500/10 px-2.5 py-1.5 text-xs text-cyan-300">
                      {(
                        regressionLatencies[shortQuestion(question.query)] ??
                        question.latency_seconds
                      ).toFixed(2)}
                      s
                    </span>
                    <ChevronDown
                      size={16}
                      className={`text-gray-500 transition ${
                        selectedQuestion === index ? "rotate-180" : ""
                      }`}
                    />
                  </div>
                </div>

                {selectedQuestion === index && (
                  <div className="mt-4 grid grid-cols-1 gap-3 border-t border-white/[0.06] pt-4 sm:grid-cols-3">
                    <div>
                      <p className="text-xs text-gray-500">Citation accuracy</p>
                      <p className="mt-1 text-sm text-white">
                        {formatPercent(question.citation_accuracy)}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs text-gray-500">
                        Abstention expected
                      </p>
                      <p className="mt-1 text-sm text-white">
                        {question.expected_abstention ? "Yes" : "No"}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs text-gray-500">Abstention check</p>
                      <p className="mt-1 text-sm text-white">
                        {question.abstention_correct ? "Correct" : "Incorrect"}
                      </p>
                    </div>
                  </div>
                )}
              </button>
            ))}
          </div>
        </Panel>

        <div className="mt-4 flex gap-3 rounded-xl border border-amber-500/20 bg-amber-500/[0.06] p-4">
          <Info className="mt-0.5 shrink-0 text-amber-400" size={18} />
          <div>
            <p className="text-sm font-medium text-amber-300">
              Interpretation limitation
            </p>
            <p className="mt-1 text-xs leading-5 text-gray-400">
              These are automated heuristic evaluation results. Point coverage
              uses lexical token overlap, citation validation checks evidence
              index and page references, and abstention detection uses
              predefined text patterns. These checks do not independently
              establish semantic correctness, factual accuracy or faithfulness.
            </p>
          </div>
        </div>
      </section>

      {/* Manual evaluation */}
      <section>
        <SectionHeading
          title="Human evaluation"
          subtitle="Manual review of generated responses across five quality dimensions, scored from 1 to 5."
          icon={Award}
        />

        <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
          <Panel className="lg:col-span-1">
            <p className="text-sm text-gray-400">Overall human review score</p>
            <p className="mt-3 text-5xl font-bold text-white">
              {manual?.overall_average?.toFixed(2) ?? "—"}
              <span className="text-xl text-gray-500">/5</span>
            </p>
            <p className="mt-2 text-xs text-gray-500">
              Based on {manual?.reviewed_questions} manually reviewed answers
            </p>
            <div className="mt-5 h-2 overflow-hidden rounded-full bg-white/10">
              <div
                className="h-full rounded-full bg-violet-500"
                style={{
                  width: `${((manual?.overall_average ?? 0) / 5) * 100}%`,
                }}
              />
            </div>
          </Panel>

          <Panel className="lg:col-span-2">
            <h3 className="mb-3 font-semibold text-white">
              Evaluation criteria
            </h3>
            <div className="h-[245px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <RadarChart data={radarData} outerRadius="75%">
                  <PolarGrid stroke="#ffffff20" />
                  <PolarAngleAxis
                    dataKey="criterion"
                    tick={{ fill: "#9ca3af", fontSize: 10 }}
                  />
                  <Radar
                    name="Human review"
                    dataKey="score"
                    stroke="#8b5cf6"
                    fill="#8b5cf6"
                    fillOpacity={0.28}
                  />
                  <Tooltip
                    contentStyle={{
                      background: "#202635",
                      border: "1px solid #ffffff18",
                      borderRadius: 12,
                    }}
                  />
                </RadarChart>
              </ResponsiveContainer>
            </div>
          </Panel>
        </div>

        <Panel className="mt-4">
          <h3 className="mb-4 font-semibold text-white">
            Average score by criterion
          </h3>
          <div className="space-y-5">
            {CRITERIA.map((criterion) => {
              const score = manual?.criteria_averages[criterion.key] ?? null;

              return (
                <div key={criterion.key}>
                  <div className="mb-2 flex items-center justify-between gap-3">
                    <span className="text-sm text-gray-300">
                      {criterion.label}
                    </span>
                    <span className="text-sm font-semibold tabular-nums text-white">
                      {score == null ? "—" : `${score.toFixed(1)} / 5`}
                    </span>
                  </div>
                  <div className="h-2 overflow-hidden rounded-full bg-white/10">
                    <div
                      className="h-full rounded-full bg-violet-500 transition-all"
                      style={{
                        width: `${score == null ? 0 : (score / 5) * 100}%`,
                      }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </Panel>

        <Panel className="mt-4">
          <h3 className="mb-4 font-semibold text-white">
            Individual manual reviews
          </h3>
          <div className="space-y-4">
            {manual?.rows.map((row, index) => (
              <div
                key={index}
                className="rounded-xl border border-white/[0.06] bg-white/[0.015] p-4"
              >
                <div className="flex flex-col justify-between gap-2 sm:flex-row sm:items-start">
                  <div>
                    <p className="text-sm font-medium text-white">
                      {shortQuestion(row.question)}
                    </p>
                    <p className="mt-1 text-xs text-gray-500">{row.question}</p>
                  </div>
                  <span className="shrink-0 rounded-lg bg-violet-500/10 px-3 py-1.5 text-sm font-semibold text-violet-300">
                    {row.average_score == null
                      ? "Not scored"
                      : `${row.average_score.toFixed(1)} / 5`}
                  </span>
                </div>

                <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-5">
                  {CRITERIA.map((criterion) => (
                    <div key={criterion.key}>
                      <p className="text-[11px] text-gray-500">
                        {criterion.label}
                      </p>
                      <p className="mt-1 text-sm font-medium text-gray-200">
                        {row.ratings[criterion.key as keyof ManualRatings] ??
                          "—"}
                        <span className="text-gray-500"> / 5</span>
                      </p>
                    </div>
                  ))}
                </div>

                <div className="mt-4 flex flex-wrap gap-2 text-xs">
                  <span
                    className={`rounded-lg px-2.5 py-1.5 ${
                      row.unsupported_claims.toLowerCase() === "yes"
                        ? "bg-amber-500/10 text-amber-300"
                        : "bg-emerald-500/10 text-emerald-300"
                    }`}
                  >
                    Unsupported claims:{" "}
                    {row.unsupported_claims || "Not recorded"}
                  </span>
                  <span className="rounded-lg bg-white/[0.05] px-2.5 py-1.5 text-gray-300">
                    Abstention appropriate:{" "}
                    {row.abstention_appropriate || "Not recorded"}
                  </span>
                </div>

                {row.review_comments && (
                  <details className="mt-4">
                    <summary className="cursor-pointer text-xs font-medium text-violet-300 hover:text-violet-200">
                      View reviewer comments
                    </summary>
                    <p className="mt-3 whitespace-pre-wrap text-xs leading-6 text-gray-400">
                      {row.review_comments}
                    </p>
                  </details>
                )}
              </div>
            ))}
          </div>
        </Panel>
      </section>

      {/* Evaluation methodology */}
      <Panel>
        <div className="flex gap-3">
          <Info className="mt-0.5 shrink-0 text-cyan-400" size={19} />
          <div>
            <h3 className="font-semibold text-white">
              Evaluation methodology and limitations
            </h3>
            <p className="mt-2 text-sm leading-6 text-gray-400">
              Retrieval metrics are calculated against the current labelled
              ground-truth set of five benchmark questions. The labels were
              initially seeded from retrieved candidates and have not all been
              independently audited. Consequently, these scores are provisional
              and should not be interpreted as general performance guarantees.
            </p>
            <p className="mt-2 text-sm leading-6 text-gray-400">
              Human evaluation provides a separate qualitative assessment.
              Review comments identify citation mismatches, unsupported claims
              and wording improvements that automated metrics may not capture.
            </p>
          </div>
        </div>
      </Panel>
    </div>
  );
}

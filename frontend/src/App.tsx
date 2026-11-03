import { useState } from "react";

import {
  Shield,
  LayoutDashboard,
  MessageSquare,
  Database,
  ChartNoAxesCombined,
  Settings,
  Search,
  Bell,
  ArrowUpRight,
  FileText,
  Activity,
  Zap,
  ShieldCheck,
  ChevronRight,
  Menu,
  X,
  Workflow,
} from "lucide-react";

import Assistant from "./components/Assistant";
import KnowledgeBase from "./pages/KnowledgeBase";
import Evaluation from "./pages/Evaluation";
import Architecture from "./pages/Architecture";

type Page =
  | "Dashboard"
  | "AI Assistant"
  | "Knowledge Base"
  | "Evaluation"
  | "Architecture";

// Dashboard statistics
const stats = [
  {
    title: "Knowledge Documents",
    value: "8",
    detail: "Trusted sources indexed",
    icon: Database,
    color: "text-cyan-400",
  },
  {
    title: "Indexed Chunks",
    value: "430",
    detail: "Fixed-size strategy",
    icon: FileText,
    color: "text-violet-400",
  },
  {
    title: "Retrieval Methods",
    value: "3",
    detail: "Dense, BM25 and Hybrid",
    icon: Zap,
    color: "text-amber-400",
  },
  {
    title: "System Status",
    value: "Ready",
    detail: "RAG pipeline configured",
    icon: Activity,
    color: "text-emerald-400",
  },
];

// Featured knowledge sources
const sources = [
  {
    name: "CERT-In Cyber Security Handbook",
    organization: "CERT-In",
    pages: "15 pages",
    type: "Government",
  },
  {
    name: "NIST SP 800-61 Rev. 3",
    organization: "NIST",
    pages: "48 pages",
    type: "Standard",
  },
  {
    name: "OWASP Authentication Cheat Sheet",
    organization: "OWASP",
    pages: "23 pages",
    type: "Technical",
  },
  {
    name: "OWASP Password Storage Cheat Sheet",
    organization: "OWASP",
    pages: "9 pages",
    type: "Technical",
  },
];

function App() {
  const [activePage, setActivePage] = useState<Page>("Dashboard");
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  // Navigation items
  const navigation = [
    {
      name: "Dashboard" as Page,
      icon: LayoutDashboard,
    },
    {
      name: "AI Assistant" as Page,
      icon: MessageSquare,
    },
    {
      name: "Knowledge Base" as Page,
      icon: Database,
    },
    {
      name: "Evaluation" as Page,
      icon: ChartNoAxesCombined,
    },
    {
      name: "Architecture" as Page,
      icon: Workflow,
    },
  ];

  const navigate = (page: Page) => {
    setActivePage(page);
    setMobileMenuOpen(false);
  };

  // Sidebar
  const Sidebar = () => (
    <aside className="flex min-h-screen w-64 shrink-0 flex-col border-r border-slate-800 bg-[#0c1423] p-5">
      {/* BRAND */}
      <div className="mb-12 flex items-center gap-3">
        <div className="rounded-xl bg-cyan-400/10 p-2">
          <Shield className="text-cyan-400" size={27} />
        </div>

        <div>
          <h1 className="text-xl font-bold tracking-tight">CyberSafe</h1>
          <p className="text-xs text-slate-500">RAG Intelligence</p>
        </div>
      </div>

      <p className="mb-4 text-xs uppercase tracking-widest text-slate-500">
        Workspace
      </p>

      {/* NAVIGATION */}
      <nav className="space-y-2">
        {navigation.map((item) => {
          const Icon = item.icon;
          const isActive = activePage === item.name;

          return (
            <button
              key={item.name}
              onClick={() => navigate(item.name)}
              className={`flex w-full items-center gap-3 rounded-xl border px-4 py-3 transition ${
                isActive
                  ? "border-cyan-400/10 bg-cyan-400/10 text-cyan-300"
                  : "border-transparent text-slate-400 hover:bg-slate-800 hover:text-white"
              }`}
            >
              <Icon size={19} />
              <span className="text-sm">{item.name}</span>
            </button>
          );
        })}
      </nav>

      {/* BOTTOM SECTION */}
      <div className="mt-auto">
        <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-4">
          <div className="mb-3 flex items-center gap-2">
            <ShieldCheck className="text-emerald-400" size={19} />
            <span className="text-sm font-semibold">System Protected</span>
          </div>

          <p className="text-xs leading-relaxed text-slate-500">
            CyberSafe uses evidence-grounded responses and abstains when
            supporting evidence is insufficient.
          </p>
        </div>

        <button
          onClick={() => navigate("Dashboard")}
          className="mt-5 flex items-center gap-3 text-slate-400 transition hover:text-white"
        >
          <Settings size={18} />
          Settings
        </button>
      </div>
    </aside>
  );

  // Dashboard
  const Dashboard = () => (
    <div className="mx-auto max-w-[1500px] p-5 md:p-9">
      {/* WELCOME */}
      <section className="relative mb-9 overflow-hidden rounded-3xl border border-cyan-400/15 bg-gradient-to-br from-[#10263a] via-[#101b30] to-[#11152a] p-7 md:p-10">
        <div className="absolute -right-20 -top-28 h-80 w-80 rounded-full bg-cyan-400/10 blur-3xl" />

        <div className="relative z-10 max-w-2xl">
          <div className="mb-5 inline-flex items-center gap-2 rounded-full border border-emerald-400/20 bg-emerald-400/10 px-3 py-1 text-xs text-emerald-300">
            <span className="h-2 w-2 rounded-full bg-emerald-400" />
            RAG Pipeline Ready
          </div>

          <h1 className="mb-4 text-3xl font-bold leading-tight md:text-4xl">
            Your cybersecurity intelligence
            <span className="text-cyan-400"> workspace.</span>
          </h1>

          <p className="mb-7 leading-relaxed text-slate-400">
            Ask cybersecurity questions, retrieve trusted evidence and receive
            transparent AI-generated guidance powered by CERT-In, NIST and
            OWASP.
          </p>

          <button
            onClick={() => navigate("AI Assistant")}
            className="inline-flex items-center gap-2 rounded-xl bg-cyan-400 px-5 py-3 text-sm font-bold text-slate-950 transition hover:bg-cyan-300"
          >
            <MessageSquare size={17} />
            Open AI Assistant
            <ArrowUpRight size={16} />
          </button>
        </div>
      </section>

      {/* STATISTICS */}
      <section className="mb-10 grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {stats.map((stat) => {
          const Icon = stat.icon;

          return (
            <div
              key={stat.title}
              className="rounded-2xl border border-slate-800 bg-[#101a2c] p-5 transition hover:border-slate-700"
            >
              <div className="mb-5 flex items-center justify-between">
                <p className="text-sm text-slate-400">{stat.title}</p>
                <Icon className={stat.color} size={21} />
              </div>

              <h3 className="mb-2 text-3xl font-bold">{stat.value}</h3>

              <p className="text-xs text-slate-500">{stat.detail}</p>
            </div>
          );
        })}
      </section>

      {/* LOWER SECTIONS */}
      <section className="grid grid-cols-1 gap-6 xl:grid-cols-3">
        {/* KNOWLEDGE BASE */}
        <div className="rounded-2xl border border-slate-800 bg-[#101a2c] p-6 xl:col-span-2">
          <div className="mb-6 flex items-center justify-between">
            <div>
              <h3 className="text-lg font-semibold">Knowledge Base</h3>
              <p className="mt-1 text-xs text-slate-500">
                Trusted cybersecurity reference documents
              </p>
            </div>

            <button
              onClick={() => navigate("Knowledge Base")}
              className="flex items-center gap-1 text-sm text-cyan-400 hover:text-cyan-300"
            >
              View all <ChevronRight size={16} />
            </button>
          </div>

          <div className="space-y-3">
            {sources.map((source) => (
              <div
                key={source.name}
                className="flex items-center justify-between gap-3 rounded-xl border border-slate-800 bg-slate-900/70 p-4 transition hover:border-slate-700"
              >
                <div className="flex min-w-0 items-center gap-3">
                  <div className="rounded-lg bg-cyan-400/10 p-2 text-cyan-400">
                    <FileText size={19} />
                  </div>

                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium">
                      {source.name}
                    </p>

                    <p className="mt-1 text-xs text-slate-500">
                      {source.organization} · {source.pages}
                    </p>
                  </div>
                </div>

                <span className="hidden rounded-full bg-slate-800 px-3 py-1 text-xs text-slate-400 sm:block">
                  {source.type}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* QUICK ACTIONS */}
        <div className="rounded-2xl border border-slate-800 bg-[#101a2c] p-6">
          <h3 className="mb-2 text-lg font-semibold">Quick Actions</h3>

          <p className="mb-6 text-xs text-slate-500">
            Explore CyberSafe capabilities
          </p>

          <div className="space-y-3">
            <button
              onClick={() => navigate("AI Assistant")}
              className="flex w-full items-center justify-between rounded-xl border border-cyan-400/15 bg-cyan-400/10 p-4 transition hover:bg-cyan-400/15"
            >
              <div className="flex items-center gap-3">
                <MessageSquare className="text-cyan-400" size={19} />
                <span className="text-sm font-medium">Ask CyberSafe</span>
              </div>
              <ArrowUpRight size={17} className="text-cyan-400" />
            </button>

            <button
              onClick={() => navigate("Knowledge Base")}
              className="flex w-full items-center justify-between rounded-xl border border-slate-800 bg-slate-900 p-4 transition hover:border-slate-700"
            >
              <div className="flex items-center gap-3">
                <Database className="text-violet-400" size={19} />
                <span className="text-sm font-medium">Explore Documents</span>
              </div>
              <ArrowUpRight size={17} className="text-slate-400" />
            </button>

            <button
              onClick={() => navigate("Evaluation")}
              className="flex w-full items-center justify-between rounded-xl border border-slate-800 bg-slate-900 p-4 transition hover:border-slate-700"
            >
              <div className="flex items-center gap-3">
                <ChartNoAxesCombined className="text-amber-400" size={19} />
                <span className="text-sm font-medium">View Evaluation</span>
              </div>
              <ArrowUpRight size={17} className="text-slate-400" />
            </button>

            <button
              onClick={() => navigate("Architecture")}
              className="flex w-full items-center justify-between rounded-xl border border-violet-400/15 bg-violet-400/5 p-4 transition hover:bg-violet-400/10"
            >
              <div className="flex items-center gap-3">
                <Workflow className="text-violet-400" size={19} />
                <span className="text-sm font-medium">
                  Explore Architecture
                </span>
              </div>
              <ArrowUpRight size={17} className="text-violet-400" />
            </button>
          </div>

          <div className="mt-7 rounded-xl border border-emerald-400/15 bg-emerald-400/5 p-4">
            <div className="mb-2 flex items-center gap-2">
              <ShieldCheck size={18} className="text-emerald-400" />
              <span className="text-sm font-semibold">Evidence First</span>
            </div>

            <p className="text-xs leading-relaxed text-slate-400">
              Every answer is generated using retrieved cybersecurity evidence,
              with citations and explicit abstention when necessary.
            </p>
          </div>
        </div>
      </section>

      {/* FOOTER */}
      <footer className="mt-10 flex flex-wrap justify-between gap-3 border-t border-slate-800 pt-6 text-xs text-slate-600">
        <p>CyberSafe RAG · Cybersecurity Intelligence Platform</p>
        <p>Powered by FAISS · BM25 · Gemini</p>
      </footer>
    </div>
  );

  // Page rendering
  const renderPage = () => {
    switch (activePage) {
      case "Dashboard":
        return <Dashboard />;

      case "AI Assistant":
        return (
          <div className="p-5 md:p-8">
            <Assistant />
          </div>
        );

      case "Knowledge Base":
        return (
          <div className="p-5 md:p-8">
            <KnowledgeBase />
          </div>
        );

      case "Evaluation":
        return (
          <div className="p-5 md:p-8">
            <Evaluation />
          </div>
        );

      case "Architecture":
        return (
          <div>
            <Architecture />
          </div>
        );

      default:
        return <Dashboard />;
    }
  };

  // Main layout
  return (
    <div className="flex min-h-screen bg-[#080e1b] text-slate-100">
      {/* DESKTOP SIDEBAR */}
      <div className="hidden md:block">
        <Sidebar />
      </div>

      {/* MOBILE MENU */}
      {mobileMenuOpen && (
        <div className="fixed inset-0 z-50 flex md:hidden">
          <div
            className="absolute inset-0 bg-black/70"
            onClick={() => setMobileMenuOpen(false)}
          />

          <div className="relative z-10">
            <Sidebar />
          </div>

          <button
            onClick={() => setMobileMenuOpen(false)}
            className="absolute right-5 top-5 z-20 text-white"
          >
            <X size={24} />
          </button>
        </div>
      )}

      {/* MAIN AREA */}
      <main className="min-w-0 flex-1">
        {/* TOP BAR */}
        <header className="flex h-20 items-center justify-between border-b border-slate-800 px-5 md:px-9">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setMobileMenuOpen(true)}
              className="rounded-lg p-2 hover:bg-slate-800 md:hidden"
            >
              <Menu size={20} />
            </button>

            <div>
              <p className="text-xs text-slate-500">Workspace / {activePage}</p>
              <h2 className="text-lg font-semibold">{activePage}</h2>
            </div>
          </div>

          <div className="flex items-center gap-4">
            <button className="rounded-xl p-2 text-slate-400 hover:bg-slate-800">
              <Search size={19} />
            </button>

            <button className="rounded-xl p-2 text-slate-400 hover:bg-slate-800">
              <Bell size={19} />
            </button>

            <div className="flex h-9 w-9 items-center justify-center rounded-full border border-cyan-400/20 bg-cyan-400/15 font-bold text-cyan-300">
              C
            </div>
          </div>
        </header>

        {/* ACTIVE PAGE */}
        {renderPage()}
      </main>
    </div>
  );
}

export default App;

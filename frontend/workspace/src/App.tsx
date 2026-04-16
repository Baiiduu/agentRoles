import { useMemo, useState } from "react";
import { WorkspaceShell } from "./components/WorkspaceShell";
import { AgentCapabilityPage } from "./pages/AgentCapabilityPage";
import { AgentConfigPage } from "./pages/AgentConfigPage";
import { AgentResourceManagerPage } from "./pages/AgentResourceManagerPage";
import { CaseWorkspacePage } from "./pages/CaseWorkspacePage";
import { DashboardPage } from "./pages/DashboardPage";
import { AgentPlaygroundPage } from "./pages/AgentPlaygroundPage";
import { api } from "./services/api";
import type { AgentSessionResponseDto } from "./types/agentPlayground";
import type { WorkspacePageKey } from "./types/workspace";

const pageLabels: Record<WorkspacePageKey, string> = {
  dashboard: "Dashboard",
  playground: "Agent Playground",
  agentConfig: "Agent Config",
  agentCapability: "Agent Capability",
  resourceManager: "Resource Manager",
  cases: "Case Workspace",
  workflows: "Workflow Studio",
  teacher: "Teacher Console",
};

export default function App() {
  const [page, setPage] = useState<WorkspacePageKey>("dashboard");
  const [activeCaseId, setActiveCaseId] = useState<string>("");
  const [playgroundAgentId, setPlaygroundAgentId] = useState<string>("");
  const [caseRefreshTick, setCaseRefreshTick] = useState(0);
  const [caseSessionLog, setCaseSessionLog] = useState<
    Record<string, AgentSessionResponseDto[]>
  >({});

  function openCaseWorkspace(caseId: string) {
    setActiveCaseId(caseId);
    setPage("cases");
  }

  function openPlayground(options?: { caseId?: string; agentId?: string }) {
    if (options?.caseId) {
      setActiveCaseId(options.caseId);
    }
    if (options?.agentId) {
      setPlaygroundAgentId(options.agentId);
    }
    setPage("playground");
  }

  function registerCaseSession(caseId: string | null, result: AgentSessionResponseDto) {
    if (!caseId) return;
    void api.appendCaseSessionFeedItem(caseId, result).finally(() => {
      setCaseRefreshTick((current) => current + 1);
    });
    setCaseSessionLog((current) => ({
      ...current,
      [caseId]: [...(current[caseId] || []), result],
    }));
  }

  const content = useMemo(() => {
    if (page === "dashboard") {
      return <DashboardPage onOpenCase={openCaseWorkspace} onOpenPlayground={openPlayground} />;
    }
    if (page === "playground") {
      return (
        <AgentPlaygroundPage
          initialCaseId={activeCaseId}
          initialAgentId={playgroundAgentId}
          onSessionCommitted={registerCaseSession}
        />
      );
    }
    if (page === "agentConfig") {
      return <AgentConfigPage />;
    }
    if (page === "agentCapability") {
      return <AgentCapabilityPage />;
    }
    if (page === "resourceManager") {
      return <AgentResourceManagerPage />;
    }
    if (page === "cases") {
      return (
        <CaseWorkspacePage
          initialCaseId={activeCaseId}
          caseSessionLog={caseSessionLog}
          refreshToken={caseRefreshTick}
          onContinueWithAgent={(options) => openPlayground(options)}
        />
      );
    }
    return (
      <section className="placeholder-panel">
        <h2>{pageLabels[page]}</h2>
        <p>页面占位已建立，后续将按同一结构继续迁入。</p>
      </section>
    );
  }, [page, activeCaseId, playgroundAgentId, caseSessionLog, caseRefreshTick]);

  return (
    <WorkspaceShell
      currentPage={page}
      onSelectPage={setPage}
      pageLabels={pageLabels}
    >
      {content}
    </WorkspaceShell>
  );
}

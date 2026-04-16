import { useEffect, useMemo, useState } from "react";
import { CaseAgentCapabilityPanel } from "../components/CaseAgentCapabilityPanel";
import { CaseCoordinatorCard } from "../components/CaseCoordinatorCard";
import { HandoffPanel } from "../components/HandoffPanel";
import { api } from "../services/api";
import type { AgentSessionResponseDto } from "../types/agentPlayground";
import type { CaseListItem, CaseWorkspaceDto } from "../types/caseWorkspace";

interface CaseWorkspacePageProps {
  initialCaseId?: string;
  caseSessionLog?: Record<string, AgentSessionResponseDto[]>;
  refreshToken?: number;
  onContinueWithAgent?: (options: { caseId?: string; agentId?: string }) => void;
}

export function CaseWorkspacePage({
  initialCaseId = "",
  caseSessionLog = {},
  refreshToken = 0,
  onContinueWithAgent,
}: CaseWorkspacePageProps) {
  const [cases, setCases] = useState<CaseListItem[]>([]);
  const [selectedCaseId, setSelectedCaseId] = useState("");
  const [workspace, setWorkspace] = useState<CaseWorkspaceDto | null>(null);
  const [error, setError] = useState("");
  const [handoffPending, setHandoffPending] = useState(false);

  useEffect(() => {
    let active = true;
    api.getCases()
      .then((payload) => {
        if (!active) return;
        setCases(payload.cases);
        if (payload.cases.length) {
          setSelectedCaseId(initialCaseId || payload.cases[0].case_id);
        }
      })
      .catch((err: Error) => {
        if (!active) return;
        setError(err.message);
      });
    return () => {
      active = false;
    };
  }, [initialCaseId]);

  useEffect(() => {
    if (!selectedCaseId) return;
    let active = true;
    api.getCase(selectedCaseId)
      .then((payload) => {
        if (!active) return;
        setWorkspace(payload);
      })
      .catch((err: Error) => {
        if (!active) return;
        setError(err.message);
      });
    return () => {
      active = false;
    };
  }, [selectedCaseId, refreshToken]);

  const localCaseSessions = selectedCaseId ? caseSessionLog[selectedCaseId] || [] : [];
  const agentNameMap = useMemo(
    () =>
      Object.fromEntries(
        (workspace?.available_agents || []).map((item) => [item.agent_id, item.name]),
      ),
    [workspace],
  );
  const workflowNameMap = useMemo(
    () =>
      Object.fromEntries(
        (workspace?.available_workflows || []).map((item) => [item.workflow_id, item.name]),
      ),
    [workspace],
  );
  const combinedFeed = useMemo(() => {
    const entries = new Map<string, AgentSessionResponseDto | CaseWorkspaceDto["session_feed"][number]>();
    for (const item of workspace?.session_feed || []) {
      entries.set(item.session_id, item);
    }
    for (const item of localCaseSessions) {
      entries.set(item.session.session_id, item);
    }
    return Array.from(entries.values()).reverse();
  }, [workspace, localCaseSessions]);

  async function handleCreateHandoff(payload: {
    targetAgentId: string;
    reason: string;
  }) {
    if (!workspace) return;
    try {
      setHandoffPending(true);
      setError("");
      const response = await api.createCaseHandoff(workspace.case.case_id, {
        target_agent_id: payload.targetAgentId,
        requested_by: "teacher",
        reason: payload.reason,
      });
      const refreshed = await api.getCase(workspace.case.case_id);
      setWorkspace(refreshed);
      onContinueWithAgent?.({
        caseId: response.navigation_target.case_id,
        agentId: response.navigation_target.agent_id,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "unknown error");
    } finally {
      setHandoffPending(false);
    }
  }

  if (error) {
    return <div className="error-banner">{error}</div>;
  }

  return (
    <section className="page-shell">
      <header className="page-header">
        <p className="workspace-eyebrow">Case Workspace</p>
        <h2 className="page-title">Learner Case Workspace</h2>
        <p className="page-copy">
          在同一个 learner case 内组织人工 handoff、单 agent 工作和协调建议。
        </p>
      </header>

      <div className="case-layout">
        <section className="panel">
          <h2 className="panel-title">Cases</h2>
          <div className="agent-list">
            {cases.map((item) => (
              <button
                key={item.case_id}
                type="button"
                className={item.case_id === selectedCaseId ? "agent-card active" : "agent-card"}
                onClick={() => setSelectedCaseId(item.case_id)}
              >
                <strong>{item.title}</strong>
                <span>{item.learner_name}</span>
                <span>{item.current_stage}</span>
              </button>
            ))}
          </div>
        </section>

        <section className="panel">
          <h2 className="panel-title">Case Overview</h2>
          {workspace ? (
            <div className="detail-card">
              <h3>{workspace.case.title}</h3>
              <p>
                {workspace.case.learner_name} | {workspace.case.goal}
              </p>
              <div className="tag-row">
                <span className="tag">{workspace.case.current_stage}</span>
                {workspace.case.active_plan.focus_areas.map((item) => (
                  <span key={item} className="tag">
                    {item}
                  </span>
                ))}
              </div>
              <p style={{ marginTop: 12 }}>{workspace.case.mastery_summary}</p>
              <div className="detail-card">
                <strong>Active Plan</strong>
                <p>{workspace.case.active_plan.title}</p>
              </div>
            </div>
          ) : (
            <p>Loading...</p>
          )}
        </section>
      </div>

      <div className="dashboard-grid">
        <section className="panel">
          <h2 className="panel-title">Artifacts</h2>
          {workspace ? (
            <div className="catalog-grid">
              {workspace.case.artifacts.map((item, index) => (
                <article key={`${item.artifact_type}-${index}`} className="catalog-card">
                  <strong>{item.artifact_type}</strong>
                  <span>{item.producer}</span>
                  <p>{item.summary}</p>
                </article>
              ))}
            </div>
          ) : (
            <p>Loading...</p>
          )}
        </section>

        {workspace ? (
          <CaseCoordinatorCard
            coordination={workspace.coordination}
            agentNameMap={agentNameMap}
            workflowNameMap={workflowNameMap}
            onContinueWithAgent={(agentId) =>
              onContinueWithAgent?.({
                caseId: workspace.case.case_id,
                agentId,
              })
            }
          />
        ) : (
          <section className="panel">
            <h2 className="panel-title">Case Coordinator</h2>
            <p>Loading...</p>
          </section>
        )}
      </div>

      <div className="dashboard-grid">
        {workspace ? (
          <HandoffPanel
            agents={workspace.available_agents}
            handoffs={workspace.handoffs}
            pending={handoffPending}
            onCreateHandoff={handleCreateHandoff}
          />
        ) : (
          <section className="panel">
            <h2 className="panel-title">Manual Agent Handoff</h2>
            <p>Loading...</p>
          </section>
          )}

        <section className="panel">
          <h2 className="panel-title">Timeline</h2>
          {workspace ? (
            <div className="catalog-grid">
              {workspace.case.timeline.map((item, index) => (
                <article key={`${item.kind}-${index}`} className="catalog-card">
                  <strong>{item.label}</strong>
                  <span>
                    {item.kind} | {item.stage}
                  </span>
                </article>
              ))}
            </div>
          ) : (
            <p>Loading...</p>
          )}
        </section>
      </div>

      {workspace ? (
        <CaseAgentCapabilityPanel
          agents={workspace.available_agents}
          onContinueWithAgent={(agentId) =>
            onContinueWithAgent?.({
              caseId: workspace.case.case_id,
              agentId,
            })
          }
        />
      ) : (
        <section className="panel">
          <h2 className="panel-title">Agent Readiness</h2>
          <p>Loading...</p>
        </section>
      )}

      <section className="panel">
        <h2 className="panel-title">Case Session Feed</h2>
        {workspace && combinedFeed.length ? (
          <div className="catalog-grid">
            {combinedFeed.map((item) =>
              "session" in item ? (
                <article key={item.session.session_id} className="catalog-card">
                  <strong>{item.agent.name}</strong>
                  <span>{item.session.status}</span>
                  <p>{item.artifact_preview?.summary || "No summary"}</p>
                </article>
              ) : (
                <article key={item.session_id} className="catalog-card">
                  <strong>{item.agent_name}</strong>
                  <span>{item.status}</span>
                  <p>{item.summary}</p>
                </article>
              ),
            )}
          </div>
        ) : (
          <p>当前还没有回流到这个 case 的 agent session 结果。</p>
        )}
      </section>
    </section>
  );
}

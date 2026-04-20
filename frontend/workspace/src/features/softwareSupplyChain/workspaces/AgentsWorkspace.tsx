import { useEffect, useMemo, useState } from "react";
import { ChatComposerBar } from "../../../components/ChatComposerBar";
import {
  SessionComposer,
  type SessionFormState,
} from "../../../components/SessionComposer";
import { SessionResultPanel } from "../../../components/SessionResultPanel";
import { api } from "../../../services/api";
import type {
  AgentBootstrapDto,
  AgentDescriptorDto,
  AgentSessionResponseDto,
  AgentSessionTaskDto,
  PersistedAgentChatMessage,
  PersistedAgentChatSession,
} from "../../../types/agentPlayground";
import type { SoftwareSupplyChainUiSettingsDto } from "../../../types/softwareSupplyChain";
import { SoftwareSupplyChainAgentList } from "../components/SoftwareSupplyChainAgentList";

const SOFTWARE_SUPPLY_CHAIN_DOMAIN = "software_supply_chain";

const defaultForm: SessionFormState = {
  caseId: "",
  message: "",
  persistArtifact: false,
};

const starterPromptsByAgentId: Record<string, string[]> = {
  dependency_auditor: [
    "Map the dependency entry points, lockfiles, and package managers in this repository.",
    "Find high-risk or weakly governed dependencies first.",
    "List the missing evidence we still need before building an SBOM story.",
  ],
  vulnerability_remediator: [
    "Propose the safest minimal remediation path for the current dependency risks.",
    "Check upgrade paths and call out compatibility risks before changing anything.",
    "If code or version updates are required, give me the verification path first.",
  ],
  compliance_specialist: [
    "Check license, provenance, and release-control gaps in this repository.",
    "Separate blockers from recommendations for the current compliance posture.",
    "Summarize the missing release-gate evidence for this repository.",
  ],
  evolver_agent: [
    "Design the next-stage supply-chain roadmap based on the current repository state.",
    "Turn dependency audit, remediation, and compliance into one executable flow.",
    "Give me a rollout plan the team can adopt incrementally.",
  ],
};

function pickDefaultAgentId(
  bootstrap: AgentBootstrapDto | null,
  agents: AgentBootstrapDto["agents"],
): string {
  if (!agents.length) return "";
  const bootstrapDefault = bootstrap?.default_agent_id || "";
  if (agents.some((agent) => agent.agent_id === bootstrapDefault)) {
    return bootstrapDefault;
  }
  return agents[0].agent_id;
}

export function AgentsWorkspace() {
  const [bootstrap, setBootstrap] = useState<AgentBootstrapDto | null>(null);
  const [uiSettings, setUiSettings] = useState<SoftwareSupplyChainUiSettingsDto | null>(null);
  const [selectedAgentId, setSelectedAgentId] = useState("");
  const [agentDetail, setAgentDetail] = useState<AgentDescriptorDto | null>(null);
  const [chatSessions, setChatSessions] = useState<PersistedAgentChatSession[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState("");
  const [chatHistory, setChatHistory] = useState<PersistedAgentChatMessage[]>([]);
  const [form, setForm] = useState<SessionFormState>(defaultForm);
  const [result, setResult] = useState<AgentSessionResponseDto | null>(null);
  const [liveTask, setLiveTask] = useState<AgentSessionTaskDto | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const supplyChainAgents = useMemo(
    () =>
      (bootstrap?.agents || []).filter(
        (agent) => agent.domain === SOFTWARE_SUPPLY_CHAIN_DOMAIN,
      ),
    [bootstrap],
  );

  const currentRepoUrl = (uiSettings?.current_repo_url || "").trim();
  const starterPrompts =
    starterPromptsByAgentId[selectedAgentId] || [
      "Run a supply-chain analysis centered on the current repository.",
      "Read the minimum necessary files, then tell me the highest-priority issue first.",
      "Keep the reasoning visible in the runtime trace so I can review the flow later.",
    ];

  useEffect(() => {
    let active = true;
    Promise.all([
      api.getAgentPlaygroundBootstrap(),
      api.getSoftwareSupplyChainUiSettings().catch(() => null),
    ])
      .then(([payload, settings]) => {
        if (!active) return;
        setBootstrap(payload);
        setUiSettings(settings);
      })
      .catch((err: Error) => {
        if (!active) return;
        setError(err.message);
      });
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    const nextAgentId = pickDefaultAgentId(bootstrap, supplyChainAgents);
    setSelectedAgentId((current) =>
      supplyChainAgents.some((agent) => agent.agent_id === current) ? current : nextAgentId,
    );
  }, [bootstrap, supplyChainAgents]);

  useEffect(() => {
    if (!selectedAgentId) {
      setAgentDetail(null);
      setChatSessions([]);
      setCurrentSessionId("");
      setChatHistory([]);
      return;
    }
    let active = true;
    Promise.all([
      api.getAgentDescriptor(selectedAgentId),
      api
        .getAgentSessions(selectedAgentId)
        .catch(() => ({ agent_id: selectedAgentId, active_session_id: null, sessions: [] })),
    ])
      .then(async ([descriptor, sessionBundle]) => {
        if (!active) return;
        setAgentDetail(descriptor);
        setChatSessions(sessionBundle.sessions || []);
        const nextSessionId =
          sessionBundle.active_session_id || sessionBundle.sessions?.[0]?.session_id || "";
        setCurrentSessionId(nextSessionId);
        setResult(null);
        setLiveTask(null);
        const history = await api
          .getAgentChatHistory(selectedAgentId, nextSessionId || undefined)
          .catch(() => ({
            agent_id: selectedAgentId,
            session_id: nextSessionId || null,
            messages: [],
          }));
        if (!active) return;
        setChatHistory(history.messages || []);
      })
      .catch((err: Error) => {
        if (!active) return;
        setError(err.message);
      });
    return () => {
      active = false;
    };
  }, [selectedAgentId]);

  useEffect(() => {
    if (!liveTask || !["queued", "running"].includes(liveTask.status)) return;
    let active = true;
    const timer = window.setInterval(() => {
      api.getAgentSessionTask(liveTask.task_id)
        .then(async (task) => {
          if (!active) return;
          setLiveTask(task);
          if (task.status === "completed" && task.result) {
            setResult(task.result);
            setCurrentSessionId(task.result.session.session_id);
            const [sessionsBundle, history] = await Promise.all([
              api.getAgentSessions(selectedAgentId),
              api.getAgentChatHistory(selectedAgentId, task.result.session.session_id),
            ]);
            if (!active) return;
            setChatSessions(sessionsBundle.sessions || []);
            setChatHistory(history.messages || []);
            setForm((current) => ({ ...current, message: "" }));
            setSubmitting(false);
          }
          if (task.status === "failed") {
            setSubmitting(false);
            setError(task.error || "run failed");
          }
        })
        .catch((err: Error) => {
          if (!active) return;
          setSubmitting(false);
          setError(err.message);
        });
    }, 800);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, [liveTask, selectedAgentId]);

  useEffect(() => {
    if (!selectedAgentId || !currentSessionId) {
      setChatHistory([]);
      return;
    }
    let active = true;
    api.getAgentChatHistory(selectedAgentId, currentSessionId)
      .then((history) => {
        if (!active) return;
        setChatHistory(history.messages || []);
      })
      .catch((err: Error) => {
        if (!active) return;
        setError(err.message);
      });
    return () => {
      active = false;
    };
  }, [selectedAgentId, currentSessionId]);

  async function handleSubmit() {
    try {
      setSubmitting(true);
      setError("");
      setResult(null);
      const task = await api.startAgentSessionTask({
        agent_id: selectedAgentId,
        session_id: currentSessionId || null,
        case_id: null,
        message: form.message.trim(),
        ephemeral_context: {
          github_repository: currentRepoUrl || null,
          software_supply_chain_context: {
            current_repo_url: currentRepoUrl || null,
            saved_repo_urls: uiSettings?.saved_repo_urls || [],
          },
        },
        persist_artifact: false,
      });
      setLiveTask(task);
      setCurrentSessionId(task.session_id || currentSessionId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "unknown error");
      setSubmitting(false);
    }
  }

  async function handleCreateSession() {
    if (!selectedAgentId) return;
    try {
      setError("");
      const created = await api.createAgentSession(selectedAgentId);
      setChatSessions((current) => [created.session, ...current]);
      setCurrentSessionId(created.session.session_id);
      setChatHistory([]);
      setResult(null);
      setLiveTask(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "unknown error");
    }
  }

  async function handleDeleteSession() {
    if (!selectedAgentId || !currentSessionId) return;
    try {
      setError("");
      const payload = await api.deleteAgentSession(selectedAgentId, currentSessionId);
      setChatSessions(payload.sessions || []);
      setCurrentSessionId(payload.active_session_id || "");
      setResult(null);
      setLiveTask(null);
      if (payload.active_session_id) {
        const history = await api.getAgentChatHistory(selectedAgentId, payload.active_session_id);
        setChatHistory(history.messages || []);
      } else {
        setChatHistory([]);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "unknown error");
    }
  }

  if (!bootstrap) {
    return (
      <main className="ssc-workspace-shell">
        <div className="ssc-workspace-panel ssc-empty-state">
          <strong>Loading supply chain agents...</strong>
          <p>The workspace is preparing the agent roster, sessions, and GitHub context.</p>
        </div>
      </main>
    );
  }

  if (!supplyChainAgents.length) {
    return (
      <main className="ssc-workspace-shell">
        <div className="ssc-workspace-panel ssc-empty-state">
          <strong>No software supply chain agents are registered.</strong>
          <p>Register the domain pack first, then this workspace can expose the agent list, sessions, and the live runtime trace.</p>
        </div>
      </main>
    );
  }

  return (
    <main className="ssc-workspace-shell">
      <header className="ssc-workspace-panel ssc-workspace-hero">
        <div className="ssc-workspace-head">
          <p className="ssc-workspace-eyebrow">Agents Workspace</p>
          <h2>Software Supply Chain Console</h2>
          <p>Switch across the four supply-chain agents, keep separate sessions per role, and review the live workflow trace without leaving the page.</p>
        </div>
        <div className={currentRepoUrl ? "ssc-inline-success" : "ssc-inline-note"}>
          {currentRepoUrl
            ? `Current GitHub context: ${currentRepoUrl}`
            : "No current GitHub link is set yet. You can still chat, but later runs will be more grounded if you set one in the GitHub workspace."}
        </div>
      </header>

      {error ? <div className="ssc-inline-error">{error}</div> : null}

      <div className="ssc-agents-shell">
        <SoftwareSupplyChainAgentList
          agents={supplyChainAgents}
          selectedAgentId={selectedAgentId}
          onSelectAgent={setSelectedAgentId}
          agentDetail={agentDetail}
          currentRepoUrl={currentRepoUrl}
        />

        <section className="ssc-agents-main">
          <SessionResultPanel result={result} history={chatHistory} liveTask={liveTask} />
          <ChatComposerBar
            message={form.message}
            onChangeMessage={(value) => setForm((current) => ({ ...current, message: value }))}
            onSubmit={handleSubmit}
            submitting={submitting}
            disabled={!selectedAgentId}
            starterPrompts={starterPrompts}
            label="Supply Chain Request"
            placeholder="Ask the selected agent to inspect dependencies, fix a vulnerability, assess compliance, or design the next supply-chain improvement step."
            sendLabel="Run Agent"
          />
        </section>

        <SessionComposer
          cases={[]}
          form={form}
          onChange={(patch) => setForm((current) => ({ ...current, ...patch }))}
          sessions={chatSessions}
          currentSessionId={currentSessionId}
          onChangeSession={setCurrentSessionId}
          onCreateSession={handleCreateSession}
          onDeleteSession={handleDeleteSession}
          title="Conversation Sessions"
          copy="Keep long-running supply-chain investigations separated by agent and repository context."
        />
      </div>
    </main>
  );
}

import { useEffect, useState } from "react";
import { AgentNavigator } from "../components/AgentNavigator";
import { ChatComposerBar } from "../components/ChatComposerBar";
import {
  SessionComposer,
  type SessionFormState,
} from "../components/SessionComposer";
import { SessionResultPanel } from "../components/SessionResultPanel";
import { api } from "../services/api";
import type { AgentCapabilityDto } from "../types/agentCapability";
import type {
  AgentBootstrapDto,
  PersistedAgentChatSession,
  AgentDescriptorDto,
  PersistedAgentChatMessage,
  AgentSessionResponseDto,
  AgentSessionTaskDto,
} from "../types/agentPlayground";

const defaultForm: SessionFormState = {
  caseId: "",
  message: "",
  persistArtifact: false,
};

interface AgentPlaygroundPageProps {
  initialCaseId?: string;
  initialAgentId?: string;
  onSessionCommitted?: (caseId: string | null, result: AgentSessionResponseDto) => void;
}

export function AgentPlaygroundPage({
  initialCaseId = "",
  initialAgentId = "",
  onSessionCommitted,
}: AgentPlaygroundPageProps) {
  const [bootstrap, setBootstrap] = useState<AgentBootstrapDto | null>(null);
  const [selectedAgentId, setSelectedAgentId] = useState("");
  const [agentDetail, setAgentDetail] = useState<AgentDescriptorDto | null>(null);
  const [capabilityDetail, setCapabilityDetail] = useState<AgentCapabilityDto | null>(null);
  const [chatSessions, setChatSessions] = useState<PersistedAgentChatSession[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState("");
  const [chatHistory, setChatHistory] = useState<PersistedAgentChatMessage[]>([]);
  const [form, setForm] = useState<SessionFormState>(defaultForm);
  const [result, setResult] = useState<AgentSessionResponseDto | null>(null);
  const [liveTask, setLiveTask] = useState<AgentSessionTaskDto | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    api.getAgentPlaygroundBootstrap()
      .then((payload) => {
        if (!active) return;
        setBootstrap(payload);
        setSelectedAgentId(initialAgentId || payload.default_agent_id || "");
        setForm((current) => ({
          ...current,
          caseId: initialCaseId || current.caseId,
        }));
      })
      .catch((err: Error) => {
        if (!active) return;
        setError(err.message);
      });
    return () => {
      active = false;
    };
  }, [initialAgentId, initialCaseId]);

  useEffect(() => {
    if (!selectedAgentId) return;
    let active = true;
    Promise.all([
      api.getAgentDescriptor(selectedAgentId),
      api.getAgentCapability(selectedAgentId).catch(() => null),
      api.getAgentSessions(selectedAgentId).catch(() => ({ agent_id: selectedAgentId, active_session_id: null, sessions: [] })),
    ])
      .then(([descriptor, capability, sessionBundle]) => {
        if (!active) return;
        setAgentDetail(descriptor);
        setCapabilityDetail(capability);
        setChatSessions(sessionBundle.sessions || []);
        const nextSessionId = sessionBundle.active_session_id || sessionBundle.sessions?.[0]?.session_id || "";
        setCurrentSessionId(nextSessionId);
        setResult(null);
        setLiveTask(null);
        return api.getAgentChatHistory(selectedAgentId, nextSessionId || undefined).catch(() => ({
          agent_id: selectedAgentId,
          session_id: nextSessionId || null,
          messages: [],
        }));
      }).then((history) => {
        if (!active || !history) return;
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
            onSessionCommitted?.(task.case_id, task.result);
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
  }, [liveTask, onSessionCommitted, selectedAgentId]);

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
      const trimmedMessage = form.message.trim();
      const payload = {
        agent_id: selectedAgentId,
        session_id: currentSessionId || null,
        case_id: form.caseId || null,
        message: trimmedMessage,
        ephemeral_context: {},
        persist_artifact: form.persistArtifact,
      };
      setResult(null);
      const task = await api.startAgentSessionTask(payload);
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

  return (
    <section className="page-shell">
      <header className="page-header">
        <p className="workspace-eyebrow">Agent Workspace</p>
        <h2 className="page-title">Agent Playground</h2>
        <p className="page-copy">
          Run a single agent like a workspace operator: chat, inspect files, call tools, and
          review execution traces in one place.
        </p>
      </header>
      {error ? <div className="error-banner">{error}</div> : null}

      <div className="agent-playground-shell">
        <AgentNavigator
          agents={bootstrap?.agents || []}
          agentTree={bootstrap?.agent_tree || []}
          selectedAgentId={selectedAgentId}
          onSelectAgent={setSelectedAgentId}
          agentDetail={agentDetail}
          capabilityDetail={capabilityDetail}
        />

        <main className="agent-playground-main">
          <SessionResultPanel result={result} history={chatHistory} liveTask={liveTask} />
          <ChatComposerBar
            message={form.message}
            onChangeMessage={(value) => setForm((current) => ({ ...current, message: value }))}
            onSubmit={handleSubmit}
            submitting={submitting}
            disabled={!selectedAgentId}
          />
        </main>

        <SessionComposer
          cases={bootstrap?.available_cases || []}
          form={form}
          onChange={(patch) => setForm((current) => ({ ...current, ...patch }))}
          sessions={chatSessions}
          currentSessionId={currentSessionId}
          onChangeSession={setCurrentSessionId}
          onCreateSession={handleCreateSession}
          onDeleteSession={handleDeleteSession}
        />
      </div>
    </section>
  );
}

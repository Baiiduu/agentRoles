import type { AgentCaseOption, PersistedAgentChatSession } from "../types/agentPlayground";

export interface SessionFormState {
  caseId: string;
  message: string;
  persistArtifact: boolean;
}

interface SessionComposerProps {
  cases: AgentCaseOption[];
  form: SessionFormState;
  onChange: (patch: Partial<SessionFormState>) => void;
  sessions: PersistedAgentChatSession[];
  currentSessionId: string;
  onChangeSession: (sessionId: string) => void;
  onCreateSession: () => void;
  onDeleteSession: () => void;
}

export function SessionComposer({
  cases,
  form,
  onChange,
  sessions,
  currentSessionId,
  onChangeSession,
  onCreateSession,
  onDeleteSession,
}: SessionComposerProps) {
  return (
    <section className="panel context-panel">
      <h2 className="panel-title">Chat Settings</h2>
      <p className="section-copy">
        Keep this playground focused on direct chat. Link a case only when you want the
        conversation associated with one.
      </p>

      <div className="field">
        <label>Conversation Session</label>
        <select
          value={currentSessionId}
          onChange={(event) => onChangeSession(event.target.value)}
        >
          <option value="">No active session</option>
          {sessions.map((item) => (
            <option key={item.session_id} value={item.session_id}>
              {item.title}
            </option>
          ))}
        </select>
      </div>

      <div className="session-action-row">
        <button type="button" className="secondary-button" onClick={onCreateSession}>
          New Session
        </button>
        <button
          type="button"
          className="secondary-button danger-button"
          onClick={onDeleteSession}
          disabled={!currentSessionId}
        >
          Delete Session
        </button>
      </div>

      <div className="field">
        <label>Linked Case</label>
        <select
          value={form.caseId}
          onChange={(event) => onChange({ caseId: event.target.value })}
        >
          <option value="">Standalone chat</option>
          {cases.map((item) => (
            <option key={item.case_id} value={item.case_id}>
              {item.title} | {item.learner_name}
            </option>
          ))}
        </select>
      </div>

      <label className="checkbox">
        <input
          type="checkbox"
          checked={form.persistArtifact}
          onChange={(event) => onChange({ persistArtifact: event.target.checked })}
        />
        <span>Write chat result back to the linked case when available</span>
      </label>
    </section>
  );
}

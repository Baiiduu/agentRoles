import { useState } from "react";
import type { CaseHandoffRecordDto } from "../types/caseHandoff";

interface AgentOption {
  agent_id: string;
  name: string;
  role: string;
  capability_summary?: {
    enabled: boolean;
    approval_mode: string;
    handoff_mode: string;
    operational_summary: string;
    attention_points: string[];
  } | null;
}

interface HandoffPanelProps {
  agents: AgentOption[];
  handoffs: CaseHandoffRecordDto[];
  onCreateHandoff: (payload: { targetAgentId: string; reason: string }) => Promise<void>;
  pending?: boolean;
}

export function HandoffPanel({
  agents,
  handoffs,
  onCreateHandoff,
  pending = false,
}: HandoffPanelProps) {
  const [targetAgentId, setTargetAgentId] = useState("");
  const [reason, setReason] = useState("");
  const selectedAgent = agents.find((item) => item.agent_id === targetAgentId);
  const blocked = selectedAgent?.capability_summary?.handoff_mode === "blocked";

  async function handleSubmit() {
    if (!targetAgentId || blocked) return;
    await onCreateHandoff({ targetAgentId, reason });
    setReason("");
  }

  return (
    <section className="panel">
      <h2 className="panel-title">Manual Agent Handoff</h2>
      <div className="field">
        <label htmlFor="handoff-agent">Next Agent</label>
        <select
          id="handoff-agent"
          value={targetAgentId}
          onChange={(event) => setTargetAgentId(event.target.value)}
        >
          <option value="">Select an agent</option>
          {agents.map((item) => (
            <option
              key={item.agent_id}
              value={item.agent_id}
              disabled={
                item.capability_summary?.enabled === false ||
                item.capability_summary?.handoff_mode === "blocked"
              }
            >
              {item.name} | {item.role}
            </option>
          ))}
        </select>
      </div>
      {selectedAgent?.capability_summary ? (
        <div className="detail-card">
          <strong>Selected Agent Readiness</strong>
          <p>{selectedAgent.capability_summary.operational_summary}</p>
          <div className="tag-row">
            <span className="tag">
              approval: {selectedAgent.capability_summary.approval_mode}
            </span>
            <span className="tag">
              handoff: {selectedAgent.capability_summary.handoff_mode}
            </span>
          </div>
          {selectedAgent.capability_summary.attention_points.length ? (
            <div className="detail-block">
              {selectedAgent.capability_summary.attention_points.map((item) => (
                <span key={item} className="tag">
                  {item}
                </span>
              ))}
            </div>
          ) : null}
        </div>
      ) : null}
      <div className="field">
        <label htmlFor="handoff-reason">Reason</label>
        <textarea
          id="handoff-reason"
          value={reason}
          onChange={(event) => setReason(event.target.value)}
          placeholder="Why do you want to hand this case to the next agent?"
        />
      </div>
      <button
        type="button"
        className="primary-button"
        disabled={pending || !targetAgentId || blocked}
        onClick={handleSubmit}
      >
        Create Handoff
      </button>
      <div className="detail-block">
        {handoffs.length ? (
          handoffs
            .slice()
            .reverse()
            .map((item) => (
              <article key={item.handoff_id} className="catalog-card">
                <strong>{item.target_agent_id}</strong>
                <span>{item.status}</span>
                <p>{item.reason || "No handoff note"}</p>
              </article>
            ))
        ) : (
          <p>There is no handoff record for this case yet.</p>
        )}
      </div>
    </section>
  );
}

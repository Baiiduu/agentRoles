import type { CaseCoordinationDto } from "../types/caseCoordinator";

interface CaseCoordinatorCardProps {
  coordination: CaseCoordinationDto;
  agentNameMap: Record<string, string>;
  workflowNameMap: Record<string, string>;
  onContinueWithAgent?: (agentId: string) => void;
}

export function CaseCoordinatorCard({
  coordination,
  agentNameMap,
  workflowNameMap,
  onContinueWithAgent,
}: CaseCoordinatorCardProps) {
  const recommendedAgentName = coordination.recommended_agent_id
    ? agentNameMap[coordination.recommended_agent_id] || coordination.recommended_agent_id
    : null;
  const recommendedWorkflowName = coordination.recommended_workflow_id
    ? workflowNameMap[coordination.recommended_workflow_id] || coordination.recommended_workflow_id
    : null;

  return (
    <section className="panel">
      <h2 className="panel-title">Case Coordinator</h2>
      <div className="detail-card">
        <strong>Recommended Mode</strong>
        <div className="tag-row">
          <span className="tag">{coordination.recommended_mode}</span>
          {recommendedAgentName ? <span className="tag">{recommendedAgentName}</span> : null}
          {recommendedWorkflowName ? <span className="tag">{recommendedWorkflowName}</span> : null}
        </div>
        <p>{coordination.reason_summary}</p>
        {coordination.supporting_signals.length ? (
          <div className="detail-block">
            {coordination.supporting_signals.map((item) => (
              <span key={item} className="tag">
                {item}
              </span>
            ))}
          </div>
        ) : null}
        {coordination.recommended_mode === "agent_session" && coordination.recommended_agent_id ? (
          <div className="action-row">
            <button
              type="button"
              className="primary-button"
              onClick={() => onContinueWithAgent?.(coordination.recommended_agent_id!)}
            >
              Continue With Recommended Agent
            </button>
          </div>
        ) : null}
      </div>
    </section>
  );
}

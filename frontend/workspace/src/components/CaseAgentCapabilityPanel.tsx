import type { CaseWorkspaceDto } from "../types/caseWorkspace";

interface CaseAgentCapabilityPanelProps {
  agents: CaseWorkspaceDto["available_agents"];
  onContinueWithAgent?: (agentId: string) => void;
}

export function CaseAgentCapabilityPanel({
  agents,
  onContinueWithAgent,
}: CaseAgentCapabilityPanelProps) {
  return (
    <section className="panel">
      <h2 className="panel-title">Agent Readiness</h2>
      <div className="catalog-grid">
        {agents.map((agent) => {
          const summary = agent.capability_summary;
          return (
            <article key={agent.agent_id} className="catalog-card">
              <strong>{agent.name}</strong>
              <span>{agent.role}</span>
              <div className="tag-row">
                <span className={summary?.enabled === false ? "tag" : "tag success"}>
                  {summary?.enabled === false ? "disabled" : "enabled"}
                </span>
                {summary ? <span className="tag">approval: {summary.approval_mode}</span> : null}
                {summary ? <span className="tag">handoff: {summary.handoff_mode}</span> : null}
              </div>
              <p>
                {summary?.operational_summary || "Capability summary is not available for this agent yet."}
              </p>
              {summary?.collaboration_summary ? <p>{summary.collaboration_summary}</p> : null}
              {summary?.mcp_servers?.length ? (
                <div className="detail-block">
                  <strong>MCP</strong>
                  <div className="tag-row">
                    {summary.mcp_servers.map((item) => (
                      <span key={item} className="tag">
                        {item}
                      </span>
                    ))}
                  </div>
                </div>
              ) : null}
              {summary?.skills?.length ? (
                <div className="detail-block">
                  <strong>Skills</strong>
                  <div className="tag-row">
                    {summary.skills.map((item) => (
                      <span key={item} className="tag">
                        {item}
                      </span>
                    ))}
                  </div>
                </div>
              ) : null}
              {summary?.attention_points?.length ? (
                <div className="detail-block">
                  <strong>Attention</strong>
                  <div className="tag-row">
                    {summary.attention_points.map((item) => (
                      <span key={item} className="tag">
                        {item}
                      </span>
                    ))}
                  </div>
                </div>
              ) : null}
              <div className="action-row">
                <button
                  type="button"
                  className="secondary-button"
                  onClick={() => onContinueWithAgent?.(agent.agent_id)}
                  disabled={summary?.enabled === false}
                >
                  Open In Playground
                </button>
              </div>
            </article>
          );
        })}
      </div>
    </section>
  );
}

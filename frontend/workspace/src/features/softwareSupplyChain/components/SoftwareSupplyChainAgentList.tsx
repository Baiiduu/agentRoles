import type {
  AgentBootstrapItem,
  AgentDescriptorDto,
} from "../../../types/agentPlayground";

interface SoftwareSupplyChainAgentListProps {
  agents: AgentBootstrapItem[];
  selectedAgentId: string;
  onSelectAgent: (agentId: string) => void;
  agentDetail: AgentDescriptorDto | null;
  currentRepoUrl: string;
}

const roleLabels: Record<string, string> = {
  auditor: "Dependency Audit",
  remediator: "Remediation",
  compliance: "Compliance",
  evolver: "Evolution",
};

export function SoftwareSupplyChainAgentList({
  agents,
  selectedAgentId,
  onSelectAgent,
  agentDetail,
  currentRepoUrl,
}: SoftwareSupplyChainAgentListProps) {
  return (
    <aside className="ssc-workspace-panel ssc-agent-list-panel">
      <div className="ssc-workspace-head">
        <p className="ssc-workspace-eyebrow">Agents</p>
        <h2>Supply Chain Team</h2>
        <p>Pick the active agent on the left, then keep the conversation and runtime trace focused on that role.</p>
      </div>

      <div className="ssc-agent-list">
        {agents.map((agent) => {
          const active = agent.agent_id === selectedAgentId;
          return (
            <button
              key={agent.agent_id}
              type="button"
              className={["ssc-agent-card", active ? "active" : ""].filter(Boolean).join(" ")}
              onClick={() => onSelectAgent(agent.agent_id)}
            >
              <div className="ssc-agent-card-head">
                <span className="ssc-agent-role">
                  {roleLabels[agent.role] || agent.role || "Agent"}
                </span>
                {active ? <span className="ssc-current-pill">Current</span> : null}
              </div>
              <strong>{agent.name}</strong>
              <p>{agent.description}</p>
              <div className="ssc-agent-chip-row">
                {agent.capabilities.slice(0, 3).map((capability) => (
                  <span key={capability} className="ssc-agent-chip">
                    {capability}
                  </span>
                ))}
              </div>
            </button>
          );
        })}
      </div>

      <section className="ssc-agent-context-card">
        <div className="ssc-agent-context-head">
          <strong>{agentDetail?.name || "No agent selected"}</strong>
          <span className="ssc-agent-role">
            {agentDetail ? roleLabels[agentDetail.role] || agentDetail.role : "Idle"}
          </span>
        </div>
        <p className="ssc-agent-context-copy">Current GitHub repository context passed into the next run:</p>
        <div className="ssc-agent-repo-pill">
          {currentRepoUrl || "No current GitHub link set yet"}
        </div>
        {agentDetail?.capabilities?.length ? (
          <div className="ssc-agent-chip-row">
            {agentDetail.capabilities.slice(0, 5).map((capability) => (
              <span key={capability} className="ssc-agent-chip">
                {capability}
              </span>
            ))}
          </div>
        ) : null}
      </section>
    </aside>
  );
}

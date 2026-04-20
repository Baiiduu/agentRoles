import type { AgentResourceManagerAgentDto } from "../../../types/agentResourceManager";

interface McpManagerAgentRailProps {
  agents: AgentResourceManagerAgentDto[];
  selectedAgentId: string;
  onSelectAgent: (agentId: string) => void;
  currentRepoUrl: string;
  serverCount: number;
}

export function McpManagerAgentRail({
  agents,
  selectedAgentId,
  onSelectAgent,
  currentRepoUrl,
  serverCount,
}: McpManagerAgentRailProps) {
  return (
    <aside className="ssc-workspace-panel ssc-mcp-rail">
      <div className="ssc-workspace-head">
        <p className="ssc-workspace-eyebrow">MCP Ops</p>
        <h2>Agents</h2>
      </div>

      <div className="ssc-mcp-summary-grid">
        <article className="ssc-mcp-stat-card">
          <span>Agents</span>
          <strong>{agents.length}</strong>
        </article>
        <article className="ssc-mcp-stat-card">
          <span>MCP</span>
          <strong>{serverCount}</strong>
        </article>
      </div>

      <div className="ssc-agent-repo-pill">
        {currentRepoUrl || "No current GitHub link set"}
      </div>

      <div className="ssc-agent-list">
        {agents.map((agent) => {
          const active = agent.agent_id === selectedAgentId;
          return (
            <button
              key={agent.agent_id}
              type="button"
              className={["ssc-agent-card", "ssc-agent-card-compact", active ? "active" : ""]
                .filter(Boolean)
                .join(" ")}
              onClick={() => onSelectAgent(agent.agent_id)}
            >
              <div className="ssc-agent-card-head">
                <strong>{agent.name}</strong>
                {active ? <span className="ssc-current-pill">Current</span> : null}
              </div>
              <div className="ssc-agent-chip-row">
                <span className="ssc-agent-chip">
                  MCP {agent.distribution.assigned_mcp_servers.length}
                </span>
                <span className="ssc-agent-chip">
                  Workspace {agent.distribution.workspace?.enabled ? "on" : "off"}
                </span>
              </div>
            </button>
          );
        })}
      </div>
    </aside>
  );
}

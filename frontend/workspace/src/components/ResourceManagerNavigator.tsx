import type { AgentResourceManagerAgentDto } from "../types/agentResourceManager";

interface ResourceManagerNavigatorProps {
  agents: AgentResourceManagerAgentDto[];
  selectedAgentId: string;
  onSelectAgent: (agentId: string) => void;
}

export function ResourceManagerNavigator({
  agents,
  selectedAgentId,
  onSelectAgent,
}: ResourceManagerNavigatorProps) {
  return (
    <section className="panel">
      <h2 className="panel-title">Agents</h2>
      <div className="agent-list">
        {agents.map((agent) => (
          <button
            key={agent.agent_id}
            type="button"
            className={agent.agent_id === selectedAgentId ? "agent-card active" : "agent-card"}
            onClick={() => onSelectAgent(agent.agent_id)}
          >
            <strong>{agent.name}</strong>
            <span>{agent.role}</span>
            <span>{agent.domain || "unknown-domain"}</span>
            <span>
              MCP {agent.distribution.assigned_mcp_servers.length} | Skill{" "}
              {agent.distribution.assigned_skills.length}
            </span>
          </button>
        ))}
      </div>
    </section>
  );
}

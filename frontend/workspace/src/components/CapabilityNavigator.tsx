import type { AgentCapabilityDto } from "../types/agentCapability";

interface CapabilityNavigatorProps {
  capabilities: AgentCapabilityDto[];
  selectedAgentId: string;
  onSelectAgent: (agentId: string) => void;
}

export function CapabilityNavigator({
  capabilities,
  selectedAgentId,
  onSelectAgent,
}: CapabilityNavigatorProps) {
  return (
    <section className="panel">
      <h2 className="panel-title">Capability Navigator</h2>
      <div className="agent-list">
        {capabilities.map((item) => (
          <button
            key={item.agent_id}
            type="button"
            className={item.agent_id === selectedAgentId ? "agent-card active" : "agent-card"}
            onClick={() => onSelectAgent(item.agent_id)}
          >
            <strong>{item.name || item.agent_id}</strong>
            <span>{item.role || "unknown"}</span>
            <span>{item.domain || "unknown-domain"}</span>
            <span>{item.enabled ? "enabled" : "disabled"}</span>
          </button>
        ))}
      </div>
    </section>
  );
}

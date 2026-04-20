import type {
  AgentResourceManagerAgentDto,
  RegisteredMCPServerDto,
} from "../../../types/agentResourceManager";
import { capabilityCount } from "../mcpManagerUtils";

interface McpAgentAccessPanelProps {
  agent: AgentResourceManagerAgentDto | null;
  selectedMcp: string[];
  onToggleMcp: (serverRef: string) => void;
  onSaveDistribution: () => Promise<void>;
  savingDistribution: boolean;
  servers: RegisteredMCPServerDto[];
}

export function McpAgentAccessPanel({
  agent,
  selectedMcp,
  onToggleMcp,
  onSaveDistribution,
  savingDistribution,
  servers,
}: McpAgentAccessPanelProps) {
  if (!agent) {
    return (
      <section className="ssc-workspace-panel">
        <div className="ssc-empty-state">
          <strong>No agent selected yet</strong>
          <p>Pick a supply-chain agent from the rail first, then this section can manage MCP access.</p>
        </div>
      </section>
    );
  }

  return (
    <section className="ssc-workspace-panel ssc-mcp-section-panel">
      <div className="ssc-workspace-head">
        <p className="ssc-workspace-eyebrow">Agent Access</p>
        <h2>Enable MCP For {agent.name}</h2>
        <p>Use line-by-line controls instead of bulk checklists, so each MCP server can be enabled deliberately and reviewed in context.</p>
      </div>

      <div className="ssc-agent-context-card">
        <div className="ssc-agent-context-head">
          <strong>{agent.name}</strong>
          <span className="ssc-agent-role">{agent.role}</span>
        </div>
        <p className="ssc-agent-context-copy">{agent.effectiveness.collaboration_summary}</p>
        <div className="ssc-agent-chip-row">
          <span className="ssc-agent-chip">{selectedMcp.length} MCP enabled</span>
          {agent.effectiveness.attention_points.slice(0, 3).map((item) => (
            <span key={item} className="ssc-agent-chip">
              {item}
            </span>
          ))}
        </div>
      </div>

      <div className="ssc-mcp-enable-list">
        {servers.map((server) => {
          const enabled = selectedMcp.includes(server.server_ref);
          return (
            <article
              key={server.server_ref}
              className={["ssc-mcp-enable-row", enabled ? "active" : ""].filter(Boolean).join(" ")}
            >
              <div className="ssc-mcp-enable-copy">
                <div className="ssc-agent-card-head">
                  <strong>{server.name || server.server_ref}</strong>
                  <span className="ssc-agent-role">{enabled ? "Enabled" : "Available"}</span>
                </div>
                <p>{server.description || "No description yet."}</p>
                <div className="ssc-agent-chip-row">
                  <span className="ssc-agent-chip">{server.server_ref}</span>
                  <span className="ssc-agent-chip">{server.transport_kind}</span>
                  <span className="ssc-agent-chip">{capabilityCount(server)} tools</span>
                </div>
              </div>
              <div className="ssc-mcp-enable-actions">
                <button
                  type="button"
                  className={["ssc-mcp-toggle", enabled ? "active" : ""].filter(Boolean).join(" ")}
                  onClick={() => onToggleMcp(server.server_ref)}
                >
                  {enabled ? "Disable MCP" : "Enable MCP"}
                </button>
              </div>
            </article>
          );
        })}
      </div>

      <div className="ssc-workspace-actions">
        <button
          className="ssc-primary-action"
          type="button"
          onClick={() => void onSaveDistribution()}
          disabled={savingDistribution}
        >
          {savingDistribution ? "Saving..." : "Save MCP access"}
        </button>
      </div>
    </section>
  );
}

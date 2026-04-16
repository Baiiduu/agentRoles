import { useEffect, useMemo, useState } from "react";
import type {
  AgentResourceManagerAgentDto,
  RegisteredMCPServerDto,
} from "../types/agentResourceManager";

interface AgentResourceDistributionPanelProps {
  agent: AgentResourceManagerAgentDto | null;
  mcpServers: RegisteredMCPServerDto[];
  onSaveDistribution: (payload: { mcp_servers: string[]; skills: string[] }) => Promise<void>;
  onSaveWorkspace: (payload: {
    relative_path: string;
    enabled: boolean;
    notes: string;
  }) => Promise<void>;
}

function toggle(items: string[], value: string) {
  return items.includes(value) ? items.filter((item) => item !== value) : [...items, value];
}

function capabilityCount(server: RegisteredMCPServerDto) {
  return server.tool_refs.length || server.discovered_tool_refs.length;
}

export function AgentResourceDistributionPanel({
  agent,
  mcpServers,
  onSaveDistribution,
  onSaveWorkspace,
}: AgentResourceDistributionPanelProps) {
  const [selectedMcp, setSelectedMcp] = useState<string[]>([]);
  const [workspacePath, setWorkspacePath] = useState("");
  const [workspaceEnabled, setWorkspaceEnabled] = useState(true);
  const [workspaceNotes, setWorkspaceNotes] = useState("");

  useEffect(() => {
    setSelectedMcp(agent?.distribution.assigned_mcp_servers || []);
    setWorkspacePath(agent?.distribution.workspace?.relative_path || "");
    setWorkspaceEnabled(agent?.distribution.workspace?.enabled ?? true);
    setWorkspaceNotes(agent?.distribution.workspace?.notes || "");
  }, [agent]);

  const selectedServerCards = useMemo(
    () =>
      selectedMcp
        .map((serverRef) => mcpServers.find((item) => item.server_ref === serverRef))
        .filter((item): item is RegisteredMCPServerDto => Boolean(item)),
    [mcpServers, selectedMcp],
  );

  const availableServerCards = useMemo(
    () =>
      mcpServers.filter(
        (item) => item.enabled && !selectedMcp.includes(item.server_ref),
      ),
    [mcpServers, selectedMcp],
  );

  return (
    <section className="panel resource-distribution-panel">
      <h2 className="panel-title">Agent MCP Access</h2>
      {agent ? (
        <>
          <div className="detail-card">
            <strong>{agent.name}</strong>
            <p>{agent.role}</p>
            <p>{agent.domain || "unknown-domain"}</p>
            <p>{agent.effectiveness.operational_summary}</p>
            <p>{agent.effectiveness.collaboration_summary}</p>
            <div className="tag-row">
              <span className="tag">Connected MCP {selectedMcp.length}</span>
              <span className="tag">Workspace {agent.distribution.workspace?.enabled ? "on" : "off"}</span>
            </div>
            {agent.effectiveness.attention_points.length ? (
              <div className="tag-row">
                {agent.effectiveness.attention_points.map((item) => (
                  <span key={item} className="tag">
                    {item}
                  </span>
                ))}
              </div>
            ) : null}
          </div>

          <div className="mcp-access-board">
            <section className="detail-card">
              <div className="section-head">
                <strong>Current MCP Access</strong>
                <p className="section-copy">当前 agent 已接入的 MCP。点击卡片可移除。</p>
              </div>
              <div className="catalog-grid">
                {selectedServerCards.length ? (
                  selectedServerCards.map((server) => (
                    <button
                      key={server.server_ref}
                      type="button"
                      className="catalog-card selectable-card selected"
                      onClick={() =>
                        setSelectedMcp((current) => current.filter((item) => item !== server.server_ref))
                      }
                    >
                      <strong>{server.name}</strong>
                      <span>{server.server_ref}</span>
                      <p>{server.description || "No description"}</p>
                      <div className="tag-row">
                        <span className="tag">
                          {server.connection_mode} / {server.transport_kind}
                        </span>
                        <span className="tag">{capabilityCount(server)} tools</span>
                      </div>
                    </button>
                  ))
                ) : (
                  <div className="empty-card-state">
                    <strong>No MCP connected yet</strong>
                    <p>从右侧资源池选择 MCP 卡片，这里会立即更新。</p>
                  </div>
                )}
              </div>
            </section>

            <section className="detail-card">
              <div className="section-head">
                <strong>Resource Manager MCP Pool</strong>
                <p className="section-copy">右侧是当前 Resource Manager 已注册且可分配的 MCP。</p>
              </div>
              <div className="catalog-grid">
                {availableServerCards.length ? (
                  availableServerCards.map((server) => (
                    <button
                      key={server.server_ref}
                      type="button"
                      className="catalog-card selectable-card"
                      onClick={() =>
                        setSelectedMcp((current) => toggle(current, server.server_ref))
                      }
                    >
                      <strong>{server.name}</strong>
                      <span>{server.server_ref}</span>
                      <p>{server.description || "No description"}</p>
                      <div className="tag-row">
                        <span className="tag">
                          {server.connection_mode} / {server.transport_kind}
                        </span>
                        <span className="tag">{capabilityCount(server)} tools</span>
                      </div>
                    </button>
                  ))
                ) : (
                  <div className="empty-card-state">
                    <strong>All MCP already selected</strong>
                    <p>当前已注册 MCP 都已经接入这个 agent。</p>
                  </div>
                )}
              </div>
            </section>
          </div>

          <div className="action-row">
            <button
              type="button"
              className="primary-button"
              onClick={() =>
                onSaveDistribution({
                  mcp_servers: selectedMcp,
                  skills: agent.distribution.assigned_skills,
                })
              }
            >
              Save MCP Access
            </button>
          </div>

          <div className="detail-card">
            <div className="section-head">
              <strong>Agent Workspace</strong>
              <p className="section-copy">
                工作区仍然由这个 agent 自己维护，MCP 文件访问会受这里的 workspace 范围约束。
              </p>
            </div>
            <div className="field">
              <label htmlFor="workspace-path">Relative Path</label>
              <input
                id="workspace-path"
                value={workspacePath}
                onChange={(event) => setWorkspacePath(event.target.value)}
              />
            </div>
            <label className="checkbox">
              <input
                type="checkbox"
                checked={workspaceEnabled}
                onChange={(event) => setWorkspaceEnabled(event.target.checked)}
              />
              <span>Workspace enabled</span>
            </label>
            <div className="field">
              <label htmlFor="workspace-notes">Notes</label>
              <textarea
                id="workspace-notes"
                value={workspaceNotes}
                onChange={(event) => setWorkspaceNotes(event.target.value)}
              />
            </div>
            {agent.distribution.workspace ? (
              <div className="detail-block">
                <span className="tag">
                  {agent.distribution.workspace.exists ? "directory ready" : "directory missing"}
                </span>
                <span className="tag">{agent.distribution.workspace.absolute_path}</span>
              </div>
            ) : null}
            <div className="action-row">
              <button
                type="button"
                className="secondary-button"
                onClick={() =>
                  onSaveWorkspace({
                    relative_path: workspacePath,
                    enabled: workspaceEnabled,
                    notes: workspaceNotes,
                  })
                }
                disabled={!workspacePath.trim()}
              >
                Save Workspace
              </button>
            </div>
          </div>
        </>
      ) : (
        <p>Select an agent first.</p>
      )}
    </section>
  );
}

import { useEffect, useMemo, useState } from "react";
import { AgentResourceDistributionPanel } from "../components/AgentResourceDistributionPanel";
import { ResourceManagerNavigator } from "../components/ResourceManagerNavigator";
import { WorkspaceRootPanel } from "../components/WorkspaceRootPanel";
import { api } from "../services/api";
import type { AgentResourceManagerSnapshotDto } from "../types/agentResourceManager";

export function AgentResourceManagerPage() {
  const [snapshot, setSnapshot] = useState<AgentResourceManagerSnapshotDto | null>(null);
  const [selectedAgentId, setSelectedAgentId] = useState("");
  const [error, setError] = useState("");

  async function refreshSnapshot(preferredAgentId?: string) {
    const payload = await api.getAgentResourceManagerSnapshot();
    setSnapshot(payload);
    const nextAgentId =
      preferredAgentId || selectedAgentId || payload.agents[0]?.agent_id || "";
    setSelectedAgentId(nextAgentId);
  }

  useEffect(() => {
    refreshSnapshot().catch((err: Error) => setError(err.message));
  }, []);

  const selectedAgent = useMemo(
    () => snapshot?.agents.find((item) => item.agent_id === selectedAgentId) || null,
    [snapshot, selectedAgentId],
  );

  return (
    <section className="page-shell">
      <header className="page-header">
        <p className="workspace-eyebrow">Resource Manager</p>
        <h2 className="page-title">Agent MCP Access Manager</h2>
        <p className="page-copy">
          这里只保留按 agent 管理 MCP 接入的流程。选择左侧 agent，然后直接在中间完成 MCP 接入和移除。
        </p>
        {snapshot ? (
          <div className="tag-row">
            <span className="tag">MCP: {snapshot.registered_counts.mcp_servers}</span>
            <span className="tag">Workspaces: {snapshot.registered_counts.workspaces}</span>
            <span className="tag">Agents with MCP: {snapshot.distribution_health.agents_with_mcp}</span>
          </div>
        ) : null}
      </header>
      {error ? <div className="error-banner">{error}</div> : null}
      <WorkspaceRootPanel
        workspaceRoot={
          snapshot?.registry.workspace_root || {
            root_path: "",
            enabled: false,
            provisioned: false,
            notes: "",
          }
        }
        resolvedPath={snapshot?.workspace_root_resolved || ""}
        agents={snapshot?.agents || []}
        onSaveRoot={async (payload) => {
          setError("");
          await api.saveAgentWorkspaceRoot(payload);
          await refreshSnapshot(selectedAgentId);
        }}
        onProvision={async () => {
          setError("");
          await api.provisionAgentWorkspaceRoot();
          await refreshSnapshot(selectedAgentId);
        }}
        onBrowse={async () => {
          setError("");
          const payload = await api.pickAgentWorkspaceRoot();
          return payload.root_path;
        }}
      />
      <div className="resource-manager-grid">
        <ResourceManagerNavigator
          agents={snapshot?.agents || []}
          selectedAgentId={selectedAgentId}
          onSelectAgent={setSelectedAgentId}
        />
        <AgentResourceDistributionPanel
          agent={selectedAgent}
          mcpServers={snapshot?.registry.mcp_servers || []}
          onSaveDistribution={async (payload) => {
            if (!selectedAgent) return;
            setError("");
            await api.saveAgentResourceDistribution(selectedAgent.agent_id, payload);
            await refreshSnapshot(selectedAgent.agent_id);
          }}
          onSaveWorkspace={async (payload) => {
            if (!selectedAgent) return;
            setError("");
            await api.saveAgentWorkspace(selectedAgent.agent_id, payload);
            await refreshSnapshot(selectedAgent.agent_id);
          }}
        />
      </div>
    </section>
  );
}

import { useEffect, useMemo, useState } from "react";
import { api } from "../../../services/api";
import type {
  AgentResourceManagerAgentDto,
  AgentResourceManagerSnapshotDto,
  WorkspaceRootConfigDto,
} from "../../../types/agentResourceManager";
import type { SoftwareSupplyChainUiSettingsDto } from "../../../types/softwareSupplyChain";
import { McpManagerAgentRail } from "../components/McpManagerAgentRail";
import { McpWorkspacePanel } from "../components/McpWorkspacePanel";

const SOFTWARE_SUPPLY_CHAIN_DOMAIN = "software_supply_chain";

function filterSupplyChainAgents(snapshot: AgentResourceManagerSnapshotDto | null) {
  return (snapshot?.agents || []).filter(
    (agent) => agent.domain === SOFTWARE_SUPPLY_CHAIN_DOMAIN,
  );
}

function findPreferredAgent(
  agents: AgentResourceManagerAgentDto[],
  preferredAgentId: string,
) {
  if (agents.some((agent) => agent.agent_id === preferredAgentId)) {
    return preferredAgentId;
  }
  return agents[0]?.agent_id || "";
}

export function WorkspaceSettingsWorkspace() {
  const [snapshot, setSnapshot] = useState<AgentResourceManagerSnapshotDto | null>(null);
  const [uiSettings, setUiSettings] = useState<SoftwareSupplyChainUiSettingsDto | null>(null);
  const [selectedAgentId, setSelectedAgentId] = useState("");
  const [workspacePath, setWorkspacePath] = useState("");
  const [workspaceEnabled, setWorkspaceEnabled] = useState(true);
  const [workspaceNotes, setWorkspaceNotes] = useState("");
  const [rootPath, setRootPath] = useState("");
  const [rootNotes, setRootNotes] = useState("");
  const [error, setError] = useState("");
  const [status, setStatus] = useState("");
  const [loading, setLoading] = useState(true);
  const [savingWorkspace, setSavingWorkspace] = useState(false);
  const [savingRoot, setSavingRoot] = useState(false);

  const supplyChainAgents = useMemo(() => filterSupplyChainAgents(snapshot), [snapshot]);
  const selectedAgent =
    supplyChainAgents.find((agent) => agent.agent_id === selectedAgentId) || null;
  const currentRepoUrl = (uiSettings?.current_repo_url || "").trim();

  async function refreshSnapshot(preferredAgentId = selectedAgentId) {
    const [nextSnapshot, nextUiSettings] = await Promise.all([
      api.getAgentResourceManagerSnapshot(),
      api.getSoftwareSupplyChainUiSettings().catch(() => null),
    ]);
    const nextAgents = filterSupplyChainAgents(nextSnapshot);
    const nextAgentId = findPreferredAgent(nextAgents, preferredAgentId);
    const nextAgent = nextAgents.find((agent) => agent.agent_id === nextAgentId) || null;

    setSnapshot(nextSnapshot);
    setUiSettings(nextUiSettings);
    setSelectedAgentId(nextAgentId);
    setWorkspacePath(nextAgent?.distribution.workspace?.relative_path || "");
    setWorkspaceEnabled(nextAgent?.distribution.workspace?.enabled ?? true);
    setWorkspaceNotes(nextAgent?.distribution.workspace?.notes || "");
    setRootPath(nextSnapshot.registry.workspace_root.root_path || "");
    setRootNotes(nextSnapshot.registry.workspace_root.notes || "");
  }

  useEffect(() => {
    refreshSnapshot()
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!selectedAgent) {
      setWorkspacePath("");
      setWorkspaceEnabled(true);
      setWorkspaceNotes("");
      return;
    }
    setWorkspacePath(selectedAgent.distribution.workspace?.relative_path || "");
    setWorkspaceEnabled(selectedAgent.distribution.workspace?.enabled ?? true);
    setWorkspaceNotes(selectedAgent.distribution.workspace?.notes || "");
  }, [selectedAgent]);

  async function handleSaveWorkspace() {
    if (!selectedAgent) return;
    try {
      setSavingWorkspace(true);
      setError("");
      setStatus("");
      await api.saveAgentWorkspace(selectedAgent.agent_id, {
        relative_path: workspacePath,
        enabled: workspaceEnabled,
        notes: workspaceNotes,
      });
      await refreshSnapshot(selectedAgent.agent_id);
      setStatus(`${selectedAgent.name} workspace settings were applied successfully.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save agent workspace");
    } finally {
      setSavingWorkspace(false);
    }
  }

  async function handleBrowseRoot() {
    try {
      setError("");
      const payload = await api.pickAgentWorkspaceRoot();
      if (payload.root_path) {
        setRootPath(payload.root_path);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to browse workspace root");
    }
  }

  async function handleSaveRoot(provision: boolean) {
    try {
      setSavingRoot(true);
      setError("");
      setStatus("");
      const payload: WorkspaceRootConfigDto = {
        root_path: rootPath,
        enabled: Boolean(rootPath.trim()),
        provisioned: snapshot?.registry.workspace_root.provisioned || false,
        notes: rootNotes,
      };
      await api.saveAgentWorkspaceRoot(payload);
      if (provision) {
        await api.provisionAgentWorkspaceRoot();
      }
      await refreshSnapshot(selectedAgentId);
      setStatus(
        provision
          ? "Workspace root saved and agent workspace directories were provisioned."
          : "Workspace root settings were saved.",
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save workspace root");
    } finally {
      setSavingRoot(false);
    }
  }

  if (loading) {
    return (
      <main className="ssc-workspace-shell">
        <div className="ssc-workspace-panel ssc-empty-state">
          <strong>Loading workspace settings...</strong>
          <p>The workspace is preparing supply-chain agents and current workspace registrations.</p>
        </div>
      </main>
    );
  }

  return (
    <main className="ssc-workspace-shell">
      <header className="ssc-workspace-panel ssc-workspace-hero">
        <div className="ssc-workspace-head">
          <p className="ssc-workspace-eyebrow">Workspace Settings</p>
          <h2>Agent Workspace Control</h2>
          <p>Manage workspace boundaries in a dedicated page so those settings stay separate from MCP registration and connection checks.</p>
        </div>
        <div className="ssc-mcp-summary-grid">
          <article className="ssc-mcp-stat-card wide">
            <span>Current GitHub context</span>
            <strong>{currentRepoUrl || "No repository selected yet"}</strong>
          </article>
          <article className="ssc-mcp-stat-card">
            <span>Agents</span>
            <strong>{supplyChainAgents.length}</strong>
          </article>
          <article className="ssc-mcp-stat-card">
            <span>Workspaces Enabled</span>
            <strong>{snapshot?.distribution_health.agents_with_workspaces || 0}</strong>
          </article>
        </div>
      </header>

      <div className="ssc-mcp-shell">
        <McpManagerAgentRail
          agents={supplyChainAgents}
          selectedAgentId={selectedAgentId}
          onSelectAgent={setSelectedAgentId}
          currentRepoUrl={currentRepoUrl}
          serverCount={snapshot?.registry.mcp_servers.length || 0}
        />

        <section className="ssc-mcp-stage">
          {error ? <div className="ssc-inline-error">{error}</div> : null}
          {status ? <div className="ssc-inline-success">{status}</div> : null}
          <McpWorkspacePanel
            agent={selectedAgent}
            workspacePath={workspacePath}
            workspaceEnabled={workspaceEnabled}
            workspaceNotes={workspaceNotes}
            onChangeWorkspacePath={setWorkspacePath}
            onChangeWorkspaceEnabled={setWorkspaceEnabled}
            onChangeWorkspaceNotes={setWorkspaceNotes}
            onSaveWorkspace={handleSaveWorkspace}
            savingWorkspace={savingWorkspace}
            rootPath={rootPath}
            rootNotes={rootNotes}
            rootConfig={
              snapshot?.registry.workspace_root || {
                root_path: "",
                enabled: false,
                provisioned: false,
                notes: "",
              }
            }
            rootResolvedPath={snapshot?.workspace_root_resolved || ""}
            onChangeRootPath={setRootPath}
            onChangeRootNotes={setRootNotes}
            onBrowseRoot={handleBrowseRoot}
            onSaveRoot={handleSaveRoot}
            savingRoot={savingRoot}
          />
        </section>
      </div>
    </main>
  );
}

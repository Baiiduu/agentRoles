import { useEffect, useMemo, useState } from "react";
import { api } from "../../../services/api";
import type {
  AgentResourceManagerAgentDto,
  AgentResourceManagerSnapshotDto,
  RegisteredMCPServerDto,
} from "../../../types/agentResourceManager";
import type { SoftwareSupplyChainUiSettingsDto } from "../../../types/softwareSupplyChain";
import { McpAgentAccessPanel } from "../components/McpAgentAccessPanel";
import { McpManagerAgentRail } from "../components/McpManagerAgentRail";
import { McpSectionTabs, type McpSectionId } from "../components/McpSectionTabs";
import { McpServerInspectorPanel } from "../components/McpServerInspectorPanel";
import { McpServerRegistryPanel } from "../components/McpServerRegistryPanel";
import {
  emptyMcpServerForm,
  workspaceFilesystemPreset,
} from "../mcpManagerUtils";

const SOFTWARE_SUPPLY_CHAIN_DOMAIN = "software_supply_chain";

interface ActionReport {
  tone: "note" | "success" | "error";
  title: string;
  body: string;
}

type McpConnectivityStatus = {
  auth: "idle" | "ready" | "failed";
  connection: "idle" | "healthy" | "failed";
  updatedAt: string | null;
};

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

function findPreferredServer(
  servers: RegisteredMCPServerDto[],
  preferredServerRef: string,
) {
  if (servers.some((server) => server.server_ref === preferredServerRef)) {
    return preferredServerRef;
  }
  return servers[0]?.server_ref || "";
}

export function McpManagerWorkspace() {
  const [snapshot, setSnapshot] = useState<AgentResourceManagerSnapshotDto | null>(null);
  const [uiSettings, setUiSettings] = useState<SoftwareSupplyChainUiSettingsDto | null>(null);
  const [activeSection, setActiveSection] = useState<McpSectionId>("catalog");
  const [selectedAgentId, setSelectedAgentId] = useState("");
  const [selectedServerRef, setSelectedServerRef] = useState("");
  const [serverForm, setServerForm] = useState<RegisteredMCPServerDto>(emptyMcpServerForm);
  const [selectedMcp, setSelectedMcp] = useState<string[]>([]);
  const [statusByServerRef, setStatusByServerRef] = useState<
    Record<string, McpConnectivityStatus>
  >({});
  const [actionReport, setActionReport] = useState<ActionReport | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [savingServer, setSavingServer] = useState(false);
  const [runningInspectorAction, setRunningInspectorAction] = useState(false);
  const [savingDistribution, setSavingDistribution] = useState(false);

  const supplyChainAgents = useMemo(() => filterSupplyChainAgents(snapshot), [snapshot]);
  const selectedAgent =
    supplyChainAgents.find((agent) => agent.agent_id === selectedAgentId) || null;
  const currentRepoUrl = (uiSettings?.current_repo_url || "").trim();
  const enabledServers = useMemo(() => {
    const allServers = snapshot?.registry.mcp_servers || [];
    return allServers.filter((server) => selectedMcp.includes(server.server_ref));
  }, [snapshot, selectedMcp]);
  const selectedCatalogServer =
    snapshot?.registry.mcp_servers.find((server) => server.server_ref === selectedServerRef) || null;
  const selectedEnabledServer =
    enabledServers.find((server) => server.server_ref === selectedServerRef) || null;

  async function refreshSnapshot(
    preferredAgentId = selectedAgentId,
    preferredServer = selectedServerRef,
  ) {
    const [nextSnapshot, nextUiSettings] = await Promise.all([
      api.getAgentResourceManagerSnapshot(),
      api.getSoftwareSupplyChainUiSettings().catch(() => null),
    ]);
    const nextAgents = filterSupplyChainAgents(nextSnapshot);
    const nextAgentId = findPreferredAgent(nextAgents, preferredAgentId);
    const nextServerRef = findPreferredServer(
      nextSnapshot.registry.mcp_servers,
      preferredServer,
    );

    setSnapshot(nextSnapshot);
    setUiSettings(nextUiSettings);
    setSelectedAgentId(nextAgentId);
    setSelectedServerRef(nextServerRef);

    const nextServer =
      nextSnapshot.registry.mcp_servers.find(
        (server) => server.server_ref === nextServerRef,
      ) || null;
    setServerForm(nextServer ? { ...nextServer } : { ...emptyMcpServerForm });

    const nextAgent = nextAgents.find((agent) => agent.agent_id === nextAgentId) || null;
    setSelectedMcp(nextAgent?.distribution.assigned_mcp_servers || []);
  }

  useEffect(() => {
    refreshSnapshot()
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!selectedCatalogServer) {
      setServerForm({ ...emptyMcpServerForm });
      return;
    }
    setServerForm({ ...selectedCatalogServer });
  }, [selectedServerRef, selectedCatalogServer]);

  useEffect(() => {
    if (!selectedAgent) {
      setSelectedMcp([]);
      return;
    }
    setSelectedMcp(selectedAgent.distribution.assigned_mcp_servers || []);
  }, [selectedAgent]);

  useEffect(() => {
    if (activeSection !== "connectivity") return;
    if (!enabledServers.length) {
      if (selectedServerRef) {
        setSelectedServerRef("");
      }
      return;
    }
    if (!enabledServers.some((server) => server.server_ref === selectedServerRef)) {
      setSelectedServerRef(enabledServers[0].server_ref);
    }
  }, [activeSection, enabledServers, selectedServerRef]);

  async function handleSaveServer() {
    try {
      setSavingServer(true);
      setError("");
      setActionReport(null);
      await api.saveRegisteredMcpServer(serverForm.server_ref, serverForm);
      await refreshSnapshot(selectedAgentId, serverForm.server_ref);
      setActionReport({
        tone: "success",
        title: "MCP saved",
        body: `${serverForm.server_ref} is now in the registry and ready for connectivity checks or agent access.`,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save MCP");
    } finally {
      setSavingServer(false);
    }
  }

  async function handleTest() {
    if (!selectedEnabledServer) return;
    try {
      setRunningInspectorAction(true);
      setError("");
      const payload = await api.testRegisteredMcpServer(selectedEnabledServer.server_ref);
      setStatusByServerRef((current) => ({
        ...current,
        [selectedEnabledServer.server_ref]: {
          auth: current[selectedEnabledServer.server_ref]?.auth || "idle",
          connection: payload.ok ? "healthy" : "failed",
          updatedAt: new Date().toISOString(),
        },
      }));
      setActionReport({
        tone: "success",
        title: payload.ok ? "Connection healthy" : "Connection check failed",
        body: `${payload.server_ref} returned ${payload.tool_count} tools over ${payload.transport_kind}.`,
      });
    } catch (err) {
      const message = err instanceof Error ? err.message : "Connection test failed";
      setStatusByServerRef((current) => ({
        ...current,
        [selectedEnabledServer.server_ref]: {
          auth: current[selectedEnabledServer.server_ref]?.auth || "idle",
          connection: "failed",
          updatedAt: new Date().toISOString(),
        },
      }));
      setError(message);
      setActionReport({
        tone: "error",
        title: "Connection test failed",
        body: message,
      });
    } finally {
      setRunningInspectorAction(false);
    }
  }

  async function handleAuthenticate() {
    if (!selectedEnabledServer) return;
    try {
      setRunningInspectorAction(true);
      setError("");
      const payload = await api.authenticateRegisteredMcpServer(
        selectedEnabledServer.server_ref,
      );
      setStatusByServerRef((current) => ({
        ...current,
        [selectedEnabledServer.server_ref]: {
          auth: "ready",
          connection: current[selectedEnabledServer.server_ref]?.connection || "idle",
          updatedAt: new Date().toISOString(),
        },
      }));
      setActionReport({
        tone: "success",
        title: "Authentication complete",
        body: `${payload.server_ref} completed ${payload.auth_flow} and is ready for later MCP usage.`,
      });
      await refreshSnapshot(selectedAgentId, selectedEnabledServer.server_ref);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Authentication failed";
      setStatusByServerRef((current) => ({
        ...current,
        [selectedEnabledServer.server_ref]: {
          auth: "failed",
          connection: current[selectedEnabledServer.server_ref]?.connection || "idle",
          updatedAt: new Date().toISOString(),
        },
      }));
      setError(message);
      setActionReport({
        tone: "error",
        title: "Authentication failed",
        body: message,
      });
    } finally {
      setRunningInspectorAction(false);
    }
  }

  async function handleSaveDistribution() {
    if (!selectedAgent) return;
    try {
      setSavingDistribution(true);
      setError("");
      await api.saveAgentResourceDistribution(selectedAgent.agent_id, {
        mcp_servers: selectedMcp,
        skills: selectedAgent.distribution.assigned_skills,
      });
      await refreshSnapshot(selectedAgent.agent_id, selectedServerRef);
      setActionReport({
        tone: "success",
        title: "Agent access updated",
        body: `${selectedAgent.name} now has ${selectedMcp.length} MCP bindings.`,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save agent access");
    } finally {
      setSavingDistribution(false);
    }
  }

  if (loading) {
    return (
      <main className="ssc-workspace-shell">
        <div className="ssc-workspace-panel ssc-empty-state">
          <strong>Loading MCP manager...</strong>
          <p>The workspace is preparing the registry, supply-chain agents, and GitHub context.</p>
        </div>
      </main>
    );
  }

  return (
    <main className="ssc-workspace-shell">
      <header className="ssc-workspace-panel ssc-workspace-hero">
        <div className="ssc-workspace-head">
          <p className="ssc-workspace-eyebrow">MCP Manager</p>
          <h2>Supply Chain MCP Control Plane</h2>
          <p>Keep MCP work focused: define the catalog, check server reachability, then enable access for the right agent.</p>
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
            <span>Registered MCP</span>
            <strong>{snapshot?.registered_counts.mcp_servers || 0}</strong>
          </article>
          <article className="ssc-mcp-stat-card">
            <span>Agents With MCP</span>
            <strong>{snapshot?.distribution_health.agents_with_mcp || 0}</strong>
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
          <div className="ssc-workspace-panel ssc-mcp-stage-panel">
            <div className="ssc-mcp-stage-head">
              <div className="ssc-workspace-head">
                <p className="ssc-workspace-eyebrow">Workflow</p>
                <h2>MCP Setup Flow</h2>
                <p>Move through one task at a time instead of juggling every control in one screen.</p>
              </div>
              <div className="ssc-agent-chip-row">
                {selectedAgent ? (
                  <span className="ssc-agent-chip">Agent: {selectedAgent.name}</span>
                ) : null}
                {selectedCatalogServer ? (
                  <span className="ssc-agent-chip">
                    Server: {selectedCatalogServer.name || selectedCatalogServer.server_ref}
                  </span>
                ) : null}
              </div>
            </div>

            <McpSectionTabs
              activeSection={activeSection}
              onChangeSection={setActiveSection}
            />

            {error ? <div className="ssc-inline-error">{error}</div> : null}
            {actionReport ? (
              <div
                className={
                  actionReport.tone === "error"
                    ? "ssc-inline-error"
                    : actionReport.tone === "success"
                      ? "ssc-inline-success"
                      : "ssc-inline-note"
                }
              >
                <strong>{actionReport.title}</strong>
                <div>{actionReport.body}</div>
              </div>
            ) : null}

            {activeSection === "catalog" ? (
              <McpServerRegistryPanel
                form={serverForm}
                onChangeForm={setServerForm}
                onResetForm={() => {
                  setServerForm({ ...emptyMcpServerForm });
                  setSelectedServerRef("");
                  setActionReport({
                    tone: "note",
                    title: "Blank MCP form ready",
                    body: "You can now draft a fresh MCP server definition without editing the current one.",
                  });
                }}
                onUsePreset={() => {
                  setServerForm({ ...workspaceFilesystemPreset });
                  setSelectedServerRef("");
                  setActionReport({
                    tone: "note",
                    title: "Filesystem preset loaded",
                    body: "This preset is a good starting point when you want workspace-scoped file tools.",
                  });
                }}
                onSaveServer={handleSaveServer}
                selectedServerRef={selectedServerRef}
                onSelectServer={setSelectedServerRef}
                servers={snapshot?.registry.mcp_servers || []}
                saving={savingServer}
              />
            ) : null}

            {activeSection === "connectivity" ? (
              <McpServerInspectorPanel
                servers={enabledServers}
                selectedServerRef={selectedServerRef}
                onSelectServer={setSelectedServerRef}
                statusByServerRef={statusByServerRef}
                actionReport={actionReport}
                busy={runningInspectorAction}
                onAuthenticate={handleAuthenticate}
                onTest={handleTest}
              />
            ) : null}

            {activeSection === "access" ? (
              <McpAgentAccessPanel
                agent={selectedAgent}
                selectedMcp={selectedMcp}
                onToggleMcp={(serverRef) =>
                  setSelectedMcp((current) =>
                    current.includes(serverRef)
                      ? current.filter((item) => item !== serverRef)
                      : [...current, serverRef],
                  )
                }
                onSaveDistribution={handleSaveDistribution}
                savingDistribution={savingDistribution}
                servers={snapshot?.registry.mcp_servers || []}
              />
            ) : null}
          </div>
        </section>
      </div>
    </main>
  );
}

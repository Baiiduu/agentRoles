import { useEffect, useMemo, useState } from "react";
import { api } from "../../../services/api";
import type {
  AgentResourceManagerAgentDto,
  AgentResourceManagerSnapshotDto,
} from "../../../types/agentResourceManager";
import type { SoftwareSupplyChainUiSettingsDto } from "../../../types/softwareSupplyChain";
import { McpManagerAgentRail } from "../components/McpManagerAgentRail";
import { SkillsManagerPanel } from "../components/SkillsManagerPanel";
import { SkillsSectionTabs, type SkillsSectionId } from "../components/SkillsSectionTabs";

const SOFTWARE_SUPPLY_CHAIN_DOMAIN = "software_supply_chain";

interface ActionReport {
  tone: "note" | "success" | "error";
  title: string;
  body: string;
}

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

export function SkillsManagerWorkspace() {
  const [snapshot, setSnapshot] = useState<AgentResourceManagerSnapshotDto | null>(null);
  const [uiSettings, setUiSettings] = useState<SoftwareSupplyChainUiSettingsDto | null>(null);
  const [activeSection, setActiveSection] = useState<SkillsSectionId>("guide");
  const [selectedAgentId, setSelectedAgentId] = useState("");
  const [selectedSkills, setSelectedSkills] = useState<string[]>([]);
  const [actionReport, setActionReport] = useState<ActionReport | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [savingDistribution, setSavingDistribution] = useState(false);

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
    setSelectedSkills(nextAgent?.distribution.assigned_skills || []);
  }

  useEffect(() => {
    refreshSnapshot()
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!selectedAgent) {
      setSelectedSkills([]);
      return;
    }
    setSelectedSkills(selectedAgent.distribution.assigned_skills || []);
  }, [selectedAgent]);

  async function handleSaveDistribution() {
    if (!selectedAgent) return;
    try {
      setSavingDistribution(true);
      setError("");
      await api.saveAgentResourceDistribution(selectedAgent.agent_id, {
        mcp_servers: selectedAgent.distribution.assigned_mcp_servers,
        skills: selectedSkills,
      });
      await refreshSnapshot(selectedAgent.agent_id);
      setActionReport({
        tone: "success",
        title: "Skill access updated",
        body: `${selectedAgent.name} now has ${selectedSkills.length} enabled skills.`,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to save skill access");
      setActionReport({
        tone: "error",
        title: "Skill access failed",
        body: err instanceof Error ? err.message : "Failed to save skill access",
      });
    } finally {
      setSavingDistribution(false);
    }
  }

  if (loading) {
    return (
      <main className="ssc-workspace-shell">
        <div className="ssc-workspace-panel ssc-empty-state">
          <strong>Loading skills manager...</strong>
          <p>The workspace is preparing the skill catalog, discovery sources, and agent assignments.</p>
        </div>
      </main>
    );
  }

  return (
    <main className="ssc-workspace-shell">
      <header className="ssc-workspace-panel ssc-workspace-hero">
        <div className="ssc-workspace-head">
          <p className="ssc-workspace-eyebrow">Skills Manager</p>
          <h2>Supply Chain Skills Control Plane</h2>
          <p>Keep skill sources, discovery, and per-agent skill access in one dedicated workspace instead of mixing them into MCP operations.</p>
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
            <span>Registered Skills</span>
            <strong>{snapshot?.registered_counts.skills || 0}</strong>
          </article>
          <article className="ssc-mcp-stat-card">
            <span>Agents With Skills</span>
            <strong>{snapshot?.distribution_health.agents_with_skills || 0}</strong>
          </article>
        </div>
      </header>

      <div className="ssc-mcp-shell">
        <McpManagerAgentRail
          agents={supplyChainAgents}
          selectedAgentId={selectedAgentId}
          onSelectAgent={setSelectedAgentId}
          currentRepoUrl={currentRepoUrl}
          serverCount={snapshot?.registry.skills.length || 0}
        />

        <section className="ssc-mcp-stage">
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

          <div className="ssc-workspace-panel ssc-mcp-stage-panel">
            <div className="ssc-mcp-stage-head">
              <div className="ssc-workspace-head">
                <p className="ssc-workspace-eyebrow">Workflow</p>
                <h2>Skills Setup Flow</h2>
                <p>Start with the guide, then configure sources, review the catalog, and only then assign skills to agents.</p>
              </div>
              <div className="ssc-agent-chip-row">
                {selectedAgent ? (
                  <span className="ssc-agent-chip">Agent: {selectedAgent.name}</span>
                ) : null}
                <span className="ssc-agent-chip">Section: {activeSection}</span>
              </div>
            </div>

            <SkillsSectionTabs
              activeSection={activeSection}
              onChangeSection={setActiveSection}
            />

            <SkillsManagerPanel
              activeSection={activeSection}
              agent={selectedAgent}
              skills={snapshot?.registry.skills || []}
              discoveredSkills={snapshot?.skill_discovery.skills || []}
              discoverySources={snapshot?.skill_discovery.sources || []}
              discoveryConflicts={snapshot?.skill_discovery.conflicts || []}
              skillSources={snapshot?.registry.skill_sources || []}
              selectedSkills={selectedSkills}
              onToggleSkill={(skillName) =>
                setSelectedSkills((current) =>
                  current.includes(skillName)
                    ? current.filter((item) => item !== skillName)
                    : [...current, skillName],
                )
              }
              onSaveDistribution={handleSaveDistribution}
              savingDistribution={savingDistribution}
              onSaveSkill={async (payload) => {
                setError("");
                await api.saveRegisteredSkill(payload.skill_name, payload);
                await refreshSnapshot(selectedAgentId);
                setActionReport({
                  tone: "success",
                  title: "Skill saved",
                  body: `${payload.skill_name} is now available in the shared skill catalog.`,
                });
              }}
              onDeleteSkill={async (skillName) => {
                setError("");
                await api.deleteRegisteredSkill(skillName);
                await refreshSnapshot(selectedAgentId);
                setActionReport({
                  tone: "success",
                  title: "Skill deleted",
                  body: `${skillName} was removed from the shared skill catalog.`,
                });
              }}
              onSaveSkillSource={async (payload) => {
                setError("");
                await api.saveRegisteredSkillSource(payload.source_ref || "", payload);
                await refreshSnapshot(selectedAgentId);
                setActionReport({
                  tone: "success",
                  title: "Skill source saved",
                  body: `${payload.source_ref} was added to the skill discovery sources.`,
                });
              }}
              onDeleteSkillSource={async (sourceRef) => {
                setError("");
                await api.deleteRegisteredSkillSource(sourceRef);
                await refreshSnapshot(selectedAgentId);
                setActionReport({
                  tone: "success",
                  title: "Skill source deleted",
                  body: `${sourceRef} was removed from the saved skill sources.`,
                });
              }}
              onSyncSkills={async () => {
                setError("");
                await api.syncRegisteredSkills();
                await refreshSnapshot(selectedAgentId);
                setActionReport({
                  tone: "success",
                  title: "Skills synced",
                  body: "The skill catalog was refreshed from the active discovery sources.",
                });
              }}
            />
          </div>
        </section>
      </div>
    </main>
  );
}

import { useEffect, useState } from "react";
import type {
  AgentResourceManagerAgentDto,
  DiscoveredSkillDto,
  RegisteredSkillDto,
  SkillDiscoveryConflictDto,
  SkillDiscoverySourceDto,
} from "../../../types/agentResourceManager";
import type { SkillsSectionId } from "./SkillsSectionTabs";

interface SkillsManagerPanelProps {
  activeSection: SkillsSectionId;
  agent: AgentResourceManagerAgentDto | null;
  skills: RegisteredSkillDto[];
  discoveredSkills: DiscoveredSkillDto[];
  discoverySources: SkillDiscoverySourceDto[];
  discoveryConflicts: SkillDiscoveryConflictDto[];
  skillSources: SkillDiscoverySourceDto[];
  selectedSkills: string[];
  onToggleSkill: (skillName: string) => void;
  onSaveDistribution: () => Promise<void>;
  savingDistribution: boolean;
  onSaveSkill: (payload: RegisteredSkillDto) => Promise<void>;
  onDeleteSkill: (skillName: string) => Promise<void>;
  onSaveSkillSource: (payload: SkillDiscoverySourceDto) => Promise<void>;
  onDeleteSkillSource: (sourceRef: string) => Promise<void>;
  onSyncSkills: () => Promise<void>;
}

const emptySkill: RegisteredSkillDto = {
  skill_name: "",
  name: "",
  description: "",
  trigger_kinds: [],
  enabled: true,
  notes: "",
};

const emptySkillSource: SkillDiscoverySourceDto = {
  source_ref: "",
  source_kind: "custom",
  root_path: "",
  label: "",
  enabled: true,
  notes: "",
};

function splitCsv(value: string) {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

export function SkillsManagerPanel({
  activeSection,
  agent,
  skills,
  discoveredSkills,
  discoverySources,
  discoveryConflicts,
  skillSources,
  selectedSkills,
  onToggleSkill,
  onSaveDistribution,
  savingDistribution,
  onSaveSkill,
  onDeleteSkill,
  onSaveSkillSource,
  onDeleteSkillSource,
  onSyncSkills,
}: SkillsManagerPanelProps) {
  const [skillForm, setSkillForm] = useState<RegisteredSkillDto>(emptySkill);
  const [skillSourceForm, setSkillSourceForm] = useState<SkillDiscoverySourceDto>(emptySkillSource);
  const [selectedSkillName, setSelectedSkillName] = useState("");
  const [selectedSourceRef, setSelectedSourceRef] = useState("");

  useEffect(() => {
    if (!selectedSkillName) return;
    const selected = skills.find((item) => item.skill_name === selectedSkillName);
    if (!selected) {
      setSelectedSkillName("");
      setSkillForm(emptySkill);
      return;
    }
    setSkillForm({
      skill_name: selected.skill_name,
      name: selected.name,
      description: selected.description,
      trigger_kinds: [...selected.trigger_kinds],
      enabled: selected.enabled,
      notes: selected.notes,
      source_kind: selected.source_kind,
      source_path: selected.source_path,
      prompt_file: selected.prompt_file,
      metadata: selected.metadata,
    });
  }, [selectedSkillName, skills]);

  useEffect(() => {
    if (!selectedSourceRef) return;
    const selected = skillSources.find((item) => item.source_ref === selectedSourceRef);
    if (!selected) {
      setSelectedSourceRef("");
      setSkillSourceForm(emptySkillSource);
      return;
    }
    setSkillSourceForm({
      source_ref: selected.source_ref,
      source_kind: selected.source_kind,
      root_path: selected.root_path,
      label: selected.label,
      enabled: selected.enabled,
      notes: selected.notes,
    });
  }, [selectedSourceRef, skillSources]);

  return (
    <section className="ssc-workspace-panel ssc-mcp-section-panel">
      <div className="ssc-workspace-head">
        <p className="ssc-workspace-eyebrow">Skills</p>
        <h2>Skill Catalog And Agent Access</h2>
        <p>Move through setup in order instead of handling every skill control at once.</p>
      </div>

      {discoveryConflicts.length ? (
        <div className="ssc-inline-error">
          <strong>Discovery conflicts</strong>
          {discoveryConflicts.map((conflict) => (
            <div key={`${conflict.conflict_kind}:${conflict.skill_name}`}>{conflict.message}</div>
          ))}
        </div>
      ) : null}

      {activeSection === "guide" ? (
        <>
          <div className="ssc-inline-note">
            <strong>How to configure this page</strong>
            <div>1. Open `Skill Sources` first and check whether your skills are already in the default folders.</div>
            <div>2. Add a custom source only if your skills live outside project `.codex/skills` or `CODEX_HOME/skills`.</div>
            <div>3. Run sync after adding or changing sources.</div>
            <div>4. Open `Skill Catalog` only if you want to rename, disable, or annotate a skill.</div>
            <div>5. Open `Agent Access` last and enable only the skills the selected agent actually needs.</div>
          </div>

          <div className="ssc-mcp-summary-grid">
            <article className="ssc-mcp-stat-card">
              <span>Saved Sources</span>
              <strong>{skillSources.length}</strong>
            </article>
            <article className="ssc-mcp-stat-card">
              <span>Discovery Sources</span>
              <strong>{discoverySources.length}</strong>
            </article>
            <article className="ssc-mcp-stat-card">
              <span>Catalog Skills</span>
              <strong>{skills.length}</strong>
            </article>
            <article className="ssc-mcp-stat-card">
              <span>Discovered Skills</span>
              <strong>{discoveredSkills.length}</strong>
            </article>
          </div>

          <div className="ssc-agent-context-card">
            <div className="ssc-agent-context-head">
              <strong>Recommended defaults</strong>
            </div>
            <p className="ssc-agent-context-copy">
              If your repository already has `.codex/skills`, or your machine already uses
              `CODEX_HOME/skills`, try sync before adding anything manually. Many teams only need
              custom sources when they keep shared skill folders outside the project.
            </p>
            <div className="ssc-agent-chip-row">
              <span className="ssc-agent-chip">Default: project .codex/skills</span>
              <span className="ssc-agent-chip">Default: CODEX_HOME/skills</span>
              {agent ? <span className="ssc-agent-chip">Current agent: {agent.name}</span> : null}
            </div>
          </div>
        </>
      ) : null}

      {activeSection === "sources" ? (
        <>
          <div className="ssc-workspace-actions">
            <button className="ssc-secondary-action" type="button" onClick={() => void onSyncSkills()}>
              Sync Skills From Sources
            </button>
            <button
              className="ssc-secondary-action"
              type="button"
              onClick={() => {
                setSelectedSourceRef("");
                setSkillSourceForm(emptySkillSource);
              }}
            >
              New Skill Source
            </button>
          </div>

          <div className="ssc-inline-note">
            <strong>When should I add a source?</strong>
            <div>Add a custom source only when your skill folders are not already visible in the default discovery paths.</div>
          </div>

          <div className="ssc-mcp-form-grid">
            <div className="ssc-field-block">
              <label htmlFor="ssc-skill-source-ref">Source Ref</label>
              <input
                id="ssc-skill-source-ref"
                value={skillSourceForm.source_ref || ""}
                onChange={(event) =>
                  setSkillSourceForm((current) => ({ ...current, source_ref: event.target.value }))
                }
                placeholder="custom.local.skills"
              />
            </div>
            <div className="ssc-field-block">
              <label htmlFor="ssc-skill-source-kind">Source Kind</label>
              <select
                id="ssc-skill-source-kind"
                value={skillSourceForm.source_kind}
                onChange={(event) =>
                  setSkillSourceForm((current) => ({ ...current, source_kind: event.target.value }))
                }
              >
                <option value="custom">custom</option>
                <option value="project">project</option>
                <option value="codex_home">codex_home</option>
              </select>
            </div>
            <div className="ssc-field-block ssc-field-span-2">
              <label htmlFor="ssc-skill-source-root">Root Path</label>
              <input
                id="ssc-skill-source-root"
                value={skillSourceForm.root_path}
                onChange={(event) =>
                  setSkillSourceForm((current) => ({ ...current, root_path: event.target.value }))
                }
                placeholder="E:\\CodexData\\.codex\\skills"
              />
            </div>
            <div className="ssc-field-block">
              <label htmlFor="ssc-skill-source-label">Label</label>
              <input
                id="ssc-skill-source-label"
                value={skillSourceForm.label}
                onChange={(event) =>
                  setSkillSourceForm((current) => ({ ...current, label: event.target.value }))
                }
                placeholder="Team Skills Folder"
              />
            </div>
            <div className="ssc-field-block">
              <label htmlFor="ssc-skill-source-notes">Notes</label>
              <input
                id="ssc-skill-source-notes"
                value={skillSourceForm.notes || ""}
                onChange={(event) =>
                  setSkillSourceForm((current) => ({ ...current, notes: event.target.value }))
                }
                placeholder="Who owns this source?"
              />
            </div>
            <div className="ssc-field-block">
              <label className="checkbox">
                <input
                  type="checkbox"
                  checked={skillSourceForm.enabled ?? true}
                  onChange={(event) =>
                    setSkillSourceForm((current) => ({ ...current, enabled: event.target.checked }))
                  }
                />
                <span>Source enabled</span>
              </label>
            </div>
          </div>

          <div className="ssc-workspace-actions">
            <button
              className="ssc-primary-action"
              type="button"
              onClick={async () => {
                await onSaveSkillSource(skillSourceForm);
                setSelectedSourceRef(skillSourceForm.source_ref || "");
              }}
              disabled={!skillSourceForm.source_ref?.trim() || !skillSourceForm.root_path.trim()}
            >
              Save Skill Source
            </button>
            <button
              className="ssc-secondary-action"
              type="button"
              onClick={async () => {
                if (!skillSourceForm.source_ref?.trim()) return;
                await onDeleteSkillSource(skillSourceForm.source_ref);
                setSelectedSourceRef("");
                setSkillSourceForm(emptySkillSource);
              }}
              disabled={!skillSourceForm.source_ref?.trim()}
            >
              Delete Skill Source
            </button>
          </div>

          <div className="ssc-mcp-catalog-list">
            {skillSources.map((source) => (
              <article
                key={`${source.source_ref}:${source.root_path}`}
                className={[
                  "ssc-mcp-catalog-row",
                  source.source_ref === selectedSourceRef ? "active" : "",
                ].filter(Boolean).join(" ")}
              >
                <button
                  type="button"
                  className="ssc-mcp-catalog-main"
                  onClick={() => setSelectedSourceRef(source.source_ref || "")}
                >
                  <div className="ssc-agent-card-head">
                    <strong>{source.label}</strong>
                    <span className="ssc-current-pill">{source.enabled ? source.source_kind : "disabled"}</span>
                  </div>
                  <span className="ssc-mcp-catalog-ref">{source.source_ref}</span>
                </button>
                <div className="ssc-agent-chip-row">
                  <span className="ssc-agent-chip">{source.root_path}</span>
                </div>
              </article>
            ))}
          </div>

          <div className="ssc-mcp-catalog-list">
            {discoverySources.map((source) => (
              <article key={`${source.source_ref}:${source.root_path}`} className="ssc-mcp-catalog-row">
                <div className="ssc-mcp-catalog-main">
                  <div className="ssc-agent-card-head">
                    <strong>{source.label}</strong>
                    <span className="ssc-agent-role">discovery source</span>
                  </div>
                  <span className="ssc-mcp-catalog-ref">{source.root_path}</span>
                </div>
              </article>
            ))}
          </div>
        </>
      ) : null}

      {activeSection === "catalog" ? (
        <>
          <div className="ssc-workspace-actions">
            <button className="ssc-secondary-action" type="button" onClick={() => void onSyncSkills()}>
              Sync Skills From Sources
            </button>
            <button
              className="ssc-secondary-action"
              type="button"
              onClick={() => {
                setSelectedSkillName("");
                setSkillForm(emptySkill);
              }}
            >
              New Skill
            </button>
          </div>

          <div className="ssc-inline-note">
            <strong>When should I edit a skill?</strong>
            <div>Edit the catalog when you want to disable a skill, improve its label, or add notes for your team. You usually do not need to create catalog entries before sync.</div>
          </div>

          <div className="ssc-mcp-form-grid">
            <div className="ssc-field-block">
              <label htmlFor="ssc-skill-name">Skill Name</label>
              <input
                id="ssc-skill-name"
                value={skillForm.skill_name}
                onChange={(event) =>
                  setSkillForm((current) => ({ ...current, skill_name: event.target.value }))
                }
                placeholder="frontend-dev"
              />
            </div>
            <div className="ssc-field-block">
              <label htmlFor="ssc-skill-display-name">Display Name</label>
              <input
                id="ssc-skill-display-name"
                value={skillForm.name}
                onChange={(event) =>
                  setSkillForm((current) => ({ ...current, name: event.target.value }))
                }
                placeholder="Frontend Dev"
              />
            </div>
            <div className="ssc-field-block ssc-field-span-2">
              <label htmlFor="ssc-skill-description">Description</label>
              <textarea
                id="ssc-skill-description"
                value={skillForm.description}
                onChange={(event) =>
                  setSkillForm((current) => ({ ...current, description: event.target.value }))
                }
                placeholder="What this skill is for."
              />
            </div>
            <div className="ssc-field-block">
              <label htmlFor="ssc-skill-triggers">Trigger Kinds</label>
              <input
                id="ssc-skill-triggers"
                value={skillForm.trigger_kinds.join(", ")}
                onChange={(event) =>
                  setSkillForm((current) => ({
                    ...current,
                    trigger_kinds: splitCsv(event.target.value),
                  }))
                }
                placeholder="analysis, handoff"
              />
            </div>
            <div className="ssc-field-block">
              <label htmlFor="ssc-skill-notes">Notes</label>
              <input
                id="ssc-skill-notes"
                value={skillForm.notes}
                onChange={(event) =>
                  setSkillForm((current) => ({ ...current, notes: event.target.value }))
                }
                placeholder="Manual fallback entry"
              />
            </div>
            <div className="ssc-field-block">
              <label className="checkbox">
                <input
                  type="checkbox"
                  checked={skillForm.enabled}
                  onChange={(event) =>
                    setSkillForm((current) => ({ ...current, enabled: event.target.checked }))
                  }
                />
                <span>Skill enabled</span>
              </label>
            </div>
          </div>

          <div className="ssc-workspace-actions">
            <button
              className="ssc-primary-action"
              type="button"
              onClick={async () => {
                await onSaveSkill(skillForm);
                setSelectedSkillName(skillForm.skill_name);
              }}
              disabled={!skillForm.skill_name.trim()}
            >
              Save Skill
            </button>
            <button
              className="ssc-secondary-action"
              type="button"
              onClick={async () => {
                if (!skillForm.skill_name.trim()) return;
                await onDeleteSkill(skillForm.skill_name);
                setSelectedSkillName("");
                setSkillForm(emptySkill);
              }}
              disabled={!skillForm.skill_name.trim()}
            >
              Delete Skill
            </button>
          </div>

          <div className="ssc-mcp-enable-list">
            {skills.map((skill) => {
              const editing = skill.skill_name === selectedSkillName;
              return (
                <article
                  key={skill.skill_name}
                  className={["ssc-mcp-enable-row", editing ? "active" : ""].filter(Boolean).join(" ")}
                >
                  <div className="ssc-mcp-enable-copy">
                    <div className="ssc-agent-card-head">
                      <strong>{skill.name || skill.skill_name}</strong>
                      <span className="ssc-agent-role">{skill.enabled ? "Enabled" : "Disabled"}</span>
                    </div>
                    <p>{skill.description || "No description yet."}</p>
                    <div className="ssc-agent-chip-row">
                      <span className="ssc-agent-chip">{skill.skill_name}</span>
                      {skill.source_kind ? <span className="ssc-agent-chip">{skill.source_kind}</span> : null}
                      {skill.trigger_kinds.length ? (
                        <span className="ssc-agent-chip">{skill.trigger_kinds.join(", ")}</span>
                      ) : null}
                    </div>
                  </div>
                  <div className="ssc-mcp-enable-actions">
                    <button
                      type="button"
                      className="ssc-secondary-action"
                      onClick={() => setSelectedSkillName(skill.skill_name)}
                    >
                      Edit
                    </button>
                  </div>
                </article>
              );
            })}
          </div>

          <div className="ssc-mcp-catalog-list">
            {discoveredSkills.map((skill) => (
              <article key={`${skill.skill_name}:${skill.prompt_file}`} className="ssc-mcp-catalog-row">
                <div className="ssc-mcp-catalog-main">
                  <div className="ssc-agent-card-head">
                    <strong>{skill.name}</strong>
                    <span className="ssc-agent-role">discovered</span>
                  </div>
                  <span className="ssc-mcp-catalog-ref">{skill.skill_name}</span>
                </div>
                <div className="ssc-agent-chip-row">
                  <span className="ssc-agent-chip">{skill.source_kind}</span>
                  <span className="ssc-agent-chip">{skill.prompt_file}</span>
                </div>
              </article>
            ))}
          </div>
        </>
      ) : null}

      {activeSection === "access" ? (
        <>
          <div className="ssc-agent-context-card">
            <div className="ssc-agent-context-head">
              <strong>{agent?.name || "No agent selected yet"}</strong>
              <span className="ssc-agent-role">{selectedSkills.length} skills enabled</span>
            </div>
            <p className="ssc-agent-context-copy">
              {agent
                ? "Enable only the skills this agent truly needs. You do not need to assign every discovered skill."
                : "Select an agent from the rail first to manage skill access."}
            </p>
            <div className="ssc-agent-chip-row">
              <span className="ssc-agent-chip">Recommended: start with 1-3 skills</span>
            </div>
          </div>

          <div className="ssc-mcp-enable-list">
            {skills.map((skill) => {
              const assigned = selectedSkills.includes(skill.skill_name);
              return (
                <article
                  key={skill.skill_name}
                  className={["ssc-mcp-enable-row", assigned ? "active" : ""].filter(Boolean).join(" ")}
                >
                  <div className="ssc-mcp-enable-copy">
                    <div className="ssc-agent-card-head">
                      <strong>{skill.name || skill.skill_name}</strong>
                      <span className="ssc-agent-role">
                        {skill.enabled ? (assigned ? "Enabled" : "Available") : "Disabled"}
                      </span>
                    </div>
                    <p>{skill.description || "No description yet."}</p>
                    <div className="ssc-agent-chip-row">
                      <span className="ssc-agent-chip">{skill.skill_name}</span>
                      {skill.source_kind ? <span className="ssc-agent-chip">{skill.source_kind}</span> : null}
                      {skill.trigger_kinds.length ? (
                        <span className="ssc-agent-chip">{skill.trigger_kinds.join(", ")}</span>
                      ) : null}
                    </div>
                  </div>
                  <div className="ssc-mcp-enable-actions">
                    <button
                      type="button"
                      className={["ssc-mcp-toggle", assigned ? "active" : ""].filter(Boolean).join(" ")}
                      onClick={() => onToggleSkill(skill.skill_name)}
                      disabled={!skill.enabled}
                    >
                      {assigned ? "Disable Skill" : "Enable Skill"}
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
              disabled={!agent || savingDistribution}
            >
              {savingDistribution ? "Saving..." : "Save Skill Access"}
            </button>
          </div>
        </>
      ) : null}
    </section>
  );
}

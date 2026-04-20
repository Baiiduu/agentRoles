import { useState } from "react";
import type {
  DiscoveredSkillDto,
  RegisteredMCPServerDto,
  RegisteredSkillDto,
  SkillDiscoverySourceDto,
} from "../types/agentResourceManager";

interface ResourceRegistryPanelProps {
  mcpServers: RegisteredMCPServerDto[];
  skills: RegisteredSkillDto[];
  discoveredSkills: DiscoveredSkillDto[];
  discoverySources: SkillDiscoverySourceDto[];
  skillSources: SkillDiscoverySourceDto[];
  onSaveMcpServer: (payload: RegisteredMCPServerDto) => Promise<void>;
  onAuthenticateMcpServer: (serverRef: string) => Promise<void>;
  onTestMcpServer: (serverRef: string) => Promise<void>;
  onDiscoverMcpTools: (serverRef: string) => Promise<void>;
  onSaveSkill: (payload: RegisteredSkillDto) => Promise<void>;
  onSaveSkillSource: (payload: SkillDiscoverySourceDto) => Promise<void>;
  onSyncSkills: () => Promise<void>;
}

const emptyMcp: RegisteredMCPServerDto = {
  server_ref: "",
  name: "",
  description: "",
  connection_mode: "internal",
  transport_kind: "custom",
  command: "",
  args: [],
  endpoint: "",
  env: {},
  cwd: "",
  tool_refs: [],
  discovered_tool_refs: [],
  enabled: true,
  notes: "",
};

const workspaceFilesystemPreset: RegisteredMCPServerDto = {
  server_ref: "filesystem.workspace",
  name: "Workspace Filesystem",
  description: "Allow the agent to operate files inside its assigned workspace directory.",
  connection_mode: "internal",
  transport_kind: "custom",
  command: "",
  args: [],
  endpoint: "",
  env: {},
  cwd: "",
  tool_refs: ["fs.list_dir", "fs.read_file", "fs.write_file", "fs.make_dir", "fs.search_files"],
  discovered_tool_refs: [],
  enabled: true,
  notes: "Restricted to the current agent workspace.",
};

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

function parseEnvLines(value: string) {
  const env: Record<string, string> = {};
  for (const line of value.split("\n")) {
    const trimmed = line.trim();
    if (!trimmed) continue;
    const index = trimmed.indexOf("=");
    if (index <= 0) continue;
    env[trimmed.slice(0, index).trim()] = trimmed.slice(index + 1).trim();
  }
  return env;
}

function formatEnvLines(value: Record<string, string>) {
  return Object.entries(value)
    .map(([key, item]) => `${key}=${item}`)
    .join("\n");
}

export function ResourceRegistryPanel({
  mcpServers,
  skills,
  discoveredSkills,
  discoverySources,
  skillSources,
  onSaveMcpServer,
  onAuthenticateMcpServer,
  onTestMcpServer,
  onDiscoverMcpTools,
  onSaveSkill,
  onSaveSkillSource,
  onSyncSkills,
}: ResourceRegistryPanelProps) {
  const [mcpForm, setMcpForm] = useState(emptyMcp);
  const [skillForm, setSkillForm] = useState(emptySkill);
  const [skillSourceForm, setSkillSourceForm] = useState(emptySkillSource);

  return (
    <section className="panel">
      <h2 className="panel-title">Registry Manager</h2>
      <div className="detail-card">
        <strong>Register MCP Server</strong>
        <div className="action-row" style={{ marginBottom: 12 }}>
          <button
            type="button"
            className="secondary-button"
            onClick={() => setMcpForm(workspaceFilesystemPreset)}
          >
            Use Workspace Filesystem Preset
          </button>
        </div>
        <div className="field">
          <label htmlFor="mcp-server-ref">Server Ref</label>
          <input
            id="mcp-server-ref"
            value={mcpForm.server_ref}
            onChange={(event) =>
              setMcpForm((current) => ({ ...current, server_ref: event.target.value }))
            }
          />
        </div>
        <div className="grid-two">
          <div className="field">
            <label htmlFor="mcp-server-name">Display Name</label>
            <input
              id="mcp-server-name"
              value={mcpForm.name}
              onChange={(event) =>
                setMcpForm((current) => ({ ...current, name: event.target.value }))
              }
            />
          </div>
          <div className="field">
            <label htmlFor="mcp-tool-refs">Tool Refs</label>
            <input
              id="mcp-tool-refs"
              placeholder="tool.alpha, tool.beta"
              value={mcpForm.tool_refs.join(", ")}
              onChange={(event) =>
                setMcpForm((current) => ({
                  ...current,
                  tool_refs: splitCsv(event.target.value),
                }))
              }
            />
          </div>
        </div>
        <div className="grid-two">
          <div className="field">
            <label htmlFor="mcp-connection-mode">Connection Mode</label>
            <select
              id="mcp-connection-mode"
              value={mcpForm.connection_mode}
              onChange={(event) =>
                setMcpForm((current) => ({ ...current, connection_mode: event.target.value }))
              }
            >
              <option value="internal">internal</option>
              <option value="external">external</option>
            </select>
          </div>
          <div className="field">
            <label htmlFor="mcp-transport-kind">Transport</label>
            <select
              id="mcp-transport-kind"
              value={mcpForm.transport_kind}
              onChange={(event) =>
                setMcpForm((current) => ({ ...current, transport_kind: event.target.value }))
              }
            >
              <option value="custom">custom</option>
              <option value="stdio">stdio</option>
              <option value="sse">sse</option>
              <option value="streamable_http">streamable_http</option>
            </select>
          </div>
        </div>
        {mcpForm.connection_mode === "external" ? (
          <>
            <div className="grid-two">
              <div className="field">
                <label htmlFor="mcp-command">Command</label>
                <input
                  id="mcp-command"
                  value={mcpForm.command}
                  onChange={(event) =>
                    setMcpForm((current) => ({ ...current, command: event.target.value }))
                  }
                />
              </div>
              <div className="field">
                <label htmlFor="mcp-args">Args</label>
                <input
                  id="mcp-args"
                  placeholder="arg1, arg2"
                  value={mcpForm.args.join(", ")}
                  onChange={(event) =>
                    setMcpForm((current) => ({ ...current, args: splitCsv(event.target.value) }))
                  }
                />
              </div>
            </div>
            <div className="grid-two">
              <div className="field">
                <label htmlFor="mcp-cwd">Working Directory</label>
                <input
                  id="mcp-cwd"
                  value={mcpForm.cwd}
                  onChange={(event) =>
                    setMcpForm((current) => ({ ...current, cwd: event.target.value }))
                  }
                />
              </div>
              <div className="field">
                <label htmlFor="mcp-endpoint">Endpoint</label>
                <input
                  id="mcp-endpoint"
                  value={mcpForm.endpoint}
                  onChange={(event) =>
                    setMcpForm((current) => ({ ...current, endpoint: event.target.value }))
                  }
                />
              </div>
            </div>
            <div className="field">
              <label htmlFor="mcp-env">Env</label>
              <textarea
                id="mcp-env"
                placeholder={"KEY=value\nANOTHER=value"}
                value={formatEnvLines(mcpForm.env)}
                onChange={(event) =>
                  setMcpForm((current) => ({ ...current, env: parseEnvLines(event.target.value) }))
                }
              />
            </div>
          </>
        ) : null}
        <div className="field">
          <label htmlFor="mcp-description">Description</label>
          <textarea
            id="mcp-description"
            value={mcpForm.description}
            onChange={(event) =>
              setMcpForm((current) => ({ ...current, description: event.target.value }))
            }
          />
        </div>
        <div className="field">
          <label htmlFor="mcp-notes">Notes</label>
          <textarea
            id="mcp-notes"
            value={mcpForm.notes}
            onChange={(event) =>
              setMcpForm((current) => ({ ...current, notes: event.target.value }))
            }
          />
        </div>
        <button
          type="button"
          className="primary-button"
          onClick={async () => {
            await onSaveMcpServer(mcpForm);
            setMcpForm(emptyMcp);
          }}
          disabled={!mcpForm.server_ref.trim()}
        >
          Save MCP Server
        </button>
        <div className="catalog-grid" style={{ marginTop: 14 }}>
          {mcpServers.map((item) => (
            <article key={item.server_ref} className="catalog-card">
              <strong>{item.name}</strong>
              <span>{item.server_ref}</span>
              <p>{item.description || "No description"}</p>
              <p>
                {item.connection_mode} / {item.transport_kind}
              </p>
              {item.tool_refs.length ? <p>Configured: {item.tool_refs.join(", ")}</p> : null}
              {item.command ? <p>Command: {item.command}</p> : null}
              {item.discovered_tool_refs.length ? (
                <p>Discovered: {item.discovered_tool_refs.join(", ")}</p>
              ) : null}
              <div className="action-row" style={{ marginTop: 12 }}>
                <button
                  type="button"
                  className="secondary-button"
                  onClick={() => onAuthenticateMcpServer(item.server_ref)}
                  disabled={item.connection_mode !== "external" || item.transport_kind === "stdio"}
                >
                  Authenticate
                </button>
                <button
                  type="button"
                  className="secondary-button"
                  onClick={() => onTestMcpServer(item.server_ref)}
                  disabled={item.connection_mode !== "external"}
                >
                  Test Connection
                </button>
                <button
                  type="button"
                  className="secondary-button"
                  onClick={() => onDiscoverMcpTools(item.server_ref)}
                  disabled={item.connection_mode !== "external"}
                >
                  Discover Tools
                </button>
              </div>
            </article>
          ))}
        </div>
      </div>

      <div className="detail-card">
        <strong>Register Skill Source</strong>
        <div className="grid-two" style={{ marginTop: 12 }}>
          <div className="field">
            <label htmlFor="skill-source-ref">Source Ref</label>
            <input
              id="skill-source-ref"
              value={skillSourceForm.source_ref || ""}
              onChange={(event) =>
                setSkillSourceForm((current) => ({ ...current, source_ref: event.target.value }))
              }
            />
          </div>
          <div className="field">
            <label htmlFor="skill-source-kind">Source Kind</label>
            <select
              id="skill-source-kind"
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
        </div>
        <div className="grid-two">
          <div className="field">
            <label htmlFor="skill-source-root">Root Path</label>
            <input
              id="skill-source-root"
              value={skillSourceForm.root_path}
              onChange={(event) =>
                setSkillSourceForm((current) => ({ ...current, root_path: event.target.value }))
              }
            />
          </div>
          <div className="field">
            <label htmlFor="skill-source-label">Label</label>
            <input
              id="skill-source-label"
              value={skillSourceForm.label}
              onChange={(event) =>
                setSkillSourceForm((current) => ({ ...current, label: event.target.value }))
              }
            />
          </div>
        </div>
        <div className="field">
          <label htmlFor="skill-source-notes">Notes</label>
          <textarea
            id="skill-source-notes"
            value={skillSourceForm.notes || ""}
            onChange={(event) =>
              setSkillSourceForm((current) => ({ ...current, notes: event.target.value }))
            }
          />
        </div>
        <button
          type="button"
          className="primary-button"
          onClick={async () => {
            await onSaveSkillSource(skillSourceForm);
            setSkillSourceForm(emptySkillSource);
          }}
          disabled={!skillSourceForm.source_ref?.trim() || !skillSourceForm.root_path.trim()}
        >
          Save Skill Source
        </button>
        <div className="catalog-grid" style={{ marginTop: 14 }}>
          {skillSources.map((item) => (
            <article key={`${item.source_ref}:${item.root_path}`} className="catalog-card">
              <strong>{item.label}</strong>
              <span>{item.source_ref}</span>
              <p>{item.root_path}</p>
              <p>Kind: {item.source_kind}</p>
            </article>
          ))}
        </div>
      </div>

      <div className="detail-card">
        <strong>Register Skill</strong>
        <div className="action-row" style={{ marginBottom: 12 }}>
          <button type="button" className="secondary-button" onClick={() => onSyncSkills()}>
            Sync Skills From Sources
          </button>
        </div>
        {discoverySources.length ? (
          <div className="catalog-grid" style={{ marginBottom: 14 }}>
            {discoverySources.map((source) => (
              <article key={`${source.source_kind}:${source.root_path}`} className="catalog-card">
                <strong>{source.label}</strong>
                <span>{source.source_kind}</span>
                <p>{source.root_path}</p>
              </article>
            ))}
          </div>
        ) : (
          <p>No skill sources discovered yet.</p>
        )}
        <div className="field">
          <label htmlFor="skill-name">Skill Name</label>
          <input
            id="skill-name"
            value={skillForm.skill_name}
            onChange={(event) =>
              setSkillForm((current) => ({ ...current, skill_name: event.target.value }))
            }
          />
        </div>
        <div className="grid-two">
          <div className="field">
            <label htmlFor="skill-display-name">Display Name</label>
            <input
              id="skill-display-name"
              value={skillForm.name}
              onChange={(event) =>
                setSkillForm((current) => ({ ...current, name: event.target.value }))
              }
            />
          </div>
          <div className="field">
            <label htmlFor="skill-triggers">Trigger Kinds</label>
            <input
              id="skill-triggers"
              placeholder="analysis, handoff, retrieval"
              value={skillForm.trigger_kinds.join(", ")}
              onChange={(event) =>
                setSkillForm((current) => ({
                  ...current,
                  trigger_kinds: splitCsv(event.target.value),
                }))
              }
            />
          </div>
        </div>
        <div className="field">
          <label htmlFor="skill-description">Description</label>
          <textarea
            id="skill-description"
            value={skillForm.description}
            onChange={(event) =>
              setSkillForm((current) => ({ ...current, description: event.target.value }))
            }
          />
        </div>
        <div className="field">
          <label htmlFor="skill-notes">Notes</label>
          <textarea
            id="skill-notes"
            value={skillForm.notes}
            onChange={(event) =>
              setSkillForm((current) => ({ ...current, notes: event.target.value }))
            }
          />
        </div>
        <button
          type="button"
          className="primary-button"
          onClick={async () => {
            await onSaveSkill(skillForm);
            setSkillForm(emptySkill);
          }}
          disabled={!skillForm.skill_name.trim()}
        >
          Save Skill
        </button>
        <div className="catalog-grid" style={{ marginTop: 14 }}>
          {skills.map((item) => (
            <article key={item.skill_name} className="catalog-card">
              <strong>{item.name}</strong>
              <span>{item.skill_name}</span>
              <p>{item.description || "No description"}</p>
              {item.source_kind ? <p>Source: {item.source_kind}</p> : null}
              {item.prompt_file ? <p>Prompt: {item.prompt_file}</p> : null}
            </article>
          ))}
        </div>
        <strong style={{ display: "block", marginTop: 18 }}>Discovered Skills</strong>
        <div className="catalog-grid" style={{ marginTop: 14 }}>
          {discoveredSkills.map((item) => (
            <article key={`${item.skill_name}:${item.prompt_file}`} className="catalog-card">
              <strong>{item.name}</strong>
              <span>{item.skill_name}</span>
              <p>{item.description || "No description"}</p>
              <p>Source: {item.source_kind}</p>
              <p>Prompt: {item.prompt_file}</p>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}

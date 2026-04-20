import type { RegisteredMCPServerDto } from "../../../types/agentResourceManager";
import {
  capabilityCount,
  formatEnvLines,
  parseEnvLines,
  splitCsv,
} from "../mcpManagerUtils";

interface McpServerRegistryPanelProps {
  form: RegisteredMCPServerDto;
  onChangeForm: (next: RegisteredMCPServerDto) => void;
  onResetForm: () => void;
  onUsePreset: () => void;
  onSaveServer: () => Promise<void>;
  selectedServerRef: string;
  onSelectServer: (serverRef: string) => void;
  servers: RegisteredMCPServerDto[];
  saving: boolean;
}

export function McpServerRegistryPanel({
  form,
  onChangeForm,
  onResetForm,
  onUsePreset,
  onSaveServer,
  selectedServerRef,
  onSelectServer,
  servers,
  saving,
}: McpServerRegistryPanelProps) {
  return (
    <section className="ssc-workspace-panel ssc-mcp-registry-panel">
      <div className="ssc-workspace-head">
        <p className="ssc-workspace-eyebrow">Registry</p>
        <h2>MCP Registry Desk</h2>
        <p>Keep the catalog compact and scannable, then open the editor only for the MCP entry you are shaping.</p>
      </div>

      <div className="ssc-workspace-actions">
        <button className="ssc-secondary-action" type="button" onClick={onUsePreset}>
          Use workspace filesystem preset
        </button>
        <button className="ssc-secondary-action" type="button" onClick={onResetForm}>
          Start a blank MCP entry
        </button>
      </div>

      <div className="ssc-mcp-catalog-list">
        {servers.map((server) => {
          const active = server.server_ref === selectedServerRef;
          return (
            <button
              key={server.server_ref}
              type="button"
              className={["ssc-mcp-catalog-row", active ? "active" : ""].filter(Boolean).join(" ")}
              onClick={() => onSelectServer(server.server_ref)}
            >
              <div className="ssc-mcp-catalog-main">
                <div className="ssc-agent-card-head">
                  <strong>{server.name || server.server_ref}</strong>
                  {active ? <span className="ssc-current-pill">Selected</span> : null}
                </div>
                <span className="ssc-mcp-catalog-ref">{server.server_ref}</span>
              </div>
              <div className="ssc-agent-chip-row">
                <span className="ssc-agent-chip">{server.connection_mode}</span>
                <span className="ssc-agent-chip">{server.transport_kind}</span>
                <span className="ssc-agent-chip">{capabilityCount(server)} tools</span>
                <span className="ssc-agent-chip">{server.enabled ? "enabled" : "disabled"}</span>
              </div>
            </button>
          );
        })}
      </div>

      <div className="ssc-mcp-editor">
        <div className="ssc-mcp-form-grid">
          <div className="ssc-field-block">
            <label htmlFor="ssc-mcp-server-ref">Server Ref</label>
            <input
              id="ssc-mcp-server-ref"
              value={form.server_ref}
              onChange={(event) => onChangeForm({ ...form, server_ref: event.target.value })}
              placeholder="github.audit"
            />
          </div>
          <div className="ssc-field-block">
            <label htmlFor="ssc-mcp-name">Display Name</label>
            <input
              id="ssc-mcp-name"
              value={form.name}
              onChange={(event) => onChangeForm({ ...form, name: event.target.value })}
              placeholder="GitHub Audit Gateway"
            />
          </div>
          <div className="ssc-field-block">
            <label htmlFor="ssc-mcp-tools">Tool Refs</label>
            <input
              id="ssc-mcp-tools"
              value={form.tool_refs.join(", ")}
              onChange={(event) => onChangeForm({ ...form, tool_refs: splitCsv(event.target.value) })}
              placeholder="repo.scan, sbom.fetch"
            />
          </div>
          <div className="ssc-field-block">
            <label htmlFor="ssc-mcp-mode">Connection Mode</label>
            <select
              id="ssc-mcp-mode"
              value={form.connection_mode}
              onChange={(event) => onChangeForm({ ...form, connection_mode: event.target.value })}
            >
              <option value="internal">internal</option>
              <option value="external">external</option>
            </select>
          </div>
          <div className="ssc-field-block">
            <label htmlFor="ssc-mcp-transport">Transport</label>
            <select
              id="ssc-mcp-transport"
              value={form.transport_kind}
              onChange={(event) => onChangeForm({ ...form, transport_kind: event.target.value })}
            >
              <option value="custom">custom</option>
              <option value="stdio">stdio</option>
              <option value="sse">sse</option>
              <option value="streamable_http">streamable_http</option>
            </select>
          </div>
        </div>

        {form.connection_mode === "external" ? (
          <div className="ssc-mcp-form-grid">
            <div className="ssc-field-block">
              <label htmlFor="ssc-mcp-command">Command</label>
              <input
                id="ssc-mcp-command"
                value={form.command}
                onChange={(event) => onChangeForm({ ...form, command: event.target.value })}
                placeholder="npx"
              />
            </div>
            <div className="ssc-field-block">
              <label htmlFor="ssc-mcp-args">Args</label>
              <input
                id="ssc-mcp-args"
                value={form.args.join(", ")}
                onChange={(event) => onChangeForm({ ...form, args: splitCsv(event.target.value) })}
                placeholder="package, --flag"
              />
            </div>
            <div className="ssc-field-block">
              <label htmlFor="ssc-mcp-cwd">Working Directory</label>
              <input
                id="ssc-mcp-cwd"
                value={form.cwd}
                onChange={(event) => onChangeForm({ ...form, cwd: event.target.value })}
                placeholder="E:\\tools\\mcp"
              />
            </div>
            <div className="ssc-field-block">
              <label htmlFor="ssc-mcp-endpoint">Endpoint</label>
              <input
                id="ssc-mcp-endpoint"
                value={form.endpoint}
                onChange={(event) => onChangeForm({ ...form, endpoint: event.target.value })}
                placeholder="http://127.0.0.1:9000/mcp"
              />
            </div>
            <div className="ssc-field-block ssc-field-span-2">
              <label htmlFor="ssc-mcp-env">Env</label>
              <textarea
                id="ssc-mcp-env"
                value={formatEnvLines(form.env)}
                onChange={(event) => onChangeForm({ ...form, env: parseEnvLines(event.target.value) })}
                placeholder={"TOKEN=value\nPROFILE=local"}
              />
            </div>
          </div>
        ) : null}

        <div className="ssc-field-block">
          <label htmlFor="ssc-mcp-description">Description</label>
          <textarea
            id="ssc-mcp-description"
            value={form.description}
            onChange={(event) => onChangeForm({ ...form, description: event.target.value })}
            placeholder="What problem should this MCP solve for the team?"
          />
        </div>

        <div className="ssc-field-block">
          <label htmlFor="ssc-mcp-notes">Notes</label>
          <textarea
            id="ssc-mcp-notes"
            value={form.notes}
            onChange={(event) => onChangeForm({ ...form, notes: event.target.value })}
            placeholder="Auth flow, rate limits, or rollout notes."
          />
        </div>

        <div className="ssc-workspace-actions">
          <button
            className="ssc-primary-action"
            type="button"
            onClick={() => void onSaveServer()}
            disabled={saving || !form.server_ref.trim()}
          >
            {saving ? "Saving..." : "Save MCP"}
          </button>
        </div>
      </div>
    </section>
  );
}

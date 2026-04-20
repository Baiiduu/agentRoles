import type { RegisteredMCPServerDto } from "../../../types/agentResourceManager";

type McpConnectivityStatus = {
  auth: "idle" | "ready" | "failed";
  connection: "idle" | "healthy" | "failed";
  updatedAt: string | null;
};

interface McpActionReport {
  tone: "note" | "success" | "error";
  title: string;
  body: string;
}

interface McpServerInspectorPanelProps {
  servers: RegisteredMCPServerDto[];
  selectedServerRef: string;
  onSelectServer: (serverRef: string) => void;
  statusByServerRef: Record<string, McpConnectivityStatus>;
  actionReport: McpActionReport | null;
  busy: boolean;
  onAuthenticate: () => Promise<void>;
  onTest: () => Promise<void>;
}

function statusLabel(value: "idle" | "ready" | "failed" | "healthy") {
  if (value === "ready") return "auth ready";
  if (value === "healthy") return "connection ok";
  if (value === "failed") return "failed";
  return "pending";
}

export function McpServerInspectorPanel({
  servers,
  selectedServerRef,
  onSelectServer,
  statusByServerRef,
  actionReport,
  busy,
  onAuthenticate,
  onTest,
}: McpServerInspectorPanelProps) {
  const selectedServer =
    servers.find((server) => server.server_ref === selectedServerRef) || null;
  const selectedStatus = selectedServer
    ? statusByServerRef[selectedServer.server_ref] || {
        auth: "idle",
        connection: "idle",
        updatedAt: null,
      }
    : null;

  return (
    <section className="ssc-workspace-panel ssc-mcp-inspector-panel">
      <div className="ssc-workspace-head">
        <p className="ssc-workspace-eyebrow">Connectivity</p>
        <h2>Enabled MCP Connections</h2>
        <p>This view only shows MCP servers that are currently enabled for the active agent, so auth and connection checks stay aligned with real usage.</p>
      </div>

      {servers.length ? (
        <>
          <div className="ssc-mcp-server-grid">
            {servers.map((server) => {
              const active = server.server_ref === selectedServerRef;
              const status = statusByServerRef[server.server_ref] || {
                auth: "idle",
                connection: "idle",
                updatedAt: null,
              };
              return (
                <button
                  key={server.server_ref}
                  type="button"
                  className={["ssc-mcp-server-card", active ? "active" : ""].filter(Boolean).join(" ")}
                  onClick={() => onSelectServer(server.server_ref)}
                >
                  <div className="ssc-agent-card-head">
                    <strong>{server.name || server.server_ref}</strong>
                    {active ? <span className="ssc-current-pill">Selected</span> : null}
                  </div>
                  <div className="ssc-agent-chip-row">
                    <span className="ssc-agent-chip">{server.server_ref}</span>
                    <span className="ssc-agent-chip">{server.transport_kind}</span>
                    <span className={`ssc-status-chip ${status.auth}`}>
                      {statusLabel(status.auth)}
                    </span>
                    <span className={`ssc-status-chip ${status.connection}`}>
                      {statusLabel(status.connection === "healthy" ? "healthy" : status.connection)}
                    </span>
                  </div>
                </button>
              );
            })}
          </div>

          {selectedServer ? (
            <div className="ssc-agent-context-card">
              <div className="ssc-agent-context-head">
                <strong>{selectedServer.name || selectedServer.server_ref}</strong>
                <span className="ssc-agent-role">{selectedServer.transport_kind}</span>
              </div>
              <p className="ssc-agent-context-copy">
                {selectedServer.description || "This MCP does not have a description yet."}
              </p>
              <div className="ssc-agent-chip-row">
                <span className="ssc-agent-chip">Ref: {selectedServer.server_ref}</span>
                <span className="ssc-agent-chip">Mode: {selectedServer.connection_mode}</span>
                {selectedStatus ? (
                  <>
                    <span className={`ssc-status-chip ${selectedStatus.auth}`}>
                      {statusLabel(selectedStatus.auth)}
                    </span>
                    <span className={`ssc-status-chip ${selectedStatus.connection}`}>
                      {statusLabel(
                        selectedStatus.connection === "healthy"
                          ? "healthy"
                          : selectedStatus.connection,
                      )}
                    </span>
                  </>
                ) : null}
              </div>
            </div>
          ) : null}

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

          <div className="ssc-workspace-actions">
            <button
              className="ssc-secondary-action"
              type="button"
              onClick={() => void onAuthenticate()}
              disabled={
                busy ||
                !selectedServer ||
                selectedServer.connection_mode !== "external" ||
                selectedServer.transport_kind === "stdio"
              }
            >
              Authenticate
            </button>
            <button
              className="ssc-primary-action"
              type="button"
              onClick={() => void onTest()}
              disabled={
                busy ||
                !selectedServer ||
                selectedServer.connection_mode !== "external"
              }
            >
              {busy ? "Testing..." : "Test MCP connection"}
            </button>
          </div>
        </>
      ) : (
        <div className="ssc-empty-state">
          <strong>No enabled MCP yet</strong>
          <p>Enable an MCP in Agent Access first. Once it is enabled for the current agent, it will appear here for authentication and connectivity checks.</p>
        </div>
      )}
    </section>
  );
}

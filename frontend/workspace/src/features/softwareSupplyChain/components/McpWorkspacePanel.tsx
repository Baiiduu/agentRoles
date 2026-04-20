import type {
  AgentResourceManagerAgentDto,
  WorkspaceRootConfigDto,
} from "../../../types/agentResourceManager";

interface McpWorkspacePanelProps {
  agent: AgentResourceManagerAgentDto | null;
  workspacePath: string;
  workspaceEnabled: boolean;
  workspaceNotes: string;
  onChangeWorkspacePath: (value: string) => void;
  onChangeWorkspaceEnabled: (value: boolean) => void;
  onChangeWorkspaceNotes: (value: string) => void;
  onSaveWorkspace: () => Promise<void>;
  savingWorkspace: boolean;
  rootPath: string;
  rootNotes: string;
  rootConfig: WorkspaceRootConfigDto;
  rootResolvedPath: string;
  onChangeRootPath: (value: string) => void;
  onChangeRootNotes: (value: string) => void;
  onBrowseRoot: () => Promise<void>;
  onSaveRoot: (provision: boolean) => Promise<void>;
  savingRoot: boolean;
}

export function McpWorkspacePanel({
  agent,
  workspacePath,
  workspaceEnabled,
  workspaceNotes,
  onChangeWorkspacePath,
  onChangeWorkspaceEnabled,
  onChangeWorkspaceNotes,
  onSaveWorkspace,
  savingWorkspace,
  rootPath,
  rootNotes,
  rootConfig,
  rootResolvedPath,
  onChangeRootPath,
  onChangeRootNotes,
  onBrowseRoot,
  onSaveRoot,
  savingRoot,
}: McpWorkspacePanelProps) {
  return (
    <section className="ssc-mcp-workspace-grid">
      <div className="ssc-workspace-panel ssc-mcp-section-panel">
        <div className="ssc-workspace-head">
          <p className="ssc-workspace-eyebrow">Agent Workspace</p>
          <h2>{agent ? `${agent.name} Workspace` : "Agent Workspace"}</h2>
          <p>Keep file-oriented MCP tools inside a deliberate workspace boundary before you enable write access for an agent.</p>
        </div>

        {agent ? (
          <>
            <div className="ssc-field-block">
              <label htmlFor="ssc-agent-workspace-path">Relative Path</label>
              <input
                id="ssc-agent-workspace-path"
                value={workspacePath}
                onChange={(event) => onChangeWorkspacePath(event.target.value)}
                placeholder="software-supply-chain/dependency-auditor"
              />
            </div>
            <label className="ssc-mcp-checkbox">
              <input
                type="checkbox"
                checked={workspaceEnabled}
                onChange={(event) => onChangeWorkspaceEnabled(event.target.checked)}
              />
              <span>Enable workspace for this agent</span>
            </label>
            <div className="ssc-field-block">
              <label htmlFor="ssc-agent-workspace-notes">Notes</label>
              <textarea
                id="ssc-agent-workspace-notes"
                value={workspaceNotes}
                onChange={(event) => onChangeWorkspaceNotes(event.target.value)}
                placeholder="Scope, guardrails, or rollout notes."
              />
            </div>
            {agent.distribution.workspace ? (
              <div className="ssc-agent-chip-row">
                <span className="ssc-agent-chip">
                  {agent.distribution.workspace.exists ? "directory ready" : "directory missing"}
                </span>
                <span className="ssc-agent-chip">{agent.distribution.workspace.absolute_path}</span>
              </div>
            ) : null}
            <div className="ssc-workspace-actions">
              <button
                className="ssc-secondary-action"
                type="button"
                onClick={() => void onSaveWorkspace()}
                disabled={savingWorkspace || !workspacePath.trim()}
              >
                {savingWorkspace ? "Saving..." : "Save workspace"}
              </button>
            </div>
          </>
        ) : (
          <div className="ssc-empty-state">
            <strong>No agent selected yet</strong>
            <p>Select a supply-chain agent from the left rail to manage its workspace boundary.</p>
          </div>
        )}
      </div>

      <div className="ssc-workspace-panel ssc-mcp-section-panel">
        <div className="ssc-workspace-head">
          <p className="ssc-workspace-eyebrow">Global Root</p>
          <h2>Workspace Root</h2>
          <p>Manage the shared root where agent workspaces are provisioned, without mixing this action into MCP registration or access flows.</p>
        </div>

        <div className="ssc-field-block">
          <label htmlFor="ssc-root-path">Root Path</label>
          <input
            id="ssc-root-path"
            value={rootPath}
            onChange={(event) => onChangeRootPath(event.target.value)}
            placeholder="E:\\agent-labs\\software-supply-chain"
          />
        </div>
        <div className="ssc-field-block">
          <label htmlFor="ssc-root-notes">Notes</label>
          <textarea
            id="ssc-root-notes"
            value={rootNotes}
            onChange={(event) => onChangeRootNotes(event.target.value)}
            placeholder="Describe directory policy or host constraints."
          />
        </div>
        <div className="ssc-agent-chip-row">
          <span className="ssc-agent-chip">{rootConfig.provisioned ? "provisioned" : "pending"}</span>
          {rootResolvedPath ? <span className="ssc-agent-chip">{rootResolvedPath}</span> : null}
        </div>
        <div className="ssc-workspace-actions">
          <button
            className="ssc-secondary-action"
            type="button"
            onClick={() => void onBrowseRoot()}
            disabled={savingRoot}
          >
            Browse
          </button>
          <button
            className="ssc-secondary-action"
            type="button"
            onClick={() => void onSaveRoot(false)}
            disabled={savingRoot}
          >
            Save root only
          </button>
          <button
            className="ssc-primary-action"
            type="button"
            onClick={() => void onSaveRoot(true)}
            disabled={savingRoot || !rootPath.trim()}
          >
            {savingRoot ? "Running..." : "Create agent workspaces"}
          </button>
        </div>
      </div>
    </section>
  );
}

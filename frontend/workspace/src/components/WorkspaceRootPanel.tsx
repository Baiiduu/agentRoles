import { useEffect, useState } from "react";
import type { AgentResourceManagerAgentDto, WorkspaceRootConfigDto } from "../types/agentResourceManager";

interface WorkspaceRootPanelProps {
  workspaceRoot: WorkspaceRootConfigDto;
  resolvedPath: string;
  agents: AgentResourceManagerAgentDto[];
  onSaveRoot: (payload: WorkspaceRootConfigDto) => Promise<void>;
  onProvision: () => Promise<void>;
  onBrowse: () => Promise<string>;
}

export function WorkspaceRootPanel({
  workspaceRoot,
  resolvedPath,
  agents,
  onSaveRoot,
  onProvision,
  onBrowse,
}: WorkspaceRootPanelProps) {
  const [rootPath, setRootPath] = useState("");
  const [notes, setNotes] = useState("");

  useEffect(() => {
    setRootPath(workspaceRoot.root_path || "");
    setNotes(workspaceRoot.notes || "");
  }, [workspaceRoot]);

  return (
    <section className="panel">
      <h2 className="panel-title">Global Workspace Root</h2>
      <p className="section-copy">
        先选择总工作目录。仅保存时不会创建真实文件；点创建后，才会在该根目录下生成以 agent 名称命名的子目录。
      </p>

      <div className="field">
        <label htmlFor="workspace-root-path">Root Path</label>
        <div className="action-row" style={{ marginTop: 0 }}>
          <input
            id="workspace-root-path"
            value={rootPath}
            onChange={(event) => setRootPath(event.target.value)}
            placeholder="D:\\agent-labs\\education-workspace"
          />
          <button
            type="button"
            className="secondary-button"
            onClick={async () => {
              const picked = await onBrowse();
              if (picked) {
                setRootPath(picked);
              }
            }}
          >
            Browse
          </button>
        </div>
      </div>

      <div className="field">
        <label htmlFor="workspace-root-notes">Notes</label>
        <textarea
          id="workspace-root-notes"
          value={notes}
          onChange={(event) => setNotes(event.target.value)}
        />
      </div>

      {resolvedPath ? (
        <div className="detail-card compact">
          <strong>Resolved Path</strong>
          <p>{resolvedPath}</p>
          <div className="tag-row">
            <span className={workspaceRoot.provisioned ? "tag success" : "tag"}>
              {workspaceRoot.provisioned ? "provisioned" : "not provisioned"}
            </span>
          </div>
        </div>
      ) : null}

      <div className="detail-card compact">
        <strong>Planned Agent Directories</strong>
        <div className="catalog-grid" style={{ marginTop: 12 }}>
          {agents.map((agent) => (
            <article key={agent.agent_id} className="catalog-card">
              <strong>{agent.name}</strong>
              <p>{rootPath ? `${rootPath}\\${agent.name}` : agent.name}</p>
            </article>
          ))}
        </div>
      </div>

      <div className="action-row">
        <button
          type="button"
          className="secondary-button"
          onClick={() =>
            onSaveRoot({
              root_path: rootPath,
              enabled: Boolean(rootPath.trim()),
              provisioned: workspaceRoot.provisioned,
              notes,
            })
          }
        >
          Save Root Only
        </button>
        <button
          type="button"
          className="primary-button"
          disabled={!rootPath.trim()}
          onClick={async () => {
            await onSaveRoot({
              root_path: rootPath,
              enabled: true,
              provisioned: workspaceRoot.provisioned,
              notes,
            });
            await onProvision();
          }}
        >
          Create Agent Workspaces
        </button>
      </div>
    </section>
  );
}

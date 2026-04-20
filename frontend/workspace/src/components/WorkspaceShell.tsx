import type { PropsWithChildren } from "react";
import type { WorkspacePageKey } from "../types/workspace";

interface WorkspaceShellProps extends PropsWithChildren {
  currentPage: WorkspacePageKey;
  onSelectPage: (page: WorkspacePageKey) => void;
  pageLabels: Record<WorkspacePageKey, string>;
}

export function WorkspaceShell({
  currentPage,
  onSelectPage,
  pageLabels,
  children,
}: WorkspaceShellProps) {
  return (
    <div className="workspace-shell">
      <aside className="workspace-sidebar">
        <p className="workspace-eyebrow">AgentsRoles Console</p>
        <h1 className="workspace-title">Multi-Agent Domain Workspace</h1>
        <p className="workspace-sidebar-copy">
          Explore domain dashboards, agent operations, and execution flows from one shared
          console.
        </p>
        <nav className="workspace-nav">
          {(Object.keys(pageLabels) as WorkspacePageKey[]).map((pageKey) => (
            <button
              key={pageKey}
              className={pageKey === currentPage ? "nav-item active" : "nav-item"}
              onClick={() => onSelectPage(pageKey)}
              type="button"
            >
              {pageLabels[pageKey]}
            </button>
          ))}
        </nav>
      </aside>
      <main className="workspace-main">{children}</main>
    </div>
  );
}

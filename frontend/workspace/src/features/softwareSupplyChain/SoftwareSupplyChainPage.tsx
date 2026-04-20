import { useState } from "react";
import "../../styles/software-supply-chain.css";
import { SoftwareSupplyChainSidebar } from "./components/SoftwareSupplyChainSidebar";
import type { SidebarNavId } from "./types";
import { AgentsWorkspace } from "./workspaces/AgentsWorkspace";
import { GitHubWorkspace } from "./workspaces/GitHubWorkspace";
import { McpManagerWorkspace } from "./workspaces/McpManagerWorkspace";
import { SkillsManagerWorkspace } from "./workspaces/SkillsManagerWorkspace";
import { WorkspaceSettingsWorkspace } from "./workspaces/WorkspaceSettingsWorkspace";

function WorkspaceCanvas({ activeItemId }: { activeItemId: SidebarNavId }) {
  if (activeItemId === "github") {
    return <GitHubWorkspace />;
  }
  if (activeItemId === "agents") {
    return <AgentsWorkspace />;
  }
  if (activeItemId === "mcp") {
    return <McpManagerWorkspace />;
  }
  if (activeItemId === "skills") {
    return <SkillsManagerWorkspace />;
  }
  if (activeItemId === "workspaces") {
    return <WorkspaceSettingsWorkspace />;
  }
  return <main className="ssc-blank-canvas" aria-label="Blank canvas" />;
}

export function SoftwareSupplyChainPage() {
  const [activeItemId, setActiveItemId] = useState<SidebarNavId>("dashboard");

  return (
    <div className="ssc-page">
      <SoftwareSupplyChainSidebar
        activeItemId={activeItemId}
        onSelectItem={setActiveItemId}
      />
      <WorkspaceCanvas activeItemId={activeItemId} />
    </div>
  );
}

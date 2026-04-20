export type SidebarNavId =
  | "dashboard"
  | "github"
  | "agents"
  | "mcp"
  | "skills"
  | "workspaces"
  | "dependencies"
  | "start"
  | "feedback"
  | "settings"
  | "docs"
  | "help";

export type SidebarIconName =
  | "dashboard"
  | "github"
  | "agents"
  | "mcp"
  | "skills"
  | "workspaces"
  | "supply"
  | "grid"
  | "megaphone"
  | "settings"
  | "document"
  | "help";

export interface SidebarNavItem {
  id: SidebarNavId;
  label: string;
  icon: SidebarIconName;
  accent?: boolean;
  value?: string;
}

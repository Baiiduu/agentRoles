import type { SidebarNavItem } from "./types";

export const primarySidebarItems: SidebarNavItem[] = [
  { id: "dashboard", label: "Dashboard", icon: "dashboard" },
  { id: "github", label: "GitHub Links", icon: "github" },
  { id: "agents", label: "Agents", icon: "agents" },
  { id: "mcp", label: "MCP Manager", icon: "mcp" },
  { id: "skills", label: "Skills Manager", icon: "skills" },
  { id: "workspaces", label: "Workspace Settings", icon: "workspaces" },
  { id: "dependencies", label: "Dependencies", icon: "supply" },
];

export const secondarySidebarItems: SidebarNavItem[] = [
  { id: "start", label: "Start", icon: "grid", accent: true, value: "16%" },
  { id: "feedback", label: "Feedback", icon: "megaphone" },
  { id: "settings", label: "Backdrop", icon: "settings" },
  { id: "docs", label: "Docs", icon: "document" },
  { id: "help", label: "Help", icon: "help" },
];

export type McpSectionId = "catalog" | "connectivity" | "access";

interface McpSectionTabsProps {
  activeSection: McpSectionId;
  onChangeSection: (section: McpSectionId) => void;
}

const sections: Array<{
  id: McpSectionId;
  label: string;
  copy: string;
}> = [
  {
    id: "catalog",
    label: "Catalog",
    copy: "Register and edit MCP definitions.",
  },
  {
    id: "connectivity",
    label: "Connectivity",
    copy: "Only test whether an MCP server is reachable.",
  },
  {
    id: "access",
    label: "Agent Access",
    copy: "Enable MCP servers for the current agent.",
  },
];

export function McpSectionTabs({
  activeSection,
  onChangeSection,
}: McpSectionTabsProps) {
  return (
    <nav className="ssc-mcp-tabs" aria-label="MCP sections">
      {sections.map((section) => (
        <button
          key={section.id}
          type="button"
          className={["ssc-mcp-tab", activeSection === section.id ? "active" : ""]
            .filter(Boolean)
            .join(" ")}
          onClick={() => onChangeSection(section.id)}
        >
          <strong>{section.label}</strong>
          <span>{section.copy}</span>
        </button>
      ))}
    </nav>
  );
}

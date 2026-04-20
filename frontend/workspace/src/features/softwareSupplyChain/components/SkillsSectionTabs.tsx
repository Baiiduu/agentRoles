export type SkillsSectionId = "guide" | "sources" | "catalog" | "access";

interface SkillsSectionTabsProps {
  activeSection: SkillsSectionId;
  onChangeSection: (section: SkillsSectionId) => void;
}

const sections: Array<{
  id: SkillsSectionId;
  label: string;
  copy: string;
}> = [
  {
    id: "guide",
    label: "Getting Started",
    copy: "See the recommended setup order and defaults first.",
  },
  {
    id: "sources",
    label: "Skill Sources",
    copy: "Register folders that should be scanned for skills.",
  },
  {
    id: "catalog",
    label: "Skill Catalog",
    copy: "Review discovered skills and edit saved catalog entries.",
  },
  {
    id: "access",
    label: "Agent Access",
    copy: "Choose which skills the selected agent should receive.",
  },
];

export function SkillsSectionTabs({
  activeSection,
  onChangeSection,
}: SkillsSectionTabsProps) {
  return (
    <nav className="ssc-mcp-tabs" aria-label="Skills sections">
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

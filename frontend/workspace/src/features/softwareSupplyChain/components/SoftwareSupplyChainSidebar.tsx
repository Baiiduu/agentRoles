import { primarySidebarItems, secondarySidebarItems } from "../config";
import {
  ButterflyMark,
  ChevronIcon,
  SidebarIcon,
  TopBarIcon,
} from "../SoftwareSupplyChainIcons";
import type { SidebarNavId, SidebarNavItem } from "../types";

interface SoftwareSupplyChainSidebarProps {
  activeItemId: SidebarNavId;
  onSelectItem: (id: SidebarNavId) => void;
}

function SidebarNavButton({
  item,
  active,
  onSelect,
}: {
  item: SidebarNavItem;
  active: boolean;
  onSelect: (id: SidebarNavId) => void;
}) {
  return (
    <button
      className={["ssc-nav-item", active ? "active" : "", item.accent ? "accent" : ""]
        .filter(Boolean)
        .join(" ")}
      type="button"
      onClick={() => onSelect(item.id)}
    >
      <span className="ssc-nav-main">
        <SidebarIcon name={item.icon} className="ssc-nav-icon" />
        <span className="ssc-nav-label">{item.label}</span>
      </span>
      {item.value ? <span className="ssc-nav-value">{item.value}</span> : null}
    </button>
  );
}

export function SoftwareSupplyChainSidebar({
  activeItemId,
  onSelectItem,
}: SoftwareSupplyChainSidebarProps) {
  return (
    <aside className="ssc-sidebar">
      <div className="ssc-sidebar-top">
        <div className="ssc-org-switcher">
          <button className="ssc-icon-button" type="button" aria-label="Open menu">
            <TopBarIcon />
          </button>
          <div className="ssc-org-title">software-supply-chain</div>
          <button className="ssc-icon-button" type="button" aria-label="Switch workspace">
            <ChevronIcon />
          </button>
        </div>

        <nav className="ssc-nav-group" aria-label="Primary navigation">
          {primarySidebarItems.map((item) => (
            <SidebarNavButton
              key={item.id}
              item={item}
              active={activeItemId === item.id}
              onSelect={onSelectItem}
            />
          ))}
        </nav>
      </div>

      <div className="ssc-sidebar-bottom">
        <nav className="ssc-nav-group secondary" aria-label="Secondary navigation">
          {secondarySidebarItems.map((item) => (
            <SidebarNavButton
              key={item.id}
              item={item}
              active={activeItemId === item.id}
              onSelect={onSelectItem}
            />
          ))}
        </nav>

        <div className="ssc-sidebar-mark">
          <ButterflyMark />
        </div>
      </div>
    </aside>
  );
}

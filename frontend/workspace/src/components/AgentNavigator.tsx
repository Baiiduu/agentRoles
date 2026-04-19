import type { AgentCapabilityDto } from "../types/agentCapability";
import type {
  AgentBootstrapItem,
  AgentDescriptorDto,
  AgentTreeNode,
} from "../types/agentPlayground";

interface AgentNavigatorProps {
  agents: AgentBootstrapItem[];
  agentTree: AgentTreeNode[];
  selectedAgentId: string;
  onSelectAgent: (agentId: string) => void;
  agentDetail: AgentDescriptorDto | null;
  capabilityDetail?: AgentCapabilityDto | null;
}

export function AgentNavigator({
  agents,
  agentTree,
  selectedAgentId,
  onSelectAgent,
  agentDetail,
  capabilityDetail,
}: AgentNavigatorProps) {
  return (
    <section className="panel playground-sidebar-panel">
      <div className="playground-sidebar-head">
        <p className="workspace-eyebrow">Agents</p>
        <h2 className="panel-title">Choose Agent</h2>
      </div>

      <div className="agent-tree compact">
        {(agentTree.length ? agentTree : buildFallbackTree(agents)).map((node) => (
          <AgentTreeBranch
            key={node.node_id}
            node={node}
            selectedAgentId={selectedAgentId}
            onSelectAgent={onSelectAgent}
            depth={0}
          />
        ))}
      </div>

      {agentDetail ? (
        <div className="detail-card compact">
          <strong>{agentDetail.name}</strong>
          <p>{agentDetail.description}</p>

          <div className="tag-row">
            {agentDetail.domain ? <span className="tag">{agentDetail.domain}</span> : null}
            {agentDetail.capabilities.map((item) => (
              <span key={item} className="tag">
                {item}
              </span>
            ))}
          </div>

          {capabilityDetail?.resolved_preview ? (
            <div className="detail-block">
              <div className="tag-row">
                <span className="tag">
                  approval: {capabilityDetail.resolved_preview.approval_policy.mode}
                </span>
                <span className="tag">
                  handoff: {capabilityDetail.resolved_preview.handoff_policy.mode}
                </span>
              </div>
              {(capabilityDetail.resolved_preview.enabled_mcp_servers || []).length ? (
                <div className="tag-row">
                  {capabilityDetail.resolved_preview.enabled_mcp_servers.map((item) => (
                    <span key={item} className="tag">
                      MCP: {item}
                    </span>
                  ))}
                </div>
              ) : null}
              {(capabilityDetail.resolved_preview.enabled_skills || []).length ? (
                <div className="tag-row">
                  {capabilityDetail.resolved_preview.enabled_skills.map((item) => (
                    <span key={item} className="tag">
                      Skill: {item}
                    </span>
                  ))}
                </div>
              ) : null}
              {capabilityDetail.resolved_preview.workspace?.enabled &&
              capabilityDetail.resolved_preview.workspace.relative_path ? (
                <div className="tag-row">
                  <span className="tag">
                    workspace: {capabilityDetail.resolved_preview.workspace.relative_path}
                  </span>
                </div>
              ) : null}
            </div>
          ) : null}

          {agentDetail.mcp_servers.length ? (
            <div className="detail-block">
              <strong>Connected Resources</strong>
              <div className="tag-row">
                {agentDetail.mcp_servers.map((server) => (
                  <span key={server.server_ref} className="tag">
                    {server.server_ref} ({server.tool_count})
                  </span>
                ))}
              </div>
              <p>Show connected MCP servers only. Concrete tool names stay inside the run timeline instead of the sidebar.</p>
            </div>
          ) : null}

          <div className="detail-block">
            <strong>Tool Surface</strong>
            <div className="tag-row">
              <span className="tag">
                local: {agentDetail.tool_catalog.local_tools.length}
              </span>
              <span className="tag">
                mcp: {agentDetail.tool_catalog.mcp_tools.length}
              </span>
            </div>
            <p>
              This panel stays high level so the main console can focus on live progress,
              decisions, and validation.
            </p>
          </div>
        </div>
      ) : (
        <div className="detail-card compact">
          <p>Loading agent details...</p>
        </div>
      )}
    </section>
  );
}

interface AgentTreeBranchProps {
  node: AgentTreeNode;
  selectedAgentId: string;
  onSelectAgent: (agentId: string) => void;
  depth: number;
}

function AgentTreeBranch({
  node,
  selectedAgentId,
  onSelectAgent,
  depth,
}: AgentTreeBranchProps) {
  if (node.kind === "agent" && node.agent_id) {
    return (
      <button
        type="button"
        className={node.agent_id === selectedAgentId ? "agent-tree-item active" : "agent-tree-item"}
        style={{ paddingLeft: 14 + depth * 16 }}
        onClick={() => onSelectAgent(node.agent_id!)}
        title={node.description || node.label || node.name}
      >
        <span className="agent-tree-icon">•</span>
        <span className="agent-tree-content">
          <strong>{node.label || node.name}</strong>
          <span>{node.role || node.domain || "agent"}</span>
        </span>
      </button>
    );
  }

  const children = node.children || [];
  return (
    <details className="agent-tree-group" open>
      <summary className="agent-tree-summary" style={{ paddingLeft: 10 + depth * 16 }}>
        <span className="agent-tree-caret">▾</span>
        <span>{formatTreeGroupName(node.name)}</span>
      </summary>
      <div className="agent-tree-children">
        {children.map((child) => (
          <AgentTreeBranch
            key={child.node_id}
            node={child}
            selectedAgentId={selectedAgentId}
            onSelectAgent={onSelectAgent}
            depth={depth + 1}
          />
        ))}
      </div>
    </details>
  );
}

function buildFallbackTree(agents: AgentBootstrapItem[]): AgentTreeNode[] {
  const groups = new Map<string, AgentBootstrapItem[]>();
  agents.forEach((agent) => {
    const domain = agent.domain || "ungrouped";
    const current = groups.get(domain) || [];
    current.push(agent);
    groups.set(domain, current);
  });
  return [
    {
      node_id: "domain_packs",
      name: "domain_packs",
      kind: "group",
      children: Array.from(groups.entries())
        .sort(([left], [right]) => left.localeCompare(right))
        .map(([domain, items]) => ({
          node_id: `domain_packs/${domain}`,
          name: domain,
          kind: "group" as const,
          children: items
            .sort((left, right) => left.name.localeCompare(right.name))
            .map((agent) => ({
              node_id: `domain_packs/${domain}/agents/${agent.agent_id}`,
              name: agent.agent_id,
              kind: "agent" as const,
              agent_id: agent.agent_id,
              label: agent.name,
              domain: agent.domain,
              role: agent.role,
              description: agent.description,
            })),
        })),
    },
  ];
}

function formatTreeGroupName(value: string) {
  return value === "domain_packs" ? "domain_packs" : value;
}

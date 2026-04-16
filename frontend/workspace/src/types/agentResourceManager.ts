export interface RegisteredMCPServerDto {
  server_ref: string;
  name: string;
  description: string;
  connection_mode: string;
  transport_kind: string;
  command: string;
  args: string[];
  endpoint: string;
  env: Record<string, string>;
  cwd: string;
  tool_refs: string[];
  discovered_tool_refs: string[];
  enabled: boolean;
  notes: string;
}

export interface AssignedMCPServerDto {
  server_ref: string;
  name: string;
  description: string;
  connection_mode: string;
  transport_kind: string;
  tool_refs: string[];
  discovered_tool_refs: string[];
  enabled: boolean;
  notes: string;
}

export interface RegisteredSkillDto {
  skill_name: string;
  name: string;
  description: string;
  trigger_kinds: string[];
  enabled: boolean;
  notes: string;
}

export interface AgentWorkspaceDto {
  agent_id: string;
  relative_path: string;
  absolute_path: string;
  enabled: boolean;
  notes: string;
  exists: boolean;
}

export interface WorkspaceRootConfigDto {
  root_path: string;
  enabled: boolean;
  provisioned: boolean;
  notes: string;
}

export interface AgentResourceDistributionDto {
  assigned_mcp_servers: string[];
  assigned_mcp_server_details: AssignedMCPServerDto[];
  assigned_skills: string[];
  workspace: AgentWorkspaceDto | null;
}

export interface AgentResourceManagerAgentDto {
  agent_id: string;
  domain?: string | null;
  name: string;
  role: string;
  distribution: AgentResourceDistributionDto;
  effectiveness: {
    operational_summary: string;
    collaboration_summary: string;
    attention_points: string[];
  };
}

export interface AgentResourceManagerSnapshotDto {
  registry: {
    workspace_root: WorkspaceRootConfigDto;
    mcp_servers: RegisteredMCPServerDto[];
    skills: RegisteredSkillDto[];
    agent_workspaces: AgentWorkspaceDto[];
  };
  agents: AgentResourceManagerAgentDto[];
  registered_counts: {
    mcp_servers: number;
    skills: number;
    workspaces: number;
  };
  distribution_health: {
    agents_with_mcp: number;
    agents_with_skills: number;
    agents_with_workspaces: number;
  };
  catalog: {
    mcp_server_refs: string[];
    skill_names: string[];
  };
  workspace_root_resolved: string;
}

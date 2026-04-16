export interface AgentMCPBindingDto {
  server_ref: string;
  tool_refs: string[];
  enabled: boolean;
  usage_notes: string;
}

export interface AgentSkillBindingDto {
  skill_name: string;
  enabled: boolean;
  trigger_kinds: string[];
  scope: string;
  execution_mode: string;
  usage_notes: string;
}

export interface AgentApprovalPolicyDto {
  mode: string;
  required_targets: string[];
  notes: string;
}

export interface AgentHandoffPolicyDto {
  mode: string;
  allowed_targets: string[];
  notes: string;
}

export interface AgentCapabilityDto {
  agent_id: string;
  domain?: string | null;
  enabled: boolean;
  tool_refs: string[];
  memory_scopes: string[];
  policy_profiles: string[];
  mcp_bindings: AgentMCPBindingDto[];
  skill_bindings: AgentSkillBindingDto[];
  approval_policy: AgentApprovalPolicyDto;
  handoff_policy: AgentHandoffPolicyDto;
  metadata: Record<string, unknown>;
  name?: string;
  role?: string;
  resolved_preview?: {
    agent_id: string;
    resolved_tool_refs: string[];
    resolved_memory_scopes: string[];
    resolved_policy_profiles: string[];
    enabled_mcp_servers: string[];
    enabled_skills: string[];
    approval_policy: AgentApprovalPolicyDto;
    handoff_policy: AgentHandoffPolicyDto;
    workspace?: {
      relative_path: string;
      enabled: boolean;
    };
    operational_summary?: string;
    collaboration_summary?: string;
    usage_guidance?: string[];
    attention_points?: string[];
  };
}

export interface AgentCapabilityListDto {
  agent_capabilities: AgentCapabilityDto[];
}

export interface CapabilityValidationResult {
  valid: boolean;
  messages: string[];
}

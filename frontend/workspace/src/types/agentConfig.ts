export interface AgentConfigDto {
  agent_id: string;
  domain?: string | null;
  enabled: boolean;
  llm_profile_ref: string;
  system_prompt: string;
  instruction_appendix: string;
  response_style: string;
  quality_bar: string;
  handoff_targets: string[];
  metadata: Record<string, unknown>;
  name?: string;
  role?: string;
}

export interface AgentConfigListDto {
  agent_configs: AgentConfigDto[];
}

export interface OverviewDto {
  project: {
    name: string;
    mode: string;
    intended_use: string;
  };
  llm_status: {
    integrated: boolean;
    configured: boolean;
    configured_provider_count: number;
    configured_profile_count: number;
    mode: string;
    summary: string;
    api_owner: string;
    next_step: string;
    providers: Array<{
      provider_ref: string;
      provider_kind: string;
      default_model: string;
      base_url: string;
    }>;
    profiles: Array<{
      profile_ref: string;
      provider_ref: string;
      model_name: string;
    }>;
    required_env_vars: string[];
  };
  counts: {
    agents: number;
    workflows: number;
    tools: number;
    eval_cases: number;
    eval_suites: number;
  };
  agents: Array<{
    agent_id: string;
    name: string;
    role: string;
    version: string;
    description: string;
    capabilities: string[];
    tool_refs: string[];
    memory_scopes: string[];
    implementation_ref: string;
  }>;
  workflows: Array<{
    workflow_id: string;
    name: string;
    version: string;
    entry_node_id: string;
    node_count: number;
    agent_node_count: number;
    tool_node_count: number;
    nodes: Array<{
      node_id: string;
      node_type: string;
      executor_ref: string;
      agent_ref: string | null;
      tool_ref?: string | null;
    }>;
  }>;
  tools: Array<{
    tool_ref: string;
    name: string;
    description: string;
    transport_kind: string;
    side_effect_kind: string;
    tags: string[];
  }>;
  eval_suites: Array<{
    suite_id: string;
    name: string;
    case_count: number;
    case_ids: string[];
  }>;
}

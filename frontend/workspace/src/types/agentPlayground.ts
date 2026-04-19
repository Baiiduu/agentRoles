export interface AgentToolDescriptorDto {
  tool_ref: string;
  name: string;
  description: string;
  transport_kind: string;
  provider_ref: string | null;
  operation_ref: string | null;
  side_effect_kind: string;
  tags: string[];
  metadata: Record<string, unknown>;
}

export interface AgentMcpToolDto {
  tool_ref: string;
  operation_ref: string;
  server_ref: string;
  server_name: string;
  display_name: string;
  description: string;
  connection_mode: string;
  transport_kind: string;
  tags: string[];
}

export interface AgentMcpServerDto {
  server_ref: string;
  name: string;
  description: string;
  connection_mode: string;
  transport_kind: string;
  tool_count: number;
  tools: AgentMcpToolDto[];
}

export interface AgentBootstrapItem {
  agent_id: string;
  domain: string | null;
  name: string;
  role: string;
  description: string;
  capabilities: string[];
  tool_refs: string[];
  memory_scopes: string[];
  config: Record<string, unknown>;
  mcp_servers: AgentMcpServerDto[];
  tool_catalog: {
    local_tools: AgentToolDescriptorDto[];
    mcp_tools: AgentToolDescriptorDto[];
  };
  tool_groups: {
    local_tool_refs: string[];
    mcp_tool_refs: string[];
  };
  tree_path: string[];
}

export interface AgentTreeNode {
  node_id: string;
  name: string;
  kind: "group" | "agent";
  children?: AgentTreeNode[];
  agent_id?: string;
  label?: string;
  domain?: string | null;
  role?: string;
  description?: string;
}

export interface AgentCaseOption {
  case_id: string;
  title: string;
  learner_name: string;
  goal: string;
}

export interface AgentBootstrapDto {
  agents: AgentBootstrapItem[];
  agent_tree: AgentTreeNode[];
  available_cases: AgentCaseOption[];
  default_agent_id: string | null;
  supported_artifact_types: string[];
}

export interface AgentDescriptorDto {
  agent_id: string;
  domain: string | null;
  name: string;
  role: string;
  description: string;
  capabilities: string[];
  tool_refs: string[];
  memory_scopes: string[];
  input_contract: Record<string, unknown>;
  output_contract: Record<string, unknown>;
  metadata: Record<string, unknown>;
  config: Record<string, unknown>;
  mcp_servers: AgentMcpServerDto[];
  tool_catalog: {
    local_tools: AgentToolDescriptorDto[];
    mcp_tools: AgentToolDescriptorDto[];
  };
  tool_groups: {
    local_tool_refs: string[];
    mcp_tool_refs: string[];
  };
  chat_history?: PersistedAgentChatMessage[];
}

export interface AgentSessionMessage {
  role: string;
  content: string;
}

export interface PersistedAgentChatMessage {
  message_id: string;
  session_id: string;
  agent_id: string;
  role: string;
  content: string;
  created_at: string;
}

export interface PersistedAgentChatSession {
  session_id: string;
  agent_id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface AgentChatHistoryDto {
  agent_id: string;
  session_id: string | null;
  messages: PersistedAgentChatMessage[];
}

export interface AgentChatSessionsDto {
  agent_id: string;
  active_session_id: string | null;
  sessions: PersistedAgentChatSession[];
}

export interface AgentSessionResponseDto {
  session: {
    session_id: string;
    agent_id: string;
    status: string;
  };
  agent: {
    agent_id: string;
    name: string;
  };
  messages: AgentSessionMessage[];
  artifact_preview: {
    artifact_type: string;
    summary: string;
    payload: Record<string, unknown>;
  } | null;
  tool_events: Array<Record<string, unknown>>;
  resource_events: Array<Record<string, unknown>>;
  memory_events: Array<Record<string, unknown>>;
  writeback_status: {
    persisted: boolean;
    case_id: string | null;
    message: string | null;
  };
}

export interface AgentSessionTaskEventDto {
  sequence: number;
  timestamp: string;
  kind: string;
  stage: string;
  status: string;
  summary: string;
  current_phase: string;
  tool_ref?: string;
  detail?: Record<string, unknown>;
}

export interface AgentSessionTaskDto {
  task_id: string;
  agent_id: string;
  session_id: string | null;
  case_id: string | null;
  message: string;
  status: string;
  stage: string;
  current_phase: string;
  current_activity: string;
  created_at: string;
  updated_at: string;
  event_count: number;
  events: AgentSessionTaskEventDto[];
  result: AgentSessionResponseDto | null;
  error: string | null;
}

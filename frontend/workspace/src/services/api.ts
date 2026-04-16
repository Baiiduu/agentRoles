import type {
  AgentConfigDto,
  AgentConfigListDto,
} from "../types/agentConfig";
import type {
  AgentCapabilityDto,
  AgentCapabilityListDto,
} from "../types/agentCapability";
import type {
  AgentResourceManagerSnapshotDto,
  AgentWorkspaceDto,
  RegisteredMCPServerDto,
  RegisteredSkillDto,
  WorkspaceRootConfigDto,
} from "../types/agentResourceManager";
import type {
  AgentBootstrapDto,
  AgentChatHistoryDto,
  AgentChatSessionsDto,
  AgentDescriptorDto,
  AgentSessionResponseDto,
} from "../types/agentPlayground";
import type { CaseCoordinationDto } from "../types/caseCoordinator";
import type { CaseHandoffResponseDto } from "../types/caseHandoff";
import type { OverviewDto } from "../types/dashboard";
import type { CaseListDto, CaseWorkspaceDto } from "../types/caseWorkspace";

const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8765").replace(/\/$/, "");

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers || {}),
    },
    ...init,
  });
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.error || `Request failed: ${response.status}`);
  }
  return payload as T;
}

export const api = {
  getOverview() {
    return requestJson<OverviewDto>("/api/overview");
  },
  getCases() {
    return requestJson<CaseListDto>("/api/cases");
  },
  getCase(caseId: string) {
    return requestJson<CaseWorkspaceDto>(`/api/cases/${caseId}`);
  },
  getCaseCoordination(caseId: string) {
    return requestJson<CaseCoordinationDto>(`/api/cases/${caseId}/coordination`);
  },
  createCaseHandoff(
    caseId: string,
    payload: {
      target_agent_id: string;
      requested_by: string;
      reason: string;
      context_overrides?: Record<string, unknown>;
    },
  ) {
    return requestJson<CaseHandoffResponseDto>(`/api/cases/${caseId}/handoffs`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },
  appendCaseSessionFeedItem(caseId: string, payload: AgentSessionResponseDto) {
    return requestJson<{ item: Record<string, unknown> }>(`/api/cases/${caseId}/session-feed`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },
  getAgentPlaygroundBootstrap() {
    return requestJson<AgentBootstrapDto>("/api/agent-playground/bootstrap");
  },
  getAgentChatHistory(agentId: string, sessionId?: string) {
    const suffix = sessionId ? `?session_id=${encodeURIComponent(sessionId)}` : "";
    return requestJson<AgentChatHistoryDto>(`/api/agents/${agentId}/chat-history${suffix}`);
  },
  getAgentSessions(agentId: string) {
    return requestJson<AgentChatSessionsDto>(`/api/agents/${agentId}/sessions`);
  },
  createAgentSession(agentId: string) {
    return requestJson<{ agent_id: string; session: AgentChatSessionsDto["sessions"][number] }>(
      `/api/agents/${agentId}/sessions/new`,
      {
        method: "POST",
        body: JSON.stringify({}),
      },
    );
  },
  deleteAgentSession(agentId: string, sessionId: string) {
    return requestJson<AgentChatSessionsDto & { deleted_session_id: string }>(
      `/api/agents/${agentId}/sessions/${sessionId}/delete`,
      {
        method: "POST",
        body: JSON.stringify({}),
      },
    );
  },
  getAgentConfigs() {
    return requestJson<AgentConfigListDto>("/api/agent-configs");
  },
  getAgentConfig(agentId: string) {
    return requestJson<AgentConfigDto>(`/api/agent-configs/${agentId}`);
  },
  saveAgentConfig(agentId: string, payload: AgentConfigDto) {
    return requestJson<AgentConfigDto>(`/api/agent-configs/${agentId}`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },
  getAgentCapabilities() {
    return requestJson<AgentCapabilityListDto>("/api/agent-capabilities");
  },
  getAgentCapability(agentId: string) {
    return requestJson<AgentCapabilityDto>(`/api/agent-capabilities/${agentId}`);
  },
  saveAgentCapability(agentId: string, payload: AgentCapabilityDto) {
    return requestJson<AgentCapabilityDto>(`/api/agent-capabilities/${agentId}`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },
  getAgentResourceManagerSnapshot() {
    return requestJson<AgentResourceManagerSnapshotDto>("/api/agent-resource-manager");
  },
  saveAgentWorkspaceRoot(payload: WorkspaceRootConfigDto) {
    return requestJson<WorkspaceRootConfigDto & { resolved_path: string }>(
      "/api/agent-resource-manager/workspace-root",
      {
        method: "POST",
        body: JSON.stringify(payload),
      },
    );
  },
  pickAgentWorkspaceRoot() {
    return requestJson<{ root_path: string }>(
      "/api/agent-resource-manager/workspace-root/pick",
      {
        method: "POST",
        body: JSON.stringify({}),
      },
    );
  },
  provisionAgentWorkspaceRoot() {
    return requestJson<{
      workspace_root: WorkspaceRootConfigDto;
      agent_workspaces: AgentWorkspaceDto[];
    }>("/api/agent-resource-manager/workspace-root/provision", {
      method: "POST",
      body: JSON.stringify({}),
    });
  },
  saveRegisteredMcpServer(serverRef: string, payload: RegisteredMCPServerDto) {
    return requestJson<RegisteredMCPServerDto>(
      `/api/agent-resource-manager/mcp-servers/${serverRef}`,
      {
        method: "POST",
        body: JSON.stringify(payload),
      },
    );
  },
  testRegisteredMcpServer(serverRef: string) {
    return requestJson<{
      ok: boolean;
      server_ref: string;
      transport_kind: string;
      tool_count: number;
      tools: string[];
    }>(`/api/agent-resource-manager/mcp-servers/${serverRef}/test`, {
      method: "POST",
      body: JSON.stringify({}),
    });
  },
  authenticateRegisteredMcpServer(serverRef: string) {
    return requestJson<{
      ok: boolean;
      server_ref: string;
      tool_count: number;
      tools: string[];
      auth_flow: string;
    }>(`/api/agent-resource-manager/mcp-servers/${serverRef}/authenticate`, {
      method: "POST",
      body: JSON.stringify({}),
    });
  },
  discoverRegisteredMcpServerTools(serverRef: string) {
    return requestJson<{
      server: RegisteredMCPServerDto;
      discovery: {
        server_ref: string;
        tools: Array<{
          name: string;
          title?: string | null;
          description: string;
          input_schema?: Record<string, unknown>;
          output_schema?: Record<string, unknown>;
        }>;
      };
    }>(`/api/agent-resource-manager/mcp-servers/${serverRef}/discover-tools`, {
      method: "POST",
      body: JSON.stringify({}),
    });
  },
  saveRegisteredSkill(skillName: string, payload: RegisteredSkillDto) {
    return requestJson<RegisteredSkillDto>(
      `/api/agent-resource-manager/skills/${skillName}`,
      {
        method: "POST",
        body: JSON.stringify(payload),
      },
    );
  },
  saveAgentWorkspace(
    agentId: string,
    payload: { relative_path: string; enabled: boolean; notes: string },
  ) {
    return requestJson<AgentWorkspaceDto>(
      `/api/agent-resource-manager/agents/${agentId}/workspace`,
      {
        method: "POST",
        body: JSON.stringify(payload),
      },
    );
  },
  saveAgentResourceDistribution(
    agentId: string,
    payload: { mcp_servers: string[]; skills: string[] },
  ) {
    return requestJson<{ agent_id: string; capability: AgentCapabilityDto }>(
      `/api/agent-resource-manager/agents/${agentId}/distribution`,
      {
        method: "POST",
        body: JSON.stringify(payload),
      },
    );
  },
  getAgentDescriptor(agentId: string) {
    return requestJson<AgentDescriptorDto>(`/api/agents/${agentId}`);
  },
  sendAgentSessionMessage(payload: {
    agent_id: string;
    case_id: string | null;
    message: string;
    ephemeral_context: Record<string, unknown>;
    persist_artifact: boolean;
  }) {
    return requestJson<AgentSessionResponseDto>("/api/agent-sessions/message", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },
};

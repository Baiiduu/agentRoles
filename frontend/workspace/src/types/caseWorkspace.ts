import type { CaseCoordinationDto } from "./caseCoordinator";
import type { CaseHandoffRecordDto } from "./caseHandoff";

export interface CaseListItem {
  case_id: string;
  title: string;
  learner_name: string;
  goal: string;
  current_stage: string;
}

export interface CaseListDto {
  cases: CaseListItem[];
}

export interface CaseWorkspaceDto {
  case: {
    case_id: string;
    title: string;
    learner_name: string;
    goal: string;
    current_stage: string;
    mastery_summary: string;
    active_plan: {
      title: string;
      focus_areas: string[];
    };
    artifacts: Array<{
      artifact_type: string;
      summary: string;
      producer: string;
    }>;
    timeline: Array<{
      kind: string;
      label: string;
      stage: string;
    }>;
  };
  handoffs: CaseHandoffRecordDto[];
  session_feed: Array<{
    case_id: string;
    session_id: string;
    agent_id: string;
    agent_name: string;
    status: string;
    summary: string;
    artifact_type: string | null;
    source: string;
    created_at: string;
  }>;
  coordination: CaseCoordinationDto;
  available_agents: Array<{
    agent_id: string;
    name: string;
    role: string;
    capability_summary?: {
      enabled: boolean;
      mcp_servers: string[];
      skills: string[];
      approval_mode: string;
      handoff_mode: string;
      allowed_targets: string[];
      operational_summary: string;
      collaboration_summary: string;
      usage_guidance: string[];
      attention_points: string[];
    } | null;
  }>;
  available_workflows: Array<{
    workflow_id: string;
    name: string;
  }>;
}

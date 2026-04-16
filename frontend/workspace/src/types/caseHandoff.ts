export interface CaseHandoffRecordDto {
  handoff_id: string;
  case_id: string;
  target_agent_id: string;
  requested_by: string;
  reason: string;
  context_overrides: Record<string, unknown>;
  source: string;
  status: string;
  created_at: string;
  resolved_session_id: string | null;
}

export interface CaseHandoffResponseDto {
  handoff: CaseHandoffRecordDto;
  navigation_target: {
    case_id: string;
    agent_id: string;
  };
}

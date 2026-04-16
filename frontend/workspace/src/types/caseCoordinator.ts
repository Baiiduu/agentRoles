export interface CaseCoordinationDto {
  recommended_mode: string;
  recommended_agent_id: string | null;
  recommended_workflow_id: string | null;
  reason_summary: string;
  supporting_signals: string[];
}

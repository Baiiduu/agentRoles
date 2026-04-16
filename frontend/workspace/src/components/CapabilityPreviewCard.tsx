import type { AgentCapabilityDto, CapabilityValidationResult } from "../types/agentCapability";

interface CapabilityPreviewCardProps {
  capability: AgentCapabilityDto;
  validation: CapabilityValidationResult;
}

export function CapabilityPreviewCard({
  capability,
  validation,
}: CapabilityPreviewCardProps) {
  const preview = capability.resolved_preview;

  return (
    <section className="panel">
      <h2 className="panel-title">Resolved Preview</h2>
      <div className="detail-card">
        <strong>Validation</strong>
        <div className="tag-row">
          <span className={validation.valid ? "tag success" : "tag"}>
            {validation.valid ? "valid" : "needs review"}
          </span>
        </div>
        {validation.messages.length ? (
          <div className="detail-block">
            {validation.messages.map((item) => (
              <span key={item} className="tag">
                {item}
              </span>
            ))}
          </div>
        ) : null}
      </div>
      <div className="detail-card">
        <strong>Operational Fit</strong>
        <p>{preview?.operational_summary || "No operational summary available yet."}</p>
        <p>{preview?.collaboration_summary || "No collaboration summary available yet."}</p>
        {preview?.workspace?.enabled && preview.workspace.relative_path ? (
          <div className="tag-row">
            <span className="tag">workspace: {preview.workspace.relative_path}</span>
          </div>
        ) : null}
        {preview?.usage_guidance?.length ? (
          <div className="detail-block">
            {preview.usage_guidance.map((item) => (
              <span key={item} className="tag">
                {item}
              </span>
            ))}
          </div>
        ) : null}
        {preview?.attention_points?.length ? (
          <div className="detail-block">
            {preview.attention_points.map((item) => (
              <span key={item} className="tag">
                {item}
              </span>
            ))}
          </div>
        ) : null}
      </div>
      <div className="detail-card">
        <strong>Resolved Tools</strong>
        <div className="tag-row">
          {(preview?.resolved_tool_refs || []).map((item) => (
            <span key={item} className="tag">
              {item}
            </span>
          ))}
        </div>
      </div>
      <div className="detail-card">
        <strong>MCP Servers</strong>
        <div className="tag-row">
          {(preview?.enabled_mcp_servers || []).map((item) => (
            <span key={item} className="tag">
              {item}
            </span>
          ))}
        </div>
      </div>
      <div className="detail-card">
        <strong>Skills</strong>
        <div className="tag-row">
          {(preview?.enabled_skills || []).map((item) => (
            <span key={item} className="tag">
              {item}
            </span>
          ))}
        </div>
      </div>
      <div className="detail-card">
        <strong>Policies</strong>
        <div className="tag-row">
          <span className="tag">approval: {preview?.approval_policy.mode || "none"}</span>
          <span className="tag">handoff: {preview?.handoff_policy.mode || "manual"}</span>
        </div>
      </div>
    </section>
  );
}

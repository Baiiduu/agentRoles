import type { AgentCapabilityDto } from "../types/agentCapability";

function splitCsv(value: string) {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

interface CapabilityPolicyEditorProps {
  capability: AgentCapabilityDto;
  onChange: (next: AgentCapabilityDto) => void;
}

export function CapabilityPolicyEditor({
  capability,
  onChange,
}: CapabilityPolicyEditorProps) {
  return (
    <div className="detail-card">
      <strong>Policies</strong>
      <div className="grid-two">
        <div className="field">
          <label>Approval Mode</label>
          <select
            value={capability.approval_policy.mode}
            onChange={(event) =>
              onChange({
                ...capability,
                approval_policy: {
                  ...capability.approval_policy,
                  mode: event.target.value,
                },
              })
            }
          >
            <option value="none">none</option>
            <option value="human_review">human_review</option>
            <option value="required">required</option>
          </select>
        </div>
        <div className="field">
          <label>Handoff Mode</label>
          <select
            value={capability.handoff_policy.mode}
            onChange={(event) =>
              onChange({
                ...capability,
                handoff_policy: {
                  ...capability.handoff_policy,
                  mode: event.target.value,
                },
              })
            }
          >
            <option value="manual">manual</option>
            <option value="guided">guided</option>
            <option value="blocked">blocked</option>
          </select>
        </div>
      </div>
      <div className="field">
        <label>Approval Required Targets</label>
        <input
          value={capability.approval_policy.required_targets.join(", ")}
          onChange={(event) =>
            onChange({
              ...capability,
              approval_policy: {
                ...capability.approval_policy,
                required_targets: splitCsv(event.target.value),
              },
            })
          }
        />
      </div>
      <div className="field">
        <label>Approval Notes</label>
        <textarea
          value={capability.approval_policy.notes}
          onChange={(event) =>
            onChange({
              ...capability,
              approval_policy: {
                ...capability.approval_policy,
                notes: event.target.value,
              },
            })
          }
        />
      </div>
      <div className="field">
        <label>Allowed Handoff Targets</label>
        <input
          value={capability.handoff_policy.allowed_targets.join(", ")}
          onChange={(event) =>
            onChange({
              ...capability,
              handoff_policy: {
                ...capability.handoff_policy,
                allowed_targets: splitCsv(event.target.value),
              },
            })
          }
        />
      </div>
      <div className="field">
        <label>Handoff Notes</label>
        <textarea
          value={capability.handoff_policy.notes}
          onChange={(event) =>
            onChange({
              ...capability,
              handoff_policy: {
                ...capability.handoff_policy,
                notes: event.target.value,
              },
            })
          }
        />
      </div>
    </div>
  );
}

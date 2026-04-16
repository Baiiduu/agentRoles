import type { AgentCapabilityDto } from "../types/agentCapability";

function splitCsv(value: string) {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

interface BaseCapabilityEditorProps {
  capability: AgentCapabilityDto;
  onChange: (next: AgentCapabilityDto) => void;
}

export function BaseCapabilityEditor({
  capability,
  onChange,
}: BaseCapabilityEditorProps) {
  return (
    <div className="detail-card">
      <strong>Base Capability</strong>
      <label className="checkbox">
        <input
          type="checkbox"
          checked={capability.enabled}
          onChange={(event) => onChange({ ...capability, enabled: event.target.checked })}
        />
        <span>Enabled</span>
      </label>
      <div className="field">
        <label>Extra Tool Refs</label>
        <input
          value={capability.tool_refs.join(", ")}
          onChange={(event) =>
            onChange({ ...capability, tool_refs: splitCsv(event.target.value) })
          }
        />
      </div>
      <div className="field">
        <label>Extra Memory Scopes</label>
        <input
          value={capability.memory_scopes.join(", ")}
          onChange={(event) =>
            onChange({ ...capability, memory_scopes: splitCsv(event.target.value) })
          }
        />
      </div>
      <div className="field">
        <label>Policy Profiles</label>
        <input
          value={capability.policy_profiles.join(", ")}
          onChange={(event) =>
            onChange({ ...capability, policy_profiles: splitCsv(event.target.value) })
          }
        />
      </div>
    </div>
  );
}

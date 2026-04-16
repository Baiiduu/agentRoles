import type { AgentCapabilityDto, AgentSkillBindingDto } from "../types/agentCapability";

interface SkillBindingsEditorProps {
  capability: AgentCapabilityDto;
  onChange: (next: AgentCapabilityDto) => void;
}

function updateBinding(
  capability: AgentCapabilityDto,
  index: number,
  patch: Partial<AgentSkillBindingDto>,
) {
  const nextBindings = capability.skill_bindings.map((item, currentIndex) =>
    currentIndex === index ? { ...item, ...patch } : item,
  );
  return { ...capability, skill_bindings: nextBindings };
}

export function SkillBindingsEditor({
  capability,
  onChange,
}: SkillBindingsEditorProps) {
  return (
    <div className="detail-card">
      <div className="section-head">
        <strong>Skill Bindings</strong>
      </div>
      <div className="catalog-grid">
        {capability.skill_bindings.map((binding, index) => (
          <article key={`${binding.skill_name}-${index}`} className="catalog-card">
            <label className="checkbox">
              <input
                type="checkbox"
                checked={binding.enabled}
                onChange={(event) =>
                  onChange(updateBinding(capability, index, { enabled: event.target.checked }))
                }
              />
              <span>Enabled</span>
            </label>
            <div className="field">
              <label>Skill Name</label>
              <input
                value={binding.skill_name}
                onChange={(event) =>
                  onChange(updateBinding(capability, index, { skill_name: event.target.value }))
                }
              />
            </div>
            <div className="grid-two">
              <div className="field">
                <label>Scope</label>
                <input
                  value={binding.scope}
                  onChange={(event) =>
                    onChange(updateBinding(capability, index, { scope: event.target.value }))
                  }
                />
              </div>
              <div className="field">
                <label>Execution Mode</label>
                <select
                  value={binding.execution_mode}
                  onChange={(event) =>
                    onChange(
                      updateBinding(capability, index, { execution_mode: event.target.value }),
                    )
                  }
                >
                  <option value="human_confirmed">human_confirmed</option>
                  <option value="advisory">advisory</option>
                  <option value="auto">auto</option>
                </select>
              </div>
            </div>
            <div className="field">
              <label>Trigger Kinds</label>
              <input
                value={binding.trigger_kinds.join(", ")}
                onChange={(event) =>
                  onChange(
                    updateBinding(capability, index, {
                      trigger_kinds: event.target.value
                        .split(",")
                        .map((item) => item.trim())
                        .filter(Boolean),
                    }),
                  )
                }
              />
            </div>
            <div className="field">
              <label>Usage Notes</label>
              <textarea
                value={binding.usage_notes}
                onChange={(event) =>
                  onChange(updateBinding(capability, index, { usage_notes: event.target.value }))
                }
              />
            </div>
            <button
              type="button"
              className="secondary-button"
              onClick={() =>
                onChange({
                  ...capability,
                  skill_bindings: capability.skill_bindings.filter((_, currentIndex) => currentIndex !== index),
                })
              }
            >
              Remove Binding
            </button>
          </article>
        ))}
      </div>
      <div className="action-row">
        <button
          type="button"
          className="secondary-button"
          onClick={() =>
            onChange({
              ...capability,
              skill_bindings: [
                ...capability.skill_bindings,
                {
                  skill_name: "",
                  enabled: true,
                  trigger_kinds: [],
                  scope: "session",
                  execution_mode: "human_confirmed",
                  usage_notes: "",
                },
              ],
            })
          }
        >
          Add Skill Binding
        </button>
      </div>
    </div>
  );
}

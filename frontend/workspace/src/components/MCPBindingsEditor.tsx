import type { AgentCapabilityDto, AgentMCPBindingDto } from "../types/agentCapability";

interface MCPBindingsEditorProps {
  capability: AgentCapabilityDto;
  onChange: (next: AgentCapabilityDto) => void;
}

function updateBinding(
  capability: AgentCapabilityDto,
  index: number,
  patch: Partial<AgentMCPBindingDto>,
) {
  const nextBindings = capability.mcp_bindings.map((item, currentIndex) =>
    currentIndex === index ? { ...item, ...patch } : item,
  );
  return { ...capability, mcp_bindings: nextBindings };
}

export function MCPBindingsEditor({
  capability,
  onChange,
}: MCPBindingsEditorProps) {
  return (
    <div className="detail-card">
      <div className="section-head">
        <strong>MCP Bindings</strong>
      </div>
      <div className="catalog-grid">
        {capability.mcp_bindings.map((binding, index) => (
          <article key={`${binding.server_ref}-${index}`} className="catalog-card">
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
              <label>Server Ref</label>
              <input
                value={binding.server_ref}
                onChange={(event) =>
                  onChange(updateBinding(capability, index, { server_ref: event.target.value }))
                }
              />
            </div>
            <div className="field">
              <label>Tool Refs</label>
              <input
                value={binding.tool_refs.join(", ")}
                onChange={(event) =>
                  onChange(
                    updateBinding(capability, index, {
                      tool_refs: event.target.value
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
                  mcp_bindings: capability.mcp_bindings.filter((_, currentIndex) => currentIndex !== index),
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
              mcp_bindings: [
                ...capability.mcp_bindings,
                { server_ref: "", tool_refs: [], enabled: true, usage_notes: "" },
              ],
            })
          }
        >
          Add MCP Binding
        </button>
      </div>
    </div>
  );
}

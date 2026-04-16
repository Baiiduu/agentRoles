import { useEffect, useState } from "react";
import { api } from "../services/api";
import type { AgentConfigDto } from "../types/agentConfig";

function splitCsv(value: string) {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

export function AgentConfigPage() {
  const [configs, setConfigs] = useState<AgentConfigDto[]>([]);
  const [selectedAgentId, setSelectedAgentId] = useState("");
  const [form, setForm] = useState<AgentConfigDto | null>(null);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    let active = true;
    api.getAgentConfigs()
      .then((payload) => {
        if (!active) return;
        setConfigs(payload.agent_configs);
        if (payload.agent_configs.length) {
          setSelectedAgentId(payload.agent_configs[0].agent_id);
          setForm(payload.agent_configs[0]);
        }
      })
      .catch((err: Error) => {
        if (!active) return;
        setError(err.message);
      });
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (!selectedAgentId) return;
    let active = true;
    api.getAgentConfig(selectedAgentId)
      .then((payload) => {
        if (!active) return;
        setForm(payload);
      })
      .catch((err: Error) => {
        if (!active) return;
        setError(err.message);
      });
    return () => {
      active = false;
    };
  }, [selectedAgentId]);

  async function handleSave() {
    if (!form) return;
    try {
      setSaving(true);
      setError("");
      const saved = await api.saveAgentConfig(form.agent_id, form);
      setForm(saved);
      const refreshed = await api.getAgentConfigs();
      setConfigs(refreshed.agent_configs);
    } catch (err) {
      setError(err instanceof Error ? err.message : "unknown error");
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="page-shell">
      <header className="page-header">
        <p className="workspace-eyebrow">Agent Config</p>
        <h2 className="page-title">Agent Configuration</h2>
        <p className="page-copy">
          在这里调整每个 agent 的系统提示、模型档位、风格和 handoff 偏好。
        </p>
      </header>
      {error ? <div className="error-banner">{error}</div> : null}
      <div className="playground-grid">
        <section className="panel">
          <h2 className="panel-title">Agents</h2>
          <div className="agent-list">
            {configs.map((item) => (
              <button
                key={item.agent_id}
                type="button"
                className={item.agent_id === selectedAgentId ? "agent-card active" : "agent-card"}
                onClick={() => setSelectedAgentId(item.agent_id)}
              >
                <strong>{item.name || item.agent_id}</strong>
                <span>{item.role || "unknown"}</span>
                <span>{item.domain || "unknown-domain"}</span>
                <span>{item.llm_profile_ref}</span>
              </button>
            ))}
          </div>
        </section>

        <section className="panel">
          <h2 className="panel-title">Config Editor</h2>
          {form ? (
            <>
              <label className="checkbox">
                <input
                  type="checkbox"
                  checked={form.enabled}
                  onChange={(event) => setForm({ ...form, enabled: event.target.checked })}
                />
                <span>Enabled</span>
              </label>
              <div className="field">
                <label>LLM Profile</label>
                <input
                  value={form.llm_profile_ref}
                  onChange={(event) => setForm({ ...form, llm_profile_ref: event.target.value })}
                />
              </div>
              <div className="field">
                <label>Response Style</label>
                <input
                  value={form.response_style}
                  onChange={(event) => setForm({ ...form, response_style: event.target.value })}
                />
              </div>
              <div className="field">
                <label>System Prompt</label>
                <textarea
                  value={form.system_prompt}
                  onChange={(event) => setForm({ ...form, system_prompt: event.target.value })}
                />
              </div>
              <div className="field">
                <label>Instruction Appendix</label>
                <textarea
                  value={form.instruction_appendix}
                  onChange={(event) =>
                    setForm({ ...form, instruction_appendix: event.target.value })
                  }
                />
              </div>
              <div className="field">
                <label>Quality Bar</label>
                <textarea
                  value={form.quality_bar}
                  onChange={(event) => setForm({ ...form, quality_bar: event.target.value })}
                />
              </div>
              <div className="field">
                <label>Handoff Targets</label>
                <input
                  value={form.handoff_targets.join(", ")}
                  onChange={(event) =>
                    setForm({ ...form, handoff_targets: splitCsv(event.target.value) })
                  }
                />
              </div>
              <button
                type="button"
                className="primary-button"
                onClick={handleSave}
                disabled={saving}
              >
                {saving ? "Saving..." : "Save Agent Config"}
              </button>
            </>
          ) : (
            <p>Loading...</p>
          )}
        </section>

        <section className="panel">
          <h2 className="panel-title">Config Notes</h2>
          {form ? (
            <div className="detail-card">
              <strong>{form.agent_id}</strong>
              <div className="tag-row">
                <span className="tag">{form.domain || "unknown-domain"}</span>
                <span className="tag">{form.response_style}</span>
                <span className="tag">{form.llm_profile_ref}</span>
              </div>
              <p>这里保存的是运行时配置，不再把 prompt 写死在 agent 页面里。</p>
            </div>
          ) : (
            <p>Loading...</p>
          )}
        </section>
      </div>
    </section>
  );
}

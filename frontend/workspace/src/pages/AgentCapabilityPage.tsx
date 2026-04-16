import { useEffect, useMemo, useState } from "react";
import { BaseCapabilityEditor } from "../components/BaseCapabilityEditor";
import { CapabilityNavigator } from "../components/CapabilityNavigator";
import { CapabilityPolicyEditor } from "../components/CapabilityPolicyEditor";
import { CapabilityPreviewCard } from "../components/CapabilityPreviewCard";
import { MCPBindingsEditor } from "../components/MCPBindingsEditor";
import { SkillBindingsEditor } from "../components/SkillBindingsEditor";
import { api } from "../services/api";
import type { AgentCapabilityDto } from "../types/agentCapability";
import { validateCapability } from "../utils/capabilityValidation";

export function AgentCapabilityPage() {
  const [capabilities, setCapabilities] = useState<AgentCapabilityDto[]>([]);
  const [selectedAgentId, setSelectedAgentId] = useState("");
  const [form, setForm] = useState<AgentCapabilityDto | null>(null);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    let active = true;
    api.getAgentCapabilities()
      .then((payload) => {
        if (!active) return;
        setCapabilities(payload.agent_capabilities);
        if (payload.agent_capabilities.length) {
          setSelectedAgentId(payload.agent_capabilities[0].agent_id);
          setForm(payload.agent_capabilities[0]);
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
    api.getAgentCapability(selectedAgentId)
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

  const validation = useMemo(
    () =>
      form
        ? validateCapability(form)
        : {
            valid: true,
            messages: [],
          },
    [form],
  );

  async function handleSave() {
    if (!form) return;
    if (!validation.valid) {
      setError("Capability has validation issues. Please review the preview panel first.");
      return;
    }
    try {
      setSaving(true);
      setError("");
      const saved = await api.saveAgentCapability(form.agent_id, form);
      setForm(saved);
      const refreshed = await api.getAgentCapabilities();
      setCapabilities(refreshed.agent_capabilities);
    } catch (err) {
      setError(err instanceof Error ? err.message : "unknown error");
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="page-shell">
      <header className="page-header">
        <p className="workspace-eyebrow">Agent Capability</p>
        <h2 className="page-title">Agent Capability</h2>
        <p className="page-copy">
          在这里配置 agent 的可用能力边界，让它更适合真实场景，而不是只靠对话提示。
        </p>
      </header>
      {error ? <div className="error-banner">{error}</div> : null}
      <div className="playground-grid">
        <CapabilityNavigator
          capabilities={capabilities}
          selectedAgentId={selectedAgentId}
          onSelectAgent={setSelectedAgentId}
        />

        <section className="panel">
          <h2 className="panel-title">Capability Editor</h2>
          {form ? (
            <div className="catalog-grid">
              <BaseCapabilityEditor capability={form} onChange={setForm} />
              <MCPBindingsEditor capability={form} onChange={setForm} />
              <SkillBindingsEditor capability={form} onChange={setForm} />
              <CapabilityPolicyEditor capability={form} onChange={setForm} />
              <div className="action-row">
                <button
                  type="button"
                  className="primary-button"
                  onClick={handleSave}
                  disabled={saving}
                >
                  {saving ? "Saving..." : "Save Capability"}
                </button>
              </div>
            </div>
          ) : (
            <p>Loading...</p>
          )}
        </section>

        {form ? (
          <CapabilityPreviewCard capability={form} validation={validation} />
        ) : (
          <section className="panel">
            <h2 className="panel-title">Resolved Preview</h2>
            <p>Loading...</p>
          </section>
        )}
      </div>
    </section>
  );
}

import { useEffect, useState } from "react";
import { CatalogSection } from "../components/CatalogSection";
import { StatCard } from "../components/StatCard";
import { api } from "../services/api";
import type { OverviewDto } from "../types/dashboard";

interface DashboardPageProps {
  onOpenCase: (caseId: string) => void;
  onOpenPlayground: (options?: { caseId?: string; agentId?: string }) => void;
}

export function DashboardPage({ onOpenCase, onOpenPlayground }: DashboardPageProps) {
  const [overview, setOverview] = useState<OverviewDto | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    api.getOverview()
      .then((payload) => {
        if (!active) return;
        setOverview(payload);
      })
      .catch((err: Error) => {
        if (!active) return;
        setError(err.message);
      });
    return () => {
      active = false;
    };
  }, []);

  if (error) {
    return <div className="error-banner">{error}</div>;
  }

  if (!overview) {
    return <section className="panel">加载中...</section>;
  }

  return (
    <section className="page-shell">
      <header className="hero-panel">
        <div>
          <p className="workspace-eyebrow">Prototype Dashboard</p>
          <h2 className="page-title">教育领域多智能体工作台</h2>
          <p className="page-copy">
            这里整合了你之前主页的核心内容，作为新前端框架下的总入口。
          </p>
        </div>
        <div className="hero-side">
          <h3>LLM 配置状态</h3>
          <p>{overview.llm_status.summary}</p>
          <div className="tag-row">
            {overview.llm_status.providers.length ? (
              overview.llm_status.providers.map((provider) => (
                <span key={provider.provider_ref} className="tag success">
                  {provider.provider_ref}: {provider.default_model}
                </span>
              ))
            ) : (
              <span className="tag">当前还没有检测到已配置的 provider</span>
            )}
          </div>
        </div>
      </header>

      <section className="stats-grid">
        <StatCard label="已接入 Agents" value={overview.counts.agents} />
        <StatCard label="已接入 Workflows" value={overview.counts.workflows} />
        <StatCard label="已接入 Tools" value={overview.counts.tools} />
        <StatCard label="评估套件" value={overview.counts.eval_suites} />
      </section>

      <section className="dashboard-grid">
        <CatalogSection
          title="当前如何判断进度"
          description="沿用你之前主页的核心引导，但收进新的框架里。"
        >
          <ol className="ordered-list">
            <li>先看 LLM 配置状态，确认 OpenAI 或 DeepSeek 是否已识别。</li>
            <li>再看统计卡片，确认 agents、workflows、tools、eval suites 都已加载。</li>
            <li>优先进入 Agent Playground 单独调试一个 agent。</li>
            <li>也可以直接进入 Case Workspace，看 learner case 里的协作脉络。</li>
          </ol>
          <div className="tag-row" style={{ marginTop: 16 }}>
            <button className="primary-button" type="button" onClick={() => onOpenPlayground()}>
              打开 Agent Playground
            </button>
            <button
              className="secondary-button"
              type="button"
              onClick={() => onOpenCase("case-algebra-foundation")}
            >
              打开示例 Case
            </button>
          </div>
        </CatalogSection>

        <CatalogSection
          title="环境变量"
          description="当前前端最需要关注的后端配置项。"
        >
          <pre className="json-view">
            {JSON.stringify(overview.llm_status.required_env_vars, null, 2)}
          </pre>
        </CatalogSection>
      </section>

      <div className="dashboard-grid">
        <CatalogSection
          title="教育域 Agents"
          description="当前已接入的平台教育 agent。"
        >
          <div className="catalog-grid">
            {overview.agents.map((agent) => (
              <article key={agent.agent_id} className="catalog-card">
                <strong>{agent.name}</strong>
                <span>{agent.agent_id} | {agent.role}</span>
                <p>{agent.description}</p>
                <div className="tag-row">
                  {agent.capabilities.map((item) => (
                    <span key={item} className="tag">
                      {item}
                    </span>
                  ))}
                </div>
                <div className="tag-row">
                  <button
                    className="secondary-button"
                    type="button"
                    onClick={() => onOpenPlayground({ agentId: agent.agent_id })}
                  >
                    使用这个 Agent
                  </button>
                </div>
              </article>
            ))}
          </div>
        </CatalogSection>

        <CatalogSection
          title="教育域 Workflows"
          description="当前教育领域已经落地的多智能体编排流程。"
        >
          <div className="catalog-grid">
            {overview.workflows.map((workflow) => (
              <article key={workflow.workflow_id} className="catalog-card">
                <strong>{workflow.name}</strong>
                <span>{workflow.workflow_id}</span>
                <p>入口节点：{workflow.entry_node_id}</p>
                <div className="tag-row">
                  <span className="tag">节点 {workflow.node_count}</span>
                  <span className="tag">Agent {workflow.agent_node_count}</span>
                  <span className="tag">Tool {workflow.tool_node_count}</span>
                </div>
              </article>
            ))}
          </div>
        </CatalogSection>
      </div>

      <CatalogSection
        title="教育域 Tools"
        description="agent 和 workflow 当前可调用的教育工具。"
      >
        <div className="catalog-grid">
          {overview.tools.map((tool) => (
            <article key={tool.tool_ref} className="catalog-card">
              <strong>{tool.name}</strong>
              <span>{tool.tool_ref}</span>
              <p>{tool.description}</p>
              <div className="tag-row">
                <span className="tag">{tool.transport_kind}</span>
                <span className="tag">{tool.side_effect_kind}</span>
              </div>
            </article>
          ))}
        </div>
      </CatalogSection>
    </section>
  );
}

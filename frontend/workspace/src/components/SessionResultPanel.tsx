import { useEffect, useRef } from "react";
import type {
  AgentSessionResponseDto,
  PersistedAgentChatMessage,
} from "../types/agentPlayground";

interface SessionResultPanelProps {
  result: AgentSessionResponseDto | null;
  history?: PersistedAgentChatMessage[];
}

function stringifyValue(value: unknown): string {
  if (typeof value === "string") return value;
  return JSON.stringify(value, null, 2);
}

export function SessionResultPanel({ result, history = [] }: SessionResultPanelProps) {
  const scrollRef = useRef<HTMLDivElement | null>(null);
  const conversation = result?.messages?.length
    ? result.messages
    : history.map((message) => ({
        role: message.role,
        content: message.content,
      }));
  const payload = result?.artifact_preview?.payload || {};
  const decision = payload.decision as Record<string, unknown> | undefined;
  const executionTrace = Array.isArray(payload.execution_trace)
    ? (payload.execution_trace as Array<Record<string, unknown>>)
    : [];
  const toolContext =
    payload.tool_context && typeof payload.tool_context === "object"
      ? (payload.tool_context as Record<string, unknown>)
      : {};
  const toolEntries = Object.entries(toolContext);
  const loopStopReason =
    typeof payload.loop_stop_reason === "string" ? payload.loop_stop_reason : "";

  useEffect(() => {
    if (!scrollRef.current) return;
    scrollRef.current.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [result, executionTrace.length, toolEntries.length]);

  return (
    <section className="playground-chat-panel agent-console-panel">
      <header className="playground-chat-head">
        <div>
          <p className="workspace-eyebrow">Run Output</p>
          <h2 className="panel-title">Agent Console</h2>
        </div>
        {result ? (
          <div className="tag-row">
            <span className="tag success">{result.session.status}</span>
            <span className="tag">{result.agent.name}</span>
            {typeof payload.mode === "string" ? <span className="tag">{payload.mode}</span> : null}
            {loopStopReason ? <span className="tag">stop: {loopStopReason}</span> : null}
            {result.writeback_status.case_id ? (
              <span className="tag">{result.writeback_status.case_id}</span>
            ) : null}
          </div>
        ) : null}
      </header>

      <div ref={scrollRef} className="playground-chat-scroll">
        {conversation.length ? (
          conversation.map((message, index) => (
            <article
              key={`${message.role}-${index}`}
              className={message.role === "agent" ? "chat-bubble agent console-bubble" : "chat-bubble user console-bubble"}
            >
              <strong>{message.role === "agent" ? result?.agent.name || "Agent" : "You"}</strong>
              <p>{message.content}</p>
            </article>
          ))
        ) : (
          <div className="chat-empty-state">
            <h3>Start a run</h3>
            <p>Send a task and the selected agent will decide, call tools when needed, and report back here.</p>
          </div>
        )}
      </div>

      <section className="playground-insights console-insights">
        {result?.artifact_preview?.summary ? (
          <div className="detail-card compact">
            <strong>Latest Summary</strong>
            <p>{result.artifact_preview.summary}</p>
          </div>
        ) : null}

        {decision ? (
          <div className="detail-card compact">
            <strong>Decision Snapshot</strong>
            <div className="detail-block">
              <div className="tag-row">
                {typeof decision.decision_type === "string" ? (
                  <span className="tag">{decision.decision_type}</span>
                ) : null}
                {typeof decision.task_kind === "string" ? (
                  <span className="tag">{decision.task_kind}</span>
                ) : null}
                {decision.adjusted ? <span className="tag">adjusted</span> : null}
              </div>
              {typeof decision.reasoning_summary === "string" && decision.reasoning_summary ? (
                <p>{decision.reasoning_summary}</p>
              ) : null}
              {typeof decision.suggested_tool_ref === "string" && decision.suggested_tool_ref ? (
                <p>Suggested tool: {decision.suggested_tool_ref}</p>
              ) : null}
            </div>
          </div>
        ) : null}

        {executionTrace.length ? (
          <div className="detail-card compact">
            <strong>Execution Trace</strong>
            <div className="trace-list">
              {executionTrace.map((entry, index) => (
                <article key={`${entry.kind || "step"}-${index}`} className="trace-item">
                  <div className="trace-item-head">
                    <span className="trace-step">Step {String(entry.step ?? index + 1)}</span>
                    <span className="trace-kind">{String(entry.kind ?? "event")}</span>
                  </div>
                  <pre className="json-view compact-json">{stringifyValue(entry)}</pre>
                </article>
              ))}
            </div>
          </div>
        ) : null}

        {toolEntries.length ? (
          <div className="detail-card compact">
            <strong>Tool Outputs</strong>
            <div className="tool-output-list">
              {toolEntries.map(([key, value]) => (
                <article key={key} className="tool-output-card">
                  <div className="trace-item-head">
                    <span className="trace-kind">{key}</span>
                  </div>
                  <pre className="json-view compact-json">{stringifyValue(value)}</pre>
                </article>
              ))}
            </div>
          </div>
        ) : null}
      </section>
    </section>
  );
}

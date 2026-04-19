import { useEffect, useMemo, useRef, useState } from "react";
import { MarkdownRenderer } from "./MarkdownRenderer";
import type {
  AgentSessionResponseDto,
  AgentSessionTaskDto,
  AgentSessionTaskEventDto,
  PersistedAgentChatMessage,
} from "../types/agentPlayground";

interface SessionResultPanelProps {
  result: AgentSessionResponseDto | null;
  history?: PersistedAgentChatMessage[];
  liveTask?: AgentSessionTaskDto | null;
}

type StreamItem =
  | {
      id: string;
      kind: "message";
      role: "user" | "agent";
      author: string;
      content: string;
    }
  | {
      id: string;
      kind: "event";
      label: string;
      summary: string;
      meta?: string;
      tone?: "default" | "success" | "muted";
    }
  | {
      id: string;
      kind: "details";
      title: string;
      open?: boolean;
      sections: Array<{ label: string; lines: string[] }>;
    };

function summarizeValidationPlan(plan: Record<string, unknown> | null): string[] {
  if (!plan) return [];
  const lines: string[] = [];
  const status = typeof plan.status === "string" ? plan.status : "unknown";
  const verificationMode =
    typeof plan.verification_mode === "string" ? plan.verification_mode : null;
  lines.push(`status: ${status}${verificationMode ? ` · ${verificationMode}` : ""}`);
  const suggested = Array.isArray(plan.suggested_checks)
    ? (plan.suggested_checks as Array<Record<string, unknown>>)
    : [];
  suggested.forEach((item) => {
    const summary = typeof item.summary === "string" ? item.summary : "";
    if (summary) lines.push(summary);
  });
  const executed = Array.isArray(plan.executed_checks)
    ? (plan.executed_checks as Array<Record<string, unknown>>)
    : [];
  executed.forEach((item) => {
    const label =
      typeof item.tool_ref === "string"
        ? item.tool_ref
        : typeof item.kind === "string"
          ? item.kind
          : "check";
    const itemStatus = typeof item.status === "string" ? item.status : "done";
    lines.push(`${label}: ${itemStatus}`);
  });
  return lines;
}

function eventLabel(event: AgentSessionTaskEventDto): string {
  if (event.kind === "tool") return "tool";
  if (event.kind === "tool_result") return "result";
  if (event.kind === "decision") return "thinking";
  if (event.kind === "complete") return "complete";
  return event.kind || "event";
}

function eventMeta(event: AgentSessionTaskEventDto): string {
  const bits = [event.current_phase, event.stage].filter(Boolean);
  if (event.tool_ref) bits.push(event.tool_ref);
  return bits.join(" · ");
}

function eventTone(event: AgentSessionTaskEventDto): "default" | "success" | "muted" {
  if (event.kind === "complete" || event.status === "completed") return "success";
  if (event.kind === "phase" || event.kind === "decision") return "muted";
  return "default";
}

function buildConversation(
  history: PersistedAgentChatMessage[],
  result: AgentSessionResponseDto | null,
  liveTask: AgentSessionTaskDto | null,
): StreamItem[] {
  const items: StreamItem[] = [];
  const effectiveMessages =
    result?.messages?.length
      ? result.messages.map((message, index) => ({
          message_id: `result-${index}`,
          role: message.role,
          content: message.content,
        }))
      : history.map((message) => ({
          message_id: message.message_id,
          role: message.role,
          content: message.content,
        }));

  effectiveMessages.forEach((message) => {
    const role = message.role === "agent" ? "agent" : "user";
    items.push({
      id: `message-${message.message_id}`,
      kind: "message",
      role,
      author: role === "agent" ? result?.agent.name || "Agent" : "You",
      content: message.content,
    });
  });

  if (liveTask && liveTask.status !== "completed" && liveTask.message.trim()) {
    const last = items[items.length - 1];
    const duplicatePendingUserMessage =
      last?.kind === "message" &&
      last.role === "user" &&
      last.content.trim() === liveTask.message.trim();
    if (!duplicatePendingUserMessage) {
      items.push({
        id: `pending-user-${liveTask.task_id}`,
        kind: "message",
        role: "user",
        author: "You",
        content: liveTask.message,
      });
    }
  }

  if (liveTask?.events?.length) {
    liveTask.events.forEach((event) => {
      items.push({
        id: `event-${event.sequence}`,
        kind: "event",
        label: eventLabel(event),
        summary: event.summary,
        meta: eventMeta(event),
        tone: eventTone(event),
      });
    });
  }

  const payload =
    result?.artifact_preview?.payload && typeof result.artifact_preview.payload === "object"
      ? result.artifact_preview.payload
      : {};
  const validationPlan =
    payload.validation_plan && typeof payload.validation_plan === "object"
      ? (payload.validation_plan as Record<string, unknown>)
      : null;
  const decision =
    payload.decision && typeof payload.decision === "object"
      ? (payload.decision as Record<string, unknown>)
      : null;

  const sections: Array<{ label: string; lines: string[] }> = [];
  const validationLines = summarizeValidationPlan(validationPlan);
  if (validationLines.length) {
    sections.push({ label: "Validation", lines: validationLines });
  }
  if (result?.artifact_preview?.summary) {
    sections.push({ label: "Summary", lines: [result.artifact_preview.summary] });
  }
  if (decision) {
    sections.push({
      label: "Decision",
      lines: [JSON.stringify(decision, null, 2)],
    });
  }
  if (sections.length) {
    items.push({
      id: "final-details",
      kind: "details",
      title: "Run details",
      open: false,
      sections,
    });
  }

  return items;
}

export function SessionResultPanel({
  result,
  history = [],
  liveTask = null,
}: SessionResultPanelProps) {
  const scrollRef = useRef<HTMLDivElement | null>(null);
  const [showRuntimeStream, setShowRuntimeStream] = useState(true);
  const stream = useMemo(
    () => buildConversation(history, result, liveTask),
    [history, liveTask, result],
  );
  const statusText = liveTask?.status || result?.session.status || "idle";
  const phaseText =
    liveTask?.current_phase ||
    String(result?.artifact_preview?.payload?.current_phase || "standby");
  const activityText =
    liveTask?.current_activity || "Send a coding request to start a live run.";
  const runCompleted = statusText === "completed";
  const hasRuntimeEvents = Boolean(liveTask?.events?.length);

  useEffect(() => {
    if (!scrollRef.current) return;
    scrollRef.current.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [stream.length, activityText, statusText]);

  useEffect(() => {
    if (runCompleted) {
      setShowRuntimeStream(false);
      return;
    }
    setShowRuntimeStream(true);
  }, [runCompleted, liveTask?.task_id]);

  return (
    <section className="playground-chat-panel terminal-session-panel">
      <header className="playground-chat-head terminal-session-head">
        <div>
          <p className="workspace-eyebrow">Live Run</p>
          <h2 className="panel-title">Conversation</h2>
        </div>
        <div className="terminal-status-inline">
          <span className={`terminal-status-dot ${statusText === "completed" ? "done" : ""}`} />
          <span>{statusText}</span>
          <span>/</span>
          <span>{phaseText}</span>
          {runCompleted && hasRuntimeEvents ? (
            <button
              type="button"
              className="terminal-inline-toggle"
              onClick={() => setShowRuntimeStream((current) => !current)}
            >
              {showRuntimeStream ? "Hide runtime" : "Show runtime"}
            </button>
          ) : null}
        </div>
      </header>

      <div ref={scrollRef} className="playground-chat-scroll terminal-stream-scroll">
        {stream.length ? (
          <div className="terminal-stream">
            {stream.map((item) => {
              if (item.kind === "message") {
                return (
                  <article
                    key={item.id}
                    className={`terminal-row terminal-message ${item.role === "agent" ? "agent" : "user"}`}
                  >
                    <div className="terminal-prefix">{item.role === "agent" ? "assistant" : "user"}</div>
                    <div className="terminal-body">
                      <div className="terminal-meta">{item.author}</div>
                      <MarkdownRenderer
                        className="terminal-content"
                        content={item.content}
                      />
                    </div>
                  </article>
                );
              }

              if (item.kind === "event") {
                if (runCompleted && !showRuntimeStream) {
                  return null;
                }
                return (
                  <article
                    key={item.id}
                    className={`terminal-row terminal-event ${item.tone || "default"}`}
                  >
                    <div className="terminal-prefix">run</div>
                    <div className="terminal-body">
                      <div className="terminal-meta">
                        <span className="terminal-event-label">{item.label}</span>
                        {item.meta ? <span>{item.meta}</span> : null}
                      </div>
                      <div className="terminal-content terminal-event-content">{item.summary}</div>
                    </div>
                  </article>
                );
              }

              return (
                <details
                  key={item.id}
                  className="terminal-row terminal-details"
                  open={item.open}
                >
                  <summary>
                    <span className="terminal-prefix">info</span>
                    <span className="terminal-body">
                      <span className="terminal-meta">{item.title}</span>
                    </span>
                  </summary>
                  <div className="terminal-details-body">
                    {item.sections.map((section) => (
                      <section key={section.label} className="terminal-details-section">
                        <strong>{section.label}</strong>
                        {section.lines.map((line, index) => (
                          <pre key={`${section.label}-${index}`} className="terminal-details-line">
                            {line}
                          </pre>
                        ))}
                      </section>
                    ))}
                  </div>
                </details>
              );
            })}

            {(liveTask?.status === "queued" || liveTask?.status === "running") && !liveTask.events.length ? (
              <article className="terminal-row terminal-event muted">
                <div className="terminal-prefix">run</div>
                <div className="terminal-body">
                  <div className="terminal-meta">starting</div>
                  <div className="terminal-content terminal-event-content">{activityText}</div>
                </div>
              </article>
            ) : null}

            {runCompleted && hasRuntimeEvents && !showRuntimeStream ? (
              <article className="terminal-row terminal-event muted">
                <div className="terminal-prefix">run</div>
                <div className="terminal-body">
                  <div className="terminal-meta">runtime</div>
                  <div className="terminal-content terminal-event-content">
                    Runtime progress is hidden after completion. Use “Show runtime” to inspect the full trace.
                  </div>
                </div>
              </article>
            ) : null}
          </div>
        ) : (
          <div className="chat-empty-state terminal-empty-state">
            <h3>Start a live coding run</h3>
            <p>
              The session will appear as one continuous conversation with short
              runtime updates instead of stacked result cards.
            </p>
          </div>
        )}
      </div>

      <footer className="terminal-session-footer">
        <div className="terminal-footer-line">
          <span className="terminal-footer-label">Current activity</span>
          <span>{activityText}</span>
        </div>
        {liveTask?.updated_at ? (
          <div className="terminal-footer-line muted">
            <span className="terminal-footer-label">Updated</span>
            <span>{new Date(liveTask.updated_at).toLocaleTimeString()}</span>
          </div>
        ) : null}
      </footer>
    </section>
  );
}

interface ChatComposerBarProps {
  message: string;
  onChangeMessage: (value: string) => void;
  onSubmit: () => void;
  submitting: boolean;
  disabled?: boolean;
  starterPrompts?: string[];
  label?: string;
  placeholder?: string;
  sendLabel?: string;
}

const defaultStarterPrompts = [
  "查看当前 workspace 顶层目录结构，并总结我可以从哪里开始。",
  "读取一个关键文件并说明它的职责。",
  "搜索仓库里与 agent loop 相关的实现。",
  "检查 git 状态并告诉我有哪些未提交改动。",
];

export function ChatComposerBar({
  message,
  onChangeMessage,
  onSubmit,
  submitting,
  disabled = false,
  starterPrompts = defaultStarterPrompts,
  label = "Message",
  placeholder = "Ask for a file read, repo search, git check, shell command, or a normal conversation with the selected agent.",
  sendLabel = "Send",
}: ChatComposerBarProps) {
  return (
    <section className="chat-composer-card">
      <div className="composer-prompt-row">
        {starterPrompts.map((prompt) => (
          <button
            key={prompt}
            type="button"
            className="prompt-chip"
            onClick={() => onChangeMessage(prompt)}
            disabled={submitting || disabled}
          >
            {prompt}
          </button>
        ))}
      </div>

      <div className="field" style={{ marginBottom: 0 }}>
        <label htmlFor="agent-message">{label}</label>
        <textarea
          id="agent-message"
          className="chat-composer-input"
          value={message}
          onChange={(event) => onChangeMessage(event.target.value)}
          onKeyDown={(event) => {
            if ((event.metaKey || event.ctrlKey) && event.key === "Enter") {
              event.preventDefault();
              onSubmit();
            }
          }}
          placeholder={placeholder}
        />
      </div>
      <div className="chat-composer-actions">
        <span className="composer-hint">Ctrl/Cmd + Enter to send</span>
        <button
          className="primary-button"
          onClick={onSubmit}
          type="button"
          disabled={submitting || disabled || !message.trim()}
        >
          {submitting ? "Sending..." : sendLabel}
        </button>
      </div>
    </section>
  );
}

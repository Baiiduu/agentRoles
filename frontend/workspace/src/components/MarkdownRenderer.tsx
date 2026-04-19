import type { ReactNode } from "react";

interface MarkdownRendererProps {
  content: string;
  className?: string;
}

type Block =
  | { kind: "heading"; level: number; text: string }
  | { kind: "paragraph"; text: string }
  | { kind: "unordered_list"; items: string[] }
  | { kind: "ordered_list"; items: string[] }
  | { kind: "blockquote"; text: string }
  | { kind: "code"; language: string; code: string };

function parseInline(text: string): ReactNode[] {
  const nodes: ReactNode[] = [];
  const pattern =
    /(\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)|`([^`]+)`|\*\*([^*]+)\*\*|\*([^*]+)\*)/g;
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = pattern.exec(text)) !== null) {
    if (match.index > lastIndex) {
      nodes.push(text.slice(lastIndex, match.index));
    }

    if (match[2] && match[3]) {
      nodes.push(
        <a
          key={`${match.index}-link`}
          href={match[3]}
          target="_blank"
          rel="noreferrer"
        >
          {match[2]}
        </a>,
      );
    } else if (match[4]) {
      nodes.push(<code key={`${match.index}-code`}>{match[4]}</code>);
    } else if (match[5]) {
      nodes.push(<strong key={`${match.index}-strong`}>{match[5]}</strong>);
    } else if (match[6]) {
      nodes.push(<em key={`${match.index}-em`}>{match[6]}</em>);
    }

    lastIndex = pattern.lastIndex;
  }

  if (lastIndex < text.length) {
    nodes.push(text.slice(lastIndex));
  }

  return nodes;
}

function parseMarkdown(content: string): Block[] {
  const blocks: Block[] = [];
  const lines = content.replace(/\r\n/g, "\n").split("\n");
  let index = 0;

  while (index < lines.length) {
    const line = lines[index];

    if (!line.trim()) {
      index += 1;
      continue;
    }

    const codeMatch = line.match(/^```([\w-]*)\s*$/);
    if (codeMatch) {
      const language = codeMatch[1] || "";
      const codeLines: string[] = [];
      index += 1;
      while (index < lines.length && !lines[index].match(/^```/)) {
        codeLines.push(lines[index]);
        index += 1;
      }
      if (index < lines.length) {
        index += 1;
      }
      blocks.push({ kind: "code", language, code: codeLines.join("\n") });
      continue;
    }

    const headingMatch = line.match(/^(#{1,6})\s+(.*)$/);
    if (headingMatch) {
      blocks.push({
        kind: "heading",
        level: headingMatch[1].length,
        text: headingMatch[2].trim(),
      });
      index += 1;
      continue;
    }

    if (line.startsWith(">")) {
      const quoteLines: string[] = [];
      while (index < lines.length && lines[index].startsWith(">")) {
        quoteLines.push(lines[index].replace(/^>\s?/, ""));
        index += 1;
      }
      blocks.push({ kind: "blockquote", text: quoteLines.join(" ") });
      continue;
    }

    if (/^[-*+]\s+/.test(line)) {
      const items: string[] = [];
      while (index < lines.length && /^[-*+]\s+/.test(lines[index])) {
        items.push(lines[index].replace(/^[-*+]\s+/, "").trim());
        index += 1;
      }
      blocks.push({ kind: "unordered_list", items });
      continue;
    }

    if (/^\d+\.\s+/.test(line)) {
      const items: string[] = [];
      while (index < lines.length && /^\d+\.\s+/.test(lines[index])) {
        items.push(lines[index].replace(/^\d+\.\s+/, "").trim());
        index += 1;
      }
      blocks.push({ kind: "ordered_list", items });
      continue;
    }

    const paragraphLines: string[] = [];
    while (
      index < lines.length &&
      lines[index].trim() &&
      !lines[index].match(/^```/) &&
      !lines[index].match(/^(#{1,6})\s+/) &&
      !lines[index].startsWith(">") &&
      !lines[index].match(/^[-*+]\s+/) &&
      !lines[index].match(/^\d+\.\s+/)
    ) {
      paragraphLines.push(lines[index].trim());
      index += 1;
    }
    blocks.push({ kind: "paragraph", text: paragraphLines.join(" ") });
  }

  return blocks;
}

export function MarkdownRenderer({
  content,
  className = "",
}: MarkdownRendererProps) {
  const blocks = parseMarkdown(content);

  return (
    <div className={`markdown-renderer ${className}`.trim()}>
      {blocks.map((block, index) => {
        if (block.kind === "heading") {
          const headingLevel = Math.min(block.level + 2, 6);
          if (headingLevel === 3) {
            return <h3 key={`heading-${index}`}>{parseInline(block.text)}</h3>;
          }
          if (headingLevel === 4) {
            return <h4 key={`heading-${index}`}>{parseInline(block.text)}</h4>;
          }
          if (headingLevel === 5) {
            return <h5 key={`heading-${index}`}>{parseInline(block.text)}</h5>;
          }
          return <h6 key={`heading-${index}`}>{parseInline(block.text)}</h6>;
        }
        if (block.kind === "blockquote") {
          return <blockquote key={`quote-${index}`}>{parseInline(block.text)}</blockquote>;
        }
        if (block.kind === "unordered_list") {
          return (
            <ul key={`ul-${index}`}>
              {block.items.map((item, itemIndex) => (
                <li key={`ul-${index}-${itemIndex}`}>{parseInline(item)}</li>
              ))}
            </ul>
          );
        }
        if (block.kind === "ordered_list") {
          return (
            <ol key={`ol-${index}`}>
              {block.items.map((item, itemIndex) => (
                <li key={`ol-${index}-${itemIndex}`}>{parseInline(item)}</li>
              ))}
            </ol>
          );
        }
        if (block.kind === "code") {
          return (
            <pre key={`code-${index}`} className="markdown-code-block">
              {block.language ? <span className="markdown-code-lang">{block.language}</span> : null}
              <code>{block.code}</code>
            </pre>
          );
        }
        return <p key={`p-${index}`}>{parseInline(block.text)}</p>;
      })}
    </div>
  );
}

"use client";

import React from "react";

interface MarkdownRendererProps {
  content: string;
}

/**
 * Lightweight Markdown renderer — handles bold, italic, code blocks,
 * inline code, headers, lists, and links without external dependencies.
 */
export default function MarkdownRenderer({ content }: MarkdownRendererProps) {
  if (!content) return null;

  const lines = content.split("\n");
  const elements: React.ReactNode[] = [];
  let inCodeBlock = false;
  let codeBlockLang = "";
  let codeLines: string[] = [];
  let listItems: React.ReactNode[] = [];
  let listType: "ul" | "ol" | null = null;

  const flushList = () => {
    if (listItems.length > 0) {
      if (listType === "ol") {
        elements.push(<ol key={`ol-${elements.length}`} className="agent-md-ol">{listItems}</ol>);
      } else {
        elements.push(<ul key={`ul-${elements.length}`} className="agent-md-ul">{listItems}</ul>);
      }
      listItems = [];
      listType = null;
    }
  };

  const renderInline = (text: string): React.ReactNode[] => {
    const parts: React.ReactNode[] = [];
    // Process bold, italic, inline code, links
    const regex = /(\*\*(.+?)\*\*)|(\*(.+?)\*)|(`(.+?)`)|(\[(.+?)\]\((.+?)\))/g;
    let lastIndex = 0;
    let match;
    let key = 0;

    while ((match = regex.exec(text)) !== null) {
      if (match.index > lastIndex) {
        parts.push(text.slice(lastIndex, match.index));
      }
      if (match[2]) {
        parts.push(<strong key={key++}>{match[2]}</strong>);
      } else if (match[4]) {
        parts.push(<em key={key++}>{match[4]}</em>);
      } else if (match[6]) {
        parts.push(<code key={key++} className="agent-md-inline-code">{match[6]}</code>);
      } else if (match[8] && match[9]) {
        parts.push(
          <a key={key++} href={match[9]} target="_blank" rel="noopener noreferrer" className="agent-md-link">
            {match[8]}
          </a>
        );
      }
      lastIndex = match.index + match[0].length;
    }
    if (lastIndex < text.length) {
      parts.push(text.slice(lastIndex));
    }
    return parts.length ? parts : [text];
  };

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    // Code block toggle
    if (line.startsWith("```")) {
      if (!inCodeBlock) {
        flushList();
        inCodeBlock = true;
        codeBlockLang = line.slice(3).trim();
        codeLines = [];
      } else {
        elements.push(
          <pre key={`code-${elements.length}`} className="agent-md-code-block">
            <div className="agent-md-code-lang">{codeBlockLang || "code"}</div>
            <code>{codeLines.join("\n")}</code>
          </pre>
        );
        inCodeBlock = false;
        codeBlockLang = "";
      }
      continue;
    }

    if (inCodeBlock) {
      codeLines.push(line);
      continue;
    }

    // Empty line
    if (!line.trim()) {
      flushList();
      continue;
    }

    // Headers
    const headerMatch = line.match(/^(#{1,4})\s+(.+)/);
    if (headerMatch) {
      flushList();
      const level = headerMatch[1].length;
      const Tag = `h${level}` as keyof JSX.IntrinsicElements;
      elements.push(
        <Tag key={`h-${elements.length}`} className={`agent-md-h${level}`}>
          {renderInline(headerMatch[2])}
        </Tag>
      );
      continue;
    }

    // Unordered list
    const ulMatch = line.match(/^[\s]*[-*]\s+(.+)/);
    if (ulMatch) {
      if (listType !== "ul") flushList();
      listType = "ul";
      listItems.push(<li key={`li-${listItems.length}`}>{renderInline(ulMatch[1])}</li>);
      continue;
    }

    // Ordered list
    const olMatch = line.match(/^[\s]*\d+[.\u3001]\s*(.+)/);
    if (olMatch) {
      if (listType !== "ol") flushList();
      listType = "ol";
      listItems.push(<li key={`li-${listItems.length}`}>{renderInline(olMatch[1])}</li>);
      continue;
    }

    // Regular paragraph
    flushList();
    elements.push(
      <p key={`p-${elements.length}`} className="agent-md-p">
        {renderInline(line)}
      </p>
    );
  }

  // Flush remaining
  if (inCodeBlock && codeLines.length) {
    elements.push(
      <pre key={`code-${elements.length}`} className="agent-md-code-block">
        <code>{codeLines.join("\n")}</code>
      </pre>
    );
  }
  flushList();

  return <div className="agent-md">{elements}</div>;
}

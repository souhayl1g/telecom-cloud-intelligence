"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";
import MessageActions from "./MessageActions";

export interface ChatMessageData {
  role: "user" | "assistant" | "system";
  content: string;
  timestamp?: number;
}

interface ChatMessageProps {
  message: ChatMessageData;
  onRegenerate?: () => void;
  disabled?: boolean;
}

export default function ChatMessage({ message, onRegenerate, disabled }: ChatMessageProps) {
  const isUser = message.role === "user";
  const timeStr = message.timestamp
    ? new Date(message.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
    : null;

  return (
    <div className={`l4-msg l4-msg-${message.role}`}>
      <div className="l4-msg-avatar">
        {isUser ? (
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
            <circle cx="12" cy="7" r="4" />
          </svg>
        ) : (
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z" />
            <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
            <line x1="12" y1="19" x2="12" y2="23" />
            <line x1="8" y1="23" x2="16" y2="23" />
          </svg>
        )}
      </div>

      <div className="l4-msg-content">
        <div className="l4-msg-meta">
          <span className="l4-msg-role">{isUser ? "You" : "NeXo"}</span>
          {timeStr && <span className="l4-msg-time">{timeStr}</span>}
        </div>

        <div className="l4-msg-markdown">
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
              code({ node, inline, className, children, ...props }: any) {
                const match = /language-(\w+)/.exec(className || "");
                const language = match ? match[1] : "text";
                const codeString = String(children).replace(/\n$/, "");

                if (!inline && codeString) {
                  return (
                    <div className="l4-msg-pre">
                      <div className="l4-msg-code-header">
                        <span className="l4-msg-code-lang">{language}</span>
                        <button
                          type="button"
                          className="l4-msg-code-copy"
                          onClick={async () => {
                            try {
                              await navigator.clipboard.writeText(codeString);
                            } catch {
                              // ignore
                            }
                          }}
                          title="Copy code"
                        >
                          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
                            <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
                          </svg>
                          Copy
                        </button>
                      </div>
                      <SyntaxHighlighter
                        style={oneDark}
                        language={language}
                        PreTag="div"
                        {...props}
                      >
                        {codeString}
                      </SyntaxHighlighter>
                    </div>
                  );
                }
                return (
                  <code className="l4-msg-code" {...props}>
                    {children}
                  </code>
                );
              },
              table({ children }: any) {
                return (
                  <div className="l4-msg-table-wrap">
                    <table className="l4-msg-table">{children}</table>
                  </div>
                );
              },
              th({ children }: any) {
                return <th className="l4-msg-th">{children}</th>;
              },
              td({ children }: any) {
                return <td className="l4-msg-td">{children}</td>;
              },
            }}
          >
            {message.content}
          </ReactMarkdown>
        </div>

        {!isUser && onRegenerate && (
          <MessageActions content={message.content} onRegenerate={onRegenerate} disabled={disabled} />
        )}
      </div>
    </div>
  );
}

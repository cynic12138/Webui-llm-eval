"use client";

import { useEffect, useRef, useState, useMemo } from "react";
import { usePathname } from "next/navigation";
import { Button, Input } from "antd";
import { SendOutlined, StopOutlined, RobotOutlined, UserOutlined } from "@ant-design/icons";
import type { ChatMessage } from "@/types";
import MarkdownRenderer from "./MarkdownRenderer";
import ToolCallCard from "./ToolCallCard";

const { TextArea } = Input;

const routeSuggestions: Record<string, string[]> = {
  "/dashboard": ["查看我的概览数据", "最近的评测任务状态", "评测趋势分析", "帮我预估评测费用"],
  "/models": ["查看我的所有模型", "帮我添加一个新模型", "测试模型连接", "对比模型性能"],
  "/datasets": ["查看数据集列表", "帮我预览数据集内容", "数据集适合哪些评测？"],
  "/evaluations": ["查看评测任务列表", "哪些评测失败了？帮我分析", "重试失败的任务", "对比多个评测结果"],
  "/evaluations/new": ["推荐评测配置", "帮我预估这次评测的费用", "哪些维度适合我的场景？"],
  "/leaderboard": ["查看 ELO 排行榜", "哪个模型综合表现最好？", "查看基准测试排行"],
  "/comparison": ["对比两个评测任务", "分析模型差异", "哪个模型在哪些方面更强？"],
  "/prompts": ["查看提示词模板", "帮我创建一个新的提示词模板", "运行提示词A/B实验"],
  "/arena": ["创建一场模型对决", "查看竞技场历史", "哪个模型竞技场胜率最高？"],
  "/benchmarks": ["查看所有基准测试", "推荐适合的基准测试", "创建基准评测任务"],
  "/admin": ["查看平台统计", "查看审计日志", "管理用户状态"],
  "/teams": ["查看我的团队", "创建一个新组织", "共享评测任务给团队"],
  "/settings/api-keys": ["查看我的API密钥", "创建新密钥", "API使用说明"],
};
const defaultSuggestions = ["查看我的所有模型", "帮我创建一个评测任务", "查看 ELO 排行榜", "带我去数据集页面"];

interface ChatViewProps {
  messages: ChatMessage[];
  loading: boolean;
  onSend: (msg: string) => void;
  onStop: () => void;
  suggestions?: {label: string; prompt: string}[];
}

export default function ChatView({ messages, loading, onSend, onStop, suggestions = [] }: ChatViewProps) {
  const [input, setInput] = useState("");
  const listRef = useRef<HTMLDivElement>(null);
  const pathname = usePathname();

  const welcomeSuggestions = useMemo(() => {
    for (const [route, items] of Object.entries(routeSuggestions)) {
      if (pathname === route || pathname.startsWith(route + "/")) return items;
    }
    return defaultSuggestions;
  }, [pathname]);

  // Auto-scroll to bottom
  useEffect(() => {
    if (listRef.current) {
      listRef.current.scrollTop = listRef.current.scrollHeight;
    }
  }, [messages]);

  const handleSend = () => {
    if (!input.trim()) return;
    onSend(input.trim());
    setInput("");
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="agent-chat-view">
      <div className="agent-chat-messages" ref={listRef}>
        {messages.length === 0 && (
          <div className="agent-chat-welcome">
            <div className="agent-chat-welcome-icon">
              <RobotOutlined />
            </div>
            <h3>AI 评测助手</h3>
            <p>你好！我可以帮你管理模型、数据集、评测任务，以及查看排行榜等。</p>
            <div className="agent-chat-suggestions">
              {welcomeSuggestions.map((s) => (
                <button
                  key={s}
                  className="agent-chat-suggestion"
                  onClick={() => onSend(s)}
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg) => (
          <div key={msg.id} className={`agent-chat-msg agent-chat-msg--${msg.role}`}>
            <div className="agent-chat-msg-avatar">
              {msg.role === "user" ? <UserOutlined /> : <RobotOutlined />}
            </div>
            <div className="agent-chat-msg-body">
              {msg.role === "assistant" ? (
                <>
                  {msg.content && <MarkdownRenderer content={msg.content} />}
                  {msg.toolCalls?.map((tc) => (
                    <ToolCallCard
                      key={tc.id}
                      name={tc.name}
                      arguments={tc.arguments}
                      status={tc.status}
                      result={tc.result}
                    />
                  ))}
                  {!msg.content && (!msg.toolCalls || msg.toolCalls.length === 0) && loading && (
                    <div className="agent-chat-typing">
                      <span /><span /><span />
                    </div>
                  )}
                </>
              ) : (
                <p>{msg.content}</p>
              )}
            </div>
          </div>
        ))}
      </div>

      {!loading && suggestions.length > 0 && messages.length > 0 && (
        <div className="agent-chat-suggestions">
          {suggestions.map((s) => (
            <button
              key={s.label}
              className="agent-chat-suggestion"
              onClick={() => onSend(s.prompt)}
            >
              {s.label}
            </button>
          ))}
        </div>
      )}

      <div className="agent-chat-input-area">
        <TextArea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="输入消息... (Enter 发送, Shift+Enter 换行)"
          autoSize={{ minRows: 1, maxRows: 4 }}
          disabled={loading}
          className="agent-chat-input"
        />
        {loading ? (
          <Button
            type="primary"
            danger
            icon={<StopOutlined />}
            onClick={onStop}
            className="agent-chat-send-btn"
          />
        ) : (
          <Button
            type="primary"
            icon={<SendOutlined />}
            onClick={handleSend}
            disabled={!input.trim()}
            className="agent-chat-send-btn"
          />
        )}
      </div>
    </div>
  );
}

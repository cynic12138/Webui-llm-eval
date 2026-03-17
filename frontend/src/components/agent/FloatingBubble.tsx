"use client";

import { RobotOutlined, CloseOutlined } from "@ant-design/icons";

interface FloatingBubbleProps {
  open: boolean;
  onClick: () => void;
}

export default function FloatingBubble({ open, onClick }: FloatingBubbleProps) {
  return (
    <button
      className={`agent-bubble ${open ? "agent-bubble--open" : ""}`}
      onClick={onClick}
      aria-label="AI 助手"
    >
      <span className={`agent-bubble-icon ${open ? "agent-bubble-icon--hidden" : ""}`}>
        <RobotOutlined />
      </span>
      <span className={`agent-bubble-icon ${!open ? "agent-bubble-icon--hidden" : ""}`}>
        <CloseOutlined />
      </span>
    </button>
  );
}

"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import { Spin } from "antd";

interface TextSelectionPopoverProps {
  children: React.ReactNode;
  onInterpret?: (text: string) => Promise<string>;
}

export default function TextSelectionPopover({ children, onInterpret }: TextSelectionPopoverProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [selection, setSelection] = useState<{ text: string; x: number; y: number } | null>(null);
  const [result, setResult] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleMouseUp = useCallback(() => {
    const sel = window.getSelection();
    if (!sel || sel.isCollapsed || !sel.toString().trim()) {
      return;
    }
    const text = sel.toString().trim();
    if (text.length < 5 || text.length > 2000) return;

    // Check if selection is within our container
    const range = sel.getRangeAt(0);
    if (!containerRef.current?.contains(range.commonAncestorContainer)) return;

    const rect = range.getBoundingClientRect();
    setSelection({
      text,
      x: rect.left + rect.width / 2,
      y: rect.bottom + 8,
    });
    setResult(null);
  }, []);

  const handleClickOutside = useCallback((e: MouseEvent) => {
    const target = e.target as HTMLElement;
    if (target.closest(".text-selection-popover")) return;
    setSelection(null);
    setResult(null);
  }, []);

  useEffect(() => {
    document.addEventListener("mouseup", handleMouseUp);
    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mouseup", handleMouseUp);
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [handleMouseUp, handleClickOutside]);

  const handleInterpret = async () => {
    if (!selection || !onInterpret) return;
    setLoading(true);
    try {
      const res = await onInterpret(selection.text);
      setResult(res);
    } catch {
      setResult("解读失败，请稍后重试。");
    } finally {
      setLoading(false);
    }
  };

  // Keep popover in viewport
  const popoverStyle: React.CSSProperties = selection ? {
    left: Math.min(Math.max(selection.x - 100, 16), window.innerWidth - 416),
    top: Math.min(selection.y, window.innerHeight - 340),
  } : {};

  return (
    <div ref={containerRef} style={{ position: "relative" }}>
      {children}
      {selection && (
        <div className="text-selection-popover" style={popoverStyle}>
          {!result && !loading && (
            <button className="text-selection-popover-btn" onClick={handleInterpret}>
              AI 解读
            </button>
          )}
          {loading && (
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <Spin size="small" /> <span style={{ fontSize: 12 }}>正在解读...</span>
            </div>
          )}
          {result && (
            <div className="text-selection-result">
              {result}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

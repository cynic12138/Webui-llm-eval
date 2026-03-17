"use client";

import { useEffect, useState, useCallback } from "react";
import { Spin, Tag, Tooltip } from "antd";
import {
  RobotOutlined, DatabaseOutlined, ExperimentOutlined,
  FileTextOutlined, TrophyOutlined, BookOutlined,
  CompassOutlined, SettingOutlined,
  DownOutlined, RightOutlined, WarningOutlined,
} from "@ant-design/icons";
import { agentApi } from "@/lib/api";
import type { AgentToolDefinition } from "@/types";

const CATEGORY_META: Record<string, { label: string; color: string; icon: React.ReactNode }> = {
  models: { label: "模型管理", color: "blue", icon: <RobotOutlined /> },
  datasets: { label: "数据集", color: "green", icon: <DatabaseOutlined /> },
  evaluations: { label: "评测任务", color: "purple", icon: <ExperimentOutlined /> },
  reports: { label: "报告", color: "orange", icon: <FileTextOutlined /> },
  leaderboard: { label: "排行榜", color: "gold", icon: <TrophyOutlined /> },
  benchmarks: { label: "基准测试", color: "cyan", icon: <BookOutlined /> },
  navigation: { label: "导航", color: "geekblue", icon: <CompassOutlined /> },
  admin: { label: "系统管理", color: "red", icon: <SettingOutlined /> },
  skills: { label: "高级技能", color: "magenta", icon: <ExperimentOutlined /> },
};

// Category display order
const CATEGORY_ORDER = [
  "models", "datasets", "evaluations", "reports",
  "leaderboard", "benchmarks", "navigation", "admin", "skills",
];

function ToolItem({ tool }: { tool: AgentToolDefinition }) {
  const [expanded, setExpanded] = useState(false);

  const params = tool.parameters as {
    properties?: Record<string, {
      type?: string;
      description?: string;
      enum?: string[];
      default?: unknown;
    }>;
    required?: string[];
  };
  const properties = params?.properties || {};
  const required = params?.required || [];
  const hasParams = Object.keys(properties).length > 0;

  return (
    <div className="agent-tools-item">
      <div
        className="agent-tools-item-header"
        onClick={() => hasParams && setExpanded(!expanded)}
        style={{ cursor: hasParams ? "pointer" : "default" }}
      >
        <div style={{ flex: 1, minWidth: 0 }}>
          <div className="agent-tools-item-name">
            {hasParams && (
              <span className="agent-tools-item-expand">
                {expanded ? <DownOutlined /> : <RightOutlined />}
              </span>
            )}
            {tool.name}
            {tool.requires_confirmation && (
              <Tooltip title="执行前需要确认">
                <WarningOutlined style={{ color: "#fa8c16", marginLeft: 6, fontSize: 12 }} />
              </Tooltip>
            )}
          </div>
          <div className="agent-tools-item-desc">{tool.description}</div>
        </div>
      </div>
      {expanded && hasParams && (
        <div className="agent-tools-item-params">
          {Object.entries(properties).map(([name, prop]) => (
            <div key={name} className="agent-tools-param">
              <span className="agent-tools-param-name">
                {name}
                {required.includes(name) && (
                  <span className="agent-tools-param-required">*</span>
                )}
              </span>
              <span className="agent-tools-param-type">{prop.type || "any"}</span>
              {prop.description && (
                <span className="agent-tools-param-desc">{prop.description}</span>
              )}
              {prop.enum && (
                <div className="agent-tools-param-enum">
                  {prop.enum.map((v) => (
                    <Tag key={v} style={{ fontSize: 11, margin: "2px 4px 2px 0" }}>{v}</Tag>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default function ToolsPanel() {
  const [tools, setTools] = useState<AgentToolDefinition[]>([]);
  const [loading, setLoading] = useState(true);
  const [collapsedCats, setCollapsedCats] = useState<Set<string>>(new Set());

  useEffect(() => {
    agentApi.tools().then(setTools).catch(() => {}).finally(() => setLoading(false));
  }, []);

  const toggleCategory = useCallback((cat: string) => {
    setCollapsedCats((prev) => {
      const next = new Set(prev);
      if (next.has(cat)) next.delete(cat);
      else next.add(cat);
      return next;
    });
  }, []);

  if (loading) {
    return (
      <div className="agent-panel-loading">
        <Spin size="small" />
      </div>
    );
  }

  // Group by category
  const grouped: Record<string, AgentToolDefinition[]> = {};
  for (const t of tools) {
    if (!grouped[t.category]) grouped[t.category] = [];
    grouped[t.category].push(t);
  }

  // Sort categories
  const sortedCategories = Object.keys(grouped).sort((a, b) => {
    const ia = CATEGORY_ORDER.indexOf(a);
    const ib = CATEGORY_ORDER.indexOf(b);
    return (ia === -1 ? 999 : ia) - (ib === -1 ? 999 : ib);
  });

  return (
    <div className="agent-tools-panel">
      <div className="agent-tools-header">
        <span className="agent-tools-count">
          {tools.length} 个可用工具 · {sortedCategories.length} 个分类
        </span>
      </div>
      {sortedCategories.map((cat) => {
        const items = grouped[cat];
        const meta = CATEGORY_META[cat] || { label: cat, color: "default", icon: null };
        const isCollapsed = collapsedCats.has(cat);
        return (
          <div key={cat} className="agent-tools-group">
            <div
              className="agent-tools-group-title"
              onClick={() => toggleCategory(cat)}
              style={{ cursor: "pointer", userSelect: "none" }}
            >
              <span className="agent-tools-group-expand">
                {isCollapsed ? <RightOutlined /> : <DownOutlined />}
              </span>
              <span className="agent-tools-group-icon">{meta.icon}</span>
              <span>{meta.label}</span>
              <Tag color={meta.color} style={{ marginLeft: 8 }}>{items.length}</Tag>
            </div>
            {!isCollapsed && items.map((t) => (
              <ToolItem key={t.name} tool={t} />
            ))}
          </div>
        );
      })}
    </div>
  );
}

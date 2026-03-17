"use client";

import { useState } from "react";
import {
  LoadingOutlined, CheckCircleOutlined,
  CloseCircleOutlined, DownOutlined, RightOutlined,
} from "@ant-design/icons";

interface ToolCallCardProps {
  name: string;
  arguments: Record<string, unknown>;
  status: "running" | "done" | "error";
  result?: Record<string, unknown>;
}

const TOOL_LABELS: Record<string, string> = {
  // models (6)
  list_models: "查询模型列表",
  get_model: "查看模型详情",
  create_model: "创建模型",
  update_model: "更新模型配置",
  delete_model: "删除模型",
  test_model_connection: "测试模型连接",
  // datasets (4)
  list_datasets: "查询数据集",
  get_dataset: "查看数据集详情",
  preview_dataset: "预览数据集",
  delete_dataset: "删除数据集",
  // evaluations (5)
  create_evaluation: "创建评测",
  list_evaluations: "查询评测任务",
  get_evaluation_status: "查看评测详情",
  cancel_evaluation: "取消评测任务",
  get_evaluation_results: "查看评测结果",
  // reports (3)
  generate_report: "生成报告",
  list_reports: "查看报告列表",
  get_report_download_url: "获取报告下载",
  // leaderboard (2)
  get_leaderboard: "查看排行榜",
  get_benchmark_leaderboard: "基准排行榜",
  // benchmarks (1)
  get_benchmarks: "查看基准测试",
  // navigation (1)
  navigate_to: "页面跳转",
  // admin (3)
  get_platform_stats: "平台统计",
  list_users: "查看用户列表",
  toggle_user_active: "切换用户状态",
  // skills (2)
  quick_model_test: "快速测试模型",
  get_my_overview: "个人概览",
};

export default function ToolCallCard({ name, arguments: args, status, result }: ToolCallCardProps) {
  const [expanded, setExpanded] = useState(false);

  const statusIcon =
    status === "running" ? <LoadingOutlined spin style={{ color: "var(--primary)" }} /> :
    status === "done" ? <CheckCircleOutlined style={{ color: "var(--success)" }} /> :
    <CloseCircleOutlined style={{ color: "var(--error)" }} />;

  const label = TOOL_LABELS[name] || name;

  return (
    <div className={`agent-tool-card agent-tool-card--${status}`}>
      <div className="agent-tool-card-header" onClick={() => setExpanded(!expanded)}>
        <span className="agent-tool-card-icon">{statusIcon}</span>
        <span className="agent-tool-card-label">{label}</span>
        <span className="agent-tool-card-expand">
          {expanded ? <DownOutlined /> : <RightOutlined />}
        </span>
      </div>
      {expanded && (
        <div className="agent-tool-card-body">
          {Object.keys(args).length > 0 && (
            <div className="agent-tool-card-section">
              <div className="agent-tool-card-section-title">参数</div>
              <pre className="agent-tool-card-json">
                {JSON.stringify(args, null, 2)}
              </pre>
            </div>
          )}
          {result && (
            <div className="agent-tool-card-section">
              <div className="agent-tool-card-section-title">结果</div>
              <pre className="agent-tool-card-json">
                {JSON.stringify(result, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

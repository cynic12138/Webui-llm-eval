"use client";

import { useState } from "react";
import { Typography, Tag, Row, Col, Steps } from "antd";
import {
  DashboardOutlined, RobotOutlined, DatabaseOutlined,
  ExperimentOutlined, TrophyOutlined, BookOutlined,
  FileTextOutlined, SwapOutlined, ThunderboltOutlined,
  KeyOutlined, TeamOutlined, SafetyCertificateOutlined,
  SettingOutlined, RocketOutlined,
  ArrowRightOutlined,
} from "@ant-design/icons";
import Link from "next/link";

const { Title, Text, Paragraph } = Typography;

/* ────────── data ────────── */

interface FeatureSection {
  key: string;
  icon: React.ReactNode;
  title: string;
  path: string;
  color: string;
  gradient: string;
  summary: string;
  bullets: string[];
  tip?: string;
}

const sections: FeatureSection[] = [
  {
    key: "dashboard", icon: <DashboardOutlined />, title: "概览", path: "/dashboard",
    color: "#4f6ef7", gradient: "linear-gradient(135deg,#4f6ef7,#818cf8)",
    summary: "系统首页，展示全局统计数据与快捷操作入口",
    bullets: ["统计卡片 — 模型/数据集/任务数量一目了然", "最近评测 — 实时展示任务状态与进度", "快捷入口 — 一键跳转到创建评测等常用功能"],
  },
  {
    key: "models", icon: <RobotOutlined />, title: "模型管理", path: "/models",
    color: "#7c5cf7", gradient: "linear-gradient(135deg,#7c5cf7,#a78bfa)",
    summary: "注册并管理待评测的大语言模型",
    bullets: ["支持 OpenAI / Anthropic / 本地部署等多种 Provider", "配置 API Key、Base URL 和推理参数", "一键连通性测试，确认模型可正常调用"],
    tip: "API Key 加密存储，不会以明文展示",
  },
  {
    key: "datasets", icon: <DatabaseOutlined />, title: "数据集", path: "/datasets",
    color: "#10b981", gradient: "linear-gradient(135deg,#10b981,#34d399)",
    summary: "上传和管理 JSONL 格式的评测数据",
    bullets: ["支持 input/question/prompt 等多种字段名", "可选 output/answer/reference 作为参考答案", "RAG 评测需提供 context 上下文字段"],
  },
  {
    key: "evaluations", icon: <ExperimentOutlined />, title: "评测任务", path: "/evaluations",
    color: "#f59e0b", gradient: "linear-gradient(135deg,#f59e0b,#fbbf24)",
    summary: "核心模块 — 创建、监控、管理评测任务",
    bullets: [
      "四步创建：选模型 → 选数据 → 配维度 → 提交",
      "实时进度：WebSocket 推送逐样本处理状态",
      "丰富维度：LLM-Judge / 幻觉 / 鲁棒性 / 安全 / RAG / 代码执行 / 客观指标等 13+ 维度",
      "结果可视化：雷达图 / 柱状图 / 分数分布 / 详情表格",
    ],
  },
  {
    key: "comparison", icon: <SwapOutlined />, title: "对比分析", path: "/comparison",
    color: "#06b6d4", gradient: "linear-gradient(135deg,#06b6d4,#22d3ee)",
    summary: "跨任务横向对比与逐样本 Diff",
    bullets: ["选择多个已完成任务进行多模型对比", "雷达图 + 柱状图直观展示各指标差异", "逐样本 Diff 查看每条数据的输出与评分差异"],
  },
  {
    key: "prompts", icon: <FileTextOutlined />, title: "提示词工程", path: "/prompts",
    color: "#8b5cf6", gradient: "linear-gradient(135deg,#8b5cf6,#c084fc)",
    summary: "管理垂直领域评测的提示词模板",
    bullets: ["创建生成提示词 — 引导模型在特定领域生成回复", "创建评测提示词 — 定义裁判模型的评判标准", "支持变量占位符，评测时自动替换"],
  },
  {
    key: "leaderboard", icon: <TrophyOutlined />, title: "ELO 排行榜", path: "/leaderboard",
    color: "#eab308", gradient: "linear-gradient(135deg,#eab308,#fde047)",
    summary: "基于 ELO 积分的模型全局排名",
    bullets: ["每次多模型评测自动更新 ELO 分数（初始 1500）", "展示胜/负/平次数和总比赛场次", "随评测积累动态调整，反映模型综合竞争力"],
    tip: "K=32，分差越悬殊 ELO 变化越大",
  },
  {
    key: "arena", icon: <ThunderboltOutlined />, title: "模型竞技场", path: "/arena",
    color: "#ec4899", gradient: "linear-gradient(135deg,#ec4899,#f472b6)",
    summary: "人工盲评对战，直觉投票选出更优回答",
    bullets: ["随机匹配两个模型对同一问题生成回答", "隐藏模型名称，仅凭质量投票", "投票后揭晓身份并更新 ELO"],
  },
  {
    key: "benchmarks", icon: <BookOutlined />, title: "标准基准", path: "/benchmarks",
    color: "#3b82f6", gradient: "linear-gradient(135deg,#3b82f6,#60a5fa)",
    summary: "15+ 内置标准评测基准，无需上传数据即可跑分",
    bullets: [
      "知识推理：MMLU-Pro / C-Eval / HellaSwag / ARC / TruthfulQA",
      "数学：GSM8K / MATH",
      "代码：HumanEval / BigCodeBench / SWE-Bench",
      "对话与指令：MT-Bench / AlpacaEval / IFEval",
      "专业领域：HealthBench / LiveBench",
    ],
  },
  {
    key: "teams", icon: <TeamOutlined />, title: "团队协作", path: "/teams",
    color: "#22c55e", gradient: "linear-gradient(135deg,#22c55e,#4ade80)",
    summary: "多人协同使用评测平台",
    bullets: ["创建团队并邀请成员", "设置管理员/成员角色", "共享模型配置、数据集和评测结果"],
  },
  {
    key: "judge-models", icon: <SafetyCertificateOutlined />, title: "裁判模型", path: "/settings/judge-models",
    color: "#ef4444", gradient: "linear-gradient(135deg,#ef4444,#f87171)",
    summary: "配置用于自动评分的裁判 LLM",
    bullets: ["推荐使用 GPT-4o / Claude 等强模型作为裁判", "适用于 LLM-Judge、垂直领域评测、MT-Bench 等", "未配置时部分维度不可用或回退到启发式评分"],
  },
  {
    key: "agent-model", icon: <RobotOutlined />, title: "AI 助手模型", path: "/settings/agent-model",
    color: "#0891b2", gradient: "linear-gradient(135deg,#0891b2,#06b6d4)",
    summary: "配置页面内 AI 浮动助手的后端模型",
    bullets: ["页面右下角浮动对话框，随时提问", "评测结果页选中文本可调用 AI 解读"],
  },
  {
    key: "api-keys", icon: <KeyOutlined />, title: "API 密钥", path: "/settings/api-keys",
    color: "#ea580c", gradient: "linear-gradient(135deg,#ea580c,#f97316)",
    summary: "管理外部系统调用评测平台的 API Key",
    bullets: ["生成 API Key 供 CI/CD 或自动化系统调用", "设置权限范围，查看/禁用/删除密钥"],
  },
  {
    key: "admin", icon: <SettingOutlined />, title: "系统管理", path: "/admin",
    color: "#64748b", gradient: "linear-gradient(135deg,#475569,#64748b)",
    summary: "用户管理与系统配置（仅管理员）",
    bullets: ["查看所有用户，修改角色/启用/禁用", "查看后台服务运行状态"],
  },
];

const quickSteps = [
  { title: "添加模型", desc: "在「模型管理」中配置待评测的 LLM 及其 API 信息" },
  { title: "准备数据", desc: "上传 JSONL 数据集，或直接使用内置标准基准测试" },
  { title: "配置裁判", desc: "（可选）在「裁判模型」中选择一个强模型用于自动评分" },
  { title: "创建评测", desc: "选择模型、数据、评测维度，一键提交评测任务" },
  { title: "查看结果", desc: "任务完成后查看雷达图、柱状图、分数分布等可视化分析" },
  { title: "对比决策", desc: "在「对比分析」中横向对比，辅助模型选型" },
];

const evalDimensions = [
  { tag: "性能分析", color: "#3b82f6", desc: "延迟与吞吐" },
  { tag: "LLM-Judge", color: "#8b5cf6", desc: "裁判模型打分" },
  { tag: "幻觉检测", color: "#f59e0b", desc: "一致性采样" },
  { tag: "鲁棒性", color: "#ef4444", desc: "输入扰动测试" },
  { tag: "安全检测", color: "#dc2626", desc: "毒性/偏见筛查" },
  { tag: "RAG 评测", color: "#06b6d4", desc: "忠实/相关/完整" },
  { tag: "代码执行", color: "#2563eb", desc: "运行验证正确性" },
  { tag: "一致性", color: "#84cc16", desc: "多次采样自洽" },
  { tag: "指令遵循", color: "#d946ef", desc: "格式约束检查" },
  { tag: "思维链", color: "#eab308", desc: "推理过程分析" },
  { tag: "性价比", color: "#64748b", desc: "成本效益计算" },
  { tag: "垂直领域", color: "#7c3aed", desc: "自定义标准评测" },
  { tag: "客观指标", color: "#10b981", desc: "ROUGE/BLEU等" },
];

/* ────────── component ────────── */

export default function GuidePage() {
  const [activeKey, setActiveKey] = useState<string | null>(null);

  return (
    <div className="page-fade-in" style={{ maxWidth: 1080, margin: "0 auto", padding: "0 0 48px" }}>

      {/* ── Hero ── */}
      <div style={{
        background: "var(--primary-gradient)",
        borderRadius: "var(--radius-lg)",
        padding: "48px 40px",
        marginBottom: 32,
        position: "relative",
        overflow: "hidden",
      }}>
        <div style={{
          position: "absolute", right: -30, top: -30,
          width: 200, height: 200, borderRadius: "50%",
          background: "rgba(255,255,255,0.08)",
        }} />
        <div style={{
          position: "absolute", right: 80, bottom: -40,
          width: 140, height: 140, borderRadius: "50%",
          background: "rgba(255,255,255,0.05)",
        }} />
        <Title level={2} style={{ color: "#fff", margin: 0, fontWeight: 700 }}>
          <RocketOutlined style={{ marginRight: 10 }} />
          功能指南
        </Title>
        <Paragraph style={{ color: "rgba(255,255,255,0.85)", fontSize: 15, margin: "12px 0 0", maxWidth: 540 }}>
          LLM 评测平台覆盖模型管理、多维度评测、可视化分析、对比决策全流程。
          以下是各功能模块的详细说明，帮助你快速上手。
        </Paragraph>
      </div>

      {/* ── Quick Start ── */}
      <div style={{
        background: "var(--bg-card)",
        borderRadius: "var(--radius-lg)",
        border: "1px solid var(--border-light)",
        padding: "28px 32px",
        marginBottom: 32,
        boxShadow: "var(--shadow-sm)",
      }}>
        <Title level={4} style={{ marginTop: 0, marginBottom: 20 }}>
          <span style={{
            display: "inline-flex", alignItems: "center", justifyContent: "center",
            width: 28, height: 28, borderRadius: "var(--radius-sm)",
            background: "var(--success-light)", color: "var(--success)",
            fontSize: 14, marginRight: 10,
          }}>
            <RocketOutlined />
          </span>
          快速上手
        </Title>
        <Steps
          current={-1}
          size="small"
          direction="horizontal"
          responsive
          items={quickSteps.map((s) => ({
            title: <Text strong style={{ fontSize: 13 }}>{s.title}</Text>,
            description: <Text type="secondary" style={{ fontSize: 12 }}>{s.desc}</Text>,
          }))}
        />
      </div>

      {/* ── Evaluation Dimensions ribbon ── */}
      <div style={{
        background: "var(--bg-card)",
        borderRadius: "var(--radius-lg)",
        border: "1px solid var(--border-light)",
        padding: "24px 32px",
        marginBottom: 32,
        boxShadow: "var(--shadow-sm)",
      }}>
        <Title level={4} style={{ marginTop: 0, marginBottom: 16 }}>
          <span style={{
            display: "inline-flex", alignItems: "center", justifyContent: "center",
            width: 28, height: 28, borderRadius: "var(--radius-sm)",
            background: "var(--warning-light)", color: "var(--warning)",
            fontSize: 14, marginRight: 10,
          }}>
            <ExperimentOutlined />
          </span>
          支持的评测维度
        </Title>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
          {evalDimensions.map((d) => (
            <div key={d.tag} style={{
              display: "inline-flex", alignItems: "center", gap: 6,
              padding: "6px 14px", borderRadius: "var(--radius-full)",
              background: `${d.color}10`, border: `1px solid ${d.color}30`,
              transition: "var(--transition-fast)",
            }}>
              <span style={{
                width: 7, height: 7, borderRadius: "50%",
                background: d.color, flexShrink: 0,
              }} />
              <Text strong style={{ fontSize: 13, color: d.color }}>{d.tag}</Text>
              <Text type="secondary" style={{ fontSize: 12 }}>{d.desc}</Text>
            </div>
          ))}
        </div>
      </div>

      {/* ── Feature Cards Grid ── */}
      <Title level={4} style={{ marginBottom: 16 }}>
        功能模块总览
      </Title>
      <Row gutter={[16, 16]}>
        {sections.map((s) => {
          const isOpen = activeKey === s.key;
          return (
            <Col xs={24} sm={12} lg={8} key={s.key}>
              <div
                onClick={() => setActiveKey(isOpen ? null : s.key)}
                style={{
                  background: "var(--bg-card)",
                  borderRadius: "var(--radius-md)",
                  border: `1px solid ${isOpen ? s.color + "60" : "var(--border-light)"}`,
                  boxShadow: isOpen ? `0 0 0 1px ${s.color}30, var(--shadow-md)` : "var(--shadow-xs)",
                  cursor: "pointer",
                  transition: "var(--transition-normal)",
                  overflow: "hidden",
                  height: "100%",
                  display: "flex",
                  flexDirection: "column",
                }}
              >
                {/* Card header */}
                <div style={{ padding: "20px 20px 12px" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 10 }}>
                    <span style={{
                      display: "inline-flex", alignItems: "center", justifyContent: "center",
                      width: 36, height: 36, borderRadius: "var(--radius-sm)",
                      background: s.gradient, color: "#fff", fontSize: 17,
                      boxShadow: `0 4px 12px ${s.color}30`,
                    }}>
                      {s.icon}
                    </span>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                        <Text strong style={{ fontSize: 15 }}>{s.title}</Text>
                        <Link href={s.path} onClick={(e) => e.stopPropagation()}
                          style={{ fontSize: 12, color: s.color, opacity: 0.8 }}
                        >
                          <ArrowRightOutlined />
                        </Link>
                      </div>
                      <Text type="secondary" style={{ fontSize: 12 }}>{s.path}</Text>
                    </div>
                  </div>
                  <Text type="secondary" style={{ fontSize: 13, lineHeight: 1.6 }}>
                    {s.summary}
                  </Text>
                </div>

                {/* Expandable detail */}
                <div style={{
                  maxHeight: isOpen ? 400 : 0,
                  opacity: isOpen ? 1 : 0,
                  overflow: "hidden",
                  transition: "max-height 0.35s cubic-bezier(0.4,0,0.2,1), opacity 0.25s ease",
                }}>
                  <div style={{
                    padding: "0 20px 16px",
                    borderTop: `1px solid var(--border-light)`,
                    marginTop: 4,
                    paddingTop: 12,
                  }}>
                    <ul style={{ margin: 0, paddingLeft: 16, listStyle: "none" }}>
                      {s.bullets.map((b, i) => (
                        <li key={i} style={{
                          fontSize: 13, color: "var(--text-secondary)",
                          lineHeight: 1.7, position: "relative", paddingLeft: 14,
                        }}>
                          <span style={{
                            position: "absolute", left: 0, top: 9,
                            width: 5, height: 5, borderRadius: "50%",
                            background: s.color, opacity: 0.6,
                          }} />
                          {b}
                        </li>
                      ))}
                    </ul>
                    {s.tip && (
                      <div style={{
                        marginTop: 10, padding: "8px 12px",
                        borderRadius: "var(--radius-sm)",
                        background: `${s.color}08`,
                        border: `1px dashed ${s.color}25`,
                        fontSize: 12, color: "var(--text-secondary)",
                      }}>
                        <Text type="secondary" style={{ fontSize: 12 }}>
                          <span style={{ color: s.color, marginRight: 4 }}>Tip:</span>{s.tip}
                        </Text>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </Col>
          );
        })}
      </Row>

      {/* ── Extra tips ── */}
      <div style={{
        background: "var(--bg-card)",
        borderRadius: "var(--radius-lg)",
        border: "1px solid var(--border-light)",
        padding: "24px 32px",
        marginTop: 24,
        boxShadow: "var(--shadow-sm)",
      }}>
        <Title level={4} style={{ marginTop: 0, marginBottom: 14 }}>
          其他实用功能
        </Title>
        <Row gutter={[16, 12]}>
          {[
            { icon: <RobotOutlined />, label: "AI 浮动助手", desc: "右下角对话气泡，随时向 AI 提问或解读评测结果", color: "#8b5cf6" },
            { icon: "🔔", label: "通知中心", desc: "顶部铃铛图标，评测完成时接收浏览器通知", color: "#f59e0b" },
            { icon: "🌓", label: "主题切换", desc: "顶部图标切换亮色 / 暗色主题", color: "#64748b" },
            { icon: "📊", label: "导出报告", desc: "评测结果页支持导出 PDF / Excel / JSONL", color: "#3b82f6" },
          ].map((item) => (
            <Col xs={24} sm={12} key={item.label}>
              <div style={{
                display: "flex", alignItems: "flex-start", gap: 12,
                padding: "12px 14px", borderRadius: "var(--radius-sm)",
                background: "var(--bg-hover)",
              }}>
                <span style={{ fontSize: 18, lineHeight: 1, flexShrink: 0, marginTop: 1 }}>
                  {typeof item.icon === "string" ? item.icon : <span style={{ color: item.color }}>{item.icon}</span>}
                </span>
                <div>
                  <Text strong style={{ fontSize: 13 }}>{item.label}</Text>
                  <br />
                  <Text type="secondary" style={{ fontSize: 12 }}>{item.desc}</Text>
                </div>
              </div>
            </Col>
          ))}
        </Row>
      </div>
    </div>
  );
}

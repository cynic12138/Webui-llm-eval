"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  Card, Progress, Tag, Button, Typography, Descriptions, Alert,
  Skeleton, Space, Row, Col, Statistic,
} from "antd";
import { BarChartOutlined, ReloadOutlined, RetweetOutlined, ThunderboltOutlined } from "@ant-design/icons";
import Link from "next/link";
import { evaluationsApi, BASE_WS_URL } from "@/lib/api";
import type { EvaluationTask, ProgressEvent } from "@/types";
import { formatDate, getStatusColor, formatDuration } from "@/lib/utils";
import { RAW_METRICS } from "@/lib/metricInfo";

const { Title, Text } = Typography;

/** Live progress from the lightweight DB-count endpoint */
interface LiveProgress {
  status: string;
  total_samples: number;
  processed_samples: number;
  progress: number;
  per_model: Record<string, number | { count: number; name: string }>;
  error_message?: string;
}

export default function EvaluationDetailPage() {
  const { id } = useParams();
  const router = useRouter();
  const [task, setTask] = useState<EvaluationTask | null>(null);
  const [loading, setLoading] = useState(true);
  const [retrying, setRetrying] = useState(false);
  const [liveProgress, setLiveProgress] = useState<LiveProgress | null>(null);
  const [wsMessage, setWsMessage] = useState<string>("");
  const [wsPerModel, setWsPerModel] = useState<ProgressEvent["per_model_progress"] | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const tickRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const doneRef = useRef(false);
  const [, setTick] = useState(0);

  const loadTask = useCallback(async () => {
    try {
      const t = await evaluationsApi.get(Number(id));
      setTask(t);
      return t;
    } finally {
      setLoading(false);
    }
  }, [id]);

  const stopPolling = useCallback(() => {
    doneRef.current = true;
    wsRef.current?.close();
    wsRef.current = null;
    if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; }
    if (tickRef.current) { clearInterval(tickRef.current); tickRef.current = null; }
  }, []);

  const connectWebSocket = useCallback(() => {
    if (wsRef.current) wsRef.current.close();
    const ws = new WebSocket(`${BASE_WS_URL}/api/v1/evaluations/${id}/progress`);
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as ProgressEvent;
        // Only use WS for real-time message text and per-model details
        if (data.message) setWsMessage(data.message);
        if (data.per_model_progress) setWsPerModel(data.per_model_progress);
        if (data.status === "completed" || data.status === "failed") {
          if (data.status === "completed" && "Notification" in window && Notification.permission === "granted") {
            new Notification("评测完成", { body: "评测任务已完成" });
          }
          loadTask();
          stopPolling();
        }
      } catch { /* ignore parse errors */ }
    };
    ws.onclose = () => {
      if (!doneRef.current) {
        setTimeout(() => { if (!doneRef.current) connectWebSocket(); }, 2000);
      }
    };
    ws.onerror = () => ws.close();
    wsRef.current = ws;
  }, [id, loadTask, stopPolling]);

  /** Poll the lightweight live-progress endpoint */
  const pollProgress = useCallback(async () => {
    if (doneRef.current) return;
    try {
      const lp = await evaluationsApi.liveProgress(Number(id));
      setLiveProgress(lp);
      if (lp.status === "completed" || lp.status === "failed") {
        await loadTask(); // Refresh full task data
        stopPolling();
      }
    } catch { /* ignore network errors during polling */ }
  }, [id, loadTask, stopPolling]);

  useEffect(() => {
    doneRef.current = false;
    loadTask().then((t) => {
      if (t && (t.status === "running" || t.status === "pending")) {
        connectWebSocket();
        // Poll live-progress every 2s — this drives the progress bar
        pollProgress(); // immediate first poll
        pollRef.current = setInterval(pollProgress, 2000);
        tickRef.current = setInterval(() => setTick((t) => t + 1), 1000);
      }
    });
    return () => { stopPolling(); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  if (loading) {
    return (
      <div className="skeleton-page">
        <Skeleton active paragraph={{ rows: 0 }} />
        <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
          <Col xs={24} lg={16}><Card><Skeleton active paragraph={{ rows: 6 }} /></Card></Col>
          <Col xs={24} lg={8}><Card><Skeleton active paragraph={{ rows: 8 }} /></Card></Col>
        </Row>
      </div>
    );
  }

  if (!task) return <Alert type="error" message="任务不存在" />;

  // === Derive display values ===
  // Priority: WS (real-time) > liveProgress (DB count) > task (ORM field) > defaults
  const status = liveProgress?.status ?? task.status;
  const total = liveProgress?.total_samples ?? task.total_samples ?? 0;

  // Compute progress from WS per-model data if available (most real-time)
  const wsProcessed = wsPerModel
    ? Object.values(wsPerModel).reduce((sum, p) => sum + (p.processed ?? 0), 0)
    : null;
  const wsTotal = wsPerModel
    ? Object.values(wsPerModel).reduce((sum, p) => sum + (p.total ?? 0), 0)
    : null;

  const processed = wsProcessed ?? liveProgress?.processed_samples ?? task.processed_samples ?? 0;
  const wsProgress = wsTotal && wsTotal > 0 ? Math.round((wsProcessed! / wsTotal) * 100) : null;
  const progress = wsProgress ?? liveProgress?.progress ?? task.progress ?? 0;
  const isActive = status === "running" || status === "pending";

  // Status message: combine WS activity description with liveProgress numbers (single source of truth)
  let statusMessage = "";
  if (status === "running") {
    if (progress >= 99 && processed >= total && total > 0) {
      statusMessage = "所有样本已完成，正在汇总结果...";
    } else if (processed > 0 && total > 0) {
      // Use liveProgress numbers as the single source of truth
      // Append WS activity hint (model name / action) if available
      const activityHint = wsMessage?.replace(/[\d]+\/[\d]+/g, "").replace(/已完成\s*$/, "").trim();
      statusMessage = `已完成 ${processed}/${total} 个样本`;
      if (activityHint) statusMessage += ` — ${activityHint}`;
    } else if (wsMessage) {
      statusMessage = wsMessage;
    } else if (total > 0) {
      statusMessage = `正在初始化评测引擎 (共 ${total} 个样本)...`;
    } else {
      statusMessage = "正在准备评测环境...";
    }
  } else if (status === "pending") {
    statusMessage = "等待 Celery Worker 执行...";
  }

  const startPollingForRetry = () => {
    doneRef.current = false;
    setWsMessage("");
    setWsPerModel(null);
    setLiveProgress(null);
    connectWebSocket();
    pollProgress();
    pollRef.current = setInterval(pollProgress, 2000);
    tickRef.current = setInterval(() => setTick((t) => t + 1), 1000);
  };

  return (
    <div className="page-fade-in">
      <div className="page-header">
        <Title level={2}>{task.name}</Title>
        <Space>
          <Button icon={<ReloadOutlined />} onClick={() => { loadTask(); pollProgress(); }}>刷新</Button>
          {(task.status === "failed" || task.status === "cancelled") && (
            <Button
              icon={<RetweetOutlined />}
              loading={retrying}
              onClick={async () => {
                setRetrying(true);
                try {
                  const updated = await evaluationsApi.retry(task.id);
                  setTask(updated);
                  startPollingForRetry();
                } finally {
                  setRetrying(false);
                }
              }}
            >
              重试 {task.retry_count ? `(${task.retry_count})` : ""}
            </Button>
          )}
          {task.status === "completed" && (
            <>
              <Button type="primary" icon={<BarChartOutlined />} onClick={() => router.push(`/results/${task.id}`)}>
                查看结果
              </Button>
              {task.evaluator_config?.domain_eval && task.evaluator_config?.eval_mode === "evaluate_optimize" && (
                <Link href={`/evaluations/${task.id}/optimize`}>
                  <Button icon={<ThunderboltOutlined />}>诊断 &amp; 优化</Button>
                </Link>
              )}
            </>
          )}
        </Space>
      </div>

      <Row gutter={[16, 16]}>
        <Col xs={24} lg={16}>
          <Card title="任务状态">
            {/* Status tag + sample counter */}
            <div style={{ marginBottom: 16, display: "flex", alignItems: "center", gap: 12 }}>
              <Tag color={getStatusColor(status)} style={{ fontSize: 14, padding: "4px 12px" }}>{status.toUpperCase()}</Tag>
              {total > 0 && (
                <Text style={{ fontSize: 14 }}>
                  <Text strong>{processed}</Text>
                  <Text type="secondary"> / {total} 样本</Text>
                </Text>
              )}
            </div>

            {/* Main progress bar — always visible */}
            <Progress
              percent={progress}
              status={status === "failed" ? "exception" : status === "completed" ? "success" : "active"}
              strokeWidth={14}
              format={(pct) => `${pct}%`}
            />

            {/* Status message */}
            {statusMessage && (
              <div style={{ marginTop: 10 }}>
                <Text type="secondary" style={{ fontSize: 13 }}>
                  {isActive && <span className="pulse-dot" style={{ display: "inline-block", width: 6, height: 6, borderRadius: "50%", background: "#1890ff", marginRight: 6, animation: "pulse 1.5s infinite" }} />}
                  {statusMessage}
                </Text>
              </div>
            )}

            {/* Per-model progress from WS or live-progress */}
            {isActive && (wsPerModel || (liveProgress?.per_model && Object.keys(liveProgress.per_model).length > 0)) && (
              <div style={{ marginTop: 16, padding: "12px 16px", background: "var(--bg-secondary, #fafafa)", borderRadius: 8 }}>
                <Text strong style={{ fontSize: 13, marginBottom: 8, display: "block" }}>各模型进度</Text>
                {wsPerModel ? (
                  // WS provides detailed per-model data
                  Object.entries(wsPerModel).map(([mid, p]) => {
                    const pct = p.total > 0 ? Math.round((p.processed / p.total) * 100) : 0;
                    return (
                      <div key={mid} style={{ marginBottom: 6 }}>
                        <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12 }}>
                          <Text type="secondary">{p.model_name || `Model ${mid}`}</Text>
                          <Text type="secondary">{p.processed}/{p.total}</Text>
                        </div>
                        <Progress percent={pct} size="small" strokeWidth={6} status={p.is_processing ? "active" : undefined} showInfo={false} />
                      </div>
                    );
                  })
                ) : (
                  // Fallback: live-progress per_model counts
                  Object.entries(liveProgress!.per_model).map(([modelId, modelInfo]) => {
                    const count = typeof modelInfo === "object" ? modelInfo.count : modelInfo;
                    const name = typeof modelInfo === "object" ? modelInfo.name : `模型 ${modelId}`;
                    const modelSamples = total > 0 ? Math.round(total / Object.keys(liveProgress!.per_model).length) : 0;
                    const pct = modelSamples > 0 ? Math.round((count / modelSamples) * 100) : 0;
                    return (
                      <div key={modelId} style={{ marginBottom: 6 }}>
                        <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12 }}>
                          <Text type="secondary">{name}</Text>
                          <Text type="secondary">{count} 条结果</Text>
                        </div>
                        <Progress percent={Math.min(pct, 100)} size="small" strokeWidth={6} status="active" showInfo={false} />
                      </div>
                    );
                  })
                )}
              </div>
            )}

            {/* Error display */}
            {(task.error_message || liveProgress?.error_message) && (
              <Alert type="error" message={task.error_message || liveProgress?.error_message} style={{ marginTop: 16 }} />
            )}
          </Card>

          {task.results_summary && (
            <Card title="评测结果概览" style={{ marginTop: 16 }}>
              {Object.entries(task.results_summary.by_model || {}).map(([modelId, summary]) => (
                <Card.Grid key={modelId} style={{ width: "100%", padding: 16 }}>
                  <div className="result-model-header">
                    <Text strong>{summary.model_name}</Text>
                    <Text type="secondary">{summary.sample_count} 样本</Text>
                  </div>
                  <Row gutter={8}>
                    {Object.entries(summary.scores).map(([metric, score]) => {
                      const isRaw = RAW_METRICS.has(metric);
                      return (
                        <Col key={metric} span={8}>
                          <Statistic
                            title={metric}
                            value={isRaw ? Math.round(score).toLocaleString() : (score * 100).toFixed(1)}
                            suffix={isRaw ? "字符" : "%"}
                            valueStyle={{ fontSize: 16, color: isRaw ? "#1890ff" : score > 0.7 ? "#52c41a" : score > 0.4 ? "#faad14" : "#ff4d4f" }}
                          />
                        </Col>
                      );
                    })}
                    <Col span={8}>
                      <Statistic
                        title="平均延迟"
                        value={(summary.avg_latency_ms / 1000).toFixed(2)}
                        suffix="s"
                        valueStyle={{ fontSize: 16 }}
                      />
                    </Col>
                  </Row>
                </Card.Grid>
              ))}
            </Card>
          )}
        </Col>

        <Col xs={24} lg={8}>
          <Card title="任务信息">
            <Descriptions column={1} size="small">
              <Descriptions.Item label="任务ID">{task.id}</Descriptions.Item>
              <Descriptions.Item label="创建时间">{formatDate(task.created_at)}</Descriptions.Item>
              <Descriptions.Item label="开始时间">{formatDate(task.started_at)}</Descriptions.Item>
              <Descriptions.Item label="完成时间">{formatDate(task.completed_at)}</Descriptions.Item>
              <Descriptions.Item label="耗时">{formatDuration(task.started_at, task.completed_at)}</Descriptions.Item>
              <Descriptions.Item label="模型数量">{task.model_ids.length} 个</Descriptions.Item>
              <Descriptions.Item label="总样本">{total || task.total_samples}</Descriptions.Item>
              <Descriptions.Item label="已完成">{processed || task.processed_samples}</Descriptions.Item>
            </Descriptions>
          </Card>

          <Card title="评测器配置" style={{ marginTop: 16 }}>
            <div className="eval-config-tags">
              {task.evaluator_config.performance && <Tag color="blue">性能分析</Tag>}
              {task.evaluator_config.llm_judge && <Tag color="purple">LLM-Judge</Tag>}
              {(task.evaluator_config.benchmarks?.length ?? 0) > 0 && <Tag color="green">基准测试</Tag>}
              {task.evaluator_config.hallucination && <Tag color="orange">幻觉检测</Tag>}
              {task.evaluator_config.robustness && <Tag color="red">鲁棒性</Tag>}
              {task.evaluator_config.safety && <Tag color="volcano">安全检测</Tag>}
              {task.evaluator_config.rag_eval && <Tag color="cyan">RAG评测</Tag>}
              {task.evaluator_config.code_execution && <Tag color="geekblue">代码执行</Tag>}
              {task.evaluator_config.consistency && <Tag color="lime">一致性</Tag>}
              {task.evaluator_config.instruction_following && <Tag color="magenta">指令遵循</Tag>}
              {task.evaluator_config.cot_reasoning && <Tag color="gold">思维链</Tag>}
              {task.evaluator_config.cost_analysis && <Tag color="default">性价比</Tag>}
              {task.evaluator_config.domain_eval && <Tag color="purple">垂直领域评测</Tag>}
            </div>
            {task.evaluator_config.domain_eval && (
              <div style={{ marginTop: 8, padding: "8px 12px", background: "var(--bg-secondary, #f5f5f5)", borderRadius: 6, fontSize: 13 }}>
                <Space wrap>
                  <span>领域: <Tag color="cyan">{task.evaluator_config.domain || "通用"}</Tag></span>
                  <span>模式: <Tag color={task.evaluator_config.eval_mode === "evaluate_optimize" ? "green" : "blue"}>{task.evaluator_config.eval_mode === "evaluate_optimize" ? "评测+优化" : "仅评测"}</Tag></span>
                </Space>
              </div>
            )}
          </Card>
        </Col>
      </Row>

      {/* Pulse animation for status dot */}
      <style jsx>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.3; }
        }
      `}</style>
    </div>
  );
}

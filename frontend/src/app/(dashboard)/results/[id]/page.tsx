"use client";

import { useEffect, useState, useMemo } from "react";
import { useParams } from "next/navigation";
import {
  Card, Typography, Table, Tag, Button, Space, Select, Skeleton, Alert,
  Row, Col, Tabs, message, Collapse, Tooltip,
} from "antd";
import { FileExcelOutlined, FilePdfOutlined, MedicineBoxOutlined, ThunderboltOutlined, ArrowLeftOutlined } from "@ant-design/icons";
import Link from "next/link";
import dynamic from "next/dynamic";
import { Spin } from "antd";

const ReactECharts = dynamic(() => import("echarts-for-react"), {
  ssr: false,
  loading: () => <div className="chart-container"><Spin /></div>,
});
import { QuestionCircleOutlined } from "@ant-design/icons";
import { evaluationsApi, reportsApi, modelsApi, agentApi, BASE_URL } from "@/lib/api";
import type { EvaluationTask, EvaluationResult, ModelConfig } from "@/types";
import { formatDate, truncate } from "@/lib/utils";
import { RAW_METRICS, getMetricName, getMetricDesc, formatScore, scoreTagColor } from "@/lib/metricInfo";
import TextSelectionPopover from "@/components/TextSelectionPopover";

const { Title, Text } = Typography;

export default function ResultsPage() {
  const { id } = useParams();
  const [task, setTask] = useState<EvaluationTask | null>(null);
  const [results, setResults] = useState<EvaluationResult[]>([]);
  const [models, setModels] = useState<ModelConfig[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedModel, setSelectedModel] = useState<number | undefined>();
  const [generating, setGenerating] = useState(false);
  const [domainPage, setDomainPage] = useState(1);
  const DOMAIN_PAGE_SIZE = 10;

  useEffect(() => {
    Promise.all([
      evaluationsApi.get(Number(id)),
      evaluationsApi.results(Number(id), { limit: 200 }),
      modelsApi.list(),
    ]).then(([t, r, m]) => {
      setTask(t);
      setResults(r);
      setModels(m);
      if (t.model_ids.length > 0) setSelectedModel(t.model_ids[0]);
    }).catch(() => {
      message.error("加载数据失败");
    }).finally(() => setLoading(false));
  }, [id]);

  const handleGenerateReport = async (format: string) => {
    setGenerating(true);
    try {
      const report = await reportsApi.generate(Number(id), format);
      message.success("报告生成成功，正在下载...");
      // Download with auth token via axios, then trigger browser download
      const resp = await reportsApi.download(report.id);
      const ext = { pdf: "pdf", excel: "xlsx", json: "json" }[format] || "bin";
      const blob = new Blob([resp], { type: resp.type || "application/octet-stream" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `report_${report.id}.${ext}`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      message.error("报告生成失败");
    } finally {
      setGenerating(false);
    }
  };

  const summary = task?.results_summary;

  const modelMap = useMemo(
    () => Object.fromEntries(models.map((m) => [m.id, m.name])),
    [models]
  );

  const scoreKeys = useMemo(() => {
    // Try summary first
    const fromSummary = Object.keys(Object.values(summary?.by_model || {})[0]?.scores || {});
    if (fromSummary.length > 0) return fromSummary;
    // Fall back to extracting from individual results
    const keys = new Set<string>();
    for (const r of results) {
      for (const k of Object.keys(r.scores || {})) keys.add(k);
    }
    return Array.from(keys);
  }, [summary, results]);

  // Count distinct models
  const modelCount = useMemo(() => {
    if (summary?.by_model) return Object.keys(summary.by_model).length;
    const ids = new Set(results.map((r) => r.model_id));
    return ids.size;
  }, [summary, results]);

  // Raw metrics only shown in radar/bar when multiple models exist (single model → always 100%, no info)
  const normalizedKeys = useMemo(
    () => modelCount >= 2 ? scoreKeys : scoreKeys.filter((k) => !RAW_METRICS.has(k)),
    [scoreKeys, modelCount],
  );

  // Pre-compute max values for raw metrics across all models (for normalization)
  const rawMetricMax = useMemo(() => {
    const maxMap: Record<string, number> = {};
    for (const k of scoreKeys) {
      if (!RAW_METRICS.has(k)) continue;
      let max = 0;
      if (summary?.by_model) {
        for (const data of Object.values(summary.by_model)) {
          max = Math.max(max, data.scores[k] || 0);
        }
      } else {
        for (const r of results) {
          max = Math.max(max, (r.scores?.[k] as number) || 0);
        }
      }
      maxMap[k] = max || 1; // avoid division by zero
    }
    return maxMap;
  }, [scoreKeys, summary, results]);

  /** Normalize a score value to 0-100 for charts. Raw metrics are divided by max. */
  const normalizeScore = (key: string, value: number): number => {
    if (RAW_METRICS.has(key)) {
      return Math.round((value / rawMetricMax[key]) * 100);
    }
    return Math.round(value * 100);
  };

  const radarOption = useMemo(() => {
    let radarData: { name: string; value: number[] }[] = [];
    if (summary?.by_model && Object.keys(summary.by_model).length > 0) {
      radarData = Object.entries(summary.by_model).map(([, data]) => ({
        name: data.model_name,
        value: normalizedKeys.map((k) => normalizeScore(k, data.scores[k] || 0)),
      }));
    } else if (results.length > 0 && normalizedKeys.length > 0) {
      const byModel: Record<number, { scores: Record<string, number[]>; name: string }> = {};
      for (const r of results) {
        if (!byModel[r.model_id]) byModel[r.model_id] = { scores: {}, name: modelMap[r.model_id] || `Model ${r.model_id}` };
        for (const [k, v] of Object.entries(r.scores || {})) {
          if (!byModel[r.model_id].scores[k]) byModel[r.model_id].scores[k] = [];
          byModel[r.model_id].scores[k].push(v as number);
        }
      }
      radarData = Object.values(byModel).map((m) => ({
        name: m.name,
        value: normalizedKeys.map((k) => {
          const vals = m.scores[k] || [];
          const avg = vals.length > 0 ? vals.reduce((a, b) => a + b, 0) / vals.length : 0;
          return normalizeScore(k, avg);
        }),
      }));
    }
    return {
      title: { text: "多维度能力雷达图", left: "center", textStyle: { fontWeight: 600 } },
      legend: { bottom: 0, data: radarData.map((d) => d.name) },
      color: ["#4f6ef7", "#7c5cf7", "#52c41a", "#fa8c16", "#13c2c2"],
      radar: {
        indicator: normalizedKeys.map((k) => ({ name: getMetricName(k), max: 100 })),
        radius: "60%",
      },
      series: [{
        type: "radar",
        data: radarData.map((d) => ({ name: d.name, value: d.value })),
      }],
      tooltip: {
        trigger: "item",
        appendToBody: true,
        formatter: (params: { name: string; value: number[] }) => {
          if (!params.value) return "";
          const lines = normalizedKeys.map((k, i) =>
            `${getMetricName(k)}: <b>${params.value[i]}%</b>`
          );
          return `<b>${params.name}</b><br/>${lines.join("<br/>")}`;
        },
      },
    };
  }, [summary, normalizedKeys, results, modelMap, rawMetricMax]);

  const barOption = useMemo(() => {
    let seriesData: { name: string; type: string; data: number[]; barMaxWidth: number; itemStyle: { borderRadius: number[] } }[] = [];
    if (summary?.by_model && Object.keys(summary.by_model).length > 0) {
      seriesData = Object.entries(summary.by_model).map(([, data]) => ({
        name: data.model_name,
        type: "bar",
        data: normalizedKeys.map((k) => normalizeScore(k, data.scores[k] || 0)),
        barMaxWidth: 40,
        itemStyle: { borderRadius: [4, 4, 0, 0] },
      }));
    } else if (results.length > 0 && normalizedKeys.length > 0) {
      const byModel: Record<number, { scores: Record<string, number[]>; name: string }> = {};
      for (const r of results) {
        if (!byModel[r.model_id]) byModel[r.model_id] = { scores: {}, name: modelMap[r.model_id] || `Model ${r.model_id}` };
        for (const [k, v] of Object.entries(r.scores || {})) {
          if (!byModel[r.model_id].scores[k]) byModel[r.model_id].scores[k] = [];
          byModel[r.model_id].scores[k].push(v as number);
        }
      }
      seriesData = Object.values(byModel).map((m) => ({
        name: m.name,
        type: "bar",
        data: normalizedKeys.map((k) => {
          const vals = m.scores[k] || [];
          const avg = vals.length > 0 ? vals.reduce((a, b) => a + b, 0) / vals.length : 0;
          return normalizeScore(k, avg);
        }),
        barMaxWidth: 40,
        itemStyle: { borderRadius: [4, 4, 0, 0] },
      }));
    }
    return {
      title: { text: "模型综合得分对比", left: "center", textStyle: { fontWeight: 600 } },
      tooltip: { trigger: "axis", appendToBody: true },
      legend: { bottom: 0 },
      color: ["#4f6ef7", "#7c5cf7", "#52c41a", "#fa8c16", "#13c2c2"],
      xAxis: { type: "category", data: normalizedKeys.map(getMetricName), axisLabel: { rotate: normalizedKeys.length > 6 ? 30 : 0, fontSize: 11 } },
      yAxis: { type: "value", max: 100, name: "分数(%)" },
      series: seriesData,
    };
  }, [summary, normalizedKeys, results, modelMap, rawMetricMax]);

  const latencyOption = useMemo(() => {
    let latencyData: { name: string; value: number }[] = [];
    if (summary?.by_model && Object.keys(summary.by_model).length > 0) {
      latencyData = Object.entries(summary.by_model).map(([, data]) => ({
        name: data.model_name,
        value: Number((data.avg_latency_ms / 1000).toFixed(2)),
      }));
    } else if (results.length > 0) {
      const byModel: Record<number, { latencies: number[]; name: string }> = {};
      for (const r of results) {
        if (!byModel[r.model_id]) byModel[r.model_id] = { latencies: [], name: modelMap[r.model_id] || `Model ${r.model_id}` };
        if (r.latency_ms) byModel[r.model_id].latencies.push(r.latency_ms);
      }
      latencyData = Object.values(byModel).map((m) => ({
        name: m.name,
        value: m.latencies.length > 0 ? Number(((m.latencies.reduce((a, b) => a + b, 0) / m.latencies.length) / 1000).toFixed(2)) : 0,
      }));
    }
    return {
      title: { text: "平均延迟对比 (s)", left: "center", textStyle: { fontWeight: 600 } },
      tooltip: { trigger: "axis", appendToBody: true },
      color: ["#4f6ef7"],
      xAxis: { type: "category", data: latencyData.map((d) => d.name) },
      yAxis: { type: "value", name: "延迟(s)" },
      series: [{
        type: "bar",
        data: latencyData.map((d) => ({
          value: d.value,
          itemStyle: { borderRadius: [4, 4, 0, 0] },
        })),
        name: "延迟(s)",
        barMaxWidth: 50,
      }],
    };
  }, [summary, results, modelMap]);

  const filteredResults = useMemo(
    () => selectedModel ? results.filter((r) => r.model_id === selectedModel) : results,
    [results, selectedModel]
  );

  const columns = useMemo(() => [
    { title: "#", dataIndex: "sample_index", key: "idx", width: 60, render: (v: number) => v + 1 },
    { title: "输入", dataIndex: "input_text", key: "input", render: (t: string) => <span title={t}>{truncate(t, 80)}</span> },
    { title: "输出", dataIndex: "output_text", key: "output", render: (t: string) => <span title={t}>{truncate(t, 80)}</span> },
    {
      title: "评分", key: "scores",
      render: (_: unknown, record: EvaluationResult) => (
        <Space wrap>
          {Object.entries(record.scores).slice(0, 3).map(([k, v]) => (
            <Tooltip key={k} title={getMetricDesc(k)}>
              <Tag color={scoreTagColor(k, v as number)}>
                {getMetricName(k)}: {formatScore(k, v as number)}
              </Tag>
            </Tooltip>
          ))}
        </Space>
      ),
    },
    { title: "延迟", dataIndex: "latency_ms", key: "latency", render: (v: number) => v ? `${(v / 1000).toFixed(2)}s` : "-" },
  ], []);

  const handleInterpret = async (text: string): Promise<string> => {
    const token = localStorage.getItem("access_token");
    if (!token) return "请先登录";
    try {
      const resp = await fetch(`${BASE_URL}/api/v1/agent/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ message: `请简要解读以下评测内容片段的含义和质量:\n\n"${text}"`, conversation_id: null }),
      });
      const reader = resp.body?.getReader();
      if (!reader) return "无法获取响应";
      let result = "";
      const decoder = new TextDecoder();
      let buffer = "";
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";
        for (const line of lines) {
          if (line.startsWith("data: ")) {
            try {
              const data = JSON.parse(line.slice(6));
              if (data.content) result += data.content;
            } catch { /* skip non-JSON */ }
          }
        }
      }
      return result || "无解读结果";
    } catch {
      return "解读失败";
    }
  };

  if (loading) {
    return (
      <div className="skeleton-page">
        <Skeleton active paragraph={{ rows: 0 }} />
        <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
          <Col xs={24} lg={12}><Card><Skeleton active paragraph={{ rows: 8 }} /></Card></Col>
          <Col xs={24} lg={12}><Card><Skeleton active paragraph={{ rows: 8 }} /></Card></Col>
        </Row>
      </div>
    );
  }

  if (!task) return <Alert type="error" message="任务不存在" />;

  return (
    <div className="page-fade-in">
      <div className="page-header">
        <Space>
          <Link href={`/evaluations/${id}`}>
            <Button icon={<ArrowLeftOutlined />} type="text" />
          </Link>
          <Title level={2} style={{ margin: 0 }}>评测结果: {task.name}</Title>
        </Space>
        <Space>
          <Button icon={<FilePdfOutlined />} loading={generating} onClick={() => handleGenerateReport("pdf")}>导出PDF</Button>
          <Button icon={<FileExcelOutlined />} loading={generating} onClick={() => handleGenerateReport("excel")}>导出Excel</Button>
          <Button onClick={() => {
            const jsonl = filteredResults.map(r => JSON.stringify({
              sample_index: r.sample_index, model_id: r.model_id,
              input: r.input_text, output: r.output_text, reference: r.reference_text,
              scores: r.scores, latency_ms: r.latency_ms,
            })).join("\n");
            const blob = new Blob([jsonl], { type: "application/jsonl" });
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a"); a.href = url; a.download = `results_${id}.jsonl`; a.click();
            URL.revokeObjectURL(url);
          }}>导出JSONL</Button>
        </Space>
      </div>

      <Tabs
        items={[
          {
            key: "overview",
            label: "总览",
            children: (
              <Row gutter={[16, 16]}>
                <Col xs={24} lg={12}>
                  {normalizedKeys.length > 0 && (
                    <Card>
                      <ReactECharts option={radarOption} style={{ height: 350 }} />
                    </Card>
                  )}
                </Col>
                <Col xs={24} lg={12}>
                  <Card>
                    <ReactECharts option={latencyOption} style={{ height: 350 }} />
                  </Card>
                </Col>
                <Col xs={24}>
                  {normalizedKeys.length > 0 && (
                    <Card>
                      <ReactECharts option={barOption} style={{ height: 350 }} />
                    </Card>
                  )}
                </Col>
                {scoreKeys.length > 0 && (
                  <Col xs={24}>
                    <Collapse
                      ghost
                      items={[{
                        key: "metric-legend",
                        label: <Space><QuestionCircleOutlined /><Text strong>指标说明</Text><Text type="secondary">({scoreKeys.length} 个指标)</Text></Space>,
                        children: (
                          <div style={{ columns: scoreKeys.length > 8 ? 2 : 1, columnGap: 24 }}>
                            {scoreKeys.map((k) => (
                              <div key={k} style={{ breakInside: "avoid", marginBottom: 8, padding: "6px 10px", background: "var(--bg-secondary, #f5f5f5)", borderRadius: 6 }}>
                                <div>
                                  <Tag color="blue" style={{ fontSize: 12 }}>{getMetricName(k)}</Tag>
                                  <Text code style={{ fontSize: 11 }}>{k}</Text>
                                </div>
                                <Text type="secondary" style={{ fontSize: 12 }}>{getMetricDesc(k)}</Text>
                              </div>
                            ))}
                          </div>
                        ),
                      }]}
                    />
                  </Col>
                )}
              </Row>
            ),
          },
          {
            key: "distribution",
            label: "分数分布",
            children: (
              <Row gutter={[16, 16]}>
                {scoreKeys.map((metric) => {
                  const isRaw = RAW_METRICS.has(metric);
                  if (isRaw) {
                    // Raw metric (e.g. response_length): use auto-range bins
                    const allValues = results.map((r) => r.scores[metric] || 0).filter((v) => v > 0);
                    if (allValues.length === 0) return null;
                    const minVal = Math.min(...allValues);
                    const maxVal = Math.max(...allValues);
                    const binCount = 10;
                    const binSize = Math.max(1, Math.ceil((maxVal - minVal + 1) / binCount));
                    const binStart = Math.floor(minVal / binSize) * binSize;
                    const bins = Array.from({ length: binCount }, (_, i) => binStart + i * binSize);
                    const counts = bins.map((b) => allValues.filter((s) => s >= b && s < b + binSize).length);
                    counts[binCount - 1] += allValues.filter((s) => s >= bins[binCount - 1] + binSize).length;
                    return (
                      <Col xs={24} lg={12} key={metric}>
                        <Card>
                          <ReactECharts
                            style={{ height: 250 }}
                            option={{
                              title: { text: `${getMetricName(metric)} 分布`, left: "center", textStyle: { fontSize: 14 } },
                              tooltip: { trigger: "axis" },
                              color: ["#fa8c16"],
                              grid: { top: 40, right: 16, bottom: 24, left: 50 },
                              xAxis: { type: "category", data: bins.map((b) => `${b}-${b + binSize}`) },
                              yAxis: { type: "value", minInterval: 1, name: "样本数" },
                              series: [{ type: "bar", data: counts, barMaxWidth: 30, itemStyle: { borderRadius: [4, 4, 0, 0] } }],
                            }}
                          />
                        </Card>
                      </Col>
                    );
                  }
                  // Normalized metric (0-1): percentage bins
                  const allScores = results.map((r) => Math.round((r.scores[metric] || 0) * 100));
                  const bins = Array.from({ length: 10 }, (_, i) => i * 10);
                  const counts = bins.map((b) => allScores.filter((s) => s >= b && s < b + 10).length);
                  counts[9] += allScores.filter((s) => s === 100).length;
                  return (
                    <Col xs={24} lg={12} key={metric}>
                      <Card>
                        <ReactECharts
                          style={{ height: 250 }}
                          option={{
                            title: { text: `${getMetricName(metric)} 分布`, left: "center", textStyle: { fontSize: 14 } },
                            tooltip: { trigger: "axis" },
                            color: ["#4f6ef7"],
                            grid: { top: 40, right: 16, bottom: 24, left: 50 },
                            xAxis: { type: "category", data: bins.map((b) => `${b}-${b + 10}%`) },
                            yAxis: { type: "value", minInterval: 1, name: "样本数" },
                            series: [{ type: "bar", data: counts, barMaxWidth: 30, itemStyle: { borderRadius: [4, 4, 0, 0] } }],
                          }}
                        />
                      </Card>
                    </Col>
                  );
                })}
              </Row>
            ),
          },
          {
            key: "details",
            label: "详细结果",
            children: (
              <Card
                extra={
                  <Select
                    style={{ width: 200 }}
                    placeholder="筛选模型"
                    allowClear
                    onChange={(v) => setSelectedModel(v)}
                    options={task.model_ids.map((mid) => ({ value: mid, label: modelMap[mid] || `Model ${mid}` }))}
                  />
                }
              >
                <Table
                  dataSource={filteredResults}
                  columns={columns}
                  rowKey="id"
                  pagination={{ pageSize: 20 }}
                  scroll={{ x: 800 }}
                />
              </Card>
            ),
          },
          ...(task.evaluator_config?.domain_eval ? [{
            key: "domain",
            label: "领域评测详情",
            children: (
              <TextSelectionPopover onInterpret={handleInterpret}>
              <div>
                <Space style={{ marginBottom: 16 }}>
                  <Select
                    style={{ width: 200 }}
                    placeholder="筛选模型"
                    allowClear
                    value={selectedModel}
                    onChange={(v) => setSelectedModel(v)}
                    options={task.model_ids.map((mid) => ({ value: mid, label: modelMap[mid] || `Model ${mid}` }))}
                  />
                  {task.evaluator_config?.eval_mode === "evaluate_optimize" && (
                    <Link href={`/evaluations/${id}/optimize`}>
                      <Button type="primary" icon={<ThunderboltOutlined />}>诊断 &amp; 优化</Button>
                    </Link>
                  )}
                </Space>
                <div style={{ marginBottom: 12, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span style={{ color: "var(--text-secondary)" }}>共 {filteredResults.length} 条结果</span>
                  <Space>
                    <Button
                      size="small"
                      disabled={domainPage <= 1}
                      onClick={() => setDomainPage((p) => p - 1)}
                    >
                      上一页
                    </Button>
                    <span>{domainPage} / {Math.max(1, Math.ceil(filteredResults.length / DOMAIN_PAGE_SIZE))}</span>
                    <Button
                      size="small"
                      disabled={domainPage >= Math.ceil(filteredResults.length / DOMAIN_PAGE_SIZE)}
                      onClick={() => setDomainPage((p) => p + 1)}
                    >
                      下一页
                    </Button>
                  </Space>
                </div>
                {filteredResults.slice((domainPage - 1) * DOMAIN_PAGE_SIZE, domainPage * DOMAIN_PAGE_SIZE).map((r) => {
                  const problems = (r.metadata?.problems as { segment: string; issue: string; suggestion: string }[]) || [];
                  const judgeReasoning = (r.metadata?.judge_reasoning as string) || "";
                  const domainScores = Object.entries(r.scores).filter(([k]) => k.startsWith("domain_"));
                  const overallScore = r.scores?.domain_overall;

                  // Highlight problem segments in output
                  let highlightedOutput = r.output_text || "";
                  for (const p of problems) {
                    if (p.segment && highlightedOutput.includes(p.segment)) {
                      highlightedOutput = highlightedOutput.replace(
                        p.segment,
                        `<mark class="eval-problem" title="${p.issue}">${p.segment}</mark>`
                      );
                    }
                  }

                  return (
                    <Card
                      key={r.id}
                      size="small"
                      className="eval-result-card"
                      style={{ marginBottom: 12 }}
                      title={
                        <Space>
                          <Tag>#{r.sample_index}</Tag>
                          <span>{modelMap[r.model_id] || `Model ${r.model_id}`}</span>
                          {overallScore !== undefined && (
                            <Tag color={overallScore > 0.7 ? "success" : overallScore > 0.4 ? "warning" : "error"}>
                              总分: {(overallScore * 100).toFixed(0)}%
                            </Tag>
                          )}
                        </Space>
                      }
                      extra={r.latency_ms ? <Tag>{(r.latency_ms / 1000).toFixed(2)}s</Tag> : null}
                    >
                      <Row gutter={16}>
                        <Col xs={24} md={12}>
                          <div style={{ marginBottom: 8 }}>
                            <strong>原始输入：</strong>
                            <div style={{ background: "var(--bg-secondary, #f5f5f5)", padding: 8, borderRadius: 6, marginTop: 4, maxHeight: 200, overflow: "auto", whiteSpace: "pre-wrap", fontSize: 13 }}>
                              {r.input_text || "-"}
                            </div>
                          </div>
                        </Col>
                        <Col xs={24} md={12}>
                          <div style={{ marginBottom: 8 }}>
                            <strong>模型输出：</strong>
                            {problems.length > 0 && <Tag color="error" style={{ marginLeft: 8 }}>{problems.length} 个问题</Tag>}
                            <div
                              style={{ background: "var(--bg-secondary, #f5f5f5)", padding: 8, borderRadius: 6, marginTop: 4, maxHeight: 200, overflow: "auto", whiteSpace: "pre-wrap", fontSize: 13 }}
                              dangerouslySetInnerHTML={{ __html: highlightedOutput }}
                            />
                          </div>
                        </Col>
                      </Row>

                      {domainScores.length > 0 && (
                        <div style={{ marginTop: 8 }}>
                          <strong>维度评分：</strong>
                          <Space wrap style={{ marginTop: 4 }}>
                            {domainScores.map(([k, v]) => (
                              <Tag key={k} color={v > 0.7 ? "success" : v > 0.4 ? "warning" : "error"}>
                                {k.replace("domain_", "")}: {(v * 100).toFixed(0)}%
                              </Tag>
                            ))}
                          </Space>
                        </div>
                      )}

                      {(judgeReasoning || problems.length > 0) && (
                        <Collapse
                          ghost
                          size="small"
                          style={{ marginTop: 8 }}
                          items={[{
                            key: "detail",
                            label: "评判详情",
                            children: (
                              <div>
                                {judgeReasoning && (
                                  <div style={{ marginBottom: 8 }}>
                                    <strong>扣分原因：</strong>
                                    <p style={{ margin: "4px 0", color: "var(--text-secondary)" }}>{judgeReasoning}</p>
                                  </div>
                                )}
                                {problems.length > 0 && (
                                  <div>
                                    <strong>问题片段：</strong>
                                    {problems.map((p, i) => (
                                      <div key={i} style={{ margin: "4px 0", padding: "6px 8px", background: "rgba(239, 68, 68, 0.05)", borderLeft: "3px solid var(--error, #ef4444)", borderRadius: 4 }}>
                                        <div style={{ fontWeight: 500 }}>{p.segment}</div>
                                        <div style={{ color: "var(--error, #ef4444)", fontSize: 12 }}>{p.issue}</div>
                                        {p.suggestion && <div style={{ color: "var(--text-secondary)", fontSize: 12 }}>建议: {p.suggestion}</div>}
                                      </div>
                                    ))}
                                  </div>
                                )}
                              </div>
                            ),
                          }]}
                        />
                      )}
                    </Card>
                  );
                })}
                {filteredResults.length === 0 && <Alert type="info" message="暂无评测结果" />}
              </div>
              </TextSelectionPopover>
            ),
          }] : []),
        ]}
      />
    </div>
  );
}

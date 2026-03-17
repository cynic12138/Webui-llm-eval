"use client";

import { useEffect, useState, useMemo, useCallback } from "react";
import {
  Card, Typography, Select, Button, Table, Tag, Row, Col, Space, Skeleton, message,
} from "antd";
import { SwapOutlined, BarChartOutlined, RadarChartOutlined } from "@ant-design/icons";
import dynamic from "next/dynamic";
import { Spin } from "antd";

const ReactECharts = dynamic(() => import("echarts-for-react"), {
  ssr: false,
  loading: () => <div className="chart-container"><Spin /></div>,
});

import { evaluationsApi, comparisonApi } from "@/lib/api";
import type { EvaluationTask, ComparisonResult } from "@/types";
import { formatDate } from "@/lib/utils";
import { RAW_METRICS, getMetricName } from "@/lib/metricInfo";
import Link from "next/link";

const { Title, Text } = Typography;

const COLORS = ["#4f6ef7", "#7c5cf7", "#52c41a", "#fa8c16", "#13c2c2", "#ff4d4f", "#722ed1", "#eb2f96"];

export default function ComparisonPage() {
  const [tasks, setTasks] = useState<EvaluationTask[]>([]);
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [result, setResult] = useState<ComparisonResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [comparing, setComparing] = useState(false);

  useEffect(() => {
    evaluationsApi.list()
      .then(setTasks)
      .finally(() => setLoading(false));
  }, []);

  const completedTasks = useMemo(
    () => tasks.filter((t) => t.status === "completed"),
    [tasks],
  );

  const handleCompare = useCallback(async () => {
    if (selectedIds.length < 2) {
      message.warning("请至少选择两个已完成的评测任务进行对比");
      return;
    }
    setComparing(true);
    try {
      const data = await comparisonApi.compare(selectedIds);
      setResult(data);
    } catch {
      message.error("对比失败，请重试");
    } finally {
      setComparing(false);
    }
  }, [selectedIds]);

  const modelNames = useMemo(() => {
    if (!result) return [];
    return Object.keys(result.by_model);
  }, [result]);

  // Pre-compute max values for raw metrics (for normalization to 0-100)
  const rawMetricMax = useMemo(() => {
    if (!result) return {};
    const maxMap: Record<string, number> = {};
    for (const k of result.score_keys) {
      if (!RAW_METRICS.has(k)) continue;
      let max = 0;
      for (const name of modelNames) {
        max = Math.max(max, result.by_model[name]?.scores[k] ?? 0);
      }
      maxMap[k] = max || 1;
    }
    return maxMap;
  }, [result, modelNames]);

  /** Normalize a score to 0-100 for charts */
  const normalizeScore = (key: string, value: number): number => {
    if (RAW_METRICS.has(key)) {
      return Math.round((value / rawMetricMax[key]) * 100);
    }
    return Math.round(value * 100);
  };

  const radarOption = useMemo(() => {
    if (!result || result.score_keys.length === 0) return null;
    const indicators = result.score_keys.map((k) => ({ name: getMetricName(k), max: 100 }));
    return {
      title: { text: "模型能力雷达图", left: "center", textStyle: { fontWeight: 600 } },
      tooltip: {
        trigger: "item",
        appendToBody: true,
        formatter: (params: { name: string; value: number[] }) => {
          if (!params.value) return "";
          const lines = result.score_keys.map((k, i) =>
            `${getMetricName(k)}: <b>${params.value[i]}%</b>`
          );
          return `<b>${params.name}</b><br/>${lines.join("<br/>")}`;
        },
      },
      legend: { bottom: 0, data: modelNames },
      color: COLORS,
      radar: { indicator: indicators, shape: "circle", radius: "60%" },
      series: [{
        type: "radar",
        data: modelNames.map((name, i) => ({
          name,
          value: result.score_keys.map((k) => normalizeScore(k, result.by_model[name]?.scores[k] ?? 0)),
          areaStyle: { opacity: 0.15 },
          lineStyle: { width: 2, color: COLORS[i % COLORS.length] },
          itemStyle: { color: COLORS[i % COLORS.length] },
        })),
      }],
    };
  }, [result, modelNames, rawMetricMax]);

  const barOption = useMemo(() => {
    if (!result || result.score_keys.length === 0) return null;
    return {
      title: { text: "指标对比柱状图", left: "center", textStyle: { fontWeight: 600 } },
      tooltip: { trigger: "axis", appendToBody: true, axisPointer: { type: "shadow" } },
      legend: { bottom: 0, data: modelNames },
      color: COLORS,
      xAxis: {
        type: "category",
        data: result.score_keys.map(getMetricName),
        axisLabel: { rotate: result.score_keys.length > 6 ? 30 : 0, fontSize: 11 },
      },
      yAxis: { type: "value", name: "分数(%)", max: 100 },
      series: modelNames.map((name, i) => ({
        name,
        type: "bar",
        data: result.score_keys.map((k) => normalizeScore(k, result.by_model[name]?.scores[k] ?? 0)),
        itemStyle: { color: COLORS[i % COLORS.length], borderRadius: [4, 4, 0, 0] },
        barMaxWidth: 40,
      })),
    };
  }, [result, modelNames, rawMetricMax]);

  const tableColumns = useMemo(() => {
    const cols: object[] = [
      {
        title: "模型",
        dataIndex: "name",
        key: "name",
        fixed: "left" as const,
        width: 160,
        render: (name: string) => <strong>{name}</strong>,
      },
    ];
    if (result) {
      result.score_keys.forEach((sk) => {
        const isRaw = RAW_METRICS.has(sk);
        cols.push({
          title: getMetricName(sk),
          key: sk,
          width: 120,
          render: (_: unknown, record: { name: string; scores: Record<string, number> }) => {
            const val = record.scores[sk];
            if (val === undefined) return "-";
            // Find the best score for this key
            const allVals = modelNames.map((n) => result.by_model[n]?.scores[sk] ?? 0);
            const maxVal = allVals.length > 0 ? Math.max(...allVals) : 0;
            const isBest = allVals.length > 1 && val === maxVal && allVals.filter((v) => v === maxVal).length === 1;
            return (
              <Tag color={isBest ? "success" : "default"} style={{ fontSize: 13 }}>
                {isRaw ? Math.round(val).toLocaleString() : `${(val * 100).toFixed(1)}%`}
              </Tag>
            );
          },
        });
      });
      cols.push(
        {
          title: "平均延迟",
          key: "latency",
          width: 120,
          render: (_: unknown, record: { avg_latency_ms: number }) => (
            <span>{record.avg_latency_ms.toFixed(0)} ms</span>
          ),
        },
        {
          title: "样本数",
          key: "sample_count",
          width: 100,
          render: (_: unknown, record: { sample_count: number }) => record.sample_count,
        },
      );
    }
    return cols;
  }, [result, modelNames]);

  const tableData = useMemo(() => {
    if (!result) return [];
    return modelNames.map((name) => ({
      key: name,
      name,
      scores: result.by_model[name]?.scores ?? {},
      avg_latency_ms: result.by_model[name]?.avg_latency_ms ?? 0,
      sample_count: result.by_model[name]?.sample_count ?? 0,
    }));
  }, [result, modelNames]);

  if (loading) {
    return (
      <div className="skeleton-page">
        <Skeleton active paragraph={{ rows: 0 }} />
        <Card style={{ marginTop: 16 }}><Skeleton active paragraph={{ rows: 6 }} /></Card>
      </div>
    );
  }

  return (
    <div className="page-fade-in">
      <Title level={2} style={{ marginBottom: 24 }}>
        <SwapOutlined style={{ marginRight: 8 }} />
        对比分析
      </Title>

      <Card style={{ marginBottom: 16 }}>
        <Space direction="vertical" size="middle" style={{ width: "100%" }}>
          <Text strong>选择已完成的评测任务进行对比：</Text>
          <Row gutter={16} align="middle">
            <Col flex="auto">
              <Select
                mode="multiple"
                placeholder="请选择至少两个已完成的评测任务"
                value={selectedIds}
                onChange={setSelectedIds}
                style={{ width: "100%" }}
                optionFilterProp="label"
                options={completedTasks.map((t) => ({
                  value: t.id,
                  label: `${t.name} (ID: ${t.id}) - ${formatDate(t.created_at)}`,
                }))}
              />
            </Col>
            <Col>
              <Button
                type="primary"
                icon={<BarChartOutlined />}
                loading={comparing}
                disabled={selectedIds.length < 2}
                onClick={handleCompare}
              >
                开始对比
              </Button>
            </Col>
          </Row>
        </Space>
      </Card>

      {result && (
        <>
          {/* Tasks info */}
          <Card size="small" style={{ marginBottom: 16 }}>
            <Space wrap>
              <Text strong>对比任务：</Text>
              {result.tasks.map((t) => (
                <Tag key={t.id} color="blue">{t.name} (ID: {t.id})</Tag>
              ))}
            </Space>
          </Card>

          {/* Charts */}
          {radarOption && barOption && (
            <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
              <Col xs={24} lg={12}>
                <Card>
                  <ReactECharts option={radarOption} style={{ height: 400 }} />
                </Card>
              </Col>
              <Col xs={24} lg={12}>
                <Card>
                  <ReactECharts option={barOption} style={{ height: 400 }} />
                </Card>
              </Col>
            </Row>
          )}

          {/* Summary table */}
          <Card
            title={
              <Space>
                <RadarChartOutlined />
                <span>模型对比摘要</span>
              </Space>
            }
            style={{ marginBottom: 16 }}
          >
            <Table
              dataSource={tableData}
              columns={tableColumns}
              pagination={false}
              scroll={{ x: "max-content" }}
              rowKey="key"
            />
          </Card>

          {/* Diff links */}
          {result.tasks.length >= 2 && (
            <Card title="逐样本对比 (Diff)">
              <Space direction="vertical" size="small">
                {result.tasks.map((ta, i) =>
                  result.tasks.slice(i + 1).map((tb) => (
                    <Link
                      key={`${ta.id}-${tb.id}`}
                      href={`/comparison/diff?a=${ta.id}&b=${tb.id}`}
                    >
                      <Button type="link" icon={<SwapOutlined />}>
                        对比: {ta.name} vs {tb.name}
                      </Button>
                    </Link>
                  ))
                )}
              </Space>
            </Card>
          )}
        </>
      )}
    </div>
  );
}

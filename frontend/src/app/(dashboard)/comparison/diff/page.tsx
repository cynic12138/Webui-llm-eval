"use client";

import { useEffect, useState, useMemo, Suspense } from "react";
import {
  Card, Typography, Table, Tag, Row, Col, Statistic, Skeleton, Button, Space,
} from "antd";
import {
  SwapOutlined, ArrowLeftOutlined, CheckCircleOutlined,
  CloseCircleOutlined, MinusCircleOutlined,
} from "@ant-design/icons";
import { useSearchParams, useRouter } from "next/navigation";
import { comparisonApi } from "@/lib/api";
import type { DiffResult } from "@/types";
import { RAW_METRICS, getMetricName } from "@/lib/metricInfo";

const { Title, Text, Paragraph } = Typography;

/** Local override: diff page shows raw metrics without unit suffix and uses toFixed(1) for percentages */
function formatScore(key: string, val: number): string {
  if (RAW_METRICS.has(key)) return Math.round(val).toLocaleString();
  return (val * 100).toFixed(1) + "%";
}

function DiffPageContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const taskA = Number(searchParams.get("a") || 0);
  const taskB = Number(searchParams.get("b") || 0);

  const [result, setResult] = useState<DiffResult | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!taskA || !taskB) return;
    setLoading(true);
    comparisonApi
      .diff(taskA, taskB)
      .then(setResult)
      .finally(() => setLoading(false));
  }, [taskA, taskB]);

  const allScoreKeys = useMemo(() => {
    if (!result) return [];
    const keys = new Set<string>();
    result.samples.forEach((s) => {
      Object.keys(s.scores_a).forEach((k) => keys.add(k));
      Object.keys(s.scores_b).forEach((k) => keys.add(k));
    });
    return Array.from(keys).sort();
  }, [result]);

  const columns = useMemo(() => {
    const cols: object[] = [
      {
        title: "#",
        dataIndex: "index",
        key: "index",
        width: 60,
        fixed: "left" as const,
      },
      {
        title: "输入",
        dataIndex: "input",
        key: "input",
        width: 250,
        ellipsis: true,
        render: (text: string) => (
          <Paragraph
            ellipsis={{ rows: 3, expandable: true, symbol: "展开" }}
            style={{ marginBottom: 0, fontSize: 12 }}
          >
            {text || "-"}
          </Paragraph>
        ),
      },
      {
        title: `任务 A (ID: ${taskA}) 输出`,
        dataIndex: "output_a",
        key: "output_a",
        width: 300,
        render: (text: string) => (
          <Paragraph
            ellipsis={{ rows: 3, expandable: true, symbol: "展开" }}
            style={{ marginBottom: 0, fontSize: 12 }}
          >
            {text || "-"}
          </Paragraph>
        ),
      },
      {
        title: `任务 B (ID: ${taskB}) 输出`,
        dataIndex: "output_b",
        key: "output_b",
        width: 300,
        render: (text: string) => (
          <Paragraph
            ellipsis={{ rows: 3, expandable: true, symbol: "展开" }}
            style={{ marginBottom: 0, fontSize: 12 }}
          >
            {text || "-"}
          </Paragraph>
        ),
      },
    ];

    // Score columns for each key
    allScoreKeys.forEach((sk) => {
      cols.push({
        title: getMetricName(sk),
        key: sk,
        width: 150,
        render: (
          _: unknown,
          record: { scores_a: Record<string, number>; scores_b: Record<string, number> },
        ) => {
          const va = record.scores_a[sk];
          const vb = record.scores_b[sk];
          const valA = va !== undefined ? va : null;
          const valB = vb !== undefined ? vb : null;
          const aWins = valA !== null && valB !== null && valA > valB + 0.01;
          const bWins = valA !== null && valB !== null && valB > valA + 0.01;
          return (
            <Space direction="vertical" size={2}>
              <Text style={{ color: aWins ? "#52c41a" : bWins ? "#ff4d4f" : undefined, fontSize: 12 }}>
                A: {valA !== null ? formatScore(sk, valA) : "-"}
              </Text>
              <Text style={{ color: bWins ? "#52c41a" : aWins ? "#ff4d4f" : undefined, fontSize: 12 }}>
                B: {valB !== null ? formatScore(sk, valB) : "-"}
              </Text>
            </Space>
          );
        },
      });
    });

    return cols;
  }, [taskA, taskB, allScoreKeys]);

  if (!taskA || !taskB) {
    return (
      <div className="page-fade-in">
        <Card>
          <Text type="warning">请提供两个任务 ID 参数，例如 ?a=1&b=2</Text>
        </Card>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="skeleton-page">
        <Skeleton active paragraph={{ rows: 0 }} />
        <Row gutter={16} style={{ marginTop: 16 }}>
          <Col span={8}><Card><Skeleton active paragraph={{ rows: 1 }} /></Card></Col>
          <Col span={8}><Card><Skeleton active paragraph={{ rows: 1 }} /></Card></Col>
          <Col span={8}><Card><Skeleton active paragraph={{ rows: 1 }} /></Card></Col>
        </Row>
        <Card style={{ marginTop: 16 }}><Skeleton active paragraph={{ rows: 8 }} /></Card>
      </div>
    );
  }

  return (
    <div className="page-fade-in">
      <Space style={{ marginBottom: 16 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => router.push("/comparison")}>
          返回对比
        </Button>
      </Space>

      <Title level={2} style={{ marginBottom: 24 }}>
        <SwapOutlined style={{ marginRight: 8 }} />
        逐样本对比: 任务 {taskA} vs 任务 {taskB}
      </Title>

      {result && (
        <>
          {/* Summary bar */}
          <Row gutter={16} style={{ marginBottom: 16 }}>
            <Col xs={24} sm={8}>
              <Card>
                <Statistic
                  title={`任务 A (ID: ${taskA}) 更优`}
                  value={result.summary.a_better_count}
                  prefix={<CheckCircleOutlined style={{ color: "#52c41a" }} />}
                  valueStyle={{ color: "#52c41a" }}
                />
              </Card>
            </Col>
            <Col xs={24} sm={8}>
              <Card>
                <Statistic
                  title={`任务 B (ID: ${taskB}) 更优`}
                  value={result.summary.b_better_count}
                  prefix={<CloseCircleOutlined style={{ color: "#ff4d4f" }} />}
                  valueStyle={{ color: "#ff4d4f" }}
                />
              </Card>
            </Col>
            <Col xs={24} sm={8}>
              <Card>
                <Statistic
                  title="平局"
                  value={result.summary.tie_count}
                  prefix={<MinusCircleOutlined style={{ color: "#faad14" }} />}
                  valueStyle={{ color: "#faad14" }}
                />
              </Card>
            </Col>
          </Row>

          {/* Summary tags */}
          <Card size="small" style={{ marginBottom: 16 }}>
            <Space>
              <Tag color="green">A 更优: {result.summary.a_better_count}</Tag>
              <Tag color="red">B 更优: {result.summary.b_better_count}</Tag>
              <Tag color="orange">平局: {result.summary.tie_count}</Tag>
              <Tag>总样本: {result.samples.length}</Tag>
            </Space>
          </Card>

          {/* Diff table */}
          <Card title="逐样本对比明细">
            <Table
              dataSource={result.samples}
              columns={columns}
              rowKey="index"
              pagination={{ pageSize: 10, showSizeChanger: true, pageSizeOptions: ["10", "20", "50"] }}
              scroll={{ x: "max-content" }}
              size="small"
            />
          </Card>
        </>
      )}
    </div>
  );
}

export default function DiffPage() {
  return (
    <Suspense fallback={<Skeleton active />}>
      <DiffPageContent />
    </Suspense>
  );
}

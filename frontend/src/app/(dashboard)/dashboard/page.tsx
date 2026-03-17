"use client";

import { useEffect, useState, useMemo, useCallback } from "react";
import { Row, Col, Card, Statistic, Table, Tag, Typography, Skeleton, Spin } from "antd";
import {
  RobotOutlined, DatabaseOutlined, ExperimentOutlined,
  CheckCircleOutlined,
} from "@ant-design/icons";
import dynamic from "next/dynamic";

const ReactECharts = dynamic(() => import("echarts-for-react"), {
  ssr: false,
  loading: () => <div style={{ height: 250, display: "flex", alignItems: "center", justifyContent: "center" }}><Spin /></div>,
});
import api, { evaluationsApi, modelsApi, datasetsApi } from "@/lib/api";
import type { EvaluationTask, ModelConfig, Dataset } from "@/types";
import { formatDate, getStatusColor } from "@/lib/utils";
import { useDataRefresh } from "@/lib/useDataRefresh";
import Link from "next/link";

const { Title, Text } = Typography;

interface TrendData {
  date: string;
  total: number;
  completed: number;
  failed: number;
  running: number;
}

export default function DashboardPage() {
  const [loading, setLoading] = useState(true);
  const [tasks, setTasks] = useState<EvaluationTask[]>([]);
  const [models, setModels] = useState<ModelConfig[]>([]);
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [trends, setTrends] = useState<TrendData[]>([]);

  const loadDashboard = useCallback(() => {
    setLoading(true);
    Promise.all([
      evaluationsApi.list().catch(() => [] as EvaluationTask[]),
      modelsApi.list().catch(() => [] as ModelConfig[]),
      datasetsApi.list().catch(() => [] as Dataset[]),
    ]).then(([t, m, d]) => {
      setTasks(t);
      setModels(m);
      setDatasets(d);
    }).finally(() => setLoading(false));

    // Fetch trends via API client (non-blocking)
    api.get<TrendData[]>("/evaluations/trends/daily")
      .then((r) => setTrends(r.data))
      .catch(() => {});
  }, []);

  useEffect(() => {
    loadDashboard();
  }, [loadDashboard]);

  useDataRefresh(["evaluations", "models", "datasets"], loadDashboard);

  const { completedTasks, runningTasks } = useMemo(() => {
    let completed = 0, running = 0;
    for (const t of tasks) {
      if (t.status === "completed") completed++;
      else if (t.status === "running") running++;
    }
    return { completedTasks: completed, runningTasks: running };
  }, [tasks]);

  const columns = useMemo(() => [
    { title: "任务名称", dataIndex: "name", key: "name", render: (name: string, record: EvaluationTask) => <Link href={`/evaluations/${record.id}`}>{name}</Link> },
    { title: "状态", dataIndex: "status", key: "status", render: (s: string) => <Tag color={getStatusColor(s)}>{s}</Tag> },
    { title: "进度", dataIndex: "progress", key: "progress", render: (p: number) => `${p}%` },
    { title: "创建时间", dataIndex: "created_at", key: "created_at", render: formatDate },
  ], []);

  if (loading) {
    return (
      <div className="skeleton-page">
        <Skeleton active paragraph={{ rows: 0 }} />
        <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
          {[1, 2, 3, 4].map((i) => (
            <Col xs={24} sm={12} lg={6} key={i}>
              <Card><Skeleton active paragraph={{ rows: 1 }} /></Card>
            </Col>
          ))}
        </Row>
        <Row gutter={[16, 16]} style={{ marginTop: 24 }}>
          <Col xs={24} lg={16}><Card><Skeleton active paragraph={{ rows: 6 }} /></Card></Col>
          <Col xs={24} lg={8}><Card><Skeleton active paragraph={{ rows: 6 }} /></Card></Col>
        </Row>
      </div>
    );
  }

  return (
    <div className="page-fade-in">
      <div style={{ marginBottom: 24 }}>
        <Title level={2} style={{ margin: 0 }}>平台概览</Title>
        <Text className="page-subtitle">查看平台整体运行状况和最新动态</Text>
      </div>

      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} lg={6}>
          <Card className="stat-card stat-card--blue">
            <span className="stat-icon"><RobotOutlined /></span>
            <Statistic title="模型数量" value={models.length} prefix={<RobotOutlined />} valueStyle={{ color: "#4f6ef7" }} />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card className="stat-card stat-card--green">
            <span className="stat-icon"><DatabaseOutlined /></span>
            <Statistic title="数据集" value={datasets.length} prefix={<DatabaseOutlined />} valueStyle={{ color: "#52c41a" }} />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card className="stat-card stat-card--purple">
            <span className="stat-icon"><ExperimentOutlined /></span>
            <Statistic title="评测任务" value={tasks.length} prefix={<ExperimentOutlined />} valueStyle={{ color: "#7c5cf7" }} />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card className="stat-card stat-card--orange">
            <span className="stat-icon"><CheckCircleOutlined /></span>
            <Statistic title="已完成" value={completedTasks} prefix={<CheckCircleOutlined />} valueStyle={{ color: "#52c41a" }} suffix={runningTasks > 0 ? <Tag color="processing" style={{ marginLeft: 8 }}>{runningTasks} 进行中</Tag> : null} />
          </Card>
        </Col>
      </Row>

      {/* Trend Charts */}
      {trends.length > 0 && (
        <Row gutter={[16, 16]} style={{ marginTop: 24 }}>
          <Col xs={24} lg={16}>
            <Card title="评测趋势">
              <ReactECharts
                style={{ height: 250 }}
                option={{
                  tooltip: { trigger: "axis" },
                  legend: { bottom: 0, data: ["总数", "已完成", "失败"] },
                  color: ["#4f6ef7", "#52c41a", "#ff4d4f"],
                  grid: { top: 10, right: 16, bottom: 40, left: 50 },
                  xAxis: { type: "category", data: trends.map((t) => t.date), axisLabel: { fontSize: 11 } },
                  yAxis: { type: "value", minInterval: 1 },
                  series: [
                    { name: "总数", type: "line", data: trends.map((t) => t.total), smooth: true, areaStyle: { opacity: 0.1 } },
                    { name: "已完成", type: "line", data: trends.map((t) => t.completed), smooth: true },
                    { name: "失败", type: "line", data: trends.map((t) => t.failed), smooth: true },
                  ],
                }}
              />
            </Card>
          </Col>
          <Col xs={24} lg={8}>
            <Card title="任务状态分布">
              <ReactECharts
                style={{ height: 250 }}
                option={{
                  tooltip: { trigger: "item" },
                  color: ["#52c41a", "#4f6ef7", "#faad14", "#ff4d4f", "#d9d9d9"],
                  series: [{
                    type: "pie",
                    radius: ["40%", "70%"],
                    label: { formatter: "{b}: {c}" },
                    data: (() => {
                      const counts: Record<string, number> = {};
                      for (const t of tasks) counts[t.status] = (counts[t.status] || 0) + 1;
                      return [
                        { name: "已完成", value: counts["completed"] || 0 },
                        { name: "运行中", value: counts["running"] || 0 },
                        { name: "等待中", value: counts["pending"] || 0 },
                        { name: "失败", value: counts["failed"] || 0 },
                        { name: "已取消", value: counts["cancelled"] || 0 },
                      ].filter((d) => d.value > 0);
                    })(),
                  }],
                }}
              />
            </Card>
          </Col>
        </Row>
      )}

      <Row gutter={[16, 16]} style={{ marginTop: 24 }}>
        <Col xs={24} lg={16}>
          <Card title="最近评测任务" extra={<Link href="/evaluations">查看全部</Link>}>
            <Table
              dataSource={tasks.slice(0, 5)}
              columns={columns}
              rowKey="id"
              pagination={false}
              size="small"
            />
          </Card>
        </Col>
        <Col xs={24} lg={8}>
          <Card title="快速操作">
            <div className="quick-actions">
              <Link href="/models">
                <div className="quick-action-card">
                  <RobotOutlined />
                  添加模型
                </div>
              </Link>
              <Link href="/datasets">
                <div className="quick-action-card">
                  <DatabaseOutlined />
                  上传数据集
                </div>
              </Link>
              <Link href="/evaluations/new">
                <div className="quick-action-card">
                  <ExperimentOutlined />
                  创建评测
                </div>
              </Link>
            </div>
          </Card>
        </Col>
      </Row>
    </div>
  );
}

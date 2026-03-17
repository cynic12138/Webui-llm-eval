"use client";

import { useEffect, useState, useMemo, useCallback } from "react";
import { Card, Table, Typography, Tag, Row, Col, Skeleton } from "antd";
import { TrophyOutlined } from "@ant-design/icons";
import dynamic from "next/dynamic";
import { Spin } from "antd";

const ReactECharts = dynamic(() => import("echarts-for-react"), {
  ssr: false,
  loading: () => <div className="chart-container"><Spin /></div>,
});
import { leaderboardApi } from "@/lib/api";
import { useDataRefresh } from "@/lib/useDataRefresh";
import type { EloScore } from "@/types";

const { Title } = Typography;

const MEDAL_COLORS = ["#FFD700", "#C0C0C0", "#CD7F32"];

export default function LeaderboardPage() {
  const [elo, setElo] = useState<EloScore[]>([]);
  const [loading, setLoading] = useState(true);

  const loadLeaderboard = useCallback(() => {
    setLoading(true);
    leaderboardApi.elo()
      .then(setElo)
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    loadLeaderboard();
  }, [loadLeaderboard]);

  useDataRefresh(["leaderboard"], loadLeaderboard);

  const chartOption = useMemo(() => ({
    title: { text: "ELO 排行榜", left: "center", textStyle: { fontWeight: 600 } },
    tooltip: { trigger: "axis" },
    xAxis: {
      type: "category",
      data: elo.map((e) => e.model_name),
      axisLabel: { rotate: 30 },
    },
    yAxis: {
      type: "value",
      name: "ELO Score",
      min: elo.length > 0 ? Math.max(0, Math.min(...elo.map((e) => e.elo_score)) - 100) : 0,
    },
    series: [{
      type: "bar",
      data: elo.map((e, i) => ({
        value: Math.round(e.elo_score),
        itemStyle: {
          color: MEDAL_COLORS[i] || "#4f6ef7",
          borderRadius: [4, 4, 0, 0],
        },
      })),
      name: "ELO Score",
      barMaxWidth: 50,
    }],
  }), [elo]);

  const winRateOption = useMemo(() => ({
    title: { text: "胜率对比", left: "center", textStyle: { fontWeight: 600 } },
    tooltip: { trigger: "item" },
    legend: { bottom: 0 },
    color: ["#4f6ef7", "#7c5cf7", "#52c41a", "#fa8c16", "#13c2c2", "#ff4d4f"],
    series: [{
      type: "pie",
      radius: ["40%", "70%"],
      data: elo.map((e) => ({ name: e.model_name, value: e.wins })),
      emphasis: {
        itemStyle: {
          shadowBlur: 10,
          shadowOffsetX: 0,
          shadowColor: "rgba(0, 0, 0, 0.1)",
        },
      },
    }],
  }), [elo]);

  const columns = useMemo(() => [
    {
      title: "排名", key: "rank", width: 80,
      render: (_: unknown, record: EloScore, index: number) => (
        index < 3
          ? <TrophyOutlined style={{ color: MEDAL_COLORS[index], fontSize: 20 }} />
          : <span className="rank-number">{index + 1}</span>
      ),
    },
    { title: "模型名称", dataIndex: "model_name", key: "name", render: (n: string) => <strong>{n}</strong> },
    {
      title: "ELO 分数", dataIndex: "elo_score", key: "elo",
      render: (s: number) => <Tag color="blue" style={{ fontSize: 14 }}>{Math.round(s)}</Tag>,
      sorter: (a: EloScore, b: EloScore) => b.elo_score - a.elo_score,
      defaultSortOrder: "descend" as const,
    },
    { title: "胜", dataIndex: "wins", key: "wins", render: (v: number) => <Tag color="success">{v}</Tag> },
    { title: "负", dataIndex: "losses", key: "losses", render: (v: number) => <Tag color="error">{v}</Tag> },
    { title: "平", dataIndex: "draws", key: "draws" },
    { title: "总对局", dataIndex: "total_matches", key: "total" },
    {
      title: "胜率", key: "win_rate",
      render: (_: unknown, r: EloScore) => (
        <span className="win-rate-text" style={{ color: r.win_rate > 0.6 ? "#52c41a" : r.win_rate > 0.4 ? "#faad14" : "#ff4d4f" }}>
          {(r.win_rate * 100).toFixed(1)}%
        </span>
      ),
    },
  ], []);

  if (loading) {
    return (
      <div className="skeleton-page">
        <Skeleton active paragraph={{ rows: 0 }} />
        <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
          <Col xs={24} lg={16}><Card><Skeleton active paragraph={{ rows: 8 }} /></Card></Col>
          <Col xs={24} lg={8}><Card><Skeleton active paragraph={{ rows: 8 }} /></Card></Col>
        </Row>
        <Card style={{ marginTop: 16 }}><Skeleton active paragraph={{ rows: 6 }} /></Card>
      </div>
    );
  }

  return (
    <div className="page-fade-in">
      <Title level={2} style={{ marginBottom: 24 }}>ELO 排行榜</Title>

      {elo.length === 0 ? (
        <Card>
          <p className="empty-state">
            暂无排行数据。完成多模型对比评测后，ELO 分数将自动更新。
          </p>
        </Card>
      ) : (
        <>
          <Row gutter={[16, 16]}>
            <Col xs={24} lg={16}>
              <Card>
                <ReactECharts option={chartOption} style={{ height: 350 }} />
              </Card>
            </Col>
            <Col xs={24} lg={8}>
              <Card>
                <ReactECharts option={winRateOption} style={{ height: 350 }} />
              </Card>
            </Col>
          </Row>

          <Card style={{ marginTop: 16 }}>
            <Table
              dataSource={elo}
              columns={columns}
              rowKey="model_id"
              pagination={false}
            />
          </Card>
        </>
      )}
    </div>
  );
}

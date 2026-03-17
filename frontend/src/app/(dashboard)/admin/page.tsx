"use client";

import { useEffect, useState, useCallback } from "react";
import {
  Card, Table, Typography, Tag, Button, message, Skeleton, Alert,
  Row, Col, Statistic,
} from "antd";
import {
  UserOutlined, RobotOutlined, DatabaseOutlined,
  ExperimentOutlined, CheckCircleOutlined, PercentageOutlined,
} from "@ant-design/icons";
import { adminApi } from "@/lib/api";
import type { User, PlatformStats } from "@/types";
import { getUser } from "@/lib/auth";
import { formatDate } from "@/lib/utils";

const { Title } = Typography;

export default function AdminPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [stats, setStats] = useState<PlatformStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [unauthorized, setUnauthorized] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [currentUser, setCurrentUser] = useState<User | null>(null);

  useEffect(() => {
    setCurrentUser(getUser());
  }, []);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [u, s] = await Promise.all([adminApi.users(), adminApi.stats()]);
      setUsers(u);
      setStats(s);
    } catch (err: unknown) {
      const axiosError = err as { response?: { status?: number; data?: { detail?: string } } };
      if (axiosError?.response?.status === 403) {
        setUnauthorized(true);
      } else {
        setError(axiosError?.response?.data?.detail || "加载数据失败，请稍后重试");
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleToggle = useCallback(async (userId: number) => {
    try {
      await adminApi.toggleUser(userId);
      message.success("用户状态已更新");
      load();
    } catch {
      message.error("操作失败");
    }
  }, [load]);

  if (unauthorized) {
    return <Alert type="error" message="权限不足" description="仅管理员可访问此页面" />;
  }

  if (error) {
    return (
      <Alert
        type="error"
        message="加载失败"
        description={error}
        action={<Button size="small" onClick={load}>重试</Button>}
      />
    );
  }

  if (loading) {
    return (
      <div className="skeleton-page">
        <Skeleton active paragraph={{ rows: 0 }} />
        <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <Col xs={12} lg={4} key={i}><Card><Skeleton active paragraph={{ rows: 1 }} /></Card></Col>
          ))}
        </Row>
        <Card style={{ marginTop: 16 }}><Skeleton active paragraph={{ rows: 6 }} /></Card>
      </div>
    );
  }

  const columns = [
    { title: "ID", dataIndex: "id", key: "id", width: 60 },
    { title: "用户名", dataIndex: "username", key: "username" },
    { title: "邮箱", dataIndex: "email", key: "email" },
    { title: "姓名", dataIndex: "full_name", key: "full_name" },
    { title: "角色", key: "role", render: (_: unknown, r: User) => <Tag color={r.is_admin ? "red" : "blue"}>{r.is_admin ? "管理员" : "用户"}</Tag> },
    { title: "状态", dataIndex: "is_active", key: "is_active", render: (v: boolean) => <Tag color={v ? "success" : "default"}>{v ? "活跃" : "禁用"}</Tag> },
    { title: "注册时间", dataIndex: "created_at", key: "created_at", render: formatDate },
    {
      title: "操作", key: "action",
      render: (_: unknown, record: User) => (
        record.id !== currentUser?.id ? (
          <Button size="small" onClick={() => handleToggle(record.id)}>
            {record.is_active ? "禁用" : "启用"}
          </Button>
        ) : <Tag>当前用户</Tag>
      ),
    },
  ];

  return (
    <div className="page-fade-in">
      <Title level={2} style={{ marginBottom: 24 }}>系统管理</Title>

      {stats && (
        <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
          <Col xs={12} lg={4}>
            <Card className="stat-card stat-card--blue">
              <span className="stat-icon"><UserOutlined /></span>
              <Statistic title="用户总数" value={stats.total_users} />
            </Card>
          </Col>
          <Col xs={12} lg={4}>
            <Card className="stat-card stat-card--green">
              <span className="stat-icon"><RobotOutlined /></span>
              <Statistic title="模型配置" value={stats.total_models} />
            </Card>
          </Col>
          <Col xs={12} lg={4}>
            <Card className="stat-card stat-card--purple">
              <span className="stat-icon"><DatabaseOutlined /></span>
              <Statistic title="数据集" value={stats.total_datasets} />
            </Card>
          </Col>
          <Col xs={12} lg={4}>
            <Card className="stat-card stat-card--orange">
              <span className="stat-icon"><ExperimentOutlined /></span>
              <Statistic title="评测总数" value={stats.total_evaluations} />
            </Card>
          </Col>
          <Col xs={12} lg={4}>
            <Card className="stat-card stat-card--cyan">
              <span className="stat-icon"><CheckCircleOutlined /></span>
              <Statistic title="已完成" value={stats.completed_evaluations} />
            </Card>
          </Col>
          <Col xs={12} lg={4}>
            <Card className="stat-card stat-card--red">
              <span className="stat-icon"><PercentageOutlined /></span>
              <Statistic
                title="完成率"
                value={stats.total_evaluations > 0 ? Math.round(stats.completed_evaluations / stats.total_evaluations * 100) : 0}
                suffix="%"
              />
            </Card>
          </Col>
        </Row>
      )}

      <Card title="用户管理">
        <Table dataSource={users} columns={columns} rowKey="id" />
      </Card>
    </div>
  );
}

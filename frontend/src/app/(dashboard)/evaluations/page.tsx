"use client";

import { useEffect, useState, useRef, useMemo, useCallback } from "react";
import {
  Table, Button, Card, Typography, Tag, Space, Progress, Popconfirm, message,
  Input, Select, Row, Col, Dropdown,
} from "antd";
import {
  PlusOutlined, EyeOutlined, StopOutlined, BarChartOutlined,
  ThunderboltOutlined, SearchOutlined, DeleteOutlined, ReloadOutlined,
  DownOutlined, CheckSquareOutlined,
} from "@ant-design/icons";
import { evaluationsApi } from "@/lib/api";
import type { EvaluationTask } from "@/types";
import { formatDate, getStatusColor } from "@/lib/utils";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useDataRefresh } from "@/lib/useDataRefresh";

const { Title, Text } = Typography;

const STATUS_OPTIONS = [
  { value: "", label: "全部状态" },
  { value: "pending", label: "等待中" },
  { value: "running", label: "运行中" },
  { value: "completed", label: "已完成" },
  { value: "failed", label: "失败" },
  { value: "cancelled", label: "已取消" },
];

export default function EvaluationsPage() {
  const [tasks, setTasks] = useState<EvaluationTask[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterStatus, setFilterStatus] = useState("");
  const [searchText, setSearchText] = useState("");
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([]);
  const [batchLoading, setBatchLoading] = useState(false);
  const router = useRouter();
  const tasksRef = useRef(tasks);
  tasksRef.current = tasks;

  const loadTasks = useCallback(async () => {
    setLoading(true);
    try {
      setTasks(await evaluationsApi.list());
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadTasks();
  }, [loadTasks]);

  useDataRefresh(["evaluations"], loadTasks);

  // Polling
  useEffect(() => {
    const interval = setInterval(() => {
      if (tasksRef.current.some((t) => t.status === "running" || t.status === "pending")) {
        evaluationsApi.listFresh().then(setTasks).catch(() => {});
      }
    }, 3000);
    return () => clearInterval(interval);
  }, []);

  const handleCancel = useCallback(async (id: number) => {
    try {
      await evaluationsApi.cancel(id);
      message.success("已取消评测");
      loadTasks();
    } catch {
      message.error("取消失败");
    }
  }, [loadTasks]);

  const handleDelete = useCallback(async (id: number) => {
    try {
      await evaluationsApi.deleteTask(id);
      message.success("已删除评测任务");
      loadTasks();
    } catch {
      message.error("删除失败");
    }
  }, [loadTasks]);

  // Batch operations
  const handleBatchDelete = useCallback(async () => {
    if (!selectedRowKeys.length) return;
    setBatchLoading(true);
    try {
      const res = await evaluationsApi.batchDelete(selectedRowKeys as number[]);
      message.success(`已删除 ${res.deleted} 个任务`);
      setSelectedRowKeys([]);
      loadTasks();
    } catch {
      message.error("批量删除失败");
    } finally {
      setBatchLoading(false);
    }
  }, [selectedRowKeys, loadTasks]);

  const handleBatchCancel = useCallback(async () => {
    if (!selectedRowKeys.length) return;
    setBatchLoading(true);
    try {
      const res = await evaluationsApi.batchCancel(selectedRowKeys as number[]);
      message.success(`已取消 ${res.cancelled} 个任务`);
      setSelectedRowKeys([]);
      loadTasks();
    } catch {
      message.error("批量取消失败");
    } finally {
      setBatchLoading(false);
    }
  }, [selectedRowKeys, loadTasks]);

  const handleBatchRetry = useCallback(async () => {
    if (!selectedRowKeys.length) return;
    setBatchLoading(true);
    try {
      const res = await evaluationsApi.batchRetry(selectedRowKeys as number[]);
      message.success(`已重试 ${res.retried} 个任务`);
      setSelectedRowKeys([]);
      loadTasks();
    } catch {
      message.error("批量重试失败");
    } finally {
      setBatchLoading(false);
    }
  }, [selectedRowKeys, loadTasks]);

  const filteredTasks = useMemo(() => {
    let result = tasks;
    if (filterStatus) {
      result = result.filter((t) => t.status === filterStatus);
    }
    if (searchText.trim()) {
      const kw = searchText.trim().toLowerCase();
      result = result.filter((t) => t.name.toLowerCase().includes(kw) || t.description?.toLowerCase().includes(kw));
    }
    return result;
  }, [tasks, filterStatus, searchText]);

  // Compute what batch actions are relevant for selected rows
  const selectedTasks = useMemo(() =>
    tasks.filter((t) => selectedRowKeys.includes(t.id)),
    [tasks, selectedRowKeys],
  );
  const hasCancellable = selectedTasks.some((t) => t.status === "running" || t.status === "pending");
  const hasRetryable = selectedTasks.some((t) => t.status === "failed" || t.status === "cancelled");

  const batchMenuItems = useMemo(() => [
    {
      key: "cancel",
      label: "批量取消",
      icon: <StopOutlined />,
      disabled: !hasCancellable,
      danger: false,
    },
    {
      key: "retry",
      label: "批量重试",
      icon: <ReloadOutlined />,
      disabled: !hasRetryable,
    },
    { type: "divider" as const, key: "d1" },
    {
      key: "delete",
      label: "批量删除",
      icon: <DeleteOutlined />,
      danger: true,
    },
  ], [hasCancellable, hasRetryable]);

  const handleBatchMenuClick = useCallback(({ key }: { key: string }) => {
    if (key === "delete") {
      // Will be handled by Popconfirm wrapping the dropdown trigger
      // So we use a separate flow
    } else if (key === "cancel") {
      handleBatchCancel();
    } else if (key === "retry") {
      handleBatchRetry();
    }
  }, [handleBatchCancel, handleBatchRetry]);

  const columns = useMemo(() => [
    {
      title: "任务名称", dataIndex: "name", key: "name",
      render: (name: string, record: EvaluationTask) => (
        <Space>
          <Link href={`/evaluations/${record.id}`}><strong>{name}</strong></Link>
          {record.evaluator_config?.domain_eval && <Tag color="purple" style={{ fontSize: 11 }}>领域评测</Tag>}
        </Space>
      ),
    },
    {
      title: "状态", dataIndex: "status", key: "status",
      render: (s: string) => <Tag color={getStatusColor(s)}>{s}</Tag>,
    },
    {
      title: "进度", key: "progress",
      render: (_: unknown, record: EvaluationTask) => (
        <div className="progress-cell">
          <Progress
            percent={record.progress}
            size="small"
            status={record.status === "failed" ? "exception" : record.status === "completed" ? "success" : record.status === "running" ? "active" : undefined}
          />
          {record.total_samples > 0 && (
            <span className="progress-text">{record.processed_samples}/{record.total_samples}</span>
          )}
        </div>
      ),
    },
    {
      title: "模型数", key: "models",
      render: (_: unknown, record: EvaluationTask) => <Tag>{record.model_ids.length} 个</Tag>,
    },
    { title: "创建时间", dataIndex: "created_at", key: "created_at", render: formatDate },
    { title: "完成时间", dataIndex: "completed_at", key: "completed_at", render: formatDate },
    {
      title: "操作", key: "action",
      render: (_: unknown, record: EvaluationTask) => (
        <Space>
          <Button size="small" icon={<EyeOutlined />} onClick={() => router.push(`/evaluations/${record.id}`)}>
            详情
          </Button>
          {record.status === "completed" && (
            <Button size="small" icon={<BarChartOutlined />} type="primary" ghost onClick={() => router.push(`/results/${record.id}`)}>
              结果
            </Button>
          )}
          {record.status === "completed" && record.evaluator_config?.domain_eval && record.evaluator_config?.eval_mode === "evaluate_optimize" && (
            <Button size="small" icon={<ThunderboltOutlined />} onClick={() => router.push(`/evaluations/${record.id}/optimize`)}>
              优化
            </Button>
          )}
          {(record.status === "running" || record.status === "pending") && (
            <Popconfirm title="确认取消?" onConfirm={() => handleCancel(record.id)}>
              <Button size="small" danger icon={<StopOutlined />}>取消</Button>
            </Popconfirm>
          )}
          {(record.status === "failed" || record.status === "cancelled") && (
            <Button size="small" icon={<ReloadOutlined />} onClick={() => evaluationsApi.retry(record.id).then(() => { message.success("已重试"); loadTasks(); }).catch(() => message.error("重试失败"))}>
              重试
            </Button>
          )}
          <Popconfirm title="确认永久删除此任务及所有结果?" onConfirm={() => handleDelete(record.id)} okType="danger">
            <Button size="small" danger icon={<DeleteOutlined />}>删除</Button>
          </Popconfirm>
        </Space>
      ),
    },
  ], [router, handleCancel, handleDelete, loadTasks]);

  const rowSelection = {
    selectedRowKeys,
    onChange: (keys: React.Key[]) => setSelectedRowKeys(keys),
  };

  return (
    <div className="page-fade-in">
      <div className="page-header">
        <Title level={2}>评测任务</Title>
        <Link href="/evaluations/new">
          <Button type="primary" icon={<PlusOutlined />}>创建评测</Button>
        </Link>
      </div>
      <Card>
        <Row gutter={12} style={{ marginBottom: 16 }} align="middle">
          <Col flex="200px">
            <Select
              style={{ width: "100%" }}
              value={filterStatus}
              onChange={setFilterStatus}
              options={STATUS_OPTIONS}
            />
          </Col>
          <Col flex="auto">
            <Input
              placeholder="搜索任务名称..."
              prefix={<SearchOutlined />}
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              allowClear
            />
          </Col>
        </Row>

        {/* Batch action bar */}
        {selectedRowKeys.length > 0 && (
          <div style={{
            marginBottom: 16,
            padding: "8px 16px",
            background: "var(--color-bg-elevated, #f0f5ff)",
            borderRadius: 8,
            display: "flex",
            alignItems: "center",
            gap: 12,
          }}>
            <CheckSquareOutlined style={{ color: "#4f6ef7" }} />
            <Text strong>已选择 {selectedRowKeys.length} 项</Text>
            <Button size="small" onClick={() => setSelectedRowKeys([])}>取消选择</Button>
            <div style={{ flex: 1 }} />
            {hasCancellable && (
              <Popconfirm title={`确认取消 ${selectedRowKeys.length} 个任务？`} onConfirm={handleBatchCancel}>
                <Button size="small" icon={<StopOutlined />} loading={batchLoading}>批量取消</Button>
              </Popconfirm>
            )}
            {hasRetryable && (
              <Button size="small" icon={<ReloadOutlined />} loading={batchLoading} onClick={handleBatchRetry}>
                批量重试
              </Button>
            )}
            <Popconfirm
              title={`确认永久删除选中的 ${selectedRowKeys.length} 个任务及所有结果？`}
              onConfirm={handleBatchDelete}
              okType="danger"
            >
              <Button size="small" danger icon={<DeleteOutlined />} loading={batchLoading}>批量删除</Button>
            </Popconfirm>
          </div>
        )}

        <Table
          dataSource={filteredTasks}
          columns={columns}
          rowKey="id"
          loading={loading}
          rowSelection={rowSelection}
        />
      </Card>
    </div>
  );
}

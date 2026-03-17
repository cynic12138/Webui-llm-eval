"use client";

import { useEffect, useState, useCallback } from "react";
import {
  Card, Button, Modal, Form, Input, Table, Tabs, Tag, Space,
  message, Typography, List, Empty, Popconfirm, Select, Badge,
} from "antd";
import {
  PlusOutlined, TeamOutlined, UserAddOutlined, DeleteOutlined,
  ShareAltOutlined, CrownOutlined, UserOutlined,
} from "@ant-design/icons";
import { teamsApi } from "@/lib/api";
import type { Organization, OrgMember, ResourceShare } from "@/types";
import type { ColumnsType } from "antd/es/table";
import dayjs from "dayjs";

const { Title, Text } = Typography;

const roleColors: Record<string, string> = {
  admin: "red",
  member: "blue",
  viewer: "green",
};

const roleLabels: Record<string, string> = {
  admin: "管理员",
  member: "成员",
  viewer: "查看者",
};

const resourceTypeLabels: Record<string, string> = {
  evaluation: "评测任务",
  dataset: "数据集",
  model: "模型",
};

export default function TeamsPage() {
  const [orgs, setOrgs] = useState<Organization[]>([]);
  const [loading, setLoading] = useState(false);
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [addMemberModalOpen, setAddMemberModalOpen] = useState(false);
  const [shareModalOpen, setShareModalOpen] = useState(false);
  const [selectedOrg, setSelectedOrg] = useState<(Organization & { members?: OrgMember[] }) | null>(null);
  const [sharedResources, setSharedResources] = useState<ResourceShare[]>([]);
  const [form] = Form.useForm();
  const [memberForm] = Form.useForm();
  const [shareForm] = Form.useForm();

  const fetchOrgs = useCallback(async () => {
    setLoading(true);
    try {
      const data = await teamsApi.list();
      setOrgs(data);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchOrgs(); }, [fetchOrgs]);

  const handleCreateOrg = async (values: { name: string; description?: string }) => {
    try {
      await teamsApi.create(values);
      message.success("组织创建成功");
      setCreateModalOpen(false);
      form.resetFields();
      fetchOrgs();
    } catch {
      message.error("创建失败");
    }
  };

  const handleSelectOrg = async (org: Organization) => {
    try {
      const detail = await teamsApi.get(org.id);
      setSelectedOrg(detail);
      const shared = await teamsApi.sharedResources(org.id);
      setSharedResources(shared);
    } catch {
      message.error("加载组织详情失败");
    }
  };

  const handleAddMember = async (values: { username: string; role: string }) => {
    if (!selectedOrg) return;
    try {
      await teamsApi.addMember(selectedOrg.id, values.username, values.role);
      message.success("成员添加成功");
      setAddMemberModalOpen(false);
      memberForm.resetFields();
      handleSelectOrg(selectedOrg);
    } catch {
      message.error("添加成员失败");
    }
  };

  const handleRemoveMember = async (userId: number) => {
    if (!selectedOrg) return;
    try {
      await teamsApi.removeMember(selectedOrg.id, userId);
      message.success("已移除成员");
      handleSelectOrg(selectedOrg);
    } catch {
      message.error("移除失败");
    }
  };

  const handleShare = async (values: { resource_type: string; resource_id: number }) => {
    if (!selectedOrg) return;
    try {
      await teamsApi.share(selectedOrg.id, values);
      message.success("资源共享成功");
      setShareModalOpen(false);
      shareForm.resetFields();
      const shared = await teamsApi.sharedResources(selectedOrg.id);
      setSharedResources(shared);
    } catch {
      message.error("共享失败");
    }
  };

  const handleUnshare = async (shareId: number) => {
    if (!selectedOrg) return;
    try {
      await teamsApi.unshare(selectedOrg.id, shareId);
      message.success("已取消共享");
      const shared = await teamsApi.sharedResources(selectedOrg.id);
      setSharedResources(shared);
    } catch {
      message.error("取消失败");
    }
  };

  const memberColumns: ColumnsType<OrgMember> = [
    {
      title: "用户名",
      dataIndex: "username",
      key: "username",
      render: (name: string) => (
        <Space>
          <UserOutlined />
          <Text strong>{name}</Text>
        </Space>
      ),
    },
    {
      title: "角色",
      dataIndex: "role",
      key: "role",
      render: (role: string) => (
        <Tag color={roleColors[role] || "default"}>
          {role === "admin" && <CrownOutlined style={{ marginRight: 4 }} />}
          {roleLabels[role] || role}
        </Tag>
      ),
    },
    {
      title: "加入时间",
      dataIndex: "joined_at",
      key: "joined_at",
      render: (val: string) => dayjs(val).format("YYYY-MM-DD HH:mm"),
    },
    {
      title: "操作",
      key: "actions",
      render: (_: unknown, record: OrgMember) => (
        <Popconfirm title="确定移除该成员？" onConfirm={() => handleRemoveMember(record.user_id)}>
          <Button type="text" size="small" danger icon={<DeleteOutlined />} />
        </Popconfirm>
      ),
    },
  ];

  const shareColumns: ColumnsType<ResourceShare> = [
    {
      title: "资源类型",
      dataIndex: "resource_type",
      key: "resource_type",
      render: (type: string) => (
        <Tag color="blue">{resourceTypeLabels[type] || type}</Tag>
      ),
    },
    {
      title: "资源 ID",
      dataIndex: "resource_id",
      key: "resource_id",
    },
    {
      title: "共享时间",
      dataIndex: "created_at",
      key: "created_at",
      render: (val: string) => dayjs(val).format("YYYY-MM-DD HH:mm"),
    },
    {
      title: "操作",
      key: "actions",
      render: (_: unknown, record: ResourceShare) => (
        <Popconfirm title="取消共享？" onConfirm={() => handleUnshare(record.id)}>
          <Button type="text" size="small" danger icon={<DeleteOutlined />} />
        </Popconfirm>
      ),
    },
  ];

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24 }}>
        <Title level={3} style={{ margin: 0 }}>
          <TeamOutlined style={{ marginRight: 8 }} />
          团队协作
        </Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateModalOpen(true)}>
          创建组织
        </Button>
      </div>

      <div style={{ display: "flex", gap: 24 }}>
        {/* Org list */}
        <div style={{ width: 320, flexShrink: 0 }}>
          {orgs.length === 0 && !loading ? (
            <Card>
              <Empty description="暂无组织，点击「创建组织」开始协作" />
            </Card>
          ) : (
            <List
              loading={loading}
              dataSource={orgs}
              renderItem={(org) => (
                <Card
                  key={org.id}
                  size="small"
                  hoverable
                  style={{
                    marginBottom: 12,
                    borderColor: selectedOrg?.id === org.id ? "#4f6ef7" : undefined,
                  }}
                  onClick={() => handleSelectOrg(org)}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <div>
                      <Text strong style={{ fontSize: 15 }}>{org.name}</Text>
                      {org.description && (
                        <div><Text type="secondary" style={{ fontSize: 12 }}>{org.description}</Text></div>
                      )}
                    </div>
                    <Badge count={org.member_count} style={{ backgroundColor: "#4f6ef7" }} />
                  </div>
                </Card>
              )}
            />
          )}
        </div>

        {/* Org detail */}
        <div style={{ flex: 1 }}>
          {selectedOrg ? (
            <Card
              title={
                <Space>
                  <TeamOutlined />
                  <span>{selectedOrg.name}</span>
                  <Tag>{selectedOrg.member_count} 成员</Tag>
                </Space>
              }
            >
              <Tabs
                items={[
                  {
                    key: "members",
                    label: "成员管理",
                    children: (
                      <div>
                        <div style={{ marginBottom: 16, textAlign: "right" }}>
                          <Button
                            icon={<UserAddOutlined />}
                            onClick={() => setAddMemberModalOpen(true)}
                          >
                            添加成员
                          </Button>
                        </div>
                        <Table
                          columns={memberColumns}
                          dataSource={selectedOrg.members || []}
                          rowKey="id"
                          pagination={false}
                          size="small"
                        />
                      </div>
                    ),
                  },
                  {
                    key: "shared",
                    label: "共享资源",
                    children: (
                      <div>
                        <div style={{ marginBottom: 16, textAlign: "right" }}>
                          <Button
                            icon={<ShareAltOutlined />}
                            onClick={() => setShareModalOpen(true)}
                          >
                            共享资源
                          </Button>
                        </div>
                        <Table
                          columns={shareColumns}
                          dataSource={sharedResources}
                          rowKey="id"
                          pagination={false}
                          size="small"
                          locale={{ emptyText: "暂无共享资源" }}
                        />
                      </div>
                    ),
                  },
                ]}
              />
            </Card>
          ) : (
            <Card>
              <Empty description="请在左侧选择一个组织查看详情" />
            </Card>
          )}
        </div>
      </div>

      {/* Create Org Modal */}
      <Modal
        title="创建组织"
        open={createModalOpen}
        onCancel={() => { setCreateModalOpen(false); form.resetFields(); }}
        onOk={() => form.submit()}
        okText="创建"
        cancelText="取消"
      >
        <Form form={form} layout="vertical" onFinish={handleCreateOrg}>
          <Form.Item name="name" label="组织名称" rules={[{ required: true, message: "请输入组织名称" }]}>
            <Input placeholder="例如：AI 研究组、评测团队" maxLength={50} />
          </Form.Item>
          <Form.Item name="description" label="描述（可选）">
            <Input.TextArea placeholder="组织的简要描述" maxLength={200} rows={3} />
          </Form.Item>
        </Form>
      </Modal>

      {/* Add Member Modal */}
      <Modal
        title="添加成员"
        open={addMemberModalOpen}
        onCancel={() => { setAddMemberModalOpen(false); memberForm.resetFields(); }}
        onOk={() => memberForm.submit()}
        okText="添加"
        cancelText="取消"
      >
        <Form form={memberForm} layout="vertical" onFinish={handleAddMember} initialValues={{ role: "member" }}>
          <Form.Item name="username" label="用户名" rules={[{ required: true, message: "请输入用户名" }]}>
            <Input placeholder="输入要添加的用户名" />
          </Form.Item>
          <Form.Item name="role" label="角色">
            <Select
              options={[
                { value: "admin", label: "管理员" },
                { value: "member", label: "成员" },
                { value: "viewer", label: "查看者" },
              ]}
            />
          </Form.Item>
        </Form>
      </Modal>

      {/* Share Resource Modal */}
      <Modal
        title="共享资源"
        open={shareModalOpen}
        onCancel={() => { setShareModalOpen(false); shareForm.resetFields(); }}
        onOk={() => shareForm.submit()}
        okText="共享"
        cancelText="取消"
      >
        <Form form={shareForm} layout="vertical" onFinish={handleShare}>
          <Form.Item name="resource_type" label="资源类型" rules={[{ required: true, message: "请选择资源类型" }]}>
            <Select
              placeholder="选择资源类型"
              options={[
                { value: "evaluation", label: "评测任务" },
                { value: "dataset", label: "数据集" },
                { value: "model", label: "模型" },
              ]}
            />
          </Form.Item>
          <Form.Item name="resource_id" label="资源 ID" rules={[{ required: true, message: "请输入资源ID" }]}>
            <Input type="number" placeholder="输入资源 ID" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}

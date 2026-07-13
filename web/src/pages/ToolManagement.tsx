// 工具管理页面：维护平台业务工具、凭据和审计约束。
import { useMemo, useState } from 'react';
import {
  Alert,
  Badge,
  Button,
  Card,
  Checkbox,
  Col,
  Descriptions,
  Form,
  Input,
  message,
  Modal,
  Popconfirm,
  Row,
  Select,
  Space,
  Statistic,
  Table,
  Tabs,
  Tag,
  Typography,
} from 'antd';
import {
  CheckCircleOutlined,
  DeleteOutlined,
  EditOutlined,
  EyeOutlined,
  KeyOutlined,
  PlusOutlined,
  ReloadOutlined,
  SafetyCertificateOutlined,
  ToolOutlined,
} from '@ant-design/icons';
import {
  type CredentialRecord,
  type CredentialType,
  type ToolDefinition,
  type ToolIntegrationType,
  type ToolManagedBy,
  type ToolStatus,
} from '../types/domain';
import { usePlatformData } from '../services/platformData';
import { api, mapTool } from '../services/api';

const { Text, Title, Paragraph } = Typography;

const managedByMap: Record<ToolManagedBy, { label: string; color: string }> = {
  platform: { label: '平台管理', color: 'green' },
};

const integrationMap: Record<ToolIntegrationType, { label: string; color: string }> = {
  platform_api: { label: '平台接口', color: 'green' },
  http_api: { label: 'HTTP 接口', color: 'orange' },
};

const riskMap: Record<string, { label: string; color: string }> = {
  low: { label: '低', color: 'green' },
  medium: { label: '中', color: 'gold' },
  high: { label: '高', color: 'red' },
};

const readWriteMap: Record<string, { label: string; color: string }> = {
  read: { label: '只读', color: 'blue' },
  write: { label: '写入', color: 'red' },
  read_only: { label: '只读', color: 'blue' },
  mixed: { label: '读写', color: 'orange' },
};

const statusMap: Record<ToolStatus, { label: string; badge: 'success' | 'processing' | 'warning' | 'default' | 'error' }> = {
  draft: { label: '草稿', badge: 'default' },
  testing: { label: '测试中', badge: 'processing' },
  published: { label: '已发布', badge: 'success' },
  disabled: { label: '已停用', badge: 'error' },
  deprecated: { label: '已废弃', badge: 'warning' },
};

const credentialTypeMap: Record<CredentialType, string> = {
  api_key: '接口密钥',
  oauth_token: 'OAuth 令牌',
  basic_auth: '基础认证',
  webhook_secret: 'Webhook 密钥',
};

const credentialOwnerOptions = [
  { label: '平台内部服务', value: 'Platform' },
  { label: '客服部', value: '客服部' },
  { label: '销售部', value: '销售部' },
  { label: '运营部', value: '运营部' },
  { label: '市场部', value: '市场部' },
  { label: '产品部', value: '产品部' },
  { label: '知识库服务', value: '知识库服务' },
];

const credentialOwnerMap = credentialOwnerOptions.reduce<Record<string, string>>((acc, option) => {
  acc[option.value] = option.label;
  return acc;
}, {});

const methodOptions = ['GET', 'POST', 'PATCH', 'PUT', 'DELETE'].map((method) => ({ label: method, value: method }));

const platformApiOptions = [
  { label: '知识检索 /api/v1/knowledge/retrieve', value: '/api/v1/knowledge/retrieve', method: 'POST' },
  { label: '审批创建 /api/v1/approvals', value: '/api/v1/approvals', method: 'POST' },
  { label: '员工目录查询 /api/v1/employees/search', value: '/api/v1/employees/search', method: 'GET' },
  { label: '文档草稿 /api/v1/documents/drafts', value: '/api/v1/documents/drafts', method: 'POST' },
  { label: '团队绩效 /api/v1/kpi/team', value: '/api/v1/kpi/team', method: 'GET' },
];

export default function ToolManagement() {
  const { tools, credentials, auditEvents, source, refreshTools, refreshCredentials } = usePlatformData();
  const [selectedTool, setSelectedTool] = useState<ToolDefinition | null>(null);
  const [editingTool, setEditingTool] = useState<ToolDefinition | null>(null);
  const [editingCredential, setEditingCredential] = useState<CredentialRecord | null>(null);
  const [detailOpen, setDetailOpen] = useState(false);
  const [toolOpen, setToolOpen] = useState(false);
  const [credentialOpen, setCredentialOpen] = useState(false);
  const [rotatingCredential, setRotatingCredential] = useState<CredentialRecord | null>(null);
  const [testOpen, setTestOpen] = useState(false);
  const [testTool, setTestTool] = useState<ToolDefinition | null>(null);
  const [categoryFilter, setCategoryFilter] = useState<string | undefined>();
  const [managedByFilter, setManagedByFilter] = useState<ToolManagedBy | undefined>();
  const [toolForm] = Form.useForm();
  const [credentialForm] = Form.useForm();
  const [rotationForm] = Form.useForm();
  const selectedIntegrationType = Form.useWatch('integrationType', toolForm) as ToolIntegrationType | undefined;

  const categories = [...new Set(tools.map((tool) => tool.category))];
  const credentialNameById = useMemo(() => {
    return credentials.reduce<Record<string, string>>((acc, credential) => {
      acc[credential.credentialId] = `${credential.name} / ${credential.maskedValue}`;
      return acc;
    }, {});
  }, [credentials]);

  const filteredTools = tools
    .filter((tool) => !categoryFilter || tool.category === categoryFilter)
    .filter((tool) => !managedByFilter || tool.managedBy === managedByFilter);

  const businessToolCount = tools.filter((tool) => tool.managedBy === 'platform').length;
  const highRiskCount = tools.filter((tool) => tool.riskLevel === 'high').length;
  const writeToolCount = tools.filter((tool) => tool.readWrite === 'write').length;
  const activeCredentialCount = credentials.filter((credential) => credential.status === 'active').length;
  const toolCallEvents = auditEvents.filter((event) => event.eventType === 'tool_call');
  const isPlatformApi = selectedIntegrationType === 'platform_api';
  const isHttpApi = selectedIntegrationType === 'http_api';

  const handleIntegrationTypeChange = (integrationType: ToolIntegrationType) => {
    if (integrationType === 'platform_api') {
      toolForm.setFieldsValue({
        managedBy: 'platform',
        credentialRef: 'cred-platform-internal',
        baseUrl: undefined,
        method: 'POST',
      });
      return;
    }

    toolForm.setFieldsValue({
      managedBy: 'platform',
      method: 'GET',
    });
  };

  const openCreateTool = () => {
    setEditingTool(null);
    toolForm.resetFields();
    toolForm.setFieldsValue({
      managedBy: 'platform',
      integrationType: 'http_api',
      readWrite: 'read',
      riskLevel: 'medium',
      requiresApproval: false,
      auditRequired: true,
      status: 'draft',
      method: 'GET',
      requestSchema: '{ }',
      responseSchema: '{ }',
      defaultConstraintsText: '',
      idempotencyPolicy: '',
    });
    setToolOpen(true);
  };

  const openEditTool = (tool: ToolDefinition) => {
    setEditingTool(tool);
    toolForm.setFieldsValue({
      ...tool,
      baseUrl: tool.endpointConfig.baseUrl,
      path: tool.endpointConfig.path,
      method: tool.endpointConfig.method,
      platformApiPath: tool.integrationType === 'platform_api' ? tool.endpointConfig.path : undefined,
      requestSchema: tool.schemaConfig.request,
      responseSchema: tool.schemaConfig.response,
      defaultConstraintsText: tool.defaultConstraints.join('\n'),
      idempotencyPolicy: tool.idempotencyPolicy,
    });
    setToolOpen(true);
  };

  const parseSchema = (value: string | undefined) => {
    try {
      return JSON.parse(value || '{}') as Record<string, unknown>;
    } catch {
      return {};
    }
  };

  const saveTool = () => {
    toolForm.validateFields().then(async (values) => {
      const integrationType = values.integrationType as ToolIntegrationType;
      const endpointConfig =
        integrationType === 'http_api'
          ? { baseUrl: values.baseUrl, path: values.path, method: values.method }
          : { path: values.platformApiPath, method: values.method };
      const defaultConstraints = String(values.defaultConstraintsText ?? '')
        .split('\n')
        .map((item) => item.trim())
        .filter(Boolean);
      if (!editingTool) {
        const created = await api.post<{ id: string }>('/tools/business', {
            name: values.displayName,
            category: values.category,
            access_shape: integrationType === 'platform_api' ? 'platform_adapter' : integrationType,
            endpoint_url: integrationType === 'http_api'
              ? `${values.baseUrl ?? ''}${values.path ?? ''}`
              : values.platformApiPath,
            method: values.method,
            request_schema: parseSchema(values.requestSchema),
            response_schema: parseSchema(values.responseSchema),
            owner: values.category,
            credential_id: integrationType === 'http_api' || integrationType === 'platform_api' ? values.credentialRef : undefined,
            risk_level: values.riskLevel,
            audit_required: values.auditRequired ?? true,
            approval_required: values.requiresApproval ?? false,
            default_constraints: defaultConstraints,
            idempotency_policy: String(values.idempotencyPolicy ?? '').trim(),
          });
        if (values.status === 'published') {
          await api.post(`/tools/${created.id}/publish`);
        }
        await refreshTools();
        setToolOpen(false);
        setEditingTool(null);
        toolForm.resetFields();
        return;
      }

      await api.patch(`/tools/${editingTool.toolId}`, {
          name: values.displayName,
          category: values.category,
          access_shape: integrationType === 'platform_api' ? 'platform_adapter' : integrationType,
          endpoint_url: endpointConfig.path,
          method: values.method,
          request_schema: parseSchema(values.requestSchema),
          response_schema: parseSchema(values.responseSchema),
          owner: values.category,
          credential_id: integrationType === 'http_api' || integrationType === 'platform_api' ? values.credentialRef : undefined,
          risk_level: values.riskLevel,
          audit_required: values.auditRequired ?? true,
          approval_required: values.requiresApproval ?? false,
          default_constraints: defaultConstraints,
          idempotency_policy: String(values.idempotencyPolicy ?? '').trim(),
          lifecycle_status: values.status === 'published' ? 'published' : 'draft',
        });
      await refreshTools();
      setToolOpen(false);
      setEditingTool(null);
      toolForm.resetFields();
    });
  };

  const testConnection = async (tool: ToolDefinition) => {
    const tested = await api.post<Parameters<typeof mapTool>[0]>(`/tools/${tool.toolId}/test`);
    setTestTool(mapTool(tested));
    // 测试是只读操作，无需全量刷新数据
    setTestOpen(true);
  };

  const toggleToolStatus = async (toolId: string) => {
    const tool = tools.find((item) => item.toolId === toolId);
    if (!tool) return;
    if (tool.status === 'published') {
      await api.patch(`/tools/${toolId}`, { lifecycle_status: 'archived' });
    } else {
      await api.post(`/tools/${toolId}/publish`);
    }
    await refreshTools();
  };

  const handleDeleteTool = async (toolId: string) => {
    await api.delete(`/tools/${toolId}`);
    message.success('工具已删除');
    await refreshTools();
  };

  const openCredential = (credential?: CredentialRecord) => {
    setEditingCredential(credential ?? null);
    credentialForm.setFieldsValue(credential ? { ...credential, secretValue: undefined } : {
      type: 'api_key',
      status: 'active',
      owner: 'Platform',
      secretValue: undefined,
    });
    setCredentialOpen(true);
  };

  const credentialOwnerType = (owner: string) => owner === 'Platform' ? 'platform' : owner.endsWith('部') ? 'department' : 'integration';

  const saveCredential = () => {
    credentialForm.validateFields().then(async (values) => {
      const payload = {
        name: values.name,
        owner_type: credentialOwnerType(values.owner),
        owner_id: values.owner,
        owner_name: credentialOwnerMap[values.owner] ?? values.owner,
        description: values.description,
        ...(values.secretValue ? { secret_value: values.secretValue } : {}),
      };
      if (editingCredential) {
        await api.patch(`/credentials/${editingCredential.credentialId}`, payload);
      } else {
        await api.post('/credentials', payload);
      }
      await refreshCredentials();
      setCredentialOpen(false);
      setEditingCredential(null);
      credentialForm.resetFields();
    });
  };

  const rotateCredential = async (credentialId: string) => {
    const credential = credentials.find((item) => item.credentialId === credentialId);
    if (!credential) return;
    setRotatingCredential(credential);
    rotationForm.resetFields();
  };

  const submitCredentialRotation = () => {
    if (!rotatingCredential) return;
    rotationForm.validateFields().then(async (values) => {
      await api.patch(`/credentials/${rotatingCredential.credentialId}`, {
        secret_value: values.secretValue,
      });
      await refreshCredentials();
      setRotatingCredential(null);
      rotationForm.resetFields();
    });
  };

  const handleDeleteCredential = async (credentialId: string, credentialName: string) => {
    try {
      await api.delete(`/credentials/${credentialId}`);
      message.success(`凭证「${credentialName}」已删除`);
      await refreshCredentials();
    } catch (err: unknown) {
      const detail = (err as Error)?.message;
      if (detail) {
        Modal.error({
          title: '无法删除凭证',
          content: detail,
          width: 520,
        });
      } else {
        message.error('删除凭证失败');
      }
    }
  };

  const toolColumns = [
    {
      title: '工具',
      dataIndex: 'displayName',
      key: 'displayName',
      width: 190,
      render: (displayName: string, row: ToolDefinition) => (
        <Space orientation="vertical" size={0}>
          <Text strong>{displayName}</Text>
          <Text type="secondary" style={{ fontSize: 12 }}>{row.name} / v{row.version}</Text>
        </Space>
      ),
    },
    {
      title: '管理方',
      dataIndex: 'managedBy',
      key: 'managedBy',
      width: 110,
      render: (managedBy: ToolManagedBy) => <Tag color={managedByMap[managedBy].color}>{managedByMap[managedBy].label}</Tag>,
    },
    {
      title: '接入形态',
      dataIndex: 'integrationType',
      key: 'integrationType',
      width: 125,
      render: (integrationType: ToolIntegrationType) => <Tag color={integrationMap[integrationType].color}>{integrationMap[integrationType].label}</Tag>,
    },
    { title: '分类', dataIndex: 'category', key: 'category', width: 90 },
    {
      title: '读写/风险',
      key: 'risk',
      width: 140,
      render: (_: unknown, row: ToolDefinition) => (
        <Space size={4}>
          <Tag color={readWriteMap[row.readWrite]?.color ?? 'default'}>{readWriteMap[row.readWrite]?.label ?? row.readWrite}</Tag>
          <Tag color={riskMap[row.riskLevel]?.color ?? 'default'}>{riskMap[row.riskLevel]?.label ?? row.riskLevel}风险</Tag>
        </Space>
      ),
    },
    {
      title: '控制',
      key: 'control',
      width: 130,
      render: (_: unknown, row: ToolDefinition) => (
        <Space size={4} wrap>
          {row.requiresApproval && <Tag color="orange">审批</Tag>}
          {row.auditRequired && <Tag color="blue">审计</Tag>}
          {row.idempotencyPolicy && <Tag color="green">幂等</Tag>}
        </Space>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: ToolStatus) => {
        const meta = statusMap[status];
        return <Badge status={meta.badge} text={meta.label} />;
      },
    },
    {
      title: '测试',
      dataIndex: 'lastTestStatus',
      key: 'lastTestStatus',
      width: 90,
      render: (status: ToolDefinition['lastTestStatus']) => {
        const map = {
          passed: <Tag color="green">通过</Tag>,
          failed: <Tag color="red">失败</Tag>,
          not_tested: <Tag>未测试</Tag>,
        };
        return map[status];
      },
    },
    { title: '绑定模板', dataIndex: 'boundTemplateCount', key: 'boundTemplateCount', width: 90 },
    {
      title: '操作',
      key: 'action',
      width: 250,
      fixed: 'right' as const,
      render: (_: unknown, row: ToolDefinition) => (
        <Space size="small">
          <Button size="small" icon={<EyeOutlined />} onClick={() => { setSelectedTool(row); setDetailOpen(true); }}>详情</Button>
          <Button size="small" icon={<EditOutlined />} onClick={() => openEditTool(row)}>编辑</Button>
          <Button size="small" icon={<CheckCircleOutlined />} onClick={() => testConnection(row)}>测试</Button>
          <Button size="small" onClick={() => toggleToolStatus(row.toolId)}>{row.status === 'disabled' ? '启用' : '停用'}</Button>
          <Popconfirm
            title="确认删除"
            description={`确定要删除工具「${row.displayName}」吗？此操作不可撤销。`}
            onConfirm={() => handleDeleteTool(row.toolId)}
            okText="删除"
            cancelText="取消"
            okButtonProps={{ danger: true }}
          >
            <Button size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  const credentialColumns = [
    { title: '凭证', dataIndex: 'name', key: 'name', width: 190, render: (name: string, row: CredentialRecord) => <Space orientation="vertical" size={0}><Text strong>{name}</Text><Text code>{row.credentialId}</Text></Space> },
    { title: '类型', dataIndex: 'type', key: 'type', width: 120, render: (type: CredentialType) => <Tag>{credentialTypeMap[type]}</Tag> },
    { title: '归属方', dataIndex: 'owner', key: 'owner', width: 140, render: (owner: string) => credentialOwnerMap[owner] ?? owner },
    { title: '脱敏值', dataIndex: 'maskedValue', key: 'maskedValue', render: (value: string) => <Text code>{value}</Text> },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: CredentialRecord['status']) => {
        const map = {
          active: <Badge status="success" text="可用" />,
          rotated: <Badge status="processing" text="已轮换" />,
          disabled: <Badge status="default" text="禁用" />,
        };
        return map[status];
      },
    },
    { title: '更新时间', dataIndex: 'updatedAt', key: 'updatedAt', width: 150 },
    {
      title: '操作',
      key: 'action',
      width: 180,
      render: (_: unknown, row: CredentialRecord) => (
        <Space size="small">
          <Button size="small" icon={<EditOutlined />} onClick={() => openCredential(row)}>编辑</Button>
          <Button size="small" icon={<ReloadOutlined />} onClick={() => rotateCredential(row.credentialId)}>轮换</Button>
          <Popconfirm
            title="确认删除"
            description={`确定要删除凭证「${row.name}」吗？如果凭证已被工具引用则无法直接删除。`}
            onConfirm={() => handleDeleteCredential(row.credentialId, row.name)}
            okText="删除"
            cancelText="取消"
            okButtonProps={{ danger: true }}
          >
            <Button size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  const toolCallColumns = [
    { title: '时间', dataIndex: 'occurredAt', key: 'occurredAt', width: 150 },
    { title: '员工', dataIndex: 'employeeId', key: 'employeeId', width: 110 },
    { title: '工具', dataIndex: ['payload', 'toolId'], key: 'toolId', width: 120, render: (toolId: string) => <Text code>{toolId}</Text> },
    { title: '状态', dataIndex: ['payload', 'status'], key: 'status', width: 90, render: (status: string) => <Tag color={status === 'success' ? 'green' : 'red'}>{status}</Tag> },
    { title: '读写', dataIndex: ['payload', 'readWrite'], key: 'readWrite', width: 90 },
    { title: '风险', dataIndex: ['payload', 'riskLevel'], key: 'riskLevel', width: 90 },
    { title: '延迟', dataIndex: ['payload', 'latencyMs'], key: 'latencyMs', width: 90, render: (value: number) => `${value} ms` },
    { title: '审批编号', dataIndex: ['payload', 'approvalId'], key: 'approvalId', width: 190, render: (value?: string) => value ? <Text code>{value}</Text> : <Text type="secondary">-</Text> },
    { title: '外部返回', dataIndex: ['payload', 'externalResponseId'], key: 'externalResponseId', render: (value?: string) => value ? <Text code>{value}</Text> : <Text type="secondary">-</Text> },
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 16, marginBottom: 16 }}>
        <div>
          <Title level={4} style={{ marginBottom: 4 }}>工具管理</Title>
          <Text type="secondary">维护 Hermes 内置工具与平台业务工具。当前数据源：{source === 'backend' ? '后端接口' : '后端不可用'}。</Text>
        </div>
        <Space>
          <Button icon={<KeyOutlined />} onClick={() => openCredential()}>新增凭证</Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={openCreateTool}>新增工具</Button>
        </Space>
      </div>

      <Alert
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
        title="业务工具默认通过平台工具网关调用。Hermes 配置目录只持有工具数据结构、平台端点和员工服务令牌，不保存业务系统凭证。"
      />

      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={24} sm={12} lg={6}><Card size="small"><Statistic title="工具总数" value={tools.length} prefix={<ToolOutlined />} /></Card></Col>
        <Col xs={24} sm={12} lg={6}><Card size="small"><Statistic title="业务工具" value={businessToolCount} prefix={<SafetyCertificateOutlined />} /></Card></Col>
        <Col xs={24} sm={12} lg={6}><Card size="small"><Statistic title="写工具 / 高风险" value={`${writeToolCount} / ${highRiskCount}`} /></Card></Col>
        <Col xs={24} sm={12} lg={6}><Card size="small"><Statistic title="可用凭证" value={activeCredentialCount} prefix={<KeyOutlined />} /></Card></Col>
      </Row>

      <Tabs
        items={[
          {
            key: 'tools',
            label: '工具列表',
            children: (
              <>
                <Row gutter={16} style={{ marginBottom: 16 }}>
                  <Col xs={24} sm={6}>
                    <Select
                      placeholder="分类筛选"
                      allowClear
                      value={categoryFilter}
                      onChange={setCategoryFilter}
                      style={{ width: '100%' }}
                      options={categories.map((category) => ({ label: category, value: category }))}
                    />
                  </Col>
                  <Col xs={24} sm={6}>
                    <Select
                      placeholder="管理方筛选"
                      allowClear
                      value={managedByFilter}
                      onChange={setManagedByFilter}
                      style={{ width: '100%' }}
                      options={Object.entries(managedByMap).map(([value, meta]) => ({ label: meta.label, value }))}
                    />
                  </Col>
                </Row>
                <Table dataSource={filteredTools} columns={toolColumns} rowKey="toolId" size="middle" scroll={{ x: 1350 }} pagination={{ pageSize: 8 }} />
              </>
            ),
          },
          {
            key: 'credentials',
            label: '凭证管理',
            children: <Table dataSource={credentials} columns={credentialColumns} rowKey="credentialId" size="middle" pagination={false} />,
          },
          {
            key: 'audit',
            label: '调用审计',
            children: <Table dataSource={toolCallEvents} columns={toolCallColumns} rowKey="eventId" size="middle" scroll={{ x: 1050 }} pagination={false} />,
          },
        ]}
      />

      <Modal
        title={editingTool ? '编辑工具' : '新增工具'}
        open={toolOpen}
        onCancel={() => { setToolOpen(false); setEditingTool(null); toolForm.resetFields(); }}
        onOk={saveTool}
        width={860}
        forceRender
        destroyOnHidden
      >
        <Form form={toolForm} layout="vertical">
          <Title level={5} style={{ marginBottom: 12 }}>基础信息</Title>
          <Row gutter={16}>
            <Col span={8}><Form.Item label="显示名称" name="displayName" rules={[{ required: true }]}><Input /></Form.Item></Col>
            <Col span={8}><Form.Item label="内部名称" name="name" rules={[{ required: true }]}><Input /></Form.Item></Col>
            <Col span={8}><Form.Item label="分类" name="category" rules={[{ required: true }]}><Input placeholder="如：客服 / 销售 / 通用" /></Form.Item></Col>
          </Row>
          <Form.Item label="说明" name="description"><Input.TextArea rows={2} /></Form.Item>

          <Row gutter={16}>
            <Col span={8}>
              <Form.Item label="管理方" name="managedBy" rules={[{ required: true }]}>
                <Select disabled options={Object.entries(managedByMap).map(([value, meta]) => ({ label: meta.label, value }))} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item label="接入形态" name="integrationType" rules={[{ required: true }]}>
                <Select
                  onChange={handleIntegrationTypeChange}
                  options={Object.entries(integrationMap).map(([value, meta]) => ({ label: meta.label, value }))}
                />
              </Form.Item>
            </Col>
            {(isHttpApi || isPlatformApi) && (
              <Col span={8}>
                <Form.Item
                  label="凭证引用"
                  name="credentialRef"
                  rules={isHttpApi ? [{ required: true, message: '请选择凭证' }] : undefined}
                >
                  <Select
                    allowClear={!isHttpApi}
                    placeholder={isPlatformApi ? '默认使用平台内部服务凭证' : '选择业务系统凭证'}
                    options={credentials
                      .filter((credential) => isHttpApi || credential.owner === 'Platform')
                      .map((credential) => ({
                        label: `${credential.name}（${credential.maskedValue}）`,
                        value: credential.credentialId,
                      }))}
                  />
                </Form.Item>
              </Col>
            )}
          </Row>

          {isPlatformApi && (
            <Row gutter={16}>
              <Col span={16}>
                <Form.Item label="平台接口" name="platformApiPath" rules={[{ required: true, message: '请选择平台接口' }]}>
                  <Select
                    placeholder="选择平台内部接口"
                    options={platformApiOptions}
                    onChange={(path) => {
                      const api = platformApiOptions.find((item) => item.value === path);
                      toolForm.setFieldsValue({ method: api?.method ?? 'POST' });
                    }}
                  />
                </Form.Item>
              </Col>
              <Col span={8}><Form.Item label="请求方法" name="method" rules={[{ required: true }]}><Select options={methodOptions} /></Form.Item></Col>
            </Row>
          )}

          {isHttpApi && (
            <Row gutter={16}>
              <Col span={10}><Form.Item label="基础地址" name="baseUrl" rules={[{ required: true, message: '请输入基础地址' }]}><Input placeholder="https://crm.internal.example" /></Form.Item></Col>
              <Col span={8}><Form.Item label="路径" name="path" rules={[{ required: true, message: '请输入路径' }]}><Input placeholder="/api/customers/search" /></Form.Item></Col>
              <Col span={6}><Form.Item label="请求方法" name="method" rules={[{ required: true }]}><Select options={methodOptions} /></Form.Item></Col>
            </Row>
          )}

          <Row gutter={16}>
            <Col span={8}>
              <Form.Item label="读写" name="readWrite" rules={[{ required: true }]}>
                <Select options={Object.entries(readWriteMap).map(([value, meta]) => ({ label: meta.label, value }))} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item label="风险等级" name="riskLevel" rules={[{ required: true }]}>
                <Select options={Object.entries(riskMap).map(([value, meta]) => ({ label: meta.label, value }))} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item label="生命周期状态" name="status" rules={[{ required: true }]}>
                <Select options={Object.entries(statusMap).map(([value, meta]) => ({ label: meta.label, value }))} />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={8}><Form.Item name="requiresApproval" valuePropName="checked"><Checkbox>需要审批</Checkbox></Form.Item></Col>
            <Col span={8}><Form.Item name="auditRequired" valuePropName="checked"><Checkbox>必须审计</Checkbox></Form.Item></Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item label="请求数据结构" name="requestSchema">
                <Input.TextArea rows={4} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="响应数据结构" name="responseSchema">
                <Input.TextArea rows={4} />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item label="默认约束" name="defaultConstraintsText">
            <Input.TextArea rows={3} placeholder="每行一个约束，如：仅限本部门客户" />
          </Form.Item>
          <Form.Item
            label="幂等性策略"
            name="idempotencyPolicy"
            rules={[{ required: true, message: '业务工具必须配置幂等性策略' }]}
            extra="平台管理工具发布前必须说明幂等键、重复请求处理和外部对象追踪方式。"
          >
            <Input.TextArea rows={3} placeholder="例如：按 employee_id + goal_run_id + work_item_id + request_hash 生成幂等键；重复请求返回已有外部对象 ID。" />
          </Form.Item>
          <Alert
            type="warning"
            showIcon
            title="写入或高风险工具发布前必须配置审批和审计，并通过后端网关配置校验。"
          />
        </Form>
      </Modal>

      <Modal
        title={editingCredential ? '编辑凭证' : '新增凭证'}
        open={credentialOpen}
        onCancel={() => { setCredentialOpen(false); setEditingCredential(null); credentialForm.resetFields(); }}
        onOk={saveCredential}
        width={620}
        forceRender
        destroyOnHidden
      >
        <Form form={credentialForm} layout="vertical">
          <Row gutter={16}>
            <Col span={12}><Form.Item label="名称" name="name" rules={[{ required: true }]}><Input /></Form.Item></Col>
            <Col span={12}>
              <Form.Item label="类型" name="type" rules={[{ required: true }]}>
                <Select options={Object.entries(credentialTypeMap).map(([value, label]) => ({ label, value }))} />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                label="归属方"
                name="owner"
                rules={[{ required: true }]}
                extra="指负责该凭证的平台内部服务或业务部门；Hermes 不持有凭证。"
              >
                <Select options={credentialOwnerOptions} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="状态" name="status" rules={[{ required: true }]}>
                <Select options={[
                  { label: '可用', value: 'active' },
                  { label: '已轮换', value: 'rotated' },
                  { label: '禁用', value: 'disabled' },
                ]} />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item
            label="密钥明文"
            name="secretValue"
            rules={editingCredential ? [] : [{ required: true, message: '新增凭证必须填写密钥明文' }]}
          >
            <Input.Password placeholder={editingCredential ? '不填写则保留原密钥' : '请输入 API Key、Token 或 Webhook Secret'} />
          </Form.Item>
          <Alert type="info" showIcon title="保存后页面只展示后端返回的脱敏值。凭证明文由本系统保存和加密管理，不下发到 Hermes 配置目录。" />
        </Form>
      </Modal>

      <Modal
        title="轮换凭证"
        open={!!rotatingCredential}
        onCancel={() => { setRotatingCredential(null); rotationForm.resetFields(); }}
        onOk={submitCredentialRotation}
        width={520}
        destroyOnHidden
      >
        <Form form={rotationForm} layout="vertical">
          <Descriptions bordered size="small" column={1} style={{ marginBottom: 16 }}>
            <Descriptions.Item label="凭证">{rotatingCredential?.name}</Descriptions.Item>
            <Descriptions.Item label="当前脱敏值"><Text code>{rotatingCredential?.maskedValue}</Text></Descriptions.Item>
          </Descriptions>
          <Form.Item label="新密钥明文" name="secretValue" rules={[{ required: true, message: '轮换凭证必须填写新密钥' }]}>
            <Input.Password placeholder="请输入新的 API Key、Token 或 Webhook Secret" />
          </Form.Item>
          <Alert type="warning" showIcon title="提交后后端会替换保存的密钥明文，并返回新的脱敏值用于页面展示。" />
        </Form>
      </Modal>

      <Modal
        title="测试调用结果"
        open={testOpen}
        onCancel={() => setTestOpen(false)}
        footer={<Button type="primary" onClick={() => setTestOpen(false)}>关闭</Button>}
        width={640}
      >
        {testTool && (
          <Descriptions bordered size="small" column={1}>
            <Descriptions.Item label="工具">{testTool.displayName}</Descriptions.Item>
            <Descriptions.Item label="接入形态"><Tag color={integrationMap[testTool.integrationType].color}>{integrationMap[testTool.integrationType].label}</Tag></Descriptions.Item>
            <Descriptions.Item label="测试结果"><Tag color={testTool.lastTestStatus === 'passed' ? 'green' : 'red'}>{testTool.lastTestStatus === 'passed' ? '通过' : '失败'}</Tag></Descriptions.Item>
            <Descriptions.Item label="网关响应"><Text code>{testTool.lastTestedAt ?? `tool_test_${testTool.toolId}`}</Text></Descriptions.Item>
            <Descriptions.Item label="审计">测试调用会记录后端工具配置校验审计事件，不访问真实业务系统。</Descriptions.Item>
          </Descriptions>
        )}
      </Modal>

      <Modal
        title="工具详情"
        open={detailOpen}
        onCancel={() => setDetailOpen(false)}
        footer={null}
        width={760}
      >
        {selectedTool && (
          <Space orientation="vertical" size={16} style={{ width: '100%' }}>
            <Descriptions bordered size="small" column={2}>
              <Descriptions.Item label="工具编号"><Text code>{selectedTool.toolId}</Text></Descriptions.Item>
              <Descriptions.Item label="状态">
                {(() => {
                  const meta = statusMap[selectedTool.status];
                  return <Badge status={meta.badge} text={meta.label} />;
                })()}
              </Descriptions.Item>
              <Descriptions.Item label="管理方"><Tag color={managedByMap[selectedTool.managedBy].color}>{managedByMap[selectedTool.managedBy].label}</Tag></Descriptions.Item>
              <Descriptions.Item label="接入形态"><Tag color={integrationMap[selectedTool.integrationType].color}>{integrationMap[selectedTool.integrationType].label}</Tag></Descriptions.Item>
              <Descriptions.Item label="凭证">{selectedTool.credentialRef ? credentialNameById[selectedTool.credentialRef] : '不需要'}</Descriptions.Item>
              <Descriptions.Item label="绑定模板">{selectedTool.boundTemplateCount}</Descriptions.Item>
              <Descriptions.Item label="读写"><Tag color={readWriteMap[selectedTool.readWrite]?.color ?? 'default'}>{readWriteMap[selectedTool.readWrite]?.label ?? selectedTool.readWrite}</Tag></Descriptions.Item>
              <Descriptions.Item label="风险"><Tag color={riskMap[selectedTool.riskLevel]?.color ?? 'default'}>{riskMap[selectedTool.riskLevel]?.label ?? selectedTool.riskLevel}风险</Tag></Descriptions.Item>
              <Descriptions.Item label="审批">{selectedTool.requiresApproval ? '需要' : '不需要'}</Descriptions.Item>
              <Descriptions.Item label="审计">{selectedTool.auditRequired ? '必须审计' : '不强制'}</Descriptions.Item>
            </Descriptions>
            <Card title="说明" size="small"><Paragraph style={{ margin: 0 }}>{selectedTool.description}</Paragraph></Card>
            <Card title="默认约束" size="small">
              <Space size={4} wrap>
                {selectedTool.defaultConstraints.map((constraint) => <Tag key={constraint}>{constraint}</Tag>)}
              </Space>
            </Card>
            <Card title="幂等性策略" size="small">
              <Paragraph style={{ margin: 0 }}>{selectedTool.idempotencyPolicy}</Paragraph>
            </Card>
            <Card title="数据结构" size="small">
              <Row gutter={16}>
                <Col span={12}><Text strong>请求</Text><pre style={{ whiteSpace: 'pre-wrap' }}>{selectedTool.schemaConfig.request}</pre></Col>
                <Col span={12}><Text strong>响应</Text><pre style={{ whiteSpace: 'pre-wrap' }}>{selectedTool.schemaConfig.response}</pre></Col>
              </Row>
            </Card>
          </Space>
        )}
      </Modal>
    </div>
  );
}

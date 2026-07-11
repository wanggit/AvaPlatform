// 预算与用量页面：维护组织级预算、Goal 预算策略和令牌用量分析。
import { useMemo, useState } from 'react';
import {
  Alert,
  Badge,
  Button,
  Card,
  Col,
  Descriptions,
  Form,
  InputNumber,
  Modal,
  Progress,
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
  EditOutlined,
  FundOutlined,
  StopOutlined,
  WarningOutlined,
  WalletOutlined,
} from '@ant-design/icons';
import {
  type Goal,
  type GoalBudgetPolicy,
  type UsageAnalyticsRow,
} from '../types/domain';
import { api } from '../services/api';
import { usePlatformData } from '../services/platformData';

const { Title, Text, Paragraph } = Typography;

function percent(used: number, limit: number) {
  if (!limit) return 0;
  return Math.min(100, Math.round((used / limit) * 100));
}

function usageStatus(used: number, limit: number, threshold: number) {
  const value = percent(used, limit);
  if (value >= 100) return 'exception' as const;
  if (value >= threshold) return 'active' as const;
  return 'normal' as const;
}

const budgetStatusMap = {
  normal: { label: '正常', color: 'success' as const },
  warning: { label: '预警', color: 'warning' as const },
  budget_blocked: { label: '预算阻断', color: 'error' as const },
};

export default function QuotaManagement() {
  const {
    organizationQuota: organizationPolicy,
    tokenLedger,
    usageAnalytics,
    employees,
    models,
    templates,
    goals,
    goalBudgetPolicies,
    refresh,
    source,
  } = usePlatformData();
  const [editingGoalBudget, setEditingGoalBudget] = useState<GoalBudgetPolicy | null>(null);
  const [orgOpen, setOrgOpen] = useState(false);
  const [goalBudgetOpen, setGoalBudgetOpen] = useState(false);
  const [orgForm] = Form.useForm();
  const [goalBudgetForm] = Form.useForm();

  const employeeNameById = useMemo(() => (
    employees.reduce<Record<string, string>>((acc, employee) => {
      acc[employee.id] = employee.name;
      return acc;
    }, {})
  ), [employees]);

  const modelNameById = useMemo(() => (
    models.reduce<Record<string, string>>((acc, model) => {
      acc[model.id] = model.name;
      return acc;
    }, {})
  ), [models]);

  const templateById = useMemo(() => (
    templates.reduce<Record<string, string>>((acc, template) => {
      acc[template.id] = `${template.role} v${template.version}`;
      return acc;
    }, {})
  ), [templates]);

  const orgUsedToday = tokenLedger.reduce((sum, entry) => sum + entry.totalTokens, 0);
  const blockedGoalCount = goals.filter((goal) => goal.status === 'budget_blocked').length;
  const warningGoalCount = goals.filter((goal) => goal.budgetStatus === 'warning').length;
  const estimatedUsage = tokenLedger.filter((entry) => entry.estimated).reduce((sum, entry) => sum + entry.totalTokens, 0);

  const openOrg = () => {
    orgForm.setFieldsValue(organizationPolicy);
    setOrgOpen(true);
  };

  const saveOrg = () => {
    orgForm.validateFields().then(async (values) => {
      await api.put('/quota/organization', {
        monthly_token_limit: values.dailyTokenLimit,
        warning_threshold_percent: values.warningThresholdPercent,
        over_limit_action: 'block_new_work',
      });
      await refresh();
      setOrgOpen(false);
    });
  };

  const openGoalBudget = (policy: GoalBudgetPolicy) => {
    setEditingGoalBudget(policy);
    goalBudgetForm.setFieldsValue(policy);
    setGoalBudgetOpen(true);
  };

  const saveGoalBudget = () => {
    goalBudgetForm.validateFields().then(async (values) => {
      if (!editingGoalBudget) return;
      await api.patch(`/quota/goal-budgets/${editingGoalBudget.id}`, {
        default_budget_tokens: values.defaultBudgetTokens,
        warning_threshold_percent: values.warningThresholdPercent,
        overage_action: values.overageAction,
        approvers: values.approvers ?? [],
      });
      await refresh();
      setGoalBudgetOpen(false);
      setEditingGoalBudget(null);
      goalBudgetForm.resetFields();
    });
  };

  const clearBudgetBlock = async (goalId: string) => {
    await api.post(`/goal-runs/${goalId}/resume`);
    await refresh();
  };

  const goalColumns = [
    {
      title: '目标运行',
      dataIndex: 'title',
      key: 'title',
      render: (title: string, row: Goal) => (
        <Space orientation="vertical" size={0}>
          <Text strong>{title}</Text>
          <Text type="secondary" style={{ fontSize: 12 }}>{templateById[row.templateId]} / 负责人：{row.rootOwnerName}</Text>
        </Space>
      ),
    },
    { title: '风险等级', dataIndex: 'riskLevel', key: 'riskLevel', width: 90, render: (riskLevel: string) => <Tag>{riskLevel}</Tag> },
    {
      title: '预算使用',
      key: 'budget',
      width: 260,
      render: (_: unknown, row: Goal) => (
        <Space orientation="vertical" size={2} style={{ width: '100%' }}>
          <Progress
            percent={percent(row.tokenUsed, row.budgetTokens)}
            size="small"
            status={usageStatus(row.tokenUsed, row.budgetTokens, 80)}
          />
          <Text type="secondary" style={{ fontSize: 12 }}>
            {(row.tokenUsed / 1000).toFixed(0)}K / {(row.budgetTokens / 1000).toFixed(0)}K 令牌
          </Text>
        </Space>
      ),
    },
    {
      title: '状态',
      dataIndex: 'budgetStatus',
      key: 'budgetStatus',
      width: 110,
      render: (status: Goal['budgetStatus']) => (
        <Badge status={budgetStatusMap[status].color} text={budgetStatusMap[status].label} />
      ),
    },
    {
      title: '动作',
      key: 'actions',
      width: 140,
      render: (_: unknown, row: Goal) => (
        row.status === 'budget_blocked'
          ? <Button size="small" icon={<StopOutlined />} onClick={() => clearBudgetBlock(row.id)}>调整后恢复</Button>
          : <Text type="secondary">控制面可用</Text>
      ),
    },
  ];

  const policyColumns = [
    {
      title: '岗位模板',
      dataIndex: 'templateId',
      key: 'templateId',
      render: (templateId: string) => <Text strong>{templateById[templateId] ?? templateId}</Text>,
    },
    { title: '默认目标预算', dataIndex: 'defaultBudgetTokens', key: 'defaultBudgetTokens', render: (value: number) => `${(value / 1000).toFixed(0)}K 令牌` },
    { title: '预警阈值', dataIndex: 'warningThresholdPercent', key: 'warningThresholdPercent', render: (value: number) => `${value}%` },
    {
      title: '超限动作',
      dataIndex: 'overageAction',
      key: 'overageAction',
      render: (value: GoalBudgetPolicy['overageAction']) => value === 'block_goal_model_calls' ? <Tag color="red">阻断该目标的新模型成本调用</Tag> : <Tag color="gold">只告警</Tag>,
    },
    { title: '审批人', dataIndex: 'approvers', key: 'approvers', render: (value: string[]) => value.map((item) => <Tag key={item}>{item}</Tag>) },
    { title: '更新', dataIndex: 'updatedAt', key: 'updatedAt', width: 150 },
    { title: '操作', key: 'actions', width: 90, render: (_: unknown, row: GoalBudgetPolicy) => <Button size="small" icon={<EditOutlined />} onClick={() => openGoalBudget(row)}>编辑</Button> },
  ];

  const ledgerColumns = [
    { title: '时间', dataIndex: 'occurredAt', key: 'occurredAt', width: 160 },
    { title: '目标运行', dataIndex: 'goalRunId', key: 'goalRunId', width: 110 },
    { title: '工作项', dataIndex: 'workItemId', key: 'workItemId', width: 130 },
    { title: '员工', dataIndex: 'employeeId', key: 'employeeId', render: (value: string) => employeeNameById[value] ?? value },
    { title: '部门', dataIndex: 'department', key: 'department', width: 90 },
    { title: '模型', dataIndex: 'modelConfigId', key: 'modelConfigId', render: (value: string) => <Text code>{modelNameById[value] ?? value}</Text> },
    { title: '令牌数', dataIndex: 'totalTokens', key: 'totalTokens', align: 'right' as const, render: (value: number) => value.toLocaleString() },
    { title: '用量来源', dataIndex: 'estimated', key: 'estimated', width: 120, render: (value: boolean) => value ? <Tag color="orange">估算</Tag> : <Tag color="green">模型服务商返回</Tag> },
  ];

  const analyticsColumns = [
    {
      title: '维度',
      key: 'dimension',
      render: (_: unknown, row: UsageAnalyticsRow) => (
        <Space orientation="vertical" size={0}>
          <Text strong>{row.name}</Text>
          <Text type="secondary" style={{ fontSize: 12 }}>
            {row.dimensionType === 'department' ? '部门' : row.dimensionType === 'employee' ? '员工' : '岗位模板'}
          </Text>
        </Space>
      ),
    },
    { title: '目标运行数', dataIndex: 'goalRuns', key: 'goalRuns', width: 110 },
    { title: '令牌数', dataIndex: 'tokens', key: 'tokens', render: (value: number) => value.toLocaleString() },
    { title: '估算令牌数', dataIndex: 'estimatedTokens', key: 'estimatedTokens', render: (value: number) => value ? <Tag color="orange">{value.toLocaleString()}</Tag> : <Text type="secondary">0</Text> },
    { title: '预算阻断目标', dataIndex: 'blockedGoals', key: 'blockedGoals', render: (value: number) => value ? <Tag color="red">{value}</Tag> : <Text type="secondary">0</Text> },
    { title: '趋势', dataIndex: 'trend', key: 'trend', render: (value: UsageAnalyticsRow['trend']) => value === 'up' ? <Tag color="blue">上升</Tag> : value === 'down' ? <Tag color="green">下降</Tag> : <Tag>持平</Tag> },
  ];

  return (
    <>
      <Space align="start" style={{ width: '100%', marginBottom: 16, justifyContent: 'space-between' }}>
        <Space orientation="vertical" size={2}>
          <Title level={4} style={{ margin: 0 }}>预算与用量</Title>
          <Text type="secondary">最小可用版本只维护组织总预算和目标预算。当前数据源：{source === 'backend' ? '后端接口' : '后端不可用'}。</Text>
        </Space>
        <Button type="primary" icon={<EditOutlined />} onClick={openOrg}>编辑组织预算</Button>
      </Space>

      <Alert
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
        title="目标预算超限后只阻断该目标运行的新模型成本调用，不停止 Hermes 实例；控制面、审计、执行追踪、令牌流水和人工调整仍保持可用。"
      />

      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card size="small">
            <Statistic title="组织总预算使用率" value={percent(orgUsedToday, organizationPolicy.dailyTokenLimit)} suffix="%" prefix={<WalletOutlined />} />
            <Progress percent={percent(orgUsedToday, organizationPolicy.dailyTokenLimit)} status={usageStatus(orgUsedToday, organizationPolicy.dailyTokenLimit, organizationPolicy.warningThresholdPercent)} />
            <Text type="secondary">{orgUsedToday.toLocaleString()} / {organizationPolicy.dailyTokenLimit.toLocaleString()} 令牌</Text>
          </Card>
        </Col>
        <Col span={6}>
          <Card size="small"><Statistic title="目标预算预警" value={warningGoalCount} prefix={<WarningOutlined />} styles={{ content: { color: warningGoalCount > 0 ? '#fa8c16' : undefined } }} /></Card>
        </Col>
        <Col span={6}>
          <Card size="small"><Statistic title="预算阻断" value={blockedGoalCount} prefix={<StopOutlined />} styles={{ content: { color: blockedGoalCount > 0 ? '#f5222d' : undefined } }} /></Card>
        </Col>
        <Col span={6}>
          <Card size="small"><Statistic title="估算令牌数" value={estimatedUsage} prefix={<FundOutlined />} /></Card>
        </Col>
      </Row>

      <Tabs
        items={[
          {
            key: 'organization',
            label: '组织总预算',
            children: (
              <Card>
                <Descriptions column={2} bordered size="small">
                  <Descriptions.Item label="周期">每日 / {organizationPolicy.timezone}</Descriptions.Item>
                  <Descriptions.Item label="执行方式"><Tag color="red">硬控</Tag></Descriptions.Item>
                  <Descriptions.Item label="每日令牌上限">{organizationPolicy.dailyTokenLimit.toLocaleString()}</Descriptions.Item>
                  <Descriptions.Item label="预警阈值">{organizationPolicy.warningThresholdPercent}%</Descriptions.Item>
                  <Descriptions.Item label="阻断数据面调用" span={2}>{organizationPolicy.blockedDataPlaneCalls.map((item) => <Tag color="red" key={item}>{item}</Tag>)}</Descriptions.Item>
                  <Descriptions.Item label="保留控制面动作" span={2}>{organizationPolicy.allowedControlPlaneActions.map((item) => <Tag key={item}>{item}</Tag>)}</Descriptions.Item>
                </Descriptions>
              </Card>
            ),
          },
          {
            key: 'goal-budgets',
            label: '目标预算',
            children: <Table dataSource={goalBudgetPolicies} columns={policyColumns} rowKey="id" pagination={false} />,
          },
          {
            key: 'blocked-goals',
            label: '目标运行状态',
            children: <Table dataSource={goals} columns={goalColumns} rowKey="id" pagination={false} />,
          },
          {
            key: 'ledger',
            label: '令牌流水',
            children: <Table dataSource={tokenLedger} columns={ledgerColumns} rowKey="id" size="middle" />,
          },
          {
            key: 'analytics',
            label: '用量分析',
            children: (
              <Space orientation="vertical" style={{ width: '100%' }}>
                <Alert type="warning" showIcon title="部门、员工、岗位模板在最小可用版本中只做分析维度，不产生独立阻断策略。" />
                <Table dataSource={usageAnalytics} columns={analyticsColumns} rowKey="id" pagination={false} />
              </Space>
            ),
          },
        ]}
      />

      <Modal title="编辑组织总预算" open={orgOpen} onOk={saveOrg} onCancel={() => setOrgOpen(false)} width={620}>
        <Form form={orgForm} layout="vertical">
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item label="每日令牌上限" name="dailyTokenLimit" rules={[{ required: true }]}>
                <InputNumber min={1} step={10000} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="预警阈值" name="warningThresholdPercent" rules={[{ required: true }]}>
                <InputNumber min={1} max={100} addonAfter="%" style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>
          <Paragraph type="secondary">组织总预算固定为硬控，超限后阻断所有新的模型成本调用。</Paragraph>
        </Form>
      </Modal>

      <Modal
        title="编辑目标预算策略"
        open={goalBudgetOpen}
        onOk={saveGoalBudget}
        onCancel={() => { setGoalBudgetOpen(false); setEditingGoalBudget(null); goalBudgetForm.resetFields(); }}
        width={720}
      >
        <Form form={goalBudgetForm} layout="vertical">
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item label="默认目标预算" name="defaultBudgetTokens" rules={[{ required: true }]}>
                <InputNumber min={1} step={10000} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="预警阈值" name="warningThresholdPercent" rules={[{ required: true }]}>
                <InputNumber min={1} max={100} addonAfter="%" style={{ width: '100%' }} />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item label="超限动作" name="overageAction" rules={[{ required: true }]}>
            <Select
              options={[
                { label: '阻断该目标的新模型成本调用', value: 'block_goal_model_calls' },
                { label: '只告警', value: 'alert_only' },
              ]}
            />
          </Form.Item>
          <Form.Item label="预算调整审批人" name="approvers">
            <Select mode="tags" />
          </Form.Item>
          <Alert type="info" showIcon title="目标预算随目标运行创建；调整策略不会追溯修改已运行目标，已运行目标应单独调整预算。" />
        </Form>
      </Modal>
    </>
  );
}

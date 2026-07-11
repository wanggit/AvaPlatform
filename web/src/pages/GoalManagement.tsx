// 目标运行页面：管理 Goal、工作项、委派关系和运行预算。
import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Badge,
  Button,
  Card,
  Col,
  Descriptions,
  Form,
  Input,
  InputNumber,
  Modal,
  Progress,
  Row,
  Select,
  Space,
  Statistic,
  Table,
  Tag,
  Timeline,
  Typography,
  Alert,
} from 'antd';
import {
  ApartmentOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  PlusOutlined,
  StopOutlined,
} from '@ant-design/icons';
import {
  type Goal,
  type GoalRiskLevel,
  type WorkItem,
} from '../types/domain';
import { api, buildCreateGoalRunPayload } from '../services/api';
import { usePlatformData } from '../services/platformData';

const { Title, Text, Paragraph } = Typography;

const statusMap: Record<Goal['status'], { label: string; color: string; badge: 'success' | 'processing' | 'warning' | 'error' | 'default' }> = {
  created: { label: '已创建', color: 'default', badge: 'default' },
  in_progress: { label: '执行中', color: 'processing', badge: 'processing' },
  needs_approval: { label: '待审批', color: 'orange', badge: 'warning' },
  needs_acceptance: { label: '待验收', color: 'purple', badge: 'warning' },
  budget_blocked: { label: '预算阻断', color: 'red', badge: 'error' },
  completed: { label: '已完成', color: 'green', badge: 'success' },
  failed: { label: '失败', color: 'red', badge: 'error' },
  cancelled: { label: '已取消', color: 'default', badge: 'default' },
};

const workItemStatusMap: Record<WorkItem['status'], { label: string; color: string }> = {
  pending: { label: '待开始', color: 'default' },
  in_progress: { label: '执行中', color: 'blue' },
  waiting_approval: { label: '等审批', color: 'orange' },
  waiting_acceptance: { label: '等验收', color: 'purple' },
  completed: { label: '已完成', color: 'green' },
  blocked: { label: '阻断', color: 'red' },
};

const acceptanceStatusMap: Record<NonNullable<WorkItem['acceptanceStatus']>, string> = {
  not_submitted: '未提交',
  submitted: '已提交',
  accepted: '已接受',
  rework_requested: '要求返工',
};

const riskOptions: { label: string; value: GoalRiskLevel }[] = [
  { label: 'L1 低风险', value: 'L1' },
  { label: 'L2 可逆业务动作', value: 'L2' },
  { label: 'L3 需要审批的业务动作', value: 'L3' },
  { label: 'L4 只准备决策材料', value: 'L4' },
];

function budgetPercent(goal: Goal) {
  return Math.min(100, Math.round((goal.tokenUsed / goal.budgetTokens) * 100));
}

export default function GoalManagement() {
  const navigate = useNavigate();
  const { goals, employees, templates, refresh, source } = usePlatformData();
  const [createOpen, setCreateOpen] = useState(false);
  const [detailOpen, setDetailOpen] = useState(false);
  const [selectedGoal, setSelectedGoal] = useState<Goal | null>(null);
  const [form] = Form.useForm();
  const selectedRootOwnerId = Form.useWatch('rootOwnerId', form) as string | undefined;

  const employeeOptions = employees.map((employee) => ({
    label: `${employee.name} / ${employee.role}`,
    value: employee.id,
  }));

  const employeeById = useMemo(() => (
    employees.reduce<Record<string, typeof employees[number]>>((acc, employee) => {
      acc[employee.id] = employee;
      return acc;
    }, {})
  ), [employees]);

  const templateById = useMemo(() => (
    templates.reduce<Record<string, typeof templates[number]>>((acc, template) => {
      acc[template.id] = template;
      return acc;
    }, {})
  ), [templates]);

  const selectedRootOwner = selectedRootOwnerId ? employeeById[selectedRootOwnerId] : undefined;
  const selectedRootOwnerTemplate = selectedRootOwner ? templateById[selectedRootOwner.templateId] : undefined;

  const createGoal = () => {
    form.validateFields().then(async (values) => {
      const owner = employeeById[values.rootOwnerId];
      const template = owner ? templateById[owner.templateId] : undefined;
      await api.post('/goal-runs', buildCreateGoalRunPayload(values, {
        ownerName: owner?.name,
        ownerTemplateId: owner?.templateId,
        defaultBudgetTokens: template?.defaultGoalBudgetTokens,
      }));
      await refresh();
      setCreateOpen(false);
      form.resetFields();
    });
  };

  const columns = [
    {
      title: '目标运行',
      dataIndex: 'title',
      key: 'title',
      render: (title: string, row: Goal) => (
        <a onClick={() => { setSelectedGoal(row); setDetailOpen(true); }}>
          <Space orientation="vertical" size={0}>
            <Text strong>{title}</Text>
            <Text type="secondary" style={{ fontSize: 12 }}>
              {templateById[row.templateId]?.role ?? row.templateId} / 负责人：{row.rootOwnerName}
            </Text>
          </Space>
        </a>
      ),
    },
    { title: '风险', dataIndex: 'riskLevel', key: 'riskLevel', width: 80, render: (risk: GoalRiskLevel) => <Tag>{risk}</Tag> },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 110,
      render: (status: Goal['status']) => <Badge status={statusMap[status].badge} text={statusMap[status].label} />,
    },
    {
      title: '执行图',
      key: 'graph',
      width: 130,
      render: (_: unknown, row: Goal) => <Tag color="blue">{row.workItems.length} 个工作项</Tag>,
    },
    {
      title: '交付物',
      key: 'artifacts',
      width: 120,
      render: (_: unknown, row: Goal) => row.artifacts.length ? <Tag color="purple">{row.artifacts.length} 个</Tag> : <Text type="secondary">-</Text>,
    },
    {
      title: '目标预算',
      key: 'budget',
      width: 220,
      render: (_: unknown, row: Goal) => (
        <Space orientation="vertical" size={0} style={{ width: '100%' }}>
          <Progress
            percent={budgetPercent(row)}
            size="small"
            status={row.budgetStatus === 'budget_blocked' ? 'exception' : row.budgetStatus === 'warning' ? 'active' : 'normal'}
          />
          <Text type="secondary" style={{ fontSize: 12 }}>{(row.tokenUsed / 1000).toFixed(0)}K / {(row.budgetTokens / 1000).toFixed(0)}K</Text>
        </Space>
      ),
    },
    { title: '截止日期', dataIndex: 'deadline', key: 'deadline', width: 120 },
  ];

  const workItemColumns = [
    {
      title: '工作项',
      dataIndex: 'title',
      key: 'title',
      render: (title: string, row: WorkItem) => (
        <Space orientation="vertical" size={0}>
          <Text strong>{title}</Text>
          <Text type="secondary" style={{ fontSize: 12 }}>{row.delegationReason}</Text>
        </Space>
      ),
    },
    { title: '执行员工', dataIndex: 'ownerEmployeeName', key: 'ownerEmployeeName', width: 140 },
    { title: '状态', dataIndex: 'status', key: 'status', width: 100, render: (status: WorkItem['status']) => <Tag color={workItemStatusMap[status].color}>{workItemStatusMap[status].label}</Tag> },
    { title: '令牌数', dataIndex: 'tokenUsed', key: 'tokenUsed', width: 110, render: (value: number) => value.toLocaleString() },
    {
      title: '验收',
      dataIndex: 'acceptanceStatus',
      key: 'acceptanceStatus',
      width: 120,
      render: (status?: WorkItem['acceptanceStatus']) => status ? <Tag>{acceptanceStatusMap[status]}</Tag> : <Text type="secondary">-</Text>,
    },
  ];

  const activeGoals = goals.filter((goal) => !['completed', 'cancelled', 'failed'].includes(goal.status)).length;
  const waitingHuman = goals.filter((goal) => goal.status === 'needs_approval' || goal.status === 'needs_acceptance').length;
  const blocked = goals.filter((goal) => goal.status === 'budget_blocked').length;
  const workItemCount = goals.reduce((sum, goal) => sum + goal.workItems.length, 0);
  const selectedGoalNeedsApproval = selectedGoal
    ? selectedGoal.status === 'needs_approval'
      || selectedGoal.status === 'needs_acceptance'
      || selectedGoal.status === 'budget_blocked'
      || selectedGoal.workItems.some((item) => item.status === 'waiting_approval' || item.status === 'waiting_acceptance')
      || selectedGoal.artifacts.some((artifact) => artifact.acceptanceStatus === 'submitted' || artifact.acceptanceStatus === 'rework_requested')
    : false;

  return (
    <>
      <Space align="start" style={{ width: '100%', marginBottom: 16, justifyContent: 'space-between' }}>
        <Space orientation="vertical" size={2}>
          <Title level={4} style={{ margin: 0 }}>目标管理</Title>
          <Text type="secondary">维护目标运行、动态执行图、工作项、交付物验收与目标预算状态。当前数据源：{source === 'backend' ? '后端接口' : '后端不可用'}。</Text>
        </Space>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateOpen(true)}>新建目标</Button>
      </Space>

      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}><Card size="small"><Statistic title="活跃目标运行" value={activeGoals} prefix={<ClockCircleOutlined />} /></Card></Col>
        <Col span={6}><Card size="small"><Statistic title="工作项" value={workItemCount} prefix={<ApartmentOutlined />} /></Card></Col>
        <Col span={6}><Card size="small"><Statistic title="等待人工处理" value={waitingHuman} styles={{ content: { color: waitingHuman ? '#fa8c16' : undefined } }} /></Card></Col>
        <Col span={6}><Card size="small"><Statistic title="预算阻断" value={blocked} prefix={<StopOutlined />} styles={{ content: { color: blocked ? '#f5222d' : undefined } }} /></Card></Col>
      </Row>

      <Table dataSource={goals} columns={columns} rowKey="id" pagination={false} />

      <Modal title="新建目标运行" open={createOpen} onCancel={() => setCreateOpen(false)} onOk={createGoal} width={760}>
        <Form
          form={form}
          layout="vertical"
          initialValues={{
            riskLevel: 'L2',
          }}
        >
          <Form.Item label="目标标题" name="title" rules={[{ required: true }]}>
            <Input placeholder="例如：整理本周重点客户续约风险" />
          </Form.Item>
          <Form.Item label="目标描述" name="description" rules={[{ required: true }]}>
            <Input.TextArea rows={3} />
          </Form.Item>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item label="根目标负责人" name="rootOwnerId" rules={[{ required: true }]}>
                <Select
                  options={employeeOptions}
                  onChange={(employeeId) => {
                    const employee = employeeById[employeeId];
                    const template = employee ? templateById[employee.templateId] : undefined;
                    form.setFieldsValue({
                      budgetTokens: template?.defaultGoalBudgetTokens,
                      riskLevel: template?.maxGoalRiskLevel && riskOptions.some((option) => option.value === template.maxGoalRiskLevel)
                        ? template.maxGoalRiskLevel
                        : 'L2',
                    });
                  }}
                />
              </Form.Item>
            </Col>
          </Row>
          {selectedRootOwner && selectedRootOwnerTemplate && (
            <Alert
              type="info"
              showIcon
              style={{ marginBottom: 16 }}
              title={`已从根目标负责人自动带出岗位模板：${selectedRootOwnerTemplate.role} v${selectedRootOwnerTemplate.version}`}
              description={`可承接最高风险等级：${selectedRootOwnerTemplate.maxGoalRiskLevel}；默认目标预算：${selectedRootOwnerTemplate.defaultGoalBudgetTokens.toLocaleString()} 令牌。`}
            />
          )}
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item label="目标风险等级" name="riskLevel" rules={[{ required: true }]}>
                <Select options={riskOptions} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item label="目标预算" name="budgetTokens" rules={[{ required: true }]}>
                <InputNumber min={1} step={10000} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item label="截止日期" name="deadline" rules={[{ required: true }]}>
                <Input type="date" />
              </Form.Item>
            </Col>
          </Row>
        </Form>
      </Modal>

      <Modal
        title={selectedGoal?.title}
        open={detailOpen}
        onCancel={() => setDetailOpen(false)}
        width={980}
        footer={<Button type="primary" onClick={() => setDetailOpen(false)}>关闭</Button>}
      >
        {selectedGoal && (
          <Space orientation="vertical" size={16} style={{ width: '100%' }}>
            {selectedGoalNeedsApproval && (
              <Alert
                type="warning"
                showIcon
                title="该目标存在需要人工处理的审批、预算阻断或产物验收事项"
                description="目标详情页只展示上下文。最终审批动作和审批记录统一进入审批中心。"
                action={<Button type="primary" onClick={() => navigate('/approvals')}>前往审批中心</Button>}
              />
            )}
            <Descriptions bordered size="small" column={3}>
              <Descriptions.Item label="状态"><Tag color={statusMap[selectedGoal.status].color}>{statusMap[selectedGoal.status].label}</Tag></Descriptions.Item>
              <Descriptions.Item label="风险等级">{selectedGoal.riskLevel}</Descriptions.Item>
              <Descriptions.Item label="根目标负责人">{selectedGoal.rootOwnerName}</Descriptions.Item>
              <Descriptions.Item label="岗位模板">{templateById[selectedGoal.templateId]?.role}</Descriptions.Item>
              <Descriptions.Item label="截止"><ClockCircleOutlined /> {selectedGoal.deadline}</Descriptions.Item>
              <Descriptions.Item label="预算">{selectedGoal.tokenUsed.toLocaleString()} / {selectedGoal.budgetTokens.toLocaleString()}</Descriptions.Item>
            </Descriptions>

            <Card size="small" title="目标说明">
              <Paragraph style={{ margin: 0 }}>{selectedGoal.description}</Paragraph>
            </Card>

            <Card size="small" title="执行图">
              <Timeline
                items={selectedGoal.workItems.map((item) => ({
                  color: item.status === 'completed' ? 'green' : item.status === 'blocked' ? 'red' : item.status.includes('waiting') ? 'orange' : 'blue',
                  children: (
                    <Space orientation="vertical" size={2}>
                      <Space>
                        <Text strong>{item.ownerEmployeeName}</Text>
                        <Text>{item.title}</Text>
                        <Tag color={workItemStatusMap[item.status].color}>{workItemStatusMap[item.status].label}</Tag>
                      </Space>
                      <Text type="secondary">{item.delegationReason}</Text>
                    </Space>
                  ),
                }))}
              />
            </Card>

            <Table dataSource={selectedGoal.workItems} columns={workItemColumns} rowKey="id" pagination={false} size="small" />

            <Card size="small" title="交付物验收">
              {selectedGoal.artifacts.length ? (
                <Space wrap>
                  {selectedGoal.artifacts.map((artifact) => (
                    <Tag key={artifact.id} color={artifact.acceptanceStatus === 'accepted' ? 'green' : artifact.acceptanceStatus === 'submitted' ? 'blue' : 'orange'}>
                      <CheckCircleOutlined /> {artifact.name} / {acceptanceStatusMap[artifact.acceptanceStatus]} / {artifact.reviewer}
                    </Tag>
                  ))}
                </Space>
              ) : <Text type="secondary">暂无交付物提交。</Text>}
            </Card>
          </Space>
        )}
      </Modal>
    </>
  );
}

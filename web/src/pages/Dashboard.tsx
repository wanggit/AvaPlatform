// 平台首页仪表盘：汇总数字员工、目标运行、告警和预算使用情况。
import { Badge, Card, Col, Progress, Row, Space, Statistic, Table, Tag, Typography } from 'antd';
import {
  AimOutlined,
  AlertOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  TeamOutlined,
  WarningOutlined,
  WalletOutlined,
} from '@ant-design/icons';
import {
  type Goal,
} from '../types/domain';
import { usePlatformData } from '../services/platformData';

const { Title, Text } = Typography;

const riskyTemplateTagStyle = {
  backgroundColor: '#fff1f0',
  borderColor: '#ffa39e',
  color: '#a8071a',
};

export default function Dashboard() {
  const { employees, templates, organizationQuota, tokenLedger, goals, templateOutcomeReports, alertMessages, source } = usePlatformData();
  const activeEmployeeCount = employees.filter((employee) => employee.lifecycleState === 'active').length;
  const unavailableActiveEmployees = employees.filter((employee) => employee.lifecycleState === 'active' && employee.availabilityState === 'unavailable').length;
  const rolloutAttention = employees.filter((employee) => ['pending_activation', 'rollout_failed', 'needs_review'].includes(employee.lifecycleState)).length;
  const activeGoals = goals.filter((goal) => !['completed', 'cancelled', 'failed'].includes(goal.status)).length;
  const budgetBlocked = goals.filter((goal) => goal.status === 'budget_blocked').length;
  const waitingHuman = goals.filter((goal) => goal.status === 'needs_approval' || goal.status === 'needs_acceptance').length;
  const orgUsedToday = tokenLedger.reduce((sum, entry) => sum + entry.totalTokens, 0);
  const orgUsagePercent = Math.round((orgUsedToday / organizationQuota.dailyTokenLimit) * 100);
  const riskyTemplates = templates.filter((template) => template.evaluation.status !== 'passed').length;

  const alertColumns = [
    {
      title: '类型',
      dataIndex: 'type',
      key: 'type',
      width: 110,
      render: (type: string) => {
        const map: Record<string, { color: string; label: string }> = {
          redline: { color: 'red', label: '红线' },
          budget: { color: 'orange', label: '预算' },
          escalation: { color: 'blue', label: '升级' },
        };
        return <Tag color={map[type]?.color ?? 'default'}>{map[type]?.label ?? type}</Tag>;
      },
    },
    { title: '消息', dataIndex: 'message', key: 'message' },
    { title: '时间', dataIndex: 'time', key: 'time', width: 150 },
    { title: '状态', dataIndex: 'resolved', key: 'resolved', width: 90, render: (resolved: boolean) => resolved ? <Tag color="green">已处理</Tag> : <Badge status="error" text="待处理" /> },
  ];

  const goalColumns = [
    {
      title: '目标运行',
      dataIndex: 'title',
      key: 'title',
      render: (title: string, row: Goal) => (
        <Space orientation="vertical" size={0}>
          <Text strong>{title}</Text>
          <Text type="secondary" style={{ fontSize: 12 }}>负责人：{row.rootOwnerName} / {row.riskLevel}</Text>
        </Space>
      ),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 120,
      render: (status: string) => {
        const map: Record<string, { color: string; label: string }> = {
          in_progress: { color: 'blue', label: '执行中' },
          needs_approval: { color: 'orange', label: '待审批' },
          needs_acceptance: { color: 'purple', label: '待验收' },
          budget_blocked: { color: 'red', label: '预算阻断' },
          completed: { color: 'green', label: '已完成' },
        };
        return <Tag color={map[status]?.color ?? 'default'}>{map[status]?.label ?? status}</Tag>;
      },
    },
    {
      title: '预算',
      key: 'budget',
      width: 190,
      render: (_: unknown, row: Goal) => (
        <Progress percent={Math.round((row.tokenUsed / row.budgetTokens) * 100)} size="small" status={row.budgetStatus === 'budget_blocked' ? 'exception' : row.budgetStatus === 'warning' ? 'active' : 'normal'} />
      ),
    },
  ];

  return (
    <>
      <Title level={4} style={{ marginTop: 0, marginBottom: 16 }}>概览看板 <Text type="secondary" style={{ fontSize: 14 }}>当前数据源：{source === 'backend' ? '后端接口' : '后端不可用'}</Text></Title>

      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}><Card size="small"><Statistic title="已上岗员工" value={activeEmployeeCount} suffix={`/ ${employees.length}`} prefix={<TeamOutlined />} /></Card></Col>
        <Col span={6}><Card size="small"><Statistic title="活跃目标运行" value={activeGoals} prefix={<AimOutlined />} /></Card></Col>
        <Col span={6}><Card size="small"><Statistic title="待人工处理" value={waitingHuman} prefix={<ClockCircleOutlined />} styles={{ content: { color: waitingHuman ? '#fa8c16' : undefined } }} /></Card></Col>
        <Col span={6}><Card size="small"><Statistic title="预算阻断" value={budgetBlocked} prefix={<AlertOutlined />} styles={{ content: { color: budgetBlocked ? '#f5222d' : undefined } }} /></Card></Col>
      </Row>

      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col xs={24} md={12} xl={6}>
          <Card size="small" title="组织总预算">
            <Statistic value={orgUsagePercent} suffix="%" prefix={<WalletOutlined />} />
            <Progress percent={orgUsagePercent} status={orgUsagePercent >= 100 ? 'exception' : orgUsagePercent >= 80 ? 'active' : 'normal'} />
            <Text type="secondary">{orgUsedToday.toLocaleString()} / {organizationQuota.dailyTokenLimit.toLocaleString()} 令牌</Text>
          </Card>
        </Col>
        <Col xs={24} md={12} xl={6}>
          <Card size="small" title="员工上岗">
            <Statistic title="待处理上岗项" value={rolloutAttention} prefix={<CheckCircleOutlined />} styles={{ content: { color: rolloutAttention ? '#fa8c16' : undefined } }} />
            <Space wrap>
              <Tag color={unavailableActiveEmployees ? 'red' : 'default'}>运行异常 {unavailableActiveEmployees}</Tag>
              {employees.filter((employee) => ['pending_activation', 'rollout_failed', 'needs_review'].includes(employee.lifecycleState)).map((employee) => (
                <Tag key={employee.id} color={employee.lifecycleState === 'rollout_failed' ? 'red' : 'gold'}>{employee.name}</Tag>
              ))}
            </Space>
          </Card>
        </Col>
        <Col xs={24} md={12} xl={6}>
          <Card size="small" title="模板评测">
            <Statistic title="不可发布模板" value={riskyTemplates} prefix={<WarningOutlined />} styles={{ content: { color: riskyTemplates ? '#d4380d' : undefined } }} />
            <Space wrap>
              {templates.filter((template) => template.evaluation.status !== 'passed').map((template) => (
                <Tag key={template.id} style={riskyTemplateTagStyle}>{template.role} / {template.evaluation.status}</Tag>
              ))}
            </Space>
          </Card>
        </Col>
        <Col xs={24} md={12} xl={6}>
          <Card size="small" title="试点效果">
            <Space orientation="vertical" style={{ width: '100%' }}>
              {templateOutcomeReports.slice(0, 3).map((report) => (
                <Space key={report.id} style={{ width: '100%', justifyContent: 'space-between' }}>
                  <Text>{report.templateRole}</Text>
                  <Tag color={report.completionRate >= 85 ? 'green' : 'orange'}>{report.completionRate}% 完成</Tag>
                </Space>
              ))}
            </Space>
          </Card>
        </Col>
      </Row>

      <Row gutter={16}>
        <Col span={14}>
          <Card title="活跃目标运行" size="small">
            <Table
              dataSource={goals.filter((goal) => goal.status !== 'completed')}
              columns={goalColumns}
              rowKey="id"
              pagination={false}
              size="small"
            />
          </Card>
        </Col>
        <Col span={10}>
          <Card title="告警与待处理" size="small">
            <Table dataSource={alertMessages} columns={alertColumns} rowKey="id" pagination={false} size="small" />
          </Card>
        </Col>
      </Row>
    </>
  );
}

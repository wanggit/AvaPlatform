// 审批中心页面：处理工具调用、预算超限、运行中断和交付物验收审批。
import { useEffect, useMemo, useState, type ReactNode } from 'react';
import {
  Alert,
  Badge,
  Button,
  Card,
  Col,
  Descriptions,
  Drawer,
  Input,
  Modal,
  Row,
  Select,
  Space,
  Statistic,
  Table,
  Tag,
  Typography,
} from 'antd';
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  ExclamationCircleOutlined,
  FileDoneOutlined,
  PauseCircleOutlined,
  SafetyCertificateOutlined,
  StopOutlined,
  WarningOutlined,
} from '@ant-design/icons';
import {
  type AuditEvent,
  type AuditSeverity,
  type Goal,
  type GoalRiskLevel,
} from '../types/domain';
import { api } from '../services/api';
import { usePlatformData } from '../services/platformData';

const { Title, Text, Paragraph } = Typography;
const { TextArea } = Input;

type ApprovalStatus = 'pending' | 'approved' | 'rejected' | 'expired' | 'needs_info';
type ApprovalType = 'tool_call' | 'budget' | 'shutdown' | 'artifact' | 'sensitive_operation';

interface ApprovalRequest {
  id: string;
  title: string;
  type: ApprovalType;
  status: ApprovalStatus;
  riskLevel: GoalRiskLevel;
  severity: AuditSeverity;
  requester: string;
  approver: string;
  createdAt: string;
  dueAt: string;
  goalId?: string;
  workItemId?: string;
  artifactId?: string;
  auditEventId?: string;
  summary: string;
  proposedAction: string;
  evidence: string[];
  decisionReason?: string;
}

const typeMeta: Record<ApprovalType, { label: string; color: string; icon: ReactNode }> = {
  tool_call: { label: '工具调用', color: 'purple', icon: <SafetyCertificateOutlined /> },
  budget: { label: '预算处理', color: 'magenta', icon: <WarningOutlined /> },
  shutdown: { label: '异常停机', color: 'volcano', icon: <StopOutlined /> },
  artifact: { label: '产物验收', color: 'blue', icon: <FileDoneOutlined /> },
  sensitive_operation: { label: '敏感操作', color: 'orange', icon: <ExclamationCircleOutlined /> },
};

const statusMeta: Record<ApprovalStatus, { label: string; color: string; badge: 'success' | 'processing' | 'warning' | 'error' | 'default' }> = {
  pending: { label: '待处理', color: 'gold', badge: 'warning' },
  approved: { label: '已通过', color: 'green', badge: 'success' },
  rejected: { label: '已拒绝', color: 'red', badge: 'error' },
  expired: { label: '已过期', color: 'default', badge: 'default' },
  needs_info: { label: '需补充', color: 'blue', badge: 'processing' },
};

const severityMeta: Record<AuditSeverity, { label: string; color: string }> = {
  low: { label: '低', color: 'blue' },
  medium: { label: '中', color: 'gold' },
  high: { label: '高', color: 'orange' },
  critical: { label: '严重', color: 'red' },
};

function payloadText(payload?: AuditEvent['payload']) {
  if (!payload) return '-';
  return Object.entries(payload).map(([key, value]) => `${key}: ${String(value)}`).join(' / ');
}

export default function ApprovalCenter() {
  const { source, goals, employees, auditEvents } = usePlatformData();
  const [approvals, setApprovals] = useState<ApprovalRequest[]>([]);
  const [statusFilter, setStatusFilter] = useState<ApprovalStatus | 'all'>('pending');
  const [typeFilter, setTypeFilter] = useState<ApprovalType | 'all'>('all');
  const [selectedApproval, setSelectedApproval] = useState<ApprovalRequest | null>(null);
  const [decisionOpen, setDecisionOpen] = useState(false);
  const [decisionAction, setDecisionAction] = useState<'approved' | 'rejected' | 'needs_info'>('approved');
  const [decisionReason, setDecisionReason] = useState('');

  const loadApprovals = async () => {
    const items = await api.get<Array<{
      id: string;
      approval_type: 'tool_call' | 'budget_overrun' | 'runtime_interruption' | 'artifact_acceptance' | 'sensitive_operation';
      status: ApprovalStatus;
      risk_level: 'low' | 'medium' | 'high' | 'critical';
      goal_run_id?: string;
      work_item_id?: string;
      artifact_id?: string;
      assignee: string;
      context: Record<string, unknown>;
      decision_reason?: string;
    }>>('/approvals');
    setApprovals(items.map((item) => {
      const context = item.context ?? {};
      const typeMap: Record<string, ApprovalType> = {
        tool_call: 'tool_call',
        budget_overrun: 'budget',
        runtime_interruption: 'shutdown',
        artifact_acceptance: 'artifact',
        sensitive_operation: 'sensitive_operation',
      };
      const riskMap: Record<string, GoalRiskLevel> = {
        low: 'L1',
        medium: 'L2',
        high: 'L3',
        critical: 'L4',
      };
      const isHermesEvaluationApproval = context.source === 'hermes_evaluation_run';
      const evidence = isHermesEvaluationApproval
        ? [
            item.id,
            context.template_version_id,
            context.profile_name,
            context.hermes_run_id,
          ].filter((value): value is string => typeof value === 'string' && value.length > 0)
        : [item.id];
      return {
        id: item.id,
        title: isHermesEvaluationApproval ? '岗位模板评测审批' : `${typeMeta[typeMap[item.approval_type]].label}审批`,
        type: typeMap[item.approval_type],
        status: item.status,
        riskLevel: riskMap[item.risk_level],
        severity: item.risk_level,
        requester: 'Platform',
        approver: item.assignee,
        createdAt: new Date().toLocaleString('zh-CN', { hour12: false }),
        dueAt: '-',
        goalId: item.goal_run_id,
        workItemId: item.work_item_id,
        artifactId: item.artifact_id,
        summary: isHermesEvaluationApproval
          ? `岗位模板评测「${String(context.template_role ?? context.template_version_id ?? '-')}」中的 Hermes Run ${String(context.hermes_run_id ?? '-')} 正在等待人工审批。`
          : JSON.stringify(context),
        proposedAction: isHermesEvaluationApproval
          ? '通过后允许本次 Hermes 待审批操作一次，并恢复评测；拒绝后阻止该操作。'
          : '等待审批人处理后继续或拒绝。',
        evidence,
        decisionReason: item.decision_reason,
      };
    }));
  };

  useEffect(() => {
    loadApprovals().catch(() => setApprovals([]));
  }, []);

  const goalById = useMemo(() => (
    goals.reduce<Record<string, Goal>>((acc, goal) => {
      acc[goal.id] = goal;
      return acc;
    }, {})
  ), [goals]);

  const employeeById = useMemo(() => (
    employees.reduce<Record<string, string>>((acc, employee) => {
      acc[employee.id] = employee.name;
      return acc;
    }, {})
  ), [employees]);

  const auditById = useMemo(() => (
    auditEvents.reduce<Record<string, AuditEvent>>((acc, event) => {
      acc[event.eventId] = event;
      return acc;
    }, {})
  ), [auditEvents]);

  const filteredApprovals = approvals
    .filter((approval) => statusFilter === 'all' || approval.status === statusFilter)
    .filter((approval) => typeFilter === 'all' || approval.type === typeFilter);

  const pendingCount = approvals.filter((approval) => approval.status === 'pending').length;
  const highRiskCount = approvals.filter((approval) => approval.status === 'pending' && ['high', 'critical'].includes(approval.severity)).length;
  const needsInfoCount = approvals.filter((approval) => approval.status === 'needs_info').length;
  const expiredCount = approvals.filter((approval) => approval.status === 'expired').length;

  const selectedGoal = selectedApproval?.goalId ? goalById[selectedApproval.goalId] : undefined;
  const selectedWorkItem = selectedGoal?.workItems.find((item) => item.id === selectedApproval?.workItemId);
  const selectedArtifact = selectedGoal?.artifacts.find((artifact) => artifact.id === selectedApproval?.artifactId);
  const selectedAudit = selectedApproval?.auditEventId ? auditById[selectedApproval.auditEventId] : undefined;

  const openDecision = (approval: ApprovalRequest, action: 'approved' | 'rejected' | 'needs_info') => {
    setSelectedApproval(approval);
    setDecisionAction(action);
    setDecisionReason('');
    setDecisionOpen(true);
  };

  const submitDecision = async () => {
    if (!selectedApproval) return;
    await api.post(`/approvals/${selectedApproval.id}/${decisionAction === 'approved' ? 'approve' : decisionAction === 'rejected' ? 'reject' : 'needs-info'}`, {
      decision_by: selectedApproval.approver,
      reason: decisionReason || statusMeta[decisionAction].label,
    });
    await loadApprovals();
    window.dispatchEvent(new Event('platform-approvals-updated'));
    setSelectedApproval(null);
    setDecisionOpen(false);
  };

  const columns = [
    {
      title: '审批事项',
      dataIndex: 'title',
      key: 'title',
      render: (title: string, row: ApprovalRequest) => (
        <Space orientation="vertical" size={2}>
          <a onClick={() => setSelectedApproval(row)}>{title}</a>
          <Text type="secondary">{row.summary}</Text>
        </Space>
      ),
    },
    {
      title: '类型',
      dataIndex: 'type',
      key: 'type',
      width: 110,
      render: (type: ApprovalType) => <Tag color={typeMeta[type].color} icon={typeMeta[type].icon}>{typeMeta[type].label}</Tag>,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: ApprovalStatus) => <Badge status={statusMeta[status].badge} text={statusMeta[status].label} />,
    },
    {
      title: '风险',
      dataIndex: 'riskLevel',
      key: 'riskLevel',
      width: 80,
      render: (risk: GoalRiskLevel) => <Tag>{risk}</Tag>,
    },
    {
      title: '严重度',
      dataIndex: 'severity',
      key: 'severity',
      width: 90,
      render: (severity: AuditSeverity) => <Tag color={severityMeta[severity].color}>{severityMeta[severity].label}</Tag>,
    },
    { title: '审批人', dataIndex: 'approver', key: 'approver', width: 120 },
    { title: '截止时间', dataIndex: 'dueAt', key: 'dueAt', width: 150 },
    {
      title: '操作',
      key: 'actions',
      width: 210,
      render: (_: unknown, row: ApprovalRequest) => row.status === 'pending' || row.status === 'needs_info' ? (
        <Space>
          <Button size="small" type="primary" icon={<CheckCircleOutlined />} onClick={() => openDecision(row, 'approved')}>通过</Button>
          <Button size="small" icon={<CloseCircleOutlined />} onClick={() => openDecision(row, 'rejected')}>拒绝</Button>
          <Button size="small" icon={<PauseCircleOutlined />} onClick={() => openDecision(row, 'needs_info')}>补充</Button>
        </Space>
      ) : <Text type="secondary">已处理</Text>,
    },
  ];

  return (
    <Space orientation="vertical" size={16} style={{ width: '100%' }}>
      <Space align="start" style={{ width: '100%', justifyContent: 'space-between' }}>
        <div>
          <Title level={4} style={{ margin: 0 }}>审批中心</Title>
          <Text type="secondary">统一处理工具调用、预算阻断、异常停机、产物验收和敏感操作复核。当前数据源：{source === 'backend' ? '后端接口' : '后端不可用'}。</Text>
        </div>
        <Space>
          <Select
            value={statusFilter}
            style={{ width: 140 }}
            onChange={setStatusFilter}
            options={[
              { label: '全部状态', value: 'all' },
              { label: '待处理', value: 'pending' },
              { label: '需补充', value: 'needs_info' },
              { label: '已通过', value: 'approved' },
              { label: '已拒绝', value: 'rejected' },
              { label: '已过期', value: 'expired' },
            ]}
          />
          <Select
            value={typeFilter}
            style={{ width: 150 }}
            onChange={setTypeFilter}
            options={[
              { label: '全部类型', value: 'all' },
              { label: '工具调用', value: 'tool_call' },
              { label: '预算处理', value: 'budget' },
              { label: '异常停机', value: 'shutdown' },
              { label: '产物验收', value: 'artifact' },
              { label: '敏感操作', value: 'sensitive_operation' },
            ]}
          />
        </Space>
      </Space>

      <Row gutter={16}>
        <Col span={6}><Card size="small"><Statistic title="待处理审批" value={pendingCount} prefix={<SafetyCertificateOutlined />} /></Card></Col>
        <Col span={6}><Card size="small"><Statistic title="高严重度待办" value={highRiskCount} prefix={<WarningOutlined />} styles={{ content: { color: highRiskCount ? '#fa8c16' : undefined } }} /></Card></Col>
        <Col span={6}><Card size="small"><Statistic title="需补充信息" value={needsInfoCount} prefix={<PauseCircleOutlined />} /></Card></Col>
        <Col span={6}><Card size="small"><Statistic title="已过期" value={expiredCount} prefix={<StopOutlined />} styles={{ content: { color: expiredCount ? '#f5222d' : undefined } }} /></Card></Col>
      </Row>

      <Alert
        showIcon
        type="info"
        title="目标详情页、工作项详情页和工具调用详情页只作为上下文入口；最终审批动作和审批记录统一归档在审批中心。"
      />

      <Table
        dataSource={filteredApprovals}
        columns={columns}
        rowKey="id"
        pagination={{ pageSize: 8 }}
      />

      <Drawer
        title={selectedApproval?.title}
        open={!!selectedApproval}
        onClose={() => setSelectedApproval(null)}
        size={620}
        extra={selectedApproval && (selectedApproval.status === 'pending' || selectedApproval.status === 'needs_info') ? (
          <Space>
            <Button type="primary" icon={<CheckCircleOutlined />} onClick={() => openDecision(selectedApproval, 'approved')}>通过</Button>
            <Button icon={<CloseCircleOutlined />} onClick={() => openDecision(selectedApproval, 'rejected')}>拒绝</Button>
            <Button icon={<PauseCircleOutlined />} onClick={() => openDecision(selectedApproval, 'needs_info')}>要求补充</Button>
          </Space>
        ) : null}
      >
        {selectedApproval && (
          <Space orientation="vertical" size={16} style={{ width: '100%' }}>
            <Descriptions bordered size="small" column={1}>
              <Descriptions.Item label="审批编号"><Text code>{selectedApproval.id}</Text></Descriptions.Item>
              <Descriptions.Item label="类型"><Tag color={typeMeta[selectedApproval.type].color}>{typeMeta[selectedApproval.type].label}</Tag></Descriptions.Item>
              <Descriptions.Item label="状态"><Tag color={statusMeta[selectedApproval.status].color}>{statusMeta[selectedApproval.status].label}</Tag></Descriptions.Item>
              <Descriptions.Item label="风险等级">{selectedApproval.riskLevel}</Descriptions.Item>
              <Descriptions.Item label="严重度"><Tag color={severityMeta[selectedApproval.severity].color}>{severityMeta[selectedApproval.severity].label}</Tag></Descriptions.Item>
              <Descriptions.Item label="发起方">{selectedApproval.requester}</Descriptions.Item>
              <Descriptions.Item label="审批人">{selectedApproval.approver}</Descriptions.Item>
              <Descriptions.Item label="创建时间">{selectedApproval.createdAt}</Descriptions.Item>
              <Descriptions.Item label="截止时间">{selectedApproval.dueAt}</Descriptions.Item>
            </Descriptions>

            <Card size="small" title="审批摘要">
              <Paragraph>{selectedApproval.summary}</Paragraph>
              <Text strong>拟执行动作</Text>
              <Paragraph style={{ marginTop: 8 }}>{selectedApproval.proposedAction}</Paragraph>
              {selectedApproval.decisionReason && (
                <Alert type="warning" showIcon title="处理说明" description={selectedApproval.decisionReason} />
              )}
            </Card>

            {selectedGoal && (
              <Card size="small" title="目标上下文">
                <Descriptions size="small" column={1}>
                  <Descriptions.Item label="目标运行"><Text code>{selectedGoal.id}</Text> {selectedGoal.title}</Descriptions.Item>
                  <Descriptions.Item label="根负责人">{selectedGoal.rootOwnerName}</Descriptions.Item>
                  <Descriptions.Item label="目标状态">{selectedGoal.status}</Descriptions.Item>
                  <Descriptions.Item label="预算">{selectedGoal.tokenUsed.toLocaleString()} / {selectedGoal.budgetTokens.toLocaleString()} 令牌</Descriptions.Item>
                  {selectedWorkItem && <Descriptions.Item label="工作项">{selectedWorkItem.title} / {selectedWorkItem.ownerEmployeeName}</Descriptions.Item>}
                  {selectedArtifact && <Descriptions.Item label="产物">{selectedArtifact.name} / {selectedArtifact.acceptanceStatus}</Descriptions.Item>}
                </Descriptions>
              </Card>
            )}

            {selectedAudit && (
              <Card size="small" title="审计上下文">
                <Descriptions size="small" column={1}>
                  <Descriptions.Item label="审计编号"><Text code>{selectedAudit.eventId}</Text></Descriptions.Item>
                  <Descriptions.Item label="事件类型">{selectedAudit.eventType}</Descriptions.Item>
                  <Descriptions.Item label="行为主体">{employeeById[selectedAudit.actorId] ?? selectedAudit.actorId}</Descriptions.Item>
                  <Descriptions.Item label="发生时间">{selectedAudit.occurredAt}</Descriptions.Item>
                  <Descriptions.Item label="载荷">{payloadText(selectedAudit.payload)}</Descriptions.Item>
                  <Descriptions.Item label="证据">{selectedAudit.evidenceRefs.map((item) => <Tag key={item}>{item}</Tag>)}</Descriptions.Item>
                </Descriptions>
              </Card>
            )}

            <Card size="small" title="证据">
              <Space wrap>
                {selectedApproval.evidence.map((item) => <Tag key={item}>{item}</Tag>)}
              </Space>
            </Card>
          </Space>
        )}
      </Drawer>

      <Modal
        title={statusMeta[decisionAction].label}
        open={decisionOpen}
        onCancel={() => setDecisionOpen(false)}
        onOk={submitDecision}
        okText="确认"
        cancelText="取消"
      >
        <Space orientation="vertical" size={12} style={{ width: '100%' }}>
          <Alert
            showIcon
            type={decisionAction === 'approved' ? 'success' : decisionAction === 'rejected' ? 'error' : 'warning'}
            title={selectedApproval?.title}
            description={decisionAction === 'approved'
              ? '通过后，平台会恢复对应工具调用、预算处理或产物流转。'
              : decisionAction === 'rejected'
                ? '拒绝后，平台会向 Hermes 返回受控拒绝结果，并记录审计事件。'
                : '要求补充信息后，审批保持未完成，相关运行继续暂停。'}
          />
          <TextArea
            rows={4}
            value={decisionReason}
            onChange={(event) => setDecisionReason(event.target.value)}
            placeholder="填写处理意见、补充要求或拒绝原因。"
          />
        </Space>
      </Modal>
    </Space>
  );
}

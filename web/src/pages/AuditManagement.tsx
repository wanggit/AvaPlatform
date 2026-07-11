// 审计规则页面：维护规则、查看事件、处理复核任务和敏感导出。
import { useEffect, useMemo, useState } from 'react';
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
  Modal,
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
  BellOutlined,
  DownloadOutlined,
  EditOutlined,
  ExperimentOutlined,
  EyeOutlined,
  FileSearchOutlined,
  PlusOutlined,
  SafetyCertificateOutlined,
} from '@ant-design/icons';
import {
  type AuditDisposition,
  type AuditEvent,
  type AuditEventType,
  type AuditRule,
  type AuditSeverity,
} from '../types/domain';
import { usePlatformData } from '../services/platformData';
import { api } from '../services/api';

const { Text, Title, Paragraph } = Typography;

const severityMap: Record<AuditSeverity, { label: string; color: string; badge: 'success' | 'processing' | 'warning' | 'error' }> = {
  low: { label: '低', color: 'blue', badge: 'success' },
  medium: { label: '中', color: 'gold', badge: 'processing' },
  high: { label: '高', color: 'orange', badge: 'warning' },
  critical: { label: '严重', color: 'red', badge: 'error' },
};

const eventTypeMap: Record<AuditEventType, { label: string; color: string }> = {
  tool_call: { label: '工具调用', color: 'purple' },
  red_line_triggered: { label: '红线触发', color: 'red' },
  approval_requested: { label: '审批请求', color: 'blue' },
  approval_decided: { label: '审批结果', color: 'cyan' },
  escalation_created: { label: '升级转人工', color: 'orange' },
  abnormal_shutdown: { label: '异常停机', color: 'volcano' },
  sensitive_operation: { label: '敏感操作', color: 'purple' },
  budget_blocked: { label: '预算阻断', color: 'magenta' },
  knowledge_preview: { label: '知识预览', color: 'green' },
  template_published: { label: '模板发布', color: 'geekblue' },
  skill_package_changed: { label: '技能变更', color: 'lime' },
  artifact_acceptance: { label: '交付物验收', color: 'blue' },
  notification_failed: { label: '通知失败', color: 'red' },
};

const dispositionMap: Record<AuditDisposition['status'], { label: string; color: string }> = {
  false_positive: { label: '误报', color: 'default' },
  confirmed: { label: '已确认', color: 'blue' },
  handled: { label: '已处理', color: 'green' },
  no_action_needed: { label: '无需处理', color: 'default' },
  escalated: { label: '升级处理', color: 'orange' },
};

const retentionLabel = (retention: AuditRule['retentionDays']) => retention === 'permanent' ? '永久' : `${retention} 天`;

const payloadText = (payload: AuditEvent['payload']) =>
  Object.entries(payload).map(([key, value]) => `${key}: ${String(value)}`).join(' / ');

export default function AuditManagement() {
  const {
    auditEvents: events,
    auditRules: rules,
    auditNotifications,
    employees,
    source,
    refresh,
  } = usePlatformData();
  const [selectedEvent, setSelectedEvent] = useState<AuditEvent | null>(null);
  const [editingRule, setEditingRule] = useState<AuditRule | null>(null);
  const [eventTypeFilter, setEventTypeFilter] = useState<AuditEventType | undefined>();
  const [severityFilter, setSeverityFilter] = useState<AuditSeverity | undefined>();
  const [detailOpen, setDetailOpen] = useState(false);
  const [dispositionOpen, setDispositionOpen] = useState(false);
  const [ruleOpen, setRuleOpen] = useState(false);
  const [testOpen, setTestOpen] = useState(false);
  const [exportOpen, setExportOpen] = useState(false);
  const [activeTab, setActiveTab] = useState('rules');
  const [testRuleId, setTestRuleId] = useState<string>('');
  const [testEventId, setTestEventId] = useState<string>(events[0]?.eventId ?? '');
  const [ruleForm] = Form.useForm();
  const [dispositionForm] = Form.useForm();
  const [exportForm] = Form.useForm();

  const employeeNameById = useMemo(() => {
    return employees.reduce<Record<string, string>>((acc, employee) => {
      acc[employee.id] = employee.name;
      return acc;
    }, {});
  }, [employees]);

  useEffect(() => {
    if (!testRuleId && rules[0]) setTestRuleId(rules[0].id);
  }, [rules, testRuleId]);

  useEffect(() => {
    if (!testEventId && events[0]) setTestEventId(events[0].eventId);
  }, [events, testEventId]);

  const filteredEvents = events
    .filter((event) => !eventTypeFilter || event.eventType === eventTypeFilter)
    .filter((event) => !severityFilter || event.severity === severityFilter);

  const reviewRequiredCount = events.filter((event) => event.reviewRequired && event.dispositions.length === 0).length;
  const kpiAffectingCount = events.filter((event) => event.kpiAffecting).length;
  const failedNotificationCount = auditNotifications.filter((record) => record.status === 'failed' || record.status === 'not_configured').length;

  const openRule = (rule?: AuditRule) => {
    setEditingRule(rule ?? null);
    ruleForm.setFieldsValue(rule ?? {
      name: '',
      description: '',
      eventTypes: ['sensitive_operation'],
      outputSeverity: 'medium',
      notify: true,
      receivers: ['管理员'],
      reviewRequired: true,
      kpiAffecting: false,
      retentionDays: 180,
      enabled: true,
    });
    setRuleOpen(true);
  };

  const saveRule = () => {
    ruleForm.validateFields().then(async (values) => {
      if (!editingRule) {
        await api.post('/audit/rules', {
          name: values.name,
          event_type: values.eventTypes[0],
          severity: values.outputSeverity,
          notification_targets: values.receivers ?? [],
          requires_review: values.reviewRequired ?? false,
          escalation_policy: values.notify ? '进入审批中心并通知接收人' : undefined,
          retention_days: values.retentionDays === 'permanent' ? 3650 : values.retentionDays,
        });
        await refresh();
        setActiveTab('rules');
        setRuleOpen(false);
        ruleForm.resetFields();
        return;
      }
      await api.patch(`/audit/rules/${editingRule.id}`, {
        name: values.name,
        event_type: values.eventTypes[0],
        severity: values.outputSeverity,
        notification_targets: values.receivers ?? [],
        requires_review: values.reviewRequired ?? false,
        escalation_policy: values.notify ? '进入审批中心并通知接收人' : undefined,
        retention_days: values.retentionDays === 'permanent' ? 3650 : values.retentionDays,
        enabled: values.enabled ?? true,
      });
      await refresh();
      setActiveTab('rules');
      setRuleOpen(false);
      setEditingRule(null);
      ruleForm.resetFields();
    });
  };

  const toggleRule = async (ruleId: string) => {
    const rule = rules.find((item) => item.id === ruleId);
    if (!rule) return;
    await api.patch(`/audit/rules/${ruleId}`, { enabled: !rule.enabled });
    await refresh();
  };

  const saveDisposition = () => {
    dispositionForm.validateFields().then(async (values) => {
      if (!selectedEvent) return;
      await api.post(`/audit/events/${selectedEvent.eventId}/dispositions`, {
        status: values.status,
        note: values.note,
        reviewer: '管理员',
      });
      await refresh();
      setSelectedEvent(null);
      setDispositionOpen(false);
      dispositionForm.resetFields();
    });
  };

  const handleExport = () => {
    exportForm.validateFields().then(async (values) => {
      await api.post('/audit/events', {
        event_type: 'sensitive_operation',
        payload: {
          subtype: values.unmasked ? 'audit_export_unmasked' : 'audit_export_masked',
          exportScope: values.scope,
          unmasked: Boolean(values.unmasked),
          reason: values.reason || 'masked export',
        },
      });
      await refresh();
      setExportOpen(false);
      exportForm.resetFields();
    });
  };

  const testedRule = rules.find((rule) => rule.id === testRuleId);
  const testedEvent = events.find((event) => event.eventId === testEventId);
  const testMatched = Boolean(testedRule && testedEvent && testedRule.enabled && testedRule.eventTypes.includes(testedEvent.eventType));

  const eventColumns = [
    {
      title: '事件',
      dataIndex: 'eventType',
      key: 'eventType',
      width: 150,
      render: (eventType: AuditEventType, row: AuditEvent) => (
        <Space orientation="vertical" size={0}>
          <Tag color={eventTypeMap[eventType].color}>{eventTypeMap[eventType].label}</Tag>
          <Text type="secondary" style={{ fontSize: 12 }}>{row.subtype ?? '-'}</Text>
        </Space>
      ),
    },
    {
      title: '严重级别',
      dataIndex: 'severity',
      key: 'severity',
      width: 100,
      render: (severity: AuditSeverity) => <Badge status={severityMap[severity].badge} text={severityMap[severity].label} />,
    },
    {
      title: '对象',
      key: 'subject',
      width: 190,
      render: (_: unknown, row: AuditEvent) => (
        <Space orientation="vertical" size={0}>
          <Text>{row.employeeId ? employeeNameById[row.employeeId] ?? row.employeeId : row.actorId}</Text>
          <Text type="secondary" style={{ fontSize: 12 }}>{row.department ?? row.resourceType ?? row.actorType}</Text>
        </Space>
      ),
    },
    {
      title: '摘要',
      dataIndex: 'payload',
      key: 'payload',
      ellipsis: true,
      render: (payload: AuditEvent['payload']) => <Text type="secondary">{payloadText(payload)}</Text>,
    },
    {
      title: '规则',
      dataIndex: 'ruleId',
      key: 'ruleId',
      width: 150,
      render: (ruleId: string, row: AuditEvent) => <Text code>{ruleId}@{row.ruleVersion}</Text>,
    },
    {
      title: '状态',
      key: 'state',
      width: 150,
      render: (_: unknown, row: AuditEvent) => (
        <Space size={4} wrap>
          {row.reviewRequired && <Tag color={row.dispositions.length ? 'green' : 'orange'}>{row.dispositions.length ? '已复核' : '需复核'}</Tag>}
          {row.kpiAffecting && <Tag color="red">绩效</Tag>}
        </Space>
      ),
    },
    { title: '发生时间', dataIndex: 'occurredAt', key: 'occurredAt', width: 155 },
    {
      title: '操作',
      key: 'action',
      width: 90,
      fixed: 'right' as const,
      render: (_: unknown, row: AuditEvent) => (
        <Button size="small" icon={<EyeOutlined />} onClick={() => { setSelectedEvent(row); setDetailOpen(true); }}>详情</Button>
      ),
    },
  ];

  const ruleColumns = [
    {
      title: '规则',
      dataIndex: 'name',
      key: 'name',
      width: 210,
      render: (name: string, row: AuditRule) => (
        <Space orientation="vertical" size={0}>
          <Text strong>{name}</Text>
          <Text type="secondary" style={{ fontSize: 12 }}>{row.version} / {row.updatedAt}</Text>
        </Space>
      ),
    },
    {
      title: '匹配事件',
      dataIndex: 'eventTypes',
      key: 'eventTypes',
      width: 260,
      render: (eventTypes: AuditEventType[]) => (
        <Space size={4} wrap>
          {eventTypes.map((eventType) => <Tag key={eventType} color={eventTypeMap[eventType].color}>{eventTypeMap[eventType].label}</Tag>)}
        </Space>
      ),
    },
    {
      title: '动作',
      key: 'actions',
      render: (_: unknown, row: AuditRule) => (
        <Space size={4} wrap>
          <Tag color={severityMap[row.outputSeverity].color}>严重级别：{severityMap[row.outputSeverity].label}</Tag>
          {row.notify && <Tag color="blue">通知</Tag>}
          {row.reviewRequired && <Tag color="orange">复核</Tag>}
          {row.kpiAffecting && <Tag color="red">绩效</Tag>}
          <Tag>保留 {retentionLabel(row.retentionDays)}</Tag>
        </Space>
      ),
    },
    {
      title: '启用',
      dataIndex: 'enabled',
      key: 'enabled',
      width: 80,
      render: (enabled: boolean) => enabled ? <Badge status="success" text="启用" /> : <Badge status="default" text="停用" />,
    },
    {
      title: '操作',
      key: 'action',
      width: 220,
      render: (_: unknown, row: AuditRule) => (
        <Space size="small">
          <Button size="small" icon={<EditOutlined />} onClick={() => openRule(row)}>编辑</Button>
          <Button size="small" onClick={() => toggleRule(row.id)}>{row.enabled ? '停用' : '启用'}</Button>
          <Button size="small" icon={<ExperimentOutlined />} onClick={() => { setTestRuleId(row.id); setTestOpen(true); }}>测试</Button>
        </Space>
      ),
    },
  ];

  const notificationColumns = [
    { title: '时间', dataIndex: 'createdAt', key: 'createdAt', width: 150 },
    { title: '事件', dataIndex: 'eventId', key: 'eventId', width: 160, render: (eventId: string) => <Text code>{eventId}</Text> },
    { title: '规则', dataIndex: 'ruleId', key: 'ruleId', width: 170, render: (ruleId: string) => <Text code>{ruleId}</Text> },
    { title: '渠道', dataIndex: 'channel', key: 'channel', width: 90, render: (channel: string) => <Tag>{channel}</Tag> },
    { title: '接收人', dataIndex: 'receiver', key: 'receiver', width: 130 },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 120,
      render: (status: string) => {
        const map: Record<string, { color: string; label: string }> = {
          sent: { color: 'green', label: '已发送' },
          pending: { color: 'blue', label: '待发送' },
          failed: { color: 'red', label: '失败' },
          not_configured: { color: 'gold', label: '未接入' },
        };
        return <Tag color={map[status].color}>{map[status].label}</Tag>;
      },
    },
    { title: '原因', dataIndex: 'failureReason', key: 'failureReason', render: (reason?: string) => reason ?? <Text type="secondary">-</Text> },
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 16, marginBottom: 16 }}>
        <div>
          <Title level={4} style={{ marginBottom: 4 }}>审计规则</Title>
          <Text type="secondary">统一管理审计事件、审计规则、通知记录和保留策略。当前数据源：{source === 'backend' ? '后端接口' : '后端不可用'}。</Text>
        </div>
        <Space>
          <Button icon={<DownloadOutlined />} onClick={() => setExportOpen(true)}>导出审计日志</Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => openRule()}>新增规则</Button>
        </Space>
      </div>

      <Alert
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
        title="审计事件是只追加记录。管理员不能修改事件主体，只能追加处理结论；规则测试不会写事件、不会发通知、不会改变绩效。"
      />

      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={24} sm={12} lg={6}>
          <Card size="small"><Statistic title="审计事件" value={events.length} prefix={<SafetyCertificateOutlined />} /></Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card size="small"><Statistic title="待复核" value={reviewRequiredCount} prefix={<FileSearchOutlined />} styles={{ content: { color: reviewRequiredCount > 0 ? '#fa8c16' : undefined } }} /></Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card size="small"><Statistic title="影响绩效" value={kpiAffectingCount} prefix={<AuditIcon />} styles={{ content: { color: kpiAffectingCount > 0 ? '#f5222d' : undefined } }} /></Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card size="small"><Statistic title="通知异常" value={failedNotificationCount} prefix={<BellOutlined />} styles={{ content: { color: failedNotificationCount > 0 ? '#fa8c16' : undefined } }} /></Card>
        </Col>
      </Row>

      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        items={[
          {
            key: 'events',
            label: '审计事件',
            children: (
              <>
                <Row gutter={16} style={{ marginBottom: 16 }}>
                  <Col xs={24} sm={6}>
                    <Select
                      placeholder="事件类型"
                      allowClear
                      value={eventTypeFilter}
                      onChange={setEventTypeFilter}
                      style={{ width: '100%' }}
                      options={Object.entries(eventTypeMap).map(([value, meta]) => ({ label: meta.label, value }))}
                    />
                  </Col>
                  <Col xs={24} sm={6}>
                    <Select
                      placeholder="严重级别"
                      allowClear
                      value={severityFilter}
                      onChange={setSeverityFilter}
                      style={{ width: '100%' }}
                      options={Object.entries(severityMap).map(([value, meta]) => ({ label: meta.label, value }))}
                    />
                  </Col>
                </Row>
                <Table
                  dataSource={filteredEvents}
                  columns={eventColumns}
                  rowKey="eventId"
                  size="middle"
                  scroll={{ x: 1250 }}
                  pagination={{ pageSize: 8 }}
                />
              </>
            ),
          },
          {
            key: 'rules',
            label: '审计规则',
            children: (
              <Table dataSource={rules} columns={ruleColumns} rowKey="id" size="middle" pagination={false} />
            ),
          },
          {
            key: 'notifications',
            label: '通知记录',
            children: (
              <Table dataSource={auditNotifications} columns={notificationColumns} rowKey="id" size="middle" pagination={false} />
            ),
          },
          {
            key: 'retention',
            label: '保留策略',
            children: (
              <Row gutter={[16, 16]}>
                <Col xs={24} md={8}>
                  <Card title="默认保留" size="small">
                    <Title level={3} style={{ margin: 0 }}>180 天</Title>
                    <Paragraph type="secondary">普通审计事件默认保留期限。</Paragraph>
                  </Card>
                </Col>
                <Col xs={24} md={8}>
                  <Card title="高危事件" size="small">
                    <Title level={3} style={{ margin: 0 }}>365 天</Title>
                    <Paragraph type="secondary">红线、高危敏感操作、可归因异常停机、预算阻断。</Paragraph>
                  </Card>
                </Col>
                <Col xs={24} md={8}>
                  <Card title="规则覆盖" size="small">
                    <Space size={4} wrap>
                      {[90, 180, 365, 'permanent'].map((retention) => <Tag key={retention}>{retentionLabel(retention as AuditRule['retentionDays'])}</Tag>)}
                    </Space>
                    <Paragraph type="secondary" style={{ marginTop: 12 }}>最小可用版本只允许从预设保留期限中选择。</Paragraph>
                  </Card>
                </Col>
                <Col span={24}>
                  <Alert type="warning" showIcon title="导出审计日志本身是敏感操作。未脱敏导出需要管理员权限、二次确认和理由。" />
                </Col>
              </Row>
            ),
          },
        ]}
      />

      <Modal
        title="审计事件详情"
        open={detailOpen}
        onCancel={() => setDetailOpen(false)}
        footer={[
          <Button key="close" onClick={() => setDetailOpen(false)}>关闭</Button>,
          <Button key="disposition" type="primary" onClick={() => setDispositionOpen(true)}>追加处理结论</Button>,
        ]}
        width={820}
      >
        {selectedEvent && (
          <Space orientation="vertical" size={16} style={{ width: '100%' }}>
            <Descriptions bordered size="small" column={2}>
              <Descriptions.Item label="事件编号"><Text code>{selectedEvent.eventId}</Text></Descriptions.Item>
              <Descriptions.Item label="事件类型"><Tag color={eventTypeMap[selectedEvent.eventType].color}>{eventTypeMap[selectedEvent.eventType].label}</Tag></Descriptions.Item>
              <Descriptions.Item label="严重级别"><Tag color={severityMap[selectedEvent.severity].color}>{severityMap[selectedEvent.severity].label}</Tag></Descriptions.Item>
              <Descriptions.Item label="发生时间">{selectedEvent.occurredAt}</Descriptions.Item>
              <Descriptions.Item label="操作者">{selectedEvent.actorType} / {selectedEvent.actorId}</Descriptions.Item>
              <Descriptions.Item label="员工">{selectedEvent.employeeId ? employeeNameById[selectedEvent.employeeId] ?? selectedEvent.employeeId : '-'}</Descriptions.Item>
              <Descriptions.Item label="资源">{selectedEvent.resourceType ?? '-'} / {selectedEvent.resourceId ?? '-'}</Descriptions.Item>
              <Descriptions.Item label="规则"><Text code>{selectedEvent.ruleId}@{selectedEvent.ruleVersion}</Text></Descriptions.Item>
              <Descriptions.Item label="绩效">{selectedEvent.kpiAffecting ? <Tag color="red">计入</Tag> : <Tag>不计入</Tag>}</Descriptions.Item>
              <Descriptions.Item label="复核">{selectedEvent.reviewRequired ? <Tag color="orange">需要</Tag> : <Tag>不需要</Tag>}</Descriptions.Item>
            </Descriptions>

            <Card title="原始载荷" size="small">
              <pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>{JSON.stringify(selectedEvent.payload, null, 2)}</pre>
            </Card>

            <Card title="证据引用" size="small">
              <Space size={4} wrap>
                {selectedEvent.evidenceRefs.map((ref) => <Tag key={ref}>{ref}</Tag>)}
              </Space>
            </Card>

            <Card title="处理结论" size="small">
              {selectedEvent.dispositions.length === 0 ? (
                <Text type="secondary">暂无处理结论</Text>
              ) : (
                <Space orientation="vertical" style={{ width: '100%' }}>
                  {selectedEvent.dispositions.map((disposition) => (
                    <div key={disposition.id} style={{ paddingBottom: 8, borderBottom: '1px solid #f0f0f0' }}>
                      <Space>
                        <Tag color={dispositionMap[disposition.status].color}>{dispositionMap[disposition.status].label}</Tag>
                        <Text>{disposition.reviewer}</Text>
                        <Text type="secondary">{disposition.createdAt}</Text>
                      </Space>
                      <div style={{ marginTop: 4 }}>{disposition.note}</div>
                    </div>
                  ))}
                </Space>
              )}
            </Card>
          </Space>
        )}
      </Modal>

      <Modal
        title="追加处理结论"
        open={dispositionOpen}
        onCancel={() => { setDispositionOpen(false); dispositionForm.resetFields(); }}
        onOk={saveDisposition}
        destroyOnHidden
      >
        <Form form={dispositionForm} layout="vertical">
          <Form.Item label="处理结果" name="status" rules={[{ required: true }]}>
            <Select options={Object.entries(dispositionMap).map(([value, meta]) => ({ label: meta.label, value }))} />
          </Form.Item>
          <Form.Item label="说明" name="note" rules={[{ required: true }]}>
            <Input.TextArea rows={3} placeholder="追加复核或处理说明，不会修改原始审计事件。" />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title={editingRule ? '编辑审计规则' : '新增审计规则'}
        open={ruleOpen}
        onCancel={() => { setRuleOpen(false); setEditingRule(null); ruleForm.resetFields(); }}
        onOk={saveRule}
        width={760}
        destroyOnHidden
      >
        <Form form={ruleForm} layout="vertical">
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item label="规则名称" name="name" rules={[{ required: true }]}>
                <Input />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="输出严重级别" name="outputSeverity" rules={[{ required: true }]}>
                <Select options={Object.entries(severityMap).map(([value, meta]) => ({ label: meta.label, value }))} />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item label="说明" name="description">
            <Input.TextArea rows={2} />
          </Form.Item>
          <Form.Item label="匹配事件类型" name="eventTypes" rules={[{ required: true }]}>
            <Select mode="multiple" options={Object.entries(eventTypeMap).map(([value, meta]) => ({ label: meta.label, value }))} />
          </Form.Item>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item label="通知对象" name="receivers">
                <Select mode="tags" tokenSeparators={[',']} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="保留期限" name="retentionDays" rules={[{ required: true }]}>
                <Select options={[
                  { label: '90 天', value: 90 },
                  { label: '180 天', value: 180 },
                  { label: '365 天', value: 365 },
                  { label: '永久', value: 'permanent' },
                ]} />
              </Form.Item>
            </Col>
          </Row>
          <Row gutter={16}>
            <Col span={6}><Form.Item name="notify" valuePropName="checked"><Checkbox>通知</Checkbox></Form.Item></Col>
            <Col span={6}><Form.Item name="reviewRequired" valuePropName="checked"><Checkbox>需要复核</Checkbox></Form.Item></Col>
            <Col span={6}><Form.Item name="kpiAffecting" valuePropName="checked"><Checkbox>计入绩效</Checkbox></Form.Item></Col>
            <Col span={6}><Form.Item name="enabled" valuePropName="checked"><Checkbox>启用</Checkbox></Form.Item></Col>
          </Row>
          <Alert type="info" showIcon title="最小可用版本只支持明确字段条件和固定动作，不支持脚本、外部调用或直接执行停员工等运行时动作。" />
        </Form>
      </Modal>

      <Modal
        title="测试规则匹配"
        open={testOpen}
        onCancel={() => setTestOpen(false)}
        footer={<Button type="primary" onClick={() => setTestOpen(false)}>关闭</Button>}
        width={760}
      >
        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col span={12}>
            <Select
              value={testRuleId}
              onChange={setTestRuleId}
              style={{ width: '100%' }}
              options={rules.map((rule) => ({ label: rule.name, value: rule.id }))}
            />
          </Col>
          <Col span={12}>
            <Select
              value={testEventId}
              onChange={setTestEventId}
              style={{ width: '100%' }}
              options={events.map((event) => ({ label: `${event.eventId} / ${eventTypeMap[event.eventType].label}`, value: event.eventId }))}
            />
          </Col>
        </Row>
        {testedRule && testedEvent && (
          <Descriptions bordered size="small" column={1}>
            <Descriptions.Item label="匹配结果">{testMatched ? <Tag color="green">命中</Tag> : <Tag color="default">未命中</Tag>}</Descriptions.Item>
            <Descriptions.Item label="命中条件">
              <Space size={4} wrap>
                {testedRule.conditionSummary.map((condition) => <Tag key={condition}>{condition}</Tag>)}
              </Space>
            </Descriptions.Item>
            <Descriptions.Item label="输出严重级别"><Tag color={severityMap[testedRule.outputSeverity].color}>{severityMap[testedRule.outputSeverity].label}</Tag></Descriptions.Item>
            <Descriptions.Item label="通知">{testedRule.notify ? testedRule.receivers.join('、') : '不通知'}</Descriptions.Item>
            <Descriptions.Item label="复核">{testedRule.reviewRequired ? '需要' : '不需要'}</Descriptions.Item>
            <Descriptions.Item label="绩效">{testedRule.kpiAffecting ? '计入' : '不计入'}</Descriptions.Item>
            <Descriptions.Item label="保留期限">{retentionLabel(testedRule.retentionDays)}</Descriptions.Item>
          </Descriptions>
        )}
      </Modal>

      <Modal
        title="导出审计日志"
        open={exportOpen}
        onCancel={() => { setExportOpen(false); exportForm.resetFields(); }}
        onOk={handleExport}
        width={620}
        destroyOnHidden
      >
        <Form form={exportForm} layout="vertical" initialValues={{ scope: 'current_filter', unmasked: false }}>
          <Form.Item label="导出范围" name="scope" rules={[{ required: true }]}>
            <Select options={[
              { label: '当前筛选结果', value: 'current_filter' },
              { label: '最近 7 天', value: 'last_7_days' },
              { label: '全部高危事件', value: 'high_risk_events' },
            ]} />
          </Form.Item>
          <Form.Item name="unmasked" valuePropName="checked">
            <Checkbox>导出未脱敏证据</Checkbox>
          </Form.Item>
          <Form.Item label="导出理由" name="reason">
            <Input.TextArea rows={3} placeholder="未脱敏导出必须填写理由；本操作会生成敏感操作审计事件。" />
          </Form.Item>
          <Alert type="warning" showIcon title="导出审计日志本身会生成敏感操作审计事件。当前版本会记录导出请求和理由，文件下载由后续报表服务承接。" />
        </Form>
      </Modal>
    </div>
  );
}

function AuditIcon() {
  return <SafetyCertificateOutlined />;
}

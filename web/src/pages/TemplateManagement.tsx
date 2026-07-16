// 岗位模板页面：维护数字员工模板、模型、技能、工具、知识源和评测状态。
import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Alert,
  Button,
  Card,
  Col,
  Descriptions,
  Divider,
  Form,
  Input,
  InputNumber,
  Modal,
  Popconfirm,
  Progress,
  Row,
  Select,
  Space,
  Switch,
  Table,
  Tag,
  Typography,
  message,
} from 'antd';
import {
  CheckCircleOutlined,
  DeleteOutlined,
  EditOutlined,
  ExperimentOutlined,
  EyeOutlined,
  MinusCircleOutlined,
  PlusOutlined,
  SendOutlined,
} from '@ant-design/icons';
import {
  gradeColorMap,
  type BusinessOutcomeMetricBinding,
  type GoalRiskLevel,
  type JobTemplate,
  type TemplateEvaluation,
  type TemplateEvaluationRun as TemplateEvaluationRunRecord,
} from '../types/domain';
import { api, mapTemplateEvaluationRun, toDepartmentId, type BackendTemplateEvaluationRun } from '../services/api';
import { usePlatformData } from '../services/platformData';

const { Title, Text, Paragraph } = Typography;

const riskOptions: { label: string; value: GoalRiskLevel }[] = [
  { label: 'L1 低风险，只读和草稿', value: 'L1' },
  { label: 'L2 可逆业务动作', value: 'L2' },
  { label: 'L3 需要审批的业务动作', value: 'L3' },
  { label: 'L4 只准备决策材料', value: 'L4' },
];

const evaluationMap: Record<TemplateEvaluation['status'], { label: string; color: string }> = {
  not_run: { label: '未评测', color: 'default' },
  passed: { label: '通过', color: 'green' },
  failed: { label: '失败', color: 'red' },
  warning: { label: '有风险', color: 'orange' },
};

const metricSourceOptions = [
  { label: '平台原生', value: 'platform_native' },
  { label: '工具业务系统', value: 'tool_business_system' },
  { label: '人工录入或导入', value: 'manual_or_imported' },
];

const pilotScenarioOptions = [
  { label: '内部验证', value: 'internal_validation' },
  { label: '部门试点', value: 'department_pilot' },
  { label: '生产试点', value: 'production_pilot' },
];

const platformMetricOptions = [
  { label: '目标运行完成率', value: '平台自动计算：目标运行完成率' },
  { label: '交付物首次验收通过率', value: '平台自动计算：交付物首次验收通过率' },
  { label: '交付物返工率', value: '平台自动计算：交付物返工率' },
  { label: '平均执行周期', value: '平台自动计算：平均执行周期' },
  { label: '令牌流水成本', value: '平台自动计算：令牌流水成本' },
];

const toolMetricOptions = [
  { label: '工单系统：关闭时间 / 服务等级状态', value: '工具网关回写：工单系统关闭时间与服务等级状态' },
  { label: '客户关系系统：商机阶段 / 方案采纳', value: '工具网关回写：客户关系系统商机阶段与方案采纳状态' },
  { label: '邮件系统：草稿采纳状态', value: '工具网关回写：邮件草稿采纳状态' },
];

const manualMetricOptions = [
  { label: '主管每周手动录入', value: '主管每周手动录入' },
  { label: 'CSV 月度导入', value: 'CSV 月度导入' },
  { label: '会议评审后录入', value: '会议评审后录入' },
];

const riskLabelMap = {
  low: '低',
  medium: '中',
  high: '高',
};

const draftMetricId = (index: number) => globalThis.crypto?.randomUUID?.() ?? `metric-draft-${index}`;

const defaultValues = {
  grade: 'Staff',
  status: 'draft',
  version: '0.1.0',
  defaultGoalBudgetTokens: 200000,
  maxGoalRiskLevel: 'L2',
  skills: [],
  knowledgeSources: [],
  toolsets: [],
  redLines: [''],
  metricBindings: [],
  isPilot: false,
};

export default function TemplateManagement() {
  const { templates, models, skills, tools, knowledgeSources, departments, refreshTemplates, source } = usePlatformData();
  const [messageApi, contextHolder] = message.useMessage();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [detailOpen, setDetailOpen] = useState(false);
  const [selectedTemplate, setSelectedTemplate] = useState<JobTemplate | null>(null);
  const [editingTemplate, setEditingTemplate] = useState<JobTemplate | null>(null);
  const [latestEvaluationRuns, setLatestEvaluationRuns] = useState<Record<string, TemplateEvaluationRunRecord | undefined>>({});
  const [form] = Form.useForm();

  const modelNameById = useMemo(() => (
    models.reduce<Record<string, string>>((acc, model) => {
      acc[model.id] = model.name;
      return acc;
    }, {})
  ), [models]);

  const toolNameById = useMemo(() => (
    tools.reduce<Record<string, string>>((acc, tool) => {
      acc[tool.toolId] = tool.displayName;
      return acc;
    }, {})
  ), [tools]);

  const modelOptions = models
    .filter((model) => model.type === 'llm' && model.status === 'active')
    .map((model) => ({ label: `${model.name} / 上下文 ${model.contextWindow.toLocaleString()}`, value: model.id }));

  const skillOptions = skills
    .filter((skill) => skill.status === 'published')
    .map((skill) => ({ label: `${skill.displayName} v${skill.version}`, value: skill.id }));

  const knowledgeOptions = knowledgeSources
    .filter((source) => source.status === 'active' && source.syncStatus === 'active')
    .map((source) => ({ label: `${source.name} / ${source.externalDatasetName}`, value: source.id }));

  const toolOptions = tools
    .filter((tool) => tool.status === 'published')
    .map((tool) => ({
      label: `${tool.displayName} / 平台管理 / ${riskLabelMap[tool.riskLevel]}风险`,
      value: tool.toolId,
    }));

  useEffect(() => {
    if (!templates.length) {
      setLatestEvaluationRuns({});
      return;
    }
    let cancelled = false;
    Promise.all(
      templates.map(async (template) => {
        try {
          const runs = await api.get<BackendTemplateEvaluationRun[]>(`/job-template-versions/${template.id}/evaluation/runs?limit=1`);
          return [template.id, runs[0] ? mapTemplateEvaluationRun(runs[0]) : undefined] as const;
        } catch {
          return [template.id, undefined] as const;
        }
      }),
    ).then((entries) => {
      if (cancelled) return;
      setLatestEvaluationRuns(Object.fromEntries(entries));
    });
    return () => {
      cancelled = true;
    };
  }, [templates]);

  const openEvaluation = (template: JobTemplate) => {
    const latestRun = latestEvaluationRuns[template.id];
    if (latestRun && ['queued', 'running', 'waiting_for_approval'].includes(latestRun.status)) {
      navigate(`/templates/${template.id}/evaluation-runs/${latestRun.id}`);
      return;
    }
    navigate(`/templates/${template.id}/evaluation`);
  };

  const openCreate = () => {
    setEditingTemplate(null);
    form.resetFields();
    form.setFieldsValue({ ...defaultValues, model: modelOptions[0]?.value });
    setOpen(true);
  };

  const openEdit = (template: JobTemplate) => {
    setEditingTemplate(template);
    form.resetFields();
    form.setFieldsValue({ ...template, department: template.departmentId ?? toDepartmentId(template.department) });
    setOpen(true);
  };

  const saveTemplate = () => {
    form.validateFields().then(async (values) => {
      const metricBindings = (values.metricBindings ?? []).map((metric: BusinessOutcomeMetricBinding, index: number) => ({
        ...metric,
        id: metric.id ?? draftMetricId(index),
      }));
      const payload = {
        role: values.role,
        version: values.version,
        grade: values.grade,
        department_id: values.department,
        model_config_id: values.model,
        description: values.description,
        system_prompt: values.systemPrompt,
        max_goal_risk_level: values.maxGoalRiskLevel,
        default_goal_budget_tokens: values.defaultGoalBudgetTokens,
        skills: values.skills ?? [],
        tools: values.toolsets ?? [],
        knowledge_sources: values.knowledgeSources ?? [],
        red_lines: values.redLines ?? [],
        metric_bindings: metricBindings,
        is_pilot: values.isPilot ?? false,
        pilot_scenario: values.pilotScenario,
      };
      if (editingTemplate) {
        await api.patch(`/job-template-versions/${editingTemplate.id}`, payload);
        messageApi.success('岗位模板已保存到后端。');
      } else {
        await api.post('/job-template-versions', payload);
        messageApi.success('岗位模板草稿已创建到后端。');
      }
      await refreshTemplates();
      setOpen(false);
      setEditingTemplate(null);
      form.resetFields();
    }).catch((err) => {
      if (err?.errorFields) return;
      messageApi.error(err instanceof Error ? err.message : '保存岗位模板失败');
    });
  };

  const publishTemplate = async (templateId: string) => {
    try {
      await api.post(`/job-template-versions/${templateId}/publish`);
      await refreshTemplates();
      messageApi.success('岗位模板已发布。');
    } catch (err) {
      messageApi.error(err instanceof Error ? err.message : '发布岗位模板失败');
    }
  };

  const deleteTemplate = async (templateId: string) => {
    try {
      await api.delete(`/job-template-versions/${templateId}`);
      await refreshTemplates();
      messageApi.success('岗位模板已删除。');
    } catch (err) {
      messageApi.error(err instanceof Error ? err.message : '删除岗位模板失败');
    }
  };

  const columns = [
    {
      title: '岗位模板版本',
      dataIndex: 'role',
      key: 'role',
      render: (role: string, row: JobTemplate) => (
        <Space orientation="vertical" size={0}>
          <Space>
            <a onClick={() => { setSelectedTemplate(row); setDetailOpen(true); }}>{role}</a>
            <Tag color={gradeColorMap[row.grade]}>{row.grade}</Tag>
            {row.isPilot && <Tag color="blue">试点</Tag>}
          </Space>
          <Text type="secondary" style={{ fontSize: 12 }}>v{row.version} / {row.department}</Text>
        </Space>
      ),
    },
    { title: '可承接最高风险', dataIndex: 'maxGoalRiskLevel', key: 'maxGoalRiskLevel', width: 130, render: (value: GoalRiskLevel) => <Tag>{value}</Tag> },
    { title: '默认单目标预算', dataIndex: 'defaultGoalBudgetTokens', key: 'defaultGoalBudgetTokens', width: 140, render: (value: number) => `${(value / 1000).toFixed(0)}K` },
    {
      title: '模型',
      dataIndex: 'model',
      key: 'model',
      width: 180,
      render: (model: string) => <Text code>{modelNameById[model] ?? model}</Text>,
    },
    {
      title: '模板评测',
      dataIndex: 'evaluation',
      key: 'evaluation',
      width: 180,
      render: (evaluation: TemplateEvaluation, row: JobTemplate) => {
        const latestRun = latestEvaluationRuns[row.id];
        const isActiveRun = latestRun && ['queued', 'running', 'waiting_for_approval'].includes(latestRun.status);
        const runLabel = latestRun?.status === 'waiting_for_approval'
          ? '等待审批'
          : latestRun?.status === 'running'
            ? '评测运行中'
            : latestRun?.status === 'queued'
              ? '评测排队中'
              : undefined;
        return (
        <Space orientation="vertical" size={0}>
          <Tag color={evaluationMap[evaluation.status].color}>{evaluationMap[evaluation.status].label}</Tag>
          {isActiveRun && <Tag color="processing">{runLabel}</Tag>}
          {evaluation.status !== 'not_run' && <Text type="secondary" style={{ fontSize: 12 }}>得分 {evaluation.score} / {evaluation.passedCaseCount}/{evaluation.caseCount}</Text>}
        </Space>
        );
      },
    },
    { title: '业务指标', dataIndex: 'metricBindings', key: 'metricBindings', width: 110, render: (items: BusinessOutcomeMetricBinding[]) => <Tag color="purple">{items.length} 个</Tag> },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 90,
      render: (status: JobTemplate['status']) => status === 'published' ? <Tag color="green">已发布</Tag> : <Tag>草稿</Tag>,
    },
    {
      title: '操作',
      key: 'actions',
      width: 280,
      render: (_: unknown, row: JobTemplate) => (
        <Space>
          <Button size="small" icon={<EyeOutlined />} onClick={() => { setSelectedTemplate(row); setDetailOpen(true); }}>详情</Button>
          <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(row)}>编辑</Button>
          <Button size="small" icon={<ExperimentOutlined />} onClick={() => openEvaluation(row)}>
            {latestEvaluationRuns[row.id] && ['queued', 'running', 'waiting_for_approval'].includes(latestEvaluationRuns[row.id]!.status) ? '查看评测' : '评测'}
          </Button>
          {row.status === 'draft' && <Button size="small" type="primary" icon={<SendOutlined />} onClick={() => publishTemplate(row.id)}>发布</Button>}
          <Popconfirm
            title="确认删除"
            description={`确定要删除岗位模板「${row.role} v${row.version}」吗？此操作不可恢复。`}
            onConfirm={() => deleteTemplate(row.id)}
            okText="确认删除"
            cancelText="取消"
            okButtonProps={{ danger: true }}
          >
            <Button size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <>
      {contextHolder}
      <Space align="start" style={{ width: '100%', marginBottom: 16, justifyContent: 'space-between' }}>
        <Space orientation="vertical" size={2}>
          <Title level={4} style={{ margin: 0 }}>岗位模板</Title>
          <Text type="secondary">维护岗位模板版本、系统提示词、技能、知识源、工具白名单、目标预算和业务结果指标。当前数据源：{source === 'backend' ? '后端接口' : '后端不可用'}。</Text>
        </Space>
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>新建岗位模板</Button>
      </Space>

      <Alert
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
        title="岗位模板发布前应查看最近一次模板评测。L4 模板只能准备决策材料，最终业务决策必须由人完成。"
      />

      <Table dataSource={templates} columns={columns} rowKey="id" pagination={false} />

      <Modal
        title={editingTemplate ? '编辑岗位模板版本' : '新建岗位模板'}
        open={open}
        onOk={saveTemplate}
        onCancel={() => { setOpen(false); setEditingTemplate(null); form.resetFields(); }}
        width={1120}
        destroyOnHidden
      >
        <Form form={form} layout="vertical">
          <Row gutter={12}>
            <Col span={16}>
              <Card size="small" title="基础信息">
                <Row gutter={12}>
                  <Col span={12}>
                    <Form.Item label="岗位名称" name="role" rules={[{ required: true }]}>
                      <Input />
                    </Form.Item>
                  </Col>
                  <Col span={12}>
                    <Form.Item label="版本" name="version" rules={[{ required: true }]}>
                      <Input />
                    </Form.Item>
                  </Col>
                </Row>
                <Row gutter={12}>
                  <Col span={12}>
                    <Form.Item label="职级" name="grade" rules={[{ required: true }]}>
                      <Select options={['Staff', 'Lead', 'Manager', 'Director'].map((grade) => ({ label: grade, value: grade }))} />
                    </Form.Item>
                  </Col>
                  <Col span={12}>
                    <Form.Item label="默认部门" name="department" rules={[{ required: true }]}>
                      <Select options={departments.map((department) => ({ label: department.name, value: department.id }))} />
                    </Form.Item>
                  </Col>
                </Row>
                <Form.Item label="岗位说明" name="description" rules={[{ required: true }]} style={{ marginBottom: 0 }}>
                  <Input.TextArea rows={3} />
                </Form.Item>
              </Card>
            </Col>
            <Col span={8}>
              <Card size="small" title="执行边界">
                <Form.Item
                  label="可承接最高风险等级"
                  name="maxGoalRiskLevel"
                  rules={[{ required: true }]}
                  tooltip="该模板创建的数字员工最多可以承接到这个风险等级。L4 只能准备决策材料，不能替人决策。"
                >
                  <Select options={riskOptions} />
                </Form.Item>
                <Form.Item
                  label="默认单目标预算"
                  name="defaultGoalBudgetTokens"
                  rules={[{ required: true }]}
                  tooltip="使用该模板创建目标运行时默认带出的令牌预算；不是员工配额，也不是模板配额。"
                >
                  <InputNumber min={1} step={10000} style={{ width: '100%' }} />
                </Form.Item>
                <Row gutter={12}>
                  <Col span={9}>
                    <Form.Item label="试点模板" name="isPilot" valuePropName="checked" style={{ marginBottom: 0 }}>
                      <Switch checkedChildren="是" unCheckedChildren="否" />
                    </Form.Item>
                  </Col>
                  <Col span={15}>
                    <Form.Item
                      noStyle
                      shouldUpdate={(prev, current) => prev.isPilot !== current.isPilot}
                    >
                      {({ getFieldValue }) => (
                        getFieldValue('isPilot') ? (
                          <Form.Item label="试点类型" name="pilotScenario" rules={[{ required: true }]} style={{ marginBottom: 0 }}>
                            <Select options={pilotScenarioOptions} />
                          </Form.Item>
                        ) : null
                      )}
                    </Form.Item>
                  </Col>
                </Row>
              </Card>
            </Col>
          </Row>

          <Card size="small" title="模型与人设" style={{ marginTop: 12 }}>
            <Form.Item label="大语言模型" name="model" rules={[{ required: true }]}>
              <Select options={modelOptions} />
            </Form.Item>
            <Form.Item label="系统提示词（人设）" name="systemPrompt" rules={[{ required: true }]}>
              <Input.TextArea
                rows={5}
                placeholder="说明数字员工的岗位身份、工作目标、可使用能力、输出格式、协作边界和禁止行为。需要明确哪些动作必须走审批、哪些知识源和工具可用于完成工作、输出时需要包含哪些证据和下一步建议。"
              />
            </Form.Item>
          </Card>

          <Card size="small" title="能力绑定" style={{ marginTop: 12 }}>
            <Row gutter={16}>
              <Col span={8}>
                <Form.Item label="绑定技能" name="skills">
                  <Select mode="multiple" maxTagCount="responsive" options={skillOptions} />
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item label="绑定知识源" name="knowledgeSources">
                  <Select mode="multiple" maxTagCount="responsive" options={knowledgeOptions} />
                </Form.Item>
              </Col>
              <Col span={8}>
                <Form.Item label="工具白名单" name="toolsets">
                  <Select mode="multiple" maxTagCount="responsive" options={toolOptions} />
                </Form.Item>
              </Col>
            </Row>
          </Card>

          <Card size="small" title="红线" style={{ marginTop: 12 }}>
            <Form.List name="redLines">
              {(fields, { add, remove }) => (
                <Space orientation="vertical" style={{ width: '100%' }}>
                  {fields.map(({ key, name, ...rest }) => (
                    <div key={key} style={{ display: 'flex', gap: 8, width: '100%', alignItems: 'flex-start' }}>
                      <Form.Item {...rest} name={name} style={{ flex: 1, marginBottom: 0 }} rules={[{ required: true }]}>
                        <Input placeholder="例如：未经审批承诺超额退款" />
                      </Form.Item>
                      <Button icon={<MinusCircleOutlined />} onClick={() => remove(name)} />
                    </div>
                  ))}
                  <Button type="dashed" icon={<PlusOutlined />} onClick={() => add()}>添加红线</Button>
                </Space>
              )}
            </Form.List>
          </Card>

          <Card size="small" title="业务结果指标绑定" style={{ marginTop: 12 }}>
            <Form.List name="metricBindings">
              {(fields, { add, remove }) => (
                <Space orientation="vertical" style={{ width: '100%' }}>
                  {fields.map(({ key, name, ...rest }) => (
                    <div
                      key={key}
                      style={{
                        border: '1px solid #f0f0f0',
                        borderRadius: 6,
                        padding: 12,
                        background: '#fafafa',
                      }}
                    >
                      <Row gutter={12}>
                        <Col span={9}><Form.Item {...rest} label="指标名称" name={[name, 'name']} rules={[{ required: true }]}><Input /></Form.Item></Col>
                        <Col span={6}><Form.Item {...rest} label="来源" name={[name, 'source']} rules={[{ required: true }]}><Select options={metricSourceOptions} /></Form.Item></Col>
                        <Col span={8}>
                          <Form.Item
                            noStyle
                            shouldUpdate={(prev, current) => {
                              const prevSource = prev.metricBindings?.[name]?.source;
                              const currentSource = current.metricBindings?.[name]?.source;
                              return prevSource !== currentSource;
                            }}
                          >
                            {({ getFieldValue }) => {
                              const source = getFieldValue(['metricBindings', name, 'source']);
                              const options = source === 'tool_business_system'
                                ? toolMetricOptions
                                : source === 'manual_or_imported'
                                  ? manualMetricOptions
                                  : platformMetricOptions;

                              return (
                                <Form.Item
                                  {...rest}
                                  label="采集配置"
                                  name={[name, 'collectionMethod']}
                                  rules={[{ required: true }]}
                                  tooltip="根据指标来源选择结构化采集方式；详情页会展示为只读摘要。"
                                >
                                  <Select options={options} placeholder="选择采集配置" />
                                </Form.Item>
                              );
                            }}
                          </Form.Item>
                        </Col>
                        <Col span={1}><Button style={{ marginTop: 30 }} icon={<MinusCircleOutlined />} onClick={() => remove(name)} /></Col>
                      </Row>
                      <Row gutter={12}>
                        <Col span={6}><Form.Item {...rest} label="单位" name={[name, 'unit']} style={{ marginBottom: 0 }}><Input /></Form.Item></Col>
                        <Col span={6}><Form.Item {...rest} label="目标值" name={[name, 'target']} style={{ marginBottom: 0 }}><Input /></Form.Item></Col>
                        <Col span={6}><Form.Item {...rest} label="当前值" name={[name, 'actual']} style={{ marginBottom: 0 }}><Input /></Form.Item></Col>
                      </Row>
                    </div>
                  ))}
                  <Button type="dashed" icon={<PlusOutlined />} onClick={() => add({ source: 'platform_native' })}>添加业务指标</Button>
                </Space>
              )}
            </Form.List>
          </Card>
        </Form>
      </Modal>

      <Modal
        title={selectedTemplate?.role}
        open={detailOpen}
        onCancel={() => setDetailOpen(false)}
        width={940}
        footer={
          <Space>
            <Button icon={<ExperimentOutlined />} onClick={() => { setDetailOpen(false); openEvaluation(selectedTemplate!); }}>评测</Button>
            <Button type="primary" onClick={() => setDetailOpen(false)}>关闭</Button>
          </Space>
        }
      >
        {selectedTemplate && (
          <Space orientation="vertical" style={{ width: '100%' }} size={16}>
            {selectedTemplate.evaluation.status !== 'passed' && (
              <Alert
                type={selectedTemplate.evaluation.status === 'failed' ? 'error' : 'warning'}
                showIcon
                title="该模板最近一次评测未完全通过，发布或创建员工前需要管理员确认风险。"
              />
            )}
            <Descriptions bordered size="small" column={3}>
              <Descriptions.Item label="岗位">{selectedTemplate.role}</Descriptions.Item>
              <Descriptions.Item label="职级"><Tag color={gradeColorMap[selectedTemplate.grade]}>{selectedTemplate.grade}</Tag></Descriptions.Item>
              <Descriptions.Item label="部门">{selectedTemplate.department}</Descriptions.Item>
              <Descriptions.Item label="版本">v{selectedTemplate.version}</Descriptions.Item>
              <Descriptions.Item label="状态">{selectedTemplate.status === 'published' ? <Tag color="green">已发布</Tag> : <Tag>草稿</Tag>}</Descriptions.Item>
              <Descriptions.Item label="最高风险">{selectedTemplate.maxGoalRiskLevel}</Descriptions.Item>
              <Descriptions.Item label="默认目标预算">{selectedTemplate.defaultGoalBudgetTokens.toLocaleString()} 令牌</Descriptions.Item>
              <Descriptions.Item label="模型"><Text code>{modelNameById[selectedTemplate.model] ?? selectedTemplate.model}</Text></Descriptions.Item>
              <Descriptions.Item label="试点">{selectedTemplate.isPilot ? selectedTemplate.pilotScenario : '否'}</Descriptions.Item>
            </Descriptions>

            <Card size="small" title="模板评测">
              <Space orientation="vertical" style={{ width: '100%' }}>
                <Space>
                  <Tag color={evaluationMap[selectedTemplate.evaluation.status].color}>{evaluationMap[selectedTemplate.evaluation.status].label}</Tag>
                  <Text>{selectedTemplate.evaluation.lastRunAt ?? '未评测'}</Text>
                </Space>
                {selectedTemplate.evaluation.status !== 'not_run' && (
                  <Progress percent={selectedTemplate.evaluation.score} status={selectedTemplate.evaluation.status === 'failed' ? 'exception' : 'active'} />
                )}
                <Paragraph type="secondary" style={{ margin: 0 }}>{selectedTemplate.evaluation.summary}</Paragraph>
              </Space>
            </Card>

            <Card size="small" title="系统提示词">
              <Paragraph style={{ whiteSpace: 'pre-wrap', margin: 0 }}>{selectedTemplate.systemPrompt}</Paragraph>
            </Card>

            <Row gutter={12}>
              <Col span={8}><Card size="small" title="技能">{selectedTemplate.skills.map((skill) => <Tag key={skill}>{skill}</Tag>)}</Card></Col>
              <Col span={8}><Card size="small" title="知识源">{selectedTemplate.knowledgeSources.map((source) => <Tag key={source} color="purple">{source}</Tag>)}</Card></Col>
              <Col span={8}><Card size="small" title="工具白名单">{selectedTemplate.toolsets.map((toolId) => <Tag key={toolId} color="blue">{toolNameById[toolId] ?? toolId}</Tag>)}</Card></Col>
            </Row>

            <Card size="small" title="业务结果指标">
              {selectedTemplate.metricBindings.length ? (
                <Table
                  dataSource={selectedTemplate.metricBindings}
                  rowKey="id"
                  pagination={false}
                  size="small"
                  columns={[
                    { title: '指标', dataIndex: 'name', key: 'name' },
                    { title: '来源', dataIndex: 'source', key: 'source', render: (source: string) => <Tag>{source}</Tag> },
                    { title: '目标', dataIndex: 'target', key: 'target' },
                    { title: '当前', dataIndex: 'actual', key: 'actual' },
                    { title: '采集方式', dataIndex: 'collectionMethod', key: 'collectionMethod' },
                  ]}
                />
              ) : <Text type="secondary">尚未绑定业务结果指标。</Text>}
            </Card>

            <Divider />
            <Space wrap>
              {selectedTemplate.redLines.map((redLine) => <Tag key={redLine} color="red"><CheckCircleOutlined /> {redLine}</Tag>)}
            </Space>
          </Space>
        )}
      </Modal>

    </>
  );
}

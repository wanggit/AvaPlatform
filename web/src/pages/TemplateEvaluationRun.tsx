// 岗位模板评测运行页面：发起异步评测、轮询过程并提交人工评审结论。
import { useCallback, useEffect, useMemo, useState, type CSSProperties, type ReactNode } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
  Alert,
  Button,
  Card,
  Col,
  Descriptions,
  Input,
  List,
  Progress,
  Row,
  Select,
  Space,
  Spin,
  Tag,
  Typography,
  message,
} from 'antd';
import {
  ArrowLeftOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ClockCircleOutlined,
  ExperimentOutlined,
  SafetyCertificateOutlined,
  SyncOutlined,
} from '@ant-design/icons';
import {
  api,
  type BackendTemplateEvaluationRun,
  mapTemplateEvaluationRun,
} from '../services/api';
import { usePlatformData } from '../services/platformData';
import type { TemplateEvaluationRun as TemplateEvaluationRunRecord, TemplateEvaluationRunStatus } from '../types/domain';

const { Title, Text, Paragraph } = Typography;
const { TextArea } = Input;

const activeStatuses = new Set<TemplateEvaluationRunStatus>(['queued', 'running', 'waiting_for_approval']);

const statusMeta: Record<TemplateEvaluationRunStatus, { label: string; color: string; icon: ReactNode; percent: number }> = {
  queued: { label: '排队中', color: 'default', icon: <ClockCircleOutlined />, percent: 8 },
  running: { label: '执行中', color: 'processing', icon: <SyncOutlined spin />, percent: 56 },
  waiting_for_approval: { label: '等待审批', color: 'warning', icon: <SafetyCertificateOutlined />, percent: 72 },
  completed: { label: '已完成', color: 'success', icon: <CheckCircleOutlined />, percent: 100 },
  error: { label: '失败', color: 'error', icon: <CloseCircleOutlined />, percent: 100 },
};

const runOutputStyle: CSSProperties = {
  maxHeight: 360,
  overflow: 'auto',
  background: '#1f2329',
  color: '#e6e6e6',
  padding: 16,
  borderRadius: 6,
  fontFamily: 'monospace',
  fontSize: 13,
  whiteSpace: 'pre-wrap',
  wordBreak: 'break-word',
};

const stepDetailsStyle: CSSProperties = {
  ...runOutputStyle,
  maxHeight: 180,
  margin: '4px 0 0',
  padding: 10,
  fontSize: 12,
};

function runPath(versionId: string, runId: string) {
  return `/templates/${versionId}/evaluation-runs/${runId}`;
}

function nonEmptyValue(value: unknown) {
  return value !== undefined && value !== null && value !== '';
}

function formatStepDetails(details: Record<string, unknown>) {
  const visibleDetails = Object.fromEntries(
    Object.entries(details ?? {}).filter(([, value]) => nonEmptyValue(value)),
  );
  if (Object.keys(visibleDetails).length === 0) return '';
  return JSON.stringify(visibleDetails, null, 2);
}

export default function TemplateEvaluationRun() {
  const { versionId = '', runId } = useParams();
  const navigate = useNavigate();
  const { templates, refreshTemplates, source } = usePlatformData();
  const [messageApi, contextHolder] = message.useMessage();
  const [taskDescription, setTaskDescription] = useState('');
  const [latestRuns, setLatestRuns] = useState<TemplateEvaluationRunRecord[]>([]);
  const [run, setRun] = useState<TemplateEvaluationRunRecord | null>(null);
  const [loadingRun, setLoadingRun] = useState(false);
  const [starting, setStarting] = useState(false);
  const [judgment, setJudgment] = useState<'passed' | 'failed'>('passed');
  const [summary, setSummary] = useState('');

  const template = useMemo(
    () => templates.find((item) => item.id === versionId),
    [templates, versionId],
  );
  const activeRun = latestRuns.find((item) => activeStatuses.has(item.status));
  const currentStatus = run ? statusMeta[run.status] : undefined;
  const latestStepDetails = useMemo(() => {
    if (!run) return '';
    const step = [...run.steps].reverse().find((item) => formatStepDetails(item.details));
    return step ? formatStepDetails(step.details) : '';
  }, [run]);
  const errorDetail = run
    ? run.errorMessage?.trim() || run.hermesOutput?.trim() || latestStepDetails || '未知错误'
    : '未知错误';

  const loadLatestRuns = useCallback(async () => {
    if (!versionId) return;
    const data = await api.get<BackendTemplateEvaluationRun[]>(`/job-template-versions/${versionId}/evaluation/runs?limit=8`);
    setLatestRuns(data.map(mapTemplateEvaluationRun));
  }, [versionId]);

  const loadRun = useCallback(async () => {
    if (!versionId || !runId) return;
    setLoadingRun(true);
    try {
      const data = await api.get<BackendTemplateEvaluationRun>(`/job-template-versions/${versionId}/evaluation/runs/${runId}`);
      const mapped = mapTemplateEvaluationRun(data);
      setRun(mapped);
      setTaskDescription(mapped.taskDescription);
    } catch (err) {
      messageApi.error(err instanceof Error ? err.message : '加载评测运行失败');
    } finally {
      setLoadingRun(false);
    }
  }, [messageApi, runId, versionId]);

  useEffect(() => {
    void loadLatestRuns().catch(() => setLatestRuns([]));
  }, [loadLatestRuns]);

  useEffect(() => {
    if (!runId) {
      setRun(null);
      return;
    }
    void loadRun();
  }, [loadRun, runId]);

  useEffect(() => {
    if (!runId || (run && !activeStatuses.has(run.status))) return;
    const timer = window.setInterval(() => {
      void loadRun();
      void loadLatestRuns().catch(() => undefined);
    }, 3000);
    return () => window.clearInterval(timer);
  }, [loadLatestRuns, loadRun, run, runId]);

  const startEvaluation = async () => {
    if (!taskDescription.trim()) {
      messageApi.warning('请输入评测任务描述');
      return;
    }
    setStarting(true);
    try {
      const data = await api.post<BackendTemplateEvaluationRun>(
        `/job-template-versions/${versionId}/evaluation/runs`,
        { task_description: taskDescription },
      );
      const nextRun = mapTemplateEvaluationRun(data);
      messageApi.success('评测运行已创建。');
      navigate(runPath(versionId, nextRun.id));
    } catch (err) {
      const messageText = err instanceof Error ? err.message : '启动评测失败';
      const existingRunId = messageText.match(/evalrun-[a-z0-9]+/i)?.[0];
      if (existingRunId) {
        messageApi.warning('该模板已有评测正在执行，已跳转到运行页面。');
        navigate(runPath(versionId, existingRunId));
      } else {
        messageApi.error(messageText);
      }
    } finally {
      setStarting(false);
    }
  };

  const submitEvaluation = async () => {
    if (!run) return;
    try {
      const evaluationCase = {
        id: globalThis.crypto?.randomUUID?.() ?? `eval-case-${Date.now()}`,
        title: run.taskDescription,
        input_payload: { task: run.taskDescription, evaluation_run_id: run.id },
        expected_result: '',
        actual_result: run.hermesOutput,
        assertions: [],
        status: judgment,
        failure_reason: judgment === 'failed' ? (summary || '人工评审未通过') : null,
      };
      await api.put(`/job-template-versions/${versionId}/evaluation`, {
        status: judgment,
        score: judgment === 'passed' ? 100 : 0,
        evaluator: '管理员',
        summary: summary || (judgment === 'passed' ? '人工评审通过。' : '人工评审未通过。'),
        cases: [evaluationCase],
      });
      await refreshTemplates();
      await loadLatestRuns();
      messageApi.success('评测结果已提交。');
    } catch (err) {
      messageApi.error(err instanceof Error ? err.message : '提交评测结果失败');
    }
  };

  return (
    <>
      {contextHolder}
      <Space orientation="vertical" size={16} style={{ width: '100%' }}>
        <Space align="start" style={{ width: '100%', justifyContent: 'space-between' }}>
          <Space orientation="vertical" size={2}>
            <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/templates')}>返回岗位模板</Button>
            <Title level={4} style={{ margin: 0 }}>岗位模板评测</Title>
            <Text type="secondary">
              当前数据源：{source === 'backend' ? '后端接口' : '后端不可用'}。
            </Text>
          </Space>
          {run && currentStatus && (
            <Tag color={currentStatus.color} icon={currentStatus.icon} style={{ padding: '4px 10px' }}>
              {currentStatus.label}
            </Tag>
          )}
        </Space>

        <Card size="small" title="模板信息">
          <Descriptions size="small" column={3}>
            <Descriptions.Item label="岗位">{template?.role ?? versionId}</Descriptions.Item>
            <Descriptions.Item label="版本">v{template?.version ?? '-'}</Descriptions.Item>
            <Descriptions.Item label="部门">{template?.department ?? '-'}</Descriptions.Item>
            <Descriptions.Item label="模型"><Text code>{template?.model ?? '-'}</Text></Descriptions.Item>
            <Descriptions.Item label="技能">{template?.skills.length ?? 0} 个</Descriptions.Item>
            <Descriptions.Item label="知识源">{template?.knowledgeSources.length ?? 0} 个</Descriptions.Item>
            <Descriptions.Item label="工具">{template?.toolsets.length ?? 0} 个</Descriptions.Item>
            <Descriptions.Item label="最高风险">{template?.maxGoalRiskLevel ?? '-'}</Descriptions.Item>
            <Descriptions.Item label="最近评测">{template?.evaluation.summary ?? '-'}</Descriptions.Item>
          </Descriptions>
        </Card>

        {!runId && (
          <Row gutter={16}>
            <Col span={15}>
              <Card size="small" title="发起评测">
                <Space orientation="vertical" size={12} style={{ width: '100%' }}>
                  {activeRun && (
                    <Alert
                      type="warning"
                      showIcon
                      message="该模板已有评测正在执行"
                      description={`运行 ${activeRun.id} 当前状态：${statusMeta[activeRun.status].label}`}
                      action={<Button size="small" type="primary" onClick={() => navigate(runPath(versionId, activeRun.id))}>查看运行</Button>}
                    />
                  )}
                  <TextArea
                    rows={6}
                    placeholder="输入本次评测任务，例如：模拟客户要求退款，要求数字员工引用知识源、判断边界并在需要时触发审批。"
                    value={taskDescription}
                    onChange={(event) => setTaskDescription(event.target.value)}
                    disabled={!!activeRun || starting}
                  />
                  <Button
                    type="primary"
                    icon={<ExperimentOutlined />}
                    loading={starting}
                    disabled={!!activeRun}
                    onClick={startEvaluation}
                  >
                    执行评测
                  </Button>
                </Space>
              </Card>
            </Col>
            <Col span={9}>
              <Card size="small" title="最近评测运行">
                <List
                  size="small"
                  dataSource={latestRuns}
                  locale={{ emptyText: '暂无评测运行。' }}
                  renderItem={(item) => (
                    <List.Item
                      actions={[
                        <Button key="view" size="small" onClick={() => navigate(runPath(versionId, item.id))}>查看</Button>,
                      ]}
                    >
                      <List.Item.Meta
                        title={<Space><Text code>{item.id}</Text><Tag color={statusMeta[item.status].color}>{statusMeta[item.status].label}</Tag></Space>}
                        description={item.startedAt}
                      />
                    </List.Item>
                  )}
                />
              </Card>
            </Col>
          </Row>
        )}

        {runId && (
          <Spin spinning={loadingRun && !run}>
            {run && currentStatus ? (
              <Space orientation="vertical" size={16} style={{ width: '100%' }}>
                <Card size="small" title="运行状态">
                  <Space orientation="vertical" size={12} style={{ width: '100%' }}>
                    <Progress percent={currentStatus.percent} status={run.status === 'error' ? 'exception' : run.status === 'completed' ? 'success' : 'active'} />
                    <Descriptions size="small" column={3}>
                      <Descriptions.Item label="运行编号"><Text code>{run.id}</Text></Descriptions.Item>
                      <Descriptions.Item label="Hermes Run">{run.hermesRunId ? <Text code>{run.hermesRunId}</Text> : '-'}</Descriptions.Item>
                      <Descriptions.Item label="状态"><Tag color={currentStatus.color}>{currentStatus.label}</Tag></Descriptions.Item>
                      <Descriptions.Item label="开始时间">{run.startedAt}</Descriptions.Item>
                      <Descriptions.Item label="更新时间">{run.updatedAt}</Descriptions.Item>
                      <Descriptions.Item label="完成时间">{run.completedAt ?? '-'}</Descriptions.Item>
                    </Descriptions>
                    {run.status === 'waiting_for_approval' && (
                      <Alert
                        type="warning"
                        showIcon
                        message="评测正在等待人工审批"
                        description="请前往审批中心处理该评测产生的 Hermes 审批，审批后本页面会继续轮询状态。"
                        action={<Button size="small" type="primary" onClick={() => navigate('/approvals')}>前往审批中心</Button>}
                      />
                    )}
                  </Space>
                </Card>

                <Card size="small" title="评测任务">
                  <Paragraph style={{ whiteSpace: 'pre-wrap', margin: 0 }}>{run.taskDescription}</Paragraph>
                </Card>

                <Card size="small" title="执行过程">
                  <List
                    size="small"
                    dataSource={run.steps}
                    renderItem={(step) => {
                      const detailsText = formatStepDetails(step.details);
                      return (
                        <List.Item>
                          <Space orientation="vertical" size={2} style={{ width: '100%' }}>
                            <Space wrap>
                              <Tag color={statusMeta[step.status].color}>{statusMeta[step.status].label}</Tag>
                              <Text>{step.message}</Text>
                            </Space>
                            <Text type="secondary">{step.createdAt}</Text>
                            {detailsText && <pre style={stepDetailsStyle}>{detailsText}</pre>}
                          </Space>
                        </List.Item>
                      );
                    }}
                  />
                </Card>

                {(run.status === 'completed' || run.status === 'error') && (
                  <Card
                    size="small"
                    title={run.status === 'completed' ? 'Hermes 执行结果' : '执行失败'}
                    style={{ borderColor: run.status === 'completed' ? '#52c41a' : '#ff4d4f' }}
                  >
                    {run.status === 'error' ? (
                      <Alert
                        type="error"
                        showIcon
                        message="评测执行失败"
                        description={<pre style={{ ...runOutputStyle, margin: '8px 0 0' }}>{errorDetail}</pre>}
                      />
                    ) : (
                      <div style={runOutputStyle}>
                        {run.hermesOutput || '(Hermes 未返回输出内容)'}
                      </div>
                    )}
                  </Card>
                )}

                {run.status === 'completed' && (
                  <Card size="small" title="人工评审结论">
                    <Space orientation="vertical" size={12} style={{ width: '100%' }}>
                      <Space>
                        <Text strong>评测结论</Text>
                        <Select
                          value={judgment}
                          onChange={setJudgment}
                          style={{ width: 130 }}
                          options={[
                            { label: '通过', value: 'passed' },
                            { label: '不通过', value: 'failed' },
                          ]}
                        />
                      </Space>
                      <TextArea
                        rows={4}
                        placeholder="描述评测结论的理由，例如任务完成度、输出质量、是否触发正确审批、是否引用知识源。"
                        value={summary}
                        onChange={(event) => setSummary(event.target.value)}
                      />
                      <Space>
                        <Button type="primary" onClick={submitEvaluation}>提交评测结果</Button>
                        <Button onClick={() => navigate(`/templates/${versionId}/evaluation`)}>重新评测</Button>
                      </Space>
                    </Space>
                  </Card>
                )}
              </Space>
            ) : (
              <Alert type="warning" showIcon message="未找到评测运行" />
            )}
          </Spin>
        )}
      </Space>
    </>
  );
}

// 数字员工管理页面：创建员工实例、维护上下级关系和运行生命周期。
import { useMemo, useState } from 'react';
import {
  Alert,
  Avatar,
  Badge,
  Button,
  Descriptions,
  Form,
  Input,
  Modal,
  Popconfirm,
  Progress,
  Select,
  Space,
  Steps,
  Table,
  Tag,
  Typography,
  message,
} from 'antd';
import {
  CheckCircleOutlined,
  EyeOutlined,
  PauseCircleOutlined,
  PlayCircleOutlined,
  PlusOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import {
  gradeColorMap,
  type DigitalEmployee,
} from '../types/domain';
import { api, buildCreateDigitalEmployeePayload } from '../services/api';
import { usePlatformData } from '../services/platformData';

const { Title, Text } = Typography;

const evaluationStatusLabel: Record<string, string> = {
  passed: '评测通过',
  failed: '评测失败',
  warning: '评测警告',
  not_run: '未评测',
  expired: '评测过期',
};

const lifecycleMap: Record<DigitalEmployee['lifecycleState'], { label: string; color: string; badge: 'processing' | 'success' | 'default' | 'warning' | 'error' }> = {
  provisioning: { label: '配置中', color: 'blue', badge: 'processing' },
  pending_activation: { label: '待上岗', color: 'gold', badge: 'warning' },
  active: { label: '已上岗', color: 'green', badge: 'success' },
  disabled: { label: '已停用', color: 'default', badge: 'default' },
  rollout_failed: { label: '上岗失败', color: 'red', badge: 'error' },
  needs_review: { label: '需人工处理', color: 'orange', badge: 'warning' },
};

const runtimeMap: Record<DigitalEmployee['runtimeState'], { label: string; color: string; badge: 'processing' | 'success' | 'default' | 'warning' | 'error' }> = {
  not_started: { label: '未启动', color: 'default', badge: 'default' },
  starting: { label: '启动中', color: 'blue', badge: 'processing' },
  healthy: { label: '健康', color: 'green', badge: 'success' },
  unhealthy: { label: '不健康', color: 'red', badge: 'error' },
  recovering: { label: '恢复中', color: 'orange', badge: 'warning' },
  stopped: { label: '已停止', color: 'default', badge: 'default' },
};

const availabilityMap: Record<DigitalEmployee['availabilityState'], { label: string; color: string; badge: 'processing' | 'success' | 'default' | 'warning' }> = {
  idle: { label: '空闲', color: 'green', badge: 'success' },
  busy: { label: '忙碌', color: 'blue', badge: 'processing' },
  unavailable: { label: '不可用', color: 'default', badge: 'default' },
};

const rolloutStepOrder: DigitalEmployee['rollout']['currentStep'][] = [
  'profile_render',
  'token_issue',
  'instance_start',
  'smoke_test',
  'pending_activation',
];

const rolloutStepLabels: Record<DigitalEmployee['rollout']['currentStep'], string> = {
  profile_render: '渲染 Profile',
  token_issue: '签发令牌',
  instance_start: '启动 Hermes',
  smoke_test: '实例冒烟',
  pending_activation: '待上岗',
  completed: '完成',
  failed: '失败',
};

function rolloutPercent(employee: DigitalEmployee) {
  if (employee.rollout.status === 'failed') return 100;
  if (employee.lifecycleState === 'active') return 100;
  const index = rolloutStepOrder.indexOf(employee.rollout.currentStep);
  return Math.max(20, Math.round(((index + 1) / rolloutStepOrder.length) * 100));
}

function rolloutSteps(employee: DigitalEmployee) {
  const currentIndex = rolloutStepOrder.indexOf(employee.rollout.currentStep);
  return rolloutStepOrder.map((step, index) => ({
    title: rolloutStepLabels[step],
    status: employee.rollout.status === 'failed' && step === employee.rollout.currentStep
      ? 'error' as const
      : index < currentIndex || employee.lifecycleState === 'active' || employee.rollout.currentStep === 'pending_activation'
        ? 'finish' as const
        : index === currentIndex
          ? 'process' as const
          : 'wait' as const,
  }));
}

export default function EmployeeManagement() {
  const [messageApi, contextHolder] = message.useMessage();
  const { employees: data, templates, departments, refreshEmployees, source } = usePlatformData();
  const [createOpen, setCreateOpen] = useState(false);
  const [detailOpen, setDetailOpen] = useState(false);
  const [selectedEmployeeId, setSelectedEmployeeId] = useState<string | null>(null);
  const [form] = Form.useForm();

  const publishedTemplates = useMemo(() => (
    templates.filter((template) => template.status === 'published')
  ), [templates]);

  const eligibleTemplates = useMemo(() => (
    publishedTemplates.filter((template) => template.evaluation.status === 'passed')
  ), [publishedTemplates]);

  const templateById = useMemo(() => (
    templates.reduce<Record<string, typeof templates[number]>>((acc, template) => {
      acc[template.id] = template;
      return acc;
    }, {})
  ), [templates]);

  const employeeNameById = useMemo(() => (
    data.reduce<Record<string, string>>((acc, employee) => {
      acc[employee.id] = employee.name;
      return acc;
    }, {})
  ), [data]);

  const reportCountByManager = useMemo(() => (
    data.reduce<Record<string, number>>((acc, employee) => {
      if (employee.managerId) acc[employee.managerId] = (acc[employee.managerId] ?? 0) + 1;
      return acc;
    }, {})
  ), [data]);

  const selectedEmployee = selectedEmployeeId ? data.find((employee) => employee.id === selectedEmployeeId) ?? null : null;

  const activateEmployee = async (id: string) => {
    try {
      await api.post(`/digital-employees/${id}/activate`);
      await refreshEmployees();
      messageApi.success('已上岗。系统会先确认 Hermes 实例健康，再允许调度目标。');
    } catch (err) {
      messageApi.error(err instanceof Error ? err.message : '员工上岗失败');
    }
  };

  const disableEmployee = async (id: string) => {
    try {
      await api.post(`/digital-employees/${id}/disable`);
      await refreshEmployees();
      messageApi.info('已停用，控制面仍可查看历史记录和审计。');
    } catch (err) {
      messageApi.error(err instanceof Error ? err.message : '员工停用失败');
    }
  };

  const rerunSmokeTest = async (id: string) => {
    await api.post(`/digital-employees/${id}/smoke-test`);
    await refreshEmployees();
    messageApi.success('冒烟测试已重新执行并通过，员工进入待上岗。');
  };

  const runSmokeConversation = (employee: DigitalEmployee) => {
    messageApi.open({
      type: 'success',
      content: `${employee.name} 已完成一次 Smoke/Test Run；不会创建 Goal Run、Work Item 或 KPI 记录。`,
    });
  };

  const createEmployee = () => {
    form.validateFields().then(async (values) => {
      await api.post('/digital-employees', buildCreateDigitalEmployeePayload(values));
      await refreshEmployees();
      setCreateOpen(false);
      form.resetFields();
      messageApi.success('已创建员工记录，后台 Rollout Job 正在异步配置。');
    }).catch((err) => {
      if (err?.errorFields) return;
      messageApi.error(err instanceof Error ? err.message : '创建数字员工失败');
    });
  };

  const columns = [
    {
      title: '数字员工',
      dataIndex: 'name',
      key: 'name',
      width: 230,
      render: (name: string, row: DigitalEmployee) => (
        <Space>
          <Avatar src={row.avatarUrl}>{row.nickname?.[0] ?? name[0]}</Avatar>
          <Space orientation="vertical" size={0}>
            <Text strong>{name}</Text>
            <Text type="secondary" style={{ fontSize: 12 }}>{row.role} / {row.department}</Text>
          </Space>
        </Space>
      ),
    },
    { title: '职级', dataIndex: 'grade', key: 'grade', width: 90, render: (grade: string) => <Tag color={gradeColorMap[grade]}>{grade}</Tag> },
    { title: '岗位模板', dataIndex: 'templateId', key: 'templateId', width: 190, render: (templateId: string) => <Text>{templateById[templateId]?.role} v{templateById[templateId]?.version}</Text> },
    { title: '生命周期', dataIndex: 'lifecycleState', key: 'lifecycleState', width: 120, render: (state: DigitalEmployee['lifecycleState']) => <Badge status={lifecycleMap[state].badge} text={lifecycleMap[state].label} /> },
    { title: 'Hermes 运行时', dataIndex: 'runtimeState', key: 'runtimeState', width: 130, render: (state: DigitalEmployee['runtimeState']) => <Tag color={runtimeMap[state].color}>{runtimeMap[state].label}</Tag> },
    { title: '可用性', dataIndex: 'availabilityState', key: 'availabilityState', width: 90, render: (state: DigitalEmployee['availabilityState']) => <Badge status={availabilityMap[state].badge} text={availabilityMap[state].label} /> },
    {
      title: 'Rollout',
      key: 'rollout',
      width: 190,
      render: (_: unknown, row: DigitalEmployee) => (
        <Space orientation="vertical" size={2} style={{ width: '100%' }}>
          <Progress percent={rolloutPercent(row)} size="small" status={row.rollout.status === 'failed' ? 'exception' : 'normal'} />
          <Text type="secondary" style={{ fontSize: 12 }}>{rolloutStepLabels[row.rollout.currentStep]}</Text>
        </Space>
      ),
    },
    { title: '活跃目标', dataIndex: 'activeGoalCount', key: 'activeGoalCount', width: 90 },
    {
      title: '操作',
      key: 'actions',
      width: 260,
      render: (_: unknown, row: DigitalEmployee) => (
        <Space wrap>
          <Button size="small" icon={<EyeOutlined />} onClick={() => { setSelectedEmployeeId(row.id); setDetailOpen(true); }}>详情</Button>
          {row.lifecycleState === 'pending_activation' && (
            <Button size="small" type="primary" icon={<CheckCircleOutlined />} onClick={() => activateEmployee(row.id)}>上岗</Button>
          )}
          {(row.lifecycleState === 'rollout_failed' || row.lifecycleState === 'needs_review') && (
            <Button size="small" icon={<ReloadOutlined />} onClick={() => rerunSmokeTest(row.id)}>重试冒烟</Button>
          )}
          {row.lifecycleState === 'active' && (
            <Popconfirm title="停用该员工？" onConfirm={() => disableEmployee(row.id)}>
              <Button size="small" icon={<PauseCircleOutlined />}>停用</Button>
            </Popconfirm>
          )}
          {row.lifecycleState === 'disabled' && (
            <Button size="small" icon={<PlayCircleOutlined />} onClick={() => activateEmployee(row.id)}>重新上岗</Button>
          )}
        </Space>
      ),
    },
  ];

  return (
    <>
      {contextHolder}
      <Space align="start" style={{ width: '100%', marginBottom: 16, justifyContent: 'space-between' }}>
        <Space orientation="vertical" size={2}>
          <Title level={4} style={{ margin: 0 }}>员工管理</Title>
          <Text type="secondary">创建员工只生成记录和异步 Rollout Job，通过冒烟测试后仍需管理员手动上岗。当前数据源：{source === 'backend' ? '后端接口' : '后端不可用'}。</Text>
        </Space>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateOpen(true)}>创建数字员工</Button>
      </Space>

      <Alert
        style={{ marginBottom: 16 }}
        type="info"
        showIcon
        title="创建数字员工不会自动创建 Goal；试运行只记录为 smoke/test，不进入 KPI 或业务产物统计。"
      />

      <Table dataSource={data} columns={columns} rowKey="id" pagination={false} scroll={{ x: 1280 }} />

      <Modal title="创建数字员工" open={createOpen} onCancel={() => setCreateOpen(false)} onOk={createEmployee} width={760}>
        <Form form={form} layout="vertical">
          <Form.Item label="姓名" name="name" rules={[{ required: true }]}>
            <Input placeholder="例如：客服小星" />
          </Form.Item>
          <Form.Item label="昵称" name="nickname">
            <Input placeholder="例如：客服小星" />
          </Form.Item>
          <Form.Item label="头像" name="avatarUrl" rules={[{ required: true, message: '请填写头像 URL' }]}>
            <Input placeholder="头像 URL（非上传），例如：https://example.com/avatar.png" />
          </Form.Item>
          <Form.Item label="岗位模板版本" name="templateId" rules={[{ required: true }]}>
            <Select
              placeholder="选择已发布且模板评测通过的版本"
              notFoundContent="暂无已发布岗位模板版本"
              options={publishedTemplates.map((template) => ({
                label: `${template.role} v${template.version} / ${template.maxGoalRiskLevel} / ${evaluationStatusLabel[template.evaluation.status] ?? template.evaluation.status}`,
                value: template.id,
                disabled: template.evaluation.status !== 'passed',
              }))}
            />
          </Form.Item>
          {publishedTemplates.length > 0 && eligibleTemplates.length === 0 && (
            <Alert
              type="warning"
              showIcon
              title="当前已发布岗位模板尚未通过模板评测，不能用于创建数字员工。"
            />
          )}
          <Form.Item label="部门" name="department" rules={[{ required: true }]}>
            <Select options={departments.map((department) => ({ label: department.name, value: department.id }))} />
          </Form.Item>
          <Form.Item label="直属上级" name="managerId">
            <Select allowClear options={data.filter((employee) => employee.lifecycleState === 'active').map((employee) => ({ label: `${employee.name} / ${employee.role}`, value: employee.id }))} />
          </Form.Item>
          <Form.Item label="备注" name="notes">
            <Input.TextArea rows={3} placeholder="只填写实例备注，不填写权限扩大、模型覆盖或模板外工具要求" />
          </Form.Item>
        </Form>
      </Modal>

      <Modal title="数字员工详情" open={detailOpen} onCancel={() => setDetailOpen(false)} footer={null} width={920}>
        {selectedEmployee && (
          <Space orientation="vertical" style={{ width: '100%' }} size={16}>
            <Space align="center">
              <Avatar size={48} src={selectedEmployee.avatarUrl}>{selectedEmployee.nickname?.[0] ?? selectedEmployee.name[0]}</Avatar>
              <Space orientation="vertical" size={0}>
                <Text strong>{selectedEmployee.name}</Text>
                <Text type="secondary">{selectedEmployee.role} / {selectedEmployee.department}</Text>
              </Space>
            </Space>

            <Descriptions bordered size="small" column={3}>
              <Descriptions.Item label="生命周期"><Badge status={lifecycleMap[selectedEmployee.lifecycleState].badge} text={lifecycleMap[selectedEmployee.lifecycleState].label} /></Descriptions.Item>
              <Descriptions.Item label="Hermes 运行时"><Tag color={runtimeMap[selectedEmployee.runtimeState].color}>{runtimeMap[selectedEmployee.runtimeState].label}</Tag></Descriptions.Item>
              <Descriptions.Item label="可用性"><Badge status={availabilityMap[selectedEmployee.availabilityState].badge} text={availabilityMap[selectedEmployee.availabilityState].label} /></Descriptions.Item>
              <Descriptions.Item label="岗位">{selectedEmployee.role} <Tag color={gradeColorMap[selectedEmployee.grade]}>{selectedEmployee.grade}</Tag></Descriptions.Item>
              <Descriptions.Item label="岗位模板">{templateById[selectedEmployee.templateId]?.role} v{templateById[selectedEmployee.templateId]?.version}</Descriptions.Item>
              <Descriptions.Item label="最高风险等级">{selectedEmployee.maxGoalRiskLevel}</Descriptions.Item>
              <Descriptions.Item label="直属上级">{selectedEmployee.managerId ? employeeNameById[selectedEmployee.managerId] : '无'}</Descriptions.Item>
              <Descriptions.Item label="直属下级">{reportCountByManager[selectedEmployee.id] ?? 0} 人</Descriptions.Item>
              <Descriptions.Item label="Hermes 端口"><Text code>127.0.0.1:{selectedEmployee.instancePort}</Text></Descriptions.Item>
              <Descriptions.Item label="Rollout Job">{selectedEmployee.rollout.jobId}</Descriptions.Item>
              <Descriptions.Item label="最近冒烟测试"><Tag color={selectedEmployee.rollout.lastSmokeTest.status === 'passed' ? 'green' : selectedEmployee.rollout.lastSmokeTest.status === 'failed' ? 'red' : 'blue'}>{selectedEmployee.rollout.lastSmokeTest.mode === 'manual' ? '人工标记' : '真实探测'}</Tag></Descriptions.Item>
              <Descriptions.Item label="月度令牌数">{selectedEmployee.monthlyTokenUsed.toLocaleString()}</Descriptions.Item>
              <Descriptions.Item label="技能" span={3}>{selectedEmployee.skills.map((skill) => <Tag key={skill}>{skill}</Tag>)}</Descriptions.Item>
              <Descriptions.Item label="备注" span={3}>{selectedEmployee.notes || <Text type="secondary">无</Text>}</Descriptions.Item>
            </Descriptions>

            <Steps size="small" items={rolloutSteps(selectedEmployee)} />

            {selectedEmployee.rollout.status === 'failed' && (
              <Alert
                type="error"
                showIcon
                title={selectedEmployee.rollout.failureReason}
                description={selectedEmployee.rollout.repairSuggestion}
              />
            )}

            <Alert
              type={selectedEmployee.rollout.lastSmokeTest.status === 'failed' ? 'error' : 'success'}
              showIcon
              title="最近冒烟 / 试运行结果"
              description={selectedEmployee.rollout.lastSmokeTest.summary}
            />

            <Space>
              {selectedEmployee.lifecycleState === 'pending_activation' && (
                <Button type="primary" icon={<CheckCircleOutlined />} onClick={() => activateEmployee(selectedEmployee.id)}>上岗</Button>
              )}
              {(selectedEmployee.lifecycleState === 'rollout_failed' || selectedEmployee.lifecycleState === 'needs_review') && (
                <Button icon={<ReloadOutlined />} onClick={() => rerunSmokeTest(selectedEmployee.id)}>重新执行冒烟测试</Button>
              )}
              <Button onClick={() => runSmokeConversation(selectedEmployee)}>试运行</Button>
            </Space>
          </Space>
        )}
      </Modal>
    </>
  );
}

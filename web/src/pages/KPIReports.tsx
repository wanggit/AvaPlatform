// 业务结果报表页面：展示岗位模板业务指标、采集来源和达成情况。
import { useState } from 'react';
import {
  Card,
  Col,
  Descriptions,
  Progress,
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
  FieldTimeOutlined,
  FundOutlined,
  RiseOutlined,
} from '@ant-design/icons';
import {
  type BusinessOutcomeMetricBinding,
  type TemplateOutcomeReport,
} from '../types/domain';
import { usePlatformData } from '../services/platformData';

const { Title, Text } = Typography;

const evaluationColorMap = {
  not_run: 'default',
  passed: 'green',
  failed: 'red',
  warning: 'orange',
};

const sourceLabelMap: Record<BusinessOutcomeMetricBinding['source'], string> = {
  platform_native: '平台原生',
  tool_business_system: '工具业务系统',
  manual_or_imported: '人工录入/导入',
};

export default function KPIReports() {
  const { templateOutcomeReports, source } = usePlatformData();
  const [period, setPeriod] = useState('当前周期');
  const [selectedReport, setSelectedReport] = useState<TemplateOutcomeReport | null>(null);

  const reports = templateOutcomeReports.filter((report) => report.period === period);
  const activeReport = selectedReport ?? reports[0] ?? null;
  const totalGoalRuns = reports.reduce((sum, report) => sum + report.goalRuns, 0);
  const avgCompletion = reports.length > 0 ? Math.round(reports.reduce((sum, report) => sum + report.completionRate, 0) / reports.length) : 0;
  const avgFirstPass = reports.length > 0 ? Math.round(reports.reduce((sum, report) => sum + report.firstPassAcceptanceRate, 0) / reports.length) : 0;
  const totalTokens = reports.reduce((sum, report) => sum + report.tokenCost, 0);

  const columns = [
    {
      title: '岗位模板版本',
      dataIndex: 'templateRole',
      key: 'templateRole',
      render: (role: string, row: TemplateOutcomeReport) => (
        <a onClick={() => setSelectedReport(row)}>
          <Space orientation="vertical" size={0}>
            <Text strong>{role}</Text>
            <Text type="secondary" style={{ fontSize: 12 }}>v{row.version} / {row.period}</Text>
          </Space>
        </a>
      ),
    },
    { title: '目标运行数', dataIndex: 'goalRuns', key: 'goalRuns', width: 110 },
    {
      title: '完成率',
      dataIndex: 'completionRate',
      key: 'completionRate',
      width: 160,
      render: (value: number) => <Progress percent={value} size="small" status={value >= 85 ? 'success' : value >= 75 ? 'active' : 'exception'} />,
    },
    {
      title: '首次验收通过',
      dataIndex: 'firstPassAcceptanceRate',
      key: 'firstPassAcceptanceRate',
      width: 170,
      render: (value: number) => <Progress percent={value} size="small" status={value >= 80 ? 'success' : value >= 70 ? 'active' : 'exception'} />,
    },
    { title: '返工率', dataIndex: 'reworkRate', key: 'reworkRate', width: 90, render: (value: number) => <Tag color={value > 15 ? 'orange' : 'green'}>{value}%</Tag> },
    { title: '平均周期', dataIndex: 'averageCycleHours', key: 'averageCycleHours', width: 100, render: (value: number) => `${value}h` },
    { title: '令牌成本', dataIndex: 'tokenCost', key: 'tokenCost', width: 120, render: (value: number) => value.toLocaleString() },
    { title: '评测', dataIndex: 'evaluationStatus', key: 'evaluationStatus', width: 90, render: (value: TemplateOutcomeReport['evaluationStatus']) => <Tag color={evaluationColorMap[value]}>{value}</Tag> },
  ];

  const metricColumns = [
    { title: '指标', dataIndex: 'name', key: 'name' },
    { title: '来源', dataIndex: 'source', key: 'source', render: (source: BusinessOutcomeMetricBinding['source']) => <Tag>{sourceLabelMap[source]}</Tag> },
    { title: '目标', dataIndex: 'target', key: 'target', width: 100 },
    { title: '当前', dataIndex: 'actual', key: 'actual', width: 100 },
    { title: '采集方式', dataIndex: 'collectionMethod', key: 'collectionMethod' },
  ];

  return (
    <>
      <Space align="start" style={{ width: '100%', marginBottom: 16, justifyContent: 'space-between' }}>
        <Space orientation="vertical" size={2}>
          <Title level={4} style={{ margin: 0 }}>业务结果与模板效果</Title>
          <Text type="secondary">按岗位模板版本观察目标运行结果、交付物验收、令牌成本和业务结果指标。当前数据源：{source === 'backend' ? '后端接口' : '后端不可用'}。</Text>
        </Space>
        <Select value={period} onChange={setPeriod} options={[{ label: '当前周期', value: '当前周期' }]} style={{ width: 140 }} />
      </Space>

      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}><Card size="small"><Statistic title="目标运行数" value={totalGoalRuns} prefix={<RiseOutlined />} /></Card></Col>
        <Col span={6}><Card size="small"><Statistic title="平均完成率" value={avgCompletion} suffix="%" prefix={<CheckCircleOutlined />} /></Card></Col>
        <Col span={6}><Card size="small"><Statistic title="首次验收通过" value={avgFirstPass} suffix="%" prefix={<FieldTimeOutlined />} /></Card></Col>
        <Col span={6}><Card size="small"><Statistic title="令牌成本" value={totalTokens} prefix={<FundOutlined />} /></Card></Col>
      </Row>

      <Table dataSource={reports} columns={columns} rowKey="id" pagination={false} />

      {activeReport && (
        <Card title={`${activeReport.templateRole} v${activeReport.version} - 业务指标`} style={{ marginTop: 16 }}>
          <Descriptions bordered size="small" column={4} style={{ marginBottom: 16 }}>
            <Descriptions.Item label="目标运行数">{activeReport.goalRuns}</Descriptions.Item>
            <Descriptions.Item label="完成率">{activeReport.completionRate}%</Descriptions.Item>
            <Descriptions.Item label="首次验收通过">{activeReport.firstPassAcceptanceRate}%</Descriptions.Item>
            <Descriptions.Item label="返工率">{activeReport.reworkRate}%</Descriptions.Item>
          </Descriptions>
          <Table
            dataSource={activeReport.businessMetrics}
            columns={metricColumns}
            rowKey="id"
            pagination={false}
            size="small"
          />
        </Card>
      )}
    </>
  );
}

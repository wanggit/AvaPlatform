// 数字员工目录页面：按部门、职级和技能筛选员工运行状态。
import { useState } from 'react';
import { Table, Tag, Space, Input, Select, Typography, Badge, Row, Col } from 'antd';
import { SearchOutlined } from '@ant-design/icons';
import { gradeColorMap, type DigitalEmployee } from '../types/domain';
import { usePlatformData } from '../services/platformData';

const { Text, Title } = Typography;

export default function EmployeeDirectory() {
  const { employees, source } = usePlatformData();
  const [search, setSearch] = useState('');
  const [gradeFilter, setGradeFilter] = useState<string | undefined>();
  const [skillFilter, setSkillFilter] = useState<string | undefined>();

  const allSkills = [...new Set(employees.flatMap((e) => e.skills))];
  const employeeNameById = employees.reduce<Record<string, string>>((acc, employee) => {
    acc[employee.id] = employee.name;
    return acc;
  }, {});

  const filtered = employees.filter((e) => {
    if (search && !e.name.includes(search) && !e.role.includes(search) && !e.department.includes(search)) return false;
    if (gradeFilter && e.grade !== gradeFilter) return false;
    if (skillFilter && !e.skills.includes(skillFilter)) return false;
    return true;
  });

  const availabilityMap: Record<DigitalEmployee['availabilityState'], { color: 'processing' | 'success' | 'default'; label: string }> = {
    busy: { color: 'processing', label: '忙碌' },
    idle: { color: 'success', label: '空闲' },
    unavailable: { color: 'default', label: '不可用' },
  };

  const lifecycleMap: Record<DigitalEmployee['lifecycleState'], { color: string; label: string }> = {
    provisioning: { color: 'blue', label: '配置中' },
    pending_activation: { color: 'gold', label: '待上岗' },
    active: { color: 'green', label: '已上岗' },
    disabled: { color: 'default', label: '已停用' },
    rollout_failed: { color: 'red', label: '上岗失败' },
    needs_review: { color: 'orange', label: '需人工处理' },
  };

  const columns = [
    {
      title: '姓名', dataIndex: 'name', key: 'name', width: 140,
      render: (t: string, r: DigitalEmployee) => (
        <Space>
          <Badge status={availabilityMap[r.availabilityState]?.color} />
          <Text strong>{t}</Text>
        </Space>
      ),
    },
    {
      title: '岗位', dataIndex: 'role', key: 'role', width: 120,
    },
    {
      title: '职级', dataIndex: 'grade', key: 'grade', width: 100,
      render: (g: string) => <Tag color={gradeColorMap[g]}>{g}</Tag>,
    },
    {
      title: '部门', dataIndex: 'department', key: 'department', width: 100,
    },
    {
      title: '最高风险', dataIndex: 'maxGoalRiskLevel', key: 'maxGoalRiskLevel', width: 90,
      render: (risk: string) => <Tag>{risk}</Tag>,
    },
    {
      title: '直属上级',
      dataIndex: 'managerId',
      key: 'managerId',
      width: 120,
      render: (managerId?: string) => managerId ? employeeNameById[managerId] : <Text type="secondary">无</Text>,
    },
    {
      title: '职责', dataIndex: 'description', key: 'description', ellipsis: true,
      render: (d: string) => <Text type="secondary" ellipsis>{d}</Text>,
    },
    {
      title: '技能', dataIndex: 'skills', key: 'skills', width: 320,
      render: (skills: string[]) => (
        <Space size={4} wrap>
          {skills.map((s) => (
            <Tag
              key={s}
              color={skillFilter === s ? 'blue' : undefined}
              style={{ cursor: 'pointer' }}
              onClick={() => setSkillFilter(skillFilter === s ? undefined : s)}
            >
              {s}
            </Tag>
          ))}
        </Space>
      ),
    },
    {
      title: '可用性', dataIndex: 'availabilityState', key: 'availabilityState', width: 90,
      render: (s: DigitalEmployee['availabilityState']) => availabilityMap[s].label,
    },
    {
      title: '生命周期', dataIndex: 'lifecycleState', key: 'lifecycleState', width: 110,
      render: (s: DigitalEmployee['lifecycleState']) => <Tag color={lifecycleMap[s].color}>{lifecycleMap[s].label}</Tag>,
    },
  ];

  return (
    <div>
      <Title level={4} style={{ marginBottom: 16 }}>员工目录 <Text type="secondary" style={{ fontSize: 14 }}>当前数据源：{source === 'backend' ? '后端接口' : '后端不可用'}</Text></Title>

      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col xs={24} sm={8}>
          <Input
            prefix={<SearchOutlined />}
            placeholder="搜索姓名、岗位、部门"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            allowClear
          />
        </Col>
        <Col xs={12} sm={4}>
          <Select
            placeholder="职级筛选"
            value={gradeFilter}
            onChange={setGradeFilter}
            allowClear
            style={{ width: '100%' }}
            options={[
              { label: 'Staff', value: 'Staff' },
              { label: 'Lead', value: 'Lead' },
              { label: 'Manager', value: 'Manager' },
              { label: 'Director', value: 'Director' },
            ]}
          />
        </Col>
        <Col xs={12} sm={4}>
          <Select
            placeholder="技能筛选"
            value={skillFilter}
            onChange={setSkillFilter}
            allowClear
            style={{ width: '100%' }}
            options={allSkills.map((s) => ({ label: s, value: s }))}
          />
        </Col>
      </Row>

      <Table
        dataSource={filtered}
        columns={columns}
        rowKey="id"
        size="middle"
        pagination={{ pageSize: 10 }}
      />
    </div>
  );
}

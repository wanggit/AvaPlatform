// 组织架构页面：以部门和上下级关系展示数字员工组织结构。
import { Badge, Card, Col, Row, Space, Tag, Tree, Typography } from 'antd';
import { ApartmentOutlined, TeamOutlined } from '@ant-design/icons';
import { gradeColorMap, type DigitalEmployee } from '../types/domain';
import { usePlatformData } from '../services/platformData';

const { Text, Title, Paragraph } = Typography;

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

function buildTree(employees: DigitalEmployee[]) {
  const childrenByManager = employees.reduce<Record<string, DigitalEmployee[]>>((acc, employee) => {
    if (employee.managerId) {
      acc[employee.managerId] = [...(acc[employee.managerId] ?? []), employee];
    }
    return acc;
  }, {});

  const toNode = (employee: DigitalEmployee): any => ({
    key: employee.id,
    title: (
      <Space size={8}>
        <Text strong>{employee.name}</Text>
        <Text type="secondary">{employee.role}</Text>
        <Tag color={gradeColorMap[employee.grade]}>{employee.grade}</Tag>
        <Tag>{employee.maxGoalRiskLevel}</Tag>
        <Tag color={lifecycleMap[employee.lifecycleState].color}>{lifecycleMap[employee.lifecycleState].label}</Tag>
        <Badge status={availabilityMap[employee.availabilityState].color} text={availabilityMap[employee.availabilityState].label} />
      </Space>
    ),
    children: (childrenByManager[employee.id] ?? []).map(toNode),
  });

  return employees.filter((employee) => !employee.managerId).map(toNode);
}

export default function OrganizationChart() {
  const { employees, source } = usePlatformData();
  const roots = employees.filter((employee) => !employee.managerId);
  const directReports = employees.reduce<Record<string, number>>((acc, employee) => {
    if (employee.managerId) acc[employee.managerId] = (acc[employee.managerId] ?? 0) + 1;
    return acc;
  }, {});

  const departments = [...new Set(employees.map((employee) => employee.department))];

  return (
    <div>
      <div style={{ marginBottom: 16 }}>
        <Title level={4} style={{ marginBottom: 4 }}>组织架构</Title>
        <Text type="secondary">展示组织内数字员工的上下级关系。当前数据源：{source === 'backend' ? '后端接口' : '后端不可用'}。</Text>
      </div>

      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={24} md={8}>
          <Card size="small">
            <Space>
              <TeamOutlined style={{ fontSize: 22, color: '#1677ff' }} />
              <div>
                <Text type="secondary">数字员工</Text>
                <Title level={3} style={{ margin: 0 }}>{employees.length}</Title>
              </div>
            </Space>
          </Card>
        </Col>
        <Col xs={24} md={8}>
          <Card size="small">
            <Space>
              <ApartmentOutlined style={{ fontSize: 22, color: '#52c41a' }} />
              <div>
                <Text type="secondary">部门</Text>
                <Title level={3} style={{ margin: 0 }}>{departments.length}</Title>
              </div>
            </Space>
          </Card>
        </Col>
        <Col xs={24} md={8}>
          <Card size="small">
            <Text type="secondary">最高负责人</Text>
            <Title level={3} style={{ margin: 0 }}>{roots.map((employee) => employee.name).join('、')}</Title>
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]}>
        <Col xs={24} xl={15}>
          <Card title="汇报关系树" size="small">
            <Tree
              showLine
              defaultExpandAll
              treeData={buildTree(employees)}
              blockNode
            />
          </Card>
        </Col>
        <Col xs={24} xl={9}>
          <Card title="管理跨度" size="small">
            {employees
              .filter((employee) => directReports[employee.id])
              .sort((a, b) => (directReports[b.id] ?? 0) - (directReports[a.id] ?? 0))
              .map((employee) => (
                <div key={employee.id} style={{ padding: '10px 0', borderBottom: '1px solid #f0f0f0' }}>
                  <Space orientation="vertical" size={2}>
                    <Space>
                      <Text strong>{employee.name}</Text>
                      <Tag color={gradeColorMap[employee.grade]}>{employee.grade}</Tag>
                    </Space>
                    <Paragraph style={{ margin: 0 }} type="secondary">
                      {employee.role} · 直属下级 {directReports[employee.id]} 人
                    </Paragraph>
                  </Space>
                </div>
              ))}
          </Card>
        </Col>
      </Row>
    </div>
  );
}

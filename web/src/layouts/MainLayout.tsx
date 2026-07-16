// 主布局组件：维护左侧导航、顶部状态区和页面内容出口。
import { useEffect, useState } from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import {
  Badge,
  Button,
  Layout,
  Menu,
  Avatar,
  Dropdown,
  theme,
  Typography,
  Space,
  Tooltip,
} from 'antd';
import {
  DashboardOutlined,
  TeamOutlined,
  UserOutlined,
  AimOutlined,
  BarChartOutlined,
  FileProtectOutlined,
  ApartmentOutlined,
  NodeIndexOutlined,
  ShopOutlined,
  DatabaseOutlined,
  ApiOutlined,
  ToolOutlined,
  WalletOutlined,
  AuditOutlined,
  SafetyCertificateOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  LogoutOutlined,
} from '@ant-design/icons';
import { api } from '../services/api';

const { Header, Sider, Content } = Layout;
const { Text } = Typography;

const menuItems = [
  {
    key: 'operations',
    label: '运营管理',
    type: 'group' as const,
    children: [
      { key: '/dashboard', icon: <DashboardOutlined />, label: '概览看板' },
      { key: '/employees', icon: <TeamOutlined />, label: '员工管理' },
      { key: '/directory', icon: <UserOutlined />, label: '员工目录' },
      { key: '/org', icon: <NodeIndexOutlined />, label: '组织架构' },
      { key: '/goals', icon: <AimOutlined />, label: '目标管理' },
      { key: '/approvals', icon: <SafetyCertificateOutlined />, label: '审批中心' },
      { key: '/kpi', icon: <BarChartOutlined />, label: '绩效报告' },
    ],
  },
  {
    key: 'settings',
    label: '系统配置',
    type: 'group' as const,
    children: [
      { key: '/templates', icon: <FileProtectOutlined />, label: '岗位模板' },
      { key: '/departments', icon: <ApartmentOutlined />, label: '部门管理' },
      { key: '/skills', icon: <ShopOutlined />, label: '技能管理' },
      { key: '/tools', icon: <ToolOutlined />, label: '工具管理' },
      { key: '/models', icon: <ApiOutlined />, label: '模型配置' },
      { key: '/knowledge', icon: <DatabaseOutlined />, label: '知识源接入' },
      { key: '/quotas', icon: <WalletOutlined />, label: '预算与用量' },
      { key: '/audit', icon: <AuditOutlined />, label: '审计规则' },
    ],
  },
];

export default function MainLayout() {
  const [collapsed, setCollapsed] = useState(false);
  const [pendingApprovalCount, setPendingApprovalCount] = useState(0);
  const navigate = useNavigate();
  const location = useLocation();
  const { token } = theme.useToken();

  const selectedKey = '/' + (location.pathname.split('/')[1] || 'dashboard');

  const loadPendingApprovalCount = async () => {
    try {
      const approvals = await api.get<Array<{ id: string }>>('/approvals?status=pending');
      setPendingApprovalCount(approvals.length);
    } catch {
      setPendingApprovalCount(0);
    }
  };

  useEffect(() => {
    void loadPendingApprovalCount();
    const timer = window.setInterval(() => {
      void loadPendingApprovalCount();
    }, 10000);
    const refresh = () => {
      void loadPendingApprovalCount();
    };
    window.addEventListener('platform-approvals-updated', refresh);
    return () => {
      window.clearInterval(timer);
      window.removeEventListener('platform-approvals-updated', refresh);
    };
  }, []);

  useEffect(() => {
    void loadPendingApprovalCount();
  }, [location.pathname]);

  const userMenu = {
    items: [
      { key: 'profile', label: '个人设置', icon: <UserOutlined /> },
      { type: 'divider' as const },
      { key: 'logout', label: '退出登录', icon: <LogoutOutlined /> },
    ],
  };

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider
        trigger={null}
        collapsible
        collapsed={collapsed}
        theme="dark"
        width={220}
        style={{
          overflow: 'auto',
          height: '100vh',
          position: 'fixed',
          left: 0,
          top: 0,
          bottom: 0,
          zIndex: 10,
        }}
      >
        <div
          style={{
            height: 48,
            margin: 12,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            borderBottom: `1px solid ${token.colorBorderSecondary}`,
          }}
        >
          <Text strong style={{ color: '#fff', fontSize: collapsed ? 14 : 16, whiteSpace: 'nowrap' }}>
            {collapsed ? 'AI' : 'AI 数字员工平台'}
          </Text>
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[selectedKey]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
        />
      </Sider>
      <Layout style={{ marginLeft: collapsed ? 80 : 220, transition: 'all 0.2s' }}>
        <Header
          style={{
            padding: '0 24px',
            background: token.colorBgContainer,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            borderBottom: `1px solid ${token.colorBorderSecondary}`,
            position: 'sticky',
            top: 0,
            zIndex: 9,
          }}
        >
          <Space>
            {collapsed ? (
              <MenuUnfoldOutlined
                style={{ fontSize: 18 }}
                onClick={() => setCollapsed(false)}
              />
            ) : (
              <MenuFoldOutlined
                style={{ fontSize: 18 }}
                onClick={() => setCollapsed(true)}
              />
            )}
            <Text strong style={{ fontSize: 16 }}>
              AI 数字员工平台 — 管理后台
            </Text>
          </Space>
          <Space size={16}>
            <Tooltip title={pendingApprovalCount ? `${pendingApprovalCount} 个待处理审批` : '暂无待处理审批'}>
              <Badge count={pendingApprovalCount} size="small" overflowCount={99}>
                <Button
                  type="text"
                  aria-label={`审批待办 ${pendingApprovalCount}`}
                  icon={<SafetyCertificateOutlined />}
                  onClick={() => navigate('/approvals')}
                >
                  审批待办
                </Button>
              </Badge>
            </Tooltip>
            <Dropdown menu={userMenu} placement="bottomRight">
              <Space style={{ cursor: 'pointer' }}>
                <Avatar size="small" icon={<UserOutlined />} />
                <Text>管理员</Text>
              </Space>
            </Dropdown>
          </Space>
        </Header>
        <Content
          style={{
            margin: 16,
            padding: 24,
            background: token.colorBgContainer,
            borderRadius: token.borderRadiusLG,
            minHeight: 280,
          }}
        >
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
}

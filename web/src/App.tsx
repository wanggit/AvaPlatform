// 应用路由入口：注册主布局和各业务页面路由。
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ConfigProvider } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import MainLayout from './layouts/MainLayout';
import Dashboard from './pages/Dashboard';
import EmployeeManagement from './pages/EmployeeManagement';
import EmployeeDirectory from './pages/EmployeeDirectory';
import GoalManagement from './pages/GoalManagement';
import KPIReports from './pages/KPIReports';
import TemplateManagement from './pages/TemplateManagement';
import DepartmentManagement from './pages/DepartmentManagement';
import OrganizationChart from './pages/OrganizationChart';
import ModelManagement from './pages/ModelManagement';
import SkillManagement from './pages/SkillManagement';
import ToolManagement from './pages/ToolManagement';
import KnowledgeManagement from './pages/KnowledgeManagement';
import QuotaManagement from './pages/QuotaManagement';
import AuditManagement from './pages/AuditManagement';
import ApprovalCenter from './pages/ApprovalCenter';
import TemplateEvaluationRun from './pages/TemplateEvaluationRun';
import { PlatformDataProvider } from './services/platformData';

export default function App() {
  return (
    <ConfigProvider
      locale={zhCN}
      theme={{
        token: {
          colorPrimary: '#1677ff',
          borderRadius: 6,
        },
      }}
    >
      <PlatformDataProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<MainLayout />}>
              <Route index element={<Navigate to="/dashboard" replace />} />
              <Route path="dashboard" element={<Dashboard />} />
              <Route path="employees" element={<EmployeeManagement />} />
              <Route path="directory" element={<EmployeeDirectory />} />
              <Route path="org" element={<OrganizationChart />} />
              <Route path="goals" element={<GoalManagement />} />
              <Route path="approvals" element={<ApprovalCenter />} />
              <Route path="kpi" element={<KPIReports />} />
              <Route path="templates" element={<TemplateManagement />} />
              <Route path="templates/:versionId/evaluation" element={<TemplateEvaluationRun />} />
              <Route path="templates/:versionId/evaluation-runs/:runId" element={<TemplateEvaluationRun />} />
              <Route path="departments" element={<DepartmentManagement />} />
              <Route path="skills" element={<SkillManagement />} />
              <Route path="tools" element={<ToolManagement />} />
              <Route path="knowledge" element={<KnowledgeManagement />} />
              <Route path="models" element={<ModelManagement />} />
              <Route path="quotas" element={<QuotaManagement />} />
              <Route path="audit" element={<AuditManagement />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </PlatformDataProvider>
    </ConfigProvider>
  );
}

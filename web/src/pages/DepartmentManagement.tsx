// 部门管理页面：维护组织部门，并展示部门下员工和模板数量。
import { useState } from 'react';
import { Table, Button, Modal, Form, Input, Typography, Space, Popconfirm } from 'antd';
import { PlusOutlined, EditOutlined } from '@ant-design/icons';
import type { Department } from '../types/domain';
import { usePlatformData } from '../services/platformData';
import { api } from '../services/api';

const { Text, Title } = Typography;

export default function DepartmentManagement() {
  const { departments, refreshDepartments, source } = usePlatformData();
  const [createOpen, setCreateOpen] = useState(false);
  const [editOpen, setEditOpen] = useState(false);
  const [editingDept, setEditingDept] = useState<Department | null>(null);
  const [form] = Form.useForm();
  const [editForm] = Form.useForm();

  const handleCreate = () => {
    form.validateFields().then(async (values) => {
      await api.post('/departments', values);
      await refreshDepartments();
      setCreateOpen(false);
      form.resetFields();
    });
  };

  const handleEdit = () => {
    editForm.validateFields().then(async (values) => {
      if (!editingDept) return;
      await api.patch(`/departments/${editingDept.id}`, values);
      await refreshDepartments();
      setEditOpen(false);
      setEditingDept(null);
    });
  };

  const handleDelete = async (id: string) => {
    await api.delete(`/departments/${id}`);
    await refreshDepartments();
  };

  const columns = [
    { title: 'ID', dataIndex: 'id', key: 'id', width: 80 },
    { title: '部门名称', dataIndex: 'name', key: 'name', width: 140, render: (t: string) => <Text strong>{t}</Text> },
    { title: '描述', dataIndex: 'description', key: 'description', ellipsis: true },
    { title: '员工数', dataIndex: 'employeeCount', key: 'employeeCount', width: 80 },
    {
      title: '操作', key: 'action', width: 160,
      render: (_: any, r: any) => (
        <Space size="small">
          <Button
            size="small"
            icon={<EditOutlined />}
            onClick={() => {
              setEditingDept(r);
              editForm.setFieldsValue(r);
              setEditOpen(true);
            }}
          >
            编辑
          </Button>
          <Popconfirm
            title={`删除部门"${r.name}"？`}
            description={r.employeeCount > 0 ? `该部门下有 ${r.employeeCount} 名员工，请先转移员工后再删除。` : '删除后不可恢复。'}
            onConfirm={() => void handleDelete(r.id)}
            okButtonProps={{ disabled: r.employeeCount > 0 }}
          >
            <Button size="small" danger disabled={r.employeeCount > 0}>删除</Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>部门管理 <Text type="secondary" style={{ fontSize: 14 }}>当前数据源：{source === 'backend' ? '后端接口' : '后端不可用'}</Text></Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateOpen(true)}>
          创建部门
        </Button>
      </div>

      <Table
        dataSource={departments}
        columns={columns}
        rowKey="id"
        size="middle"
        pagination={{ pageSize: 10 }}
      />

      <Modal
        title="创建部门"
        open={createOpen}
        onCancel={() => { setCreateOpen(false); form.resetFields(); }}
        onOk={handleCreate}
        width={500}
      >
        <Form form={form} layout="vertical">
          <Form.Item label="部门名称" name="name" rules={[{ required: true }]}>
            <Input placeholder="如：客服部" />
          </Form.Item>
          <Form.Item label="描述" name="description">
            <Input.TextArea rows={2} placeholder="部门职责简述" />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title="编辑部门"
        open={editOpen}
        onCancel={() => { setEditOpen(false); setEditingDept(null); }}
        onOk={handleEdit}
        width={500}
      >
        <Form form={editForm} layout="vertical">
          <Form.Item label="部门名称" name="name" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item label="描述" name="description">
            <Input.TextArea rows={2} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}

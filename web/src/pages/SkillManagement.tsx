// Skill 管理页面：上传 zip 技能包、发布技能并供岗位模板绑定。
import { useState } from 'react';
import { Button, Card, Col, Descriptions, Form, Input, Modal, Row, Select, Space, Table, Tag, Typography, Upload } from 'antd';
import { EditOutlined, EyeOutlined, PlusOutlined, SendOutlined, StopOutlined, UploadOutlined } from '@ant-design/icons';
import { type SkillDefinition } from '../types/domain';
import { usePlatformData } from '../services/platformData';
import { api } from '../services/api';

const { Text, Title, Paragraph } = Typography;

const categoryOptions = ['客服', '销售', '市场', '产品', '管理', '通用'];

const defaultSkillValues = {
  category: '通用',
  version: '1.0.0',
  status: 'draft',
  packageFile: [],
};

const normalizeUpload = (event: unknown) => {
  if (Array.isArray(event)) return event;
  if (event && typeof event === 'object' && 'fileList' in event) {
    return (event as { fileList?: unknown[] }).fileList;
  }
  return [];
};

const toPackageFileList = (skill: SkillDefinition) => [
  {
    uid: skill.id,
    name: skill.packageFile,
    status: 'done',
  },
];

export default function SkillManagement() {
  const { skills, source, refresh } = usePlatformData();
  const [editOpen, setEditOpen] = useState(false);
  const [detailOpen, setDetailOpen] = useState(false);
  const [editingSkill, setEditingSkill] = useState<SkillDefinition | null>(null);
  const [selectedSkill, setSelectedSkill] = useState<SkillDefinition | null>(null);
  const [form] = Form.useForm();

  const openCreate = () => {
    setEditingSkill(null);
    form.resetFields();
    form.setFieldsValue(defaultSkillValues);
    setEditOpen(true);
  };

  const openEdit = (skill: SkillDefinition) => {
    setEditingSkill(skill);
    form.setFieldsValue({
      ...skill,
      packageFile: toPackageFileList(skill),
    });
    setEditOpen(true);
  };

  const readFileAsBase64 = (file: File) => new Promise<string>((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result).split(',')[1] ?? '');
    reader.onerror = () => reject(reader.error);
    reader.readAsDataURL(file);
  });

  const saveSkill = () => {
    form.validateFields().then(async (values) => {
      const packageFile = values.packageFile?.[0]?.name ?? '';
      const nextValues = {
        ...values,
        packageFile,
      };

      if (editingSkill) {
        await api.patch(`/skill-packages/${editingSkill.id}`, {
          name: nextValues.name,
          version: nextValues.version,
          description: nextValues.description,
        });
        if (nextValues.status === 'published' && editingSkill.status !== 'published') {
          await api.post(`/skill-packages/${editingSkill.id}/publish`);
        }
        await refresh();
      } else {
        const file = values.packageFile?.[0]?.originFileObj as File | undefined;
        if (!file) throw new Error('请上传技能压缩包');
        const created = await api.post<{ id: string }>('/skill-packages', {
          name: values.name,
          version: values.version,
          package_file_name: file.name,
          package_content_base64: await readFileAsBase64(file),
          description: values.description,
        });
        if (values.status === 'published') {
          await api.post(`/skill-packages/${created.id}/publish`);
        }
        await refresh();
      }
      setEditOpen(false);
      setEditingSkill(null);
      form.resetFields();
    });
  };

  const togglePublish = async (skillId: string) => {
    const skill = skills.find((item) => item.id === skillId);
    if (!skill || skill.status === 'published') return;
    await api.post(`/skill-packages/${skillId}/publish`);
    await refresh();
  };

  const columns = [
    {
      title: '技能',
      dataIndex: 'displayName',
      key: 'displayName',
      width: 180,
      render: (displayName: string, row: SkillDefinition) => (
        <Space orientation="vertical" size={0}>
          <Text strong>{displayName}</Text>
          <Text type="secondary" style={{ fontSize: 12 }}>{row.name}</Text>
        </Space>
      ),
    },
    { title: '分类', dataIndex: 'category', key: 'category', width: 90, render: (category: string) => <Tag>{category}</Tag> },
    { title: '版本', dataIndex: 'version', key: 'version', width: 90, render: (version: string) => <Text code>v{version}</Text> },
    { title: '说明', dataIndex: 'description', key: 'description', ellipsis: true },
    { title: '技能包', dataIndex: 'packageFile', key: 'packageFile', width: 220, render: (packageFile: string) => <Text code>{packageFile}</Text> },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 90,
      render: (status: string) => status === 'published' ? <Tag color="green">已发布</Tag> : <Tag>草稿</Tag>,
    },
    { title: '更新时间', dataIndex: 'updatedAt', key: 'updatedAt', width: 150 },
    {
      title: '操作',
      key: 'action',
      width: 220,
      render: (_: unknown, row: SkillDefinition) => (
        <Space size="small">
          <Button size="small" icon={<EyeOutlined />} onClick={() => { setSelectedSkill(row); setDetailOpen(true); }}>详情</Button>
          <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(row)}>编辑</Button>
          <Button
            size="small"
            type={row.status === 'published' ? 'default' : 'primary'}
            icon={row.status === 'published' ? <StopOutlined /> : <SendOutlined />}
            disabled={row.status === 'published'}
            onClick={() => togglePublish(row.id)}
          >
            {row.status === 'published' ? '下架' : '发布'}
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <div>
          <Title level={4} style={{ marginBottom: 4 }}>技能管理</Title>
          <Text type="secondary">维护全局技能库。当前数据源：{source === 'backend' ? '后端接口' : '后端不可用'}。</Text>
        </div>
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>新增技能</Button>
      </div>

      <Table dataSource={skills} columns={columns} rowKey="id" size="middle" pagination={{ pageSize: 10 }} />

      <Modal
        title={editingSkill ? '编辑技能' : '新增技能'}
        open={editOpen}
        onCancel={() => { setEditOpen(false); setEditingSkill(null); form.resetFields(); }}
        onOk={saveSkill}
        width={680}
        forceRender
        destroyOnHidden
      >
        <Form form={form} layout="vertical" initialValues={defaultSkillValues}>
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item label="显示名称" name="displayName" rules={[{ required: true, message: '请输入显示名称' }]}>
                <Input placeholder="如：客户沟通" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="技能名称" name="name" rules={[{ required: true, message: '请输入技能名称' }]}>
                <Input placeholder="如：customer-communication" />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={8}>
              <Form.Item label="分类" name="category" rules={[{ required: true }]}>
                <Select options={categoryOptions.map((category) => ({ label: category, value: category }))} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item label="版本" name="version" rules={[{ required: true, message: '请输入版本号' }]}>
                <Input placeholder="如：1.0.0" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item label="状态" name="status" rules={[{ required: true }]}>
                <Select options={[
                  { label: '草稿', value: 'draft' },
                  { label: '已发布', value: 'published' },
                ]} />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            {/* <Col span={12}>
              <Form.Item label="入口文件" name="entryFile" rules={[{ required: true }]}>
                <Input placeholder="SKILL.md" />
              </Form.Item>
            </Col> */}
            <Col>
              <Form.Item
                label="技能压缩包"
                name="packageFile"
                valuePropName="fileList"
                getValueFromEvent={normalizeUpload}
                rules={[
                  { required: true, message: '请上传技能压缩包' },
                  {
                    validator: (_, fileList: Array<{ name?: string }> = []) => {
                      const fileName = fileList[0]?.name?.toLowerCase() ?? '';
                      return fileName.endsWith('.zip')
                        ? Promise.resolve()
                        : Promise.reject(new Error('只能上传 .zip 文件'));
                    },
                  },
                ]}
              >
                <Upload accept=".zip,application/zip" maxCount={1} beforeUpload={() => false}>
                  <Button icon={<UploadOutlined />}>上传 ZIP 包</Button>
                </Upload>
              </Form.Item>
            </Col>
          </Row>

          <Form.Item label="说明" name="description" rules={[{ required: true, message: '请输入说明' }]}>
            <Input.TextArea rows={3} placeholder="说明该技能的用途和适用岗位" />
          </Form.Item>
        </Form>
      </Modal>

      <Modal title="技能详情" open={detailOpen} onCancel={() => setDetailOpen(false)} footer={null} width={720}>
        {selectedSkill && (
          <>
            <Descriptions bordered size="small" column={2} style={{ marginBottom: 16 }}>
              <Descriptions.Item label="显示名称">{selectedSkill.displayName}</Descriptions.Item>
              <Descriptions.Item label="技能名称"><Text code>{selectedSkill.name}</Text></Descriptions.Item>
              <Descriptions.Item label="分类"><Tag>{selectedSkill.category}</Tag></Descriptions.Item>
              <Descriptions.Item label="版本">v{selectedSkill.version}</Descriptions.Item>
              <Descriptions.Item label="入口文件">{selectedSkill.entryFile}</Descriptions.Item>
              <Descriptions.Item label="技能压缩包"><Text code>{selectedSkill.packageFile}</Text></Descriptions.Item>
              <Descriptions.Item label="状态">{selectedSkill.status === 'published' ? <Tag color="green">已发布</Tag> : <Tag>草稿</Tag>}</Descriptions.Item>
              <Descriptions.Item label="更新时间">{selectedSkill.updatedAt}</Descriptions.Item>
            </Descriptions>
            <Card title="下发规则" size="small" style={{ marginBottom: 16 }}>
              <Paragraph style={{ marginBottom: 0 }}>
                绑定到岗位模板后，创建或更新数字员工时，平台会把该技能的目录复制到目标员工配置目录的 <Text code>skills/{selectedSkill.name}/</Text> 下。
              </Paragraph>
            </Card>
            <Card title="说明" size="small">
              <Paragraph style={{ marginBottom: 0 }}>{selectedSkill.description}</Paragraph>
            </Card>
          </>
        )}
      </Modal>
    </div>
  );
}

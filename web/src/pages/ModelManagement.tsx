// 模型配置页面：维护大语言模型、向量模型、排序模型等模型连接信息。
import { useState } from 'react';
import { Badge, Button, Col, Descriptions, Form, Input, InputNumber, Modal, Row, Select, Space, Table, Tag, Typography, message } from 'antd';
import { EditOutlined, EyeOutlined, PlusOutlined, PoweroffOutlined } from '@ant-design/icons';
import { modelTypeLabelMap, type ModelConfig, type ModelType } from '../types/domain';
import { api, modelPayload } from '../services/api';
import { usePlatformData } from '../services/platformData';

const { Text, Title, Paragraph } = Typography;

const modelTypeOptions: { label: string; value: ModelType }[] = [
  { label: '大语言模型', value: 'llm' },
  { label: '向量模型', value: 'embedding' },
  { label: '排序模型', value: 'rerank' },
  { label: '视觉模型', value: 'vision' },
  { label: '语音模型', value: 'audio' },
];

const providerOptions = [
  'OpenAI Compatible',
  'Anthropic',
  'DeepSeek',
  'Kimi',
  'GLM',
  'Local Inference',
  'Ollama',
];

export default function ModelManagement() {
  const { models, refresh, source } = usePlatformData();
  const [messageApi, contextHolder] = message.useMessage();
  const [editOpen, setEditOpen] = useState(false);
  const [detailOpen, setDetailOpen] = useState(false);
  const [editingModel, setEditingModel] = useState<ModelConfig | null>(null);
  const [selectedModel, setSelectedModel] = useState<ModelConfig | null>(null);
  const [form] = Form.useForm();

  const openCreate = () => {
    setEditingModel(null);
    form.resetFields();
    form.setFieldsValue({
      type: 'llm',
      provider: 'OpenAI Compatible',
      status: 'active',
      contextWindow: 128000,
      maxOutputTokens: 8192,
    });
    setEditOpen(true);
  };

  const openEdit = (model: ModelConfig) => {
    setEditingModel(model);
    form.setFieldsValue(model);
    setEditOpen(true);
  };

  const saveModel = () => {
    form.validateFields().then(async (values) => {
      if (editingModel) {
        const credentialId = values.apiKey?.startsWith('cred-') ? values.apiKey : editingModel.apiKey;
        await api.patch(`/model-configurations/${editingModel.id}`, modelPayload(values, credentialId));
        await refresh();
        messageApi.success('模型配置已保存到后端。');
      } else {
        const credential = await api.post<{ id: string }>('/credentials', {
          name: `${values.name} 接口密钥`,
          owner_type: 'platform',
          owner_id: 'platform',
          owner_name: 'Platform',
          secret_value: values.apiKey,
          description: `${values.name} 模型配置使用的接口密钥。`,
        });
        await api.post('/model-configurations', modelPayload(values, credential.id));
        await refresh();
        messageApi.success('模型配置已创建到后端。');
      }
      setEditOpen(false);
      setEditingModel(null);
      form.resetFields();
    }).catch((err) => {
      if (err?.errorFields) return;
      messageApi.error(err instanceof Error ? err.message : '保存模型配置失败');
    });
  };

  const toggleStatus = async (model: ModelConfig) => {
    try {
      await api.post(`/model-configurations/${model.id}/${model.status === 'active' ? 'disable' : 'enable'}`);
      await refresh();
      messageApi.success(model.status === 'active' ? '模型已停用。' : '模型已启用。');
    } catch (err) {
      messageApi.error(err instanceof Error ? err.message : '模型启停失败');
    }
  };

  const columns = [
    {
      title: '显示名称',
      dataIndex: 'name',
      key: 'name',
      width: 170,
      render: (name: string, row: ModelConfig) => (
        <Space orientation="vertical" size={0}>
          <Text strong>{name}</Text>
          <Text type="secondary" style={{ fontSize: 12 }}>{row.provider}</Text>
        </Space>
      ),
    },
    {
      title: '模型类型',
      dataIndex: 'type',
      key: 'type',
      width: 110,
      render: (type: ModelType) => <Tag color={type === 'llm' ? 'blue' : type === 'embedding' ? 'purple' : 'orange'}>{modelTypeLabelMap[type]}</Tag>,
    },
    { title: '模型名称', dataIndex: 'modelName', key: 'modelName', width: 180, render: (modelName: string) => <Text code>{modelName}</Text> },
    { title: '基础地址', dataIndex: 'baseUrl', key: 'baseUrl', ellipsis: true },
    {
      title: '上下文',
      dataIndex: 'contextWindow',
      key: 'contextWindow',
      width: 110,
      render: (value: number) => `${(value / 1000).toFixed(0)}K`,
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 90,
      render: (status: string) => status === 'active' ? <Badge status="success" text="启用" /> : <Badge status="default" text="停用" />,
    },
    {
      title: '默认',
      dataIndex: 'isDefault',
      key: 'isDefault',
      width: 80,
      render: (isDefault?: boolean) => isDefault ? <Tag color="green">默认</Tag> : <Text type="secondary">-</Text>,
    },
    {
      title: '操作',
      key: 'action',
      width: 210,
      render: (_: unknown, row: ModelConfig) => (
        <Space size="small">
          <Button size="small" icon={<EyeOutlined />} onClick={() => { setSelectedModel(row); setDetailOpen(true); }}>详情</Button>
          <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(row)}>编辑</Button>
          <Button size="small" icon={<PoweroffOutlined />} onClick={() => toggleStatus(row)}>
            {row.status === 'active' ? '停用' : '启用'}
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <div>
      {contextHolder}
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <div>
          <Title level={4} style={{ marginBottom: 4 }}>模型配置</Title>
          <Text type="secondary">维护平台可用模型。当前数据源：{source === 'backend' ? '后端接口' : '后端不可用'}。</Text>
        </div>
        <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>新增模型</Button>
      </div>

      <Table dataSource={models} columns={columns} rowKey="id" size="middle" pagination={{ pageSize: 10 }} />

      <Modal
        title={editingModel ? '编辑模型配置' : '新增模型配置'}
        open={editOpen}
        onCancel={() => { setEditOpen(false); setEditingModel(null); form.resetFields(); }}
        onOk={saveModel}
        width={760}
        destroyOnHidden
      >
        <Form form={form} layout="vertical">
          <Title level={5} style={{ marginBottom: 12 }}>基础信息</Title>
          <Row gutter={16}>
            <Col span={8}>
              <Form.Item label="显示名称" name="name" rules={[{ required: true, message: '请输入显示名称' }]}>
                <Input placeholder="如：Claude Sonnet 4" />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item label="模型类型" name="type" rules={[{ required: true }]}>
                <Select options={modelTypeOptions} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item label="服务商" name="provider" rules={[{ required: true }]}>
                <Select showSearch options={providerOptions.map((provider) => ({ label: provider, value: provider }))} />
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item label="模型名称" name="modelName" rules={[{ required: true, message: '请输入模型名称' }]}>
                <Input placeholder="如：claude-sonnet-4 / text-embedding-3-large" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="状态" name="status" rules={[{ required: true }]}>
                <Select options={[
                  { label: '启用', value: 'active' },
                  { label: '停用', value: 'disabled' },
                ]} />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item label="基础地址" name="baseUrl" rules={[{ required: true, message: '请输入基础地址' }]}>
            <Input placeholder="如：https://api.openai.com/v1" />
          </Form.Item>

          <Form.Item label="接口密钥" name="apiKey" rules={[{ required: true, message: '请输入接口密钥' }]}>
            <Input.Password placeholder="用于调用该模型服务的接口密钥" />
          </Form.Item>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item label="上下文大小" name="contextWindow" rules={[{ required: true }]}>
                <InputNumber min={1024} step={1024} style={{ width: '100%' }} addonAfter="令牌" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="最大输出" name="maxOutputTokens">
                <InputNumber min={256} step={256} style={{ width: '100%' }} addonAfter="令牌" />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item label="说明" name="description">
            <Input.TextArea rows={3} placeholder="描述该模型适用场景、成本或调用限制" />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title="模型详情"
        open={detailOpen}
        onCancel={() => setDetailOpen(false)}
        footer={null}
        width={720}
      >
        {selectedModel && (
          <>
            <Descriptions bordered size="small" column={2}>
              <Descriptions.Item label="显示名称">{selectedModel.name}</Descriptions.Item>
              <Descriptions.Item label="模型类型"><Tag>{modelTypeLabelMap[selectedModel.type]}</Tag></Descriptions.Item>
              <Descriptions.Item label="服务商">{selectedModel.provider}</Descriptions.Item>
              <Descriptions.Item label="模型名称"><Text code>{selectedModel.modelName}</Text></Descriptions.Item>
              <Descriptions.Item label="基础地址" span={2}><Text code>{selectedModel.baseUrl}</Text></Descriptions.Item>
              <Descriptions.Item label="接口密钥" span={2}><Text code>{selectedModel.apiKey}</Text></Descriptions.Item>
              <Descriptions.Item label="上下文大小">{selectedModel.contextWindow.toLocaleString()} 令牌</Descriptions.Item>
              <Descriptions.Item label="最大输出">{selectedModel.maxOutputTokens ? `${selectedModel.maxOutputTokens.toLocaleString()} 令牌` : '-'}</Descriptions.Item>
              <Descriptions.Item label="状态">{selectedModel.status === 'active' ? <Badge status="success" text="启用" /> : <Badge status="default" text="停用" />}</Descriptions.Item>
              <Descriptions.Item label="默认模型">{selectedModel.isDefault ? '是' : '否'}</Descriptions.Item>
            </Descriptions>
            {selectedModel.description && (
              <Paragraph style={{ marginTop: 16, marginBottom: 0 }}>{selectedModel.description}</Paragraph>
            )}
          </>
        )}
      </Modal>
    </div>
  );
}

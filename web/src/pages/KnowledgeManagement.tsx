// 知识库管理页面：维护 RAGFlow 连接、知识源注册和检索预览。
import { useMemo, useState } from 'react';
import {
  Alert,
  Badge,
  Button,
  Card,
  Col,
  Descriptions,
  Form,
  Input,
  Modal,
  Row,
  Select,
  Space,
  Statistic,
  Table,
  Tag,
  Typography,
} from 'antd';
import {
  ApiOutlined,
  CheckCircleOutlined,
  CloudSyncOutlined,
  EditOutlined,
  EyeOutlined,
  LinkOutlined,
  PoweroffOutlined,
  SearchOutlined,
  WarningOutlined,
} from '@ant-design/icons';
import {
  type KnowledgePreviewHit,
  type KnowledgeSource,
} from '../types/domain';
import { usePlatformData } from '../services/platformData';
import { api, mapKnowledgeSource } from '../services/api';

const { Text, Title, Paragraph } = Typography;

const syncStatusMap: Record<KnowledgeSource['syncStatus'], { label: string; color: string }> = {
  active: { label: '已登记', color: 'green' },
  missing: { label: '失联', color: 'red' },
  unregistered: { label: '未登记', color: 'gold' },
};

const categoryOptions = ['客服', '销售', '市场', '产品', '运营', '通用'];

export default function KnowledgeManagement() {
  const {
    knowledgeConnection: connection,
    knowledgeSources: sources,
    setKnowledgeSources: setSources,
    templates,
    source,
    refresh,
    refreshKnowledgeConnection,
    refreshKnowledgeSources,
  } = usePlatformData();
  const [connectionOpen, setConnectionOpen] = useState(false);
  const [sourceOpen, setSourceOpen] = useState(false);
  const [editingSource, setEditingSource] = useState<KnowledgeSource | null>(null);
  const [previewSourceIds, setPreviewSourceIds] = useState<string[]>([]);
  const [previewQuery, setPreviewQuery] = useState('');
  const [previewHits, setPreviewHits] = useState<KnowledgePreviewHit[]>([]);
  const [previewWarnings, setPreviewWarnings] = useState<string[]>([]);
  const [previewAuditId, setPreviewAuditId] = useState('');
  const [previewRan, setPreviewRan] = useState(false);
  const [connectionForm] = Form.useForm();
  const [sourceForm] = Form.useForm();

  const registeredSources = sources.filter((source) => source.syncStatus !== 'unregistered');
  const activeSources = sources.filter((source) => source.status === 'active' && source.syncStatus === 'active');
  const missingBoundSources = sources.filter((source) => source.syncStatus === 'missing' && source.boundTemplateCount > 0);
  const totalChunks = sources
    .filter((source) => source.syncStatus === 'active')
    .reduce((sum, source) => sum + source.chunkCount, 0);

  const templateNamesBySource = useMemo(() => {
    return templates.reduce<Record<string, string[]>>((acc, template) => {
      template.knowledgeSources.forEach((sourceName) => {
        acc[sourceName] = [...(acc[sourceName] ?? []), template.role];
      });
      return acc;
    }, {});
  }, [templates]);

  const openConnection = () => {
    connectionForm.setFieldsValue(connection);
    setConnectionOpen(true);
  };

  const saveConnection = () => {
    connectionForm.validateFields().then(async (values) => {
      if (connection.id) {
        await api.patch(`/knowledge-connections/${connection.id}`, {
          name: values.name,
          base_url: values.baseUrl,
          credential_id: values.apiKeyRef,
        });
      } else {
        await api.post('/knowledge-connections', {
          name: values.name,
          provider: 'ragflow',
          base_url: values.baseUrl,
          credential_id: values.apiKeyRef,
        });
      }
      await refreshKnowledgeConnection();
      setConnectionOpen(false);
    });
  };

  const testConnection = async () => {
    if (!connection.id) return;
    await api.post(`/knowledge-connections/${connection.id}/test`);
    await refreshKnowledgeConnection();
  };

  const syncDatasets = async () => {
    if (!connection.id) return;
    const discovered = await api.get<Parameters<typeof mapKnowledgeSource>[0][]>(`/knowledge-connections/${connection.id}/discover`);
    setSources(discovered.map(mapKnowledgeSource));
  };

  const openSource = (source: KnowledgeSource) => {
    setEditingSource(source);
    sourceForm.setFieldsValue({
      ...source,
      status: source.syncStatus === 'unregistered' ? 'active' : source.status,
    });
    setSourceOpen(true);
  };

  const saveSource = () => {
    sourceForm.validateFields().then(async (values) => {
      if (!editingSource) return;
      if (editingSource.syncStatus === 'unregistered') {
        await api.post(`/knowledge-connections/${editingSource.connectionId}/sources`, {
          external_id: editingSource.externalDatasetId,
          display_name: values.name,
          source_type: 'dataset',
          authorization_scope: [values.category],
          retrieval_settings: { top_k: 5 },
        });
        await refreshKnowledgeSources();
        setSourceOpen(false);
        setEditingSource(null);
        sourceForm.resetFields();
        return;
      }
      await api.patch(`/knowledge-sources/${editingSource.id}`, {
        display_name: values.name,
        authorization_scope: [values.category],
        retrieval_settings: { description: values.description, top_k: 5 },
        status: values.status === 'active' ? 'active' : 'archived',
      });
      await refreshKnowledgeSources();
      setSourceOpen(false);
      setEditingSource(null);
      sourceForm.resetFields();
    });
  };

  const toggleSourceStatus = async (sourceId: string) => {
    const source = sources.find((item) => item.id === sourceId);
    if (!source) return;
    await api.patch(`/knowledge-sources/${sourceId}`, {
      status: source.status === 'active' ? 'archived' : 'active',
    });
    await refreshKnowledgeSources();
  };

  const runPreview = async (sourceIds = previewSourceIds, query = previewQuery) => {
    setPreviewRan(true);
    if (sourceIds.length === 0 || !query.trim()) {
      setPreviewAuditId('');
      setPreviewWarnings(['请选择知识源并输入检索问题。']);
      setPreviewHits([]);
      return;
    }
    try {
      const result = await api.post<{
        audit_id: string;
        warnings: string[];
        hits: Array<{
          id: string;
          content: string;
          source_name: string;
          document_name: string;
          chunk_id: string;
          score: number;
          citation: string;
        }>;
      }>('/knowledge/preview', {
        source_ids: sourceIds,
        query,
        top_k: 5,
      });
      setPreviewAuditId(result.audit_id);
      setPreviewWarnings(result.warnings);
      setPreviewHits(result.hits.map((hit) => ({
        id: hit.id,
        content: hit.content,
        sourceName: hit.source_name,
        documentName: hit.document_name,
        chunkId: hit.chunk_id,
        score: hit.score,
        citation: hit.citation,
      })));
    } catch (error) {
      setPreviewAuditId('');
      setPreviewWarnings([error instanceof Error ? error.message : 'RAGFlow 检索失败']);
      setPreviewHits([]);
    }
  };

  const columns = [
    {
      title: '知识源',
      dataIndex: 'name',
      key: 'name',
      width: 190,
      render: (name: string, row: KnowledgeSource) => (
        <Space orientation="vertical" size={0}>
          <Text strong>{name}</Text>
          <Text type="secondary" style={{ fontSize: 12 }}>{row.category}</Text>
        </Space>
      ),
    },
    {
      title: 'RAGFlow 数据集',
      dataIndex: 'externalDatasetName',
      key: 'externalDatasetName',
      width: 230,
      render: (datasetName: string, row: KnowledgeSource) => (
        <Space orientation="vertical" size={0}>
          <Text code>{datasetName}</Text>
          <Text type="secondary" style={{ fontSize: 12 }}>{row.externalDatasetId}</Text>
        </Space>
      ),
    },
    {
      title: '同步状态',
      dataIndex: 'syncStatus',
      key: 'syncStatus',
      width: 100,
      render: (syncStatus: KnowledgeSource['syncStatus']) => (
        <Tag color={syncStatusMap[syncStatus].color}>{syncStatusMap[syncStatus].label}</Tag>
      ),
    },
    {
      title: '启停',
      dataIndex: 'status',
      key: 'status',
      width: 90,
      render: (status: KnowledgeSource['status']) =>
        status === 'active' ? <Badge status="success" text="启用" /> : <Badge status="default" text="停用" />,
    },
    { title: '文档', dataIndex: 'documentCount', key: 'documentCount', width: 80 },
    { title: '分块数', dataIndex: 'chunkCount', key: 'chunkCount', width: 90 },
    {
      title: '绑定模板',
      dataIndex: 'boundTemplateCount',
      key: 'boundTemplateCount',
      width: 120,
      render: (count: number, row: KnowledgeSource) => (
        <Space orientation="vertical" size={0}>
          <Text>{count} 个</Text>
          {templateNamesBySource[row.name]?.length > 0 && (
            <Text type="secondary" style={{ fontSize: 12 }}>{templateNamesBySource[row.name].join(' / ')}</Text>
          )}
        </Space>
      ),
    },
    { title: '最近同步', dataIndex: 'lastSyncedAt', key: 'lastSyncedAt', width: 150, render: (value?: string) => value ?? '-' },
    {
      title: '操作',
      key: 'action',
      width: 230,
      render: (_: unknown, row: KnowledgeSource) => (
        <Space size="small">
          <Button size="small" icon={<EditOutlined />} onClick={() => openSource(row)}>
            {row.syncStatus === 'unregistered' ? '登记' : '编辑'}
          </Button>
          {row.syncStatus !== 'unregistered' && (
            <Button size="small" icon={<PoweroffOutlined />} onClick={() => toggleSourceStatus(row.id)}>
              {row.status === 'active' ? '停用' : '启用'}
            </Button>
          )}
          <Button
            size="small"
            icon={<EyeOutlined />}
            onClick={() => {
              setPreviewSourceIds([row.id]);
              const nextQuery = row.syncStatus === 'missing' ? '测试失联知识源' : previewQuery;
              setPreviewQuery(nextQuery);
              void runPreview([row.id], nextQuery);
            }}
          >
            预览
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <div>
          <Title level={4} style={{ marginBottom: 4 }}>知识源接入</Title>
          <Text type="secondary">接入单个 RAGFlow 知识连接，同步数据集，并登记为岗位模板可绑定的知识源。当前数据源：{source === 'backend' ? '后端接口' : '后端不可用'}。</Text>
        </div>
        <Space>
          <Button icon={<CheckCircleOutlined />} onClick={testConnection}>测试连接</Button>
          <Button type="primary" icon={<CloudSyncOutlined />} onClick={syncDatasets}>同步数据集</Button>
        </Space>
      </div>

      {missingBoundSources.length > 0 && (
        <Alert
          type="warning"
          showIcon
          style={{ marginBottom: 16 }}
          title="存在已绑定岗位模板的失联知识源"
          description={`${missingBoundSources.map((source) => source.name).join('、')} 已失联。运行时会跳过部分失联知识源；如果全部授权知识源失联，将返回“知识源不可用”错误。`}
        />
      )}

      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col xs={24} lg={12}>
          <Card
            title={<Space><LinkOutlined />RAGFlow 连接</Space>}
            size="small"
            extra={<Button size="small" icon={<EditOutlined />} onClick={openConnection}>编辑</Button>}
          >
            <Descriptions size="small" column={1}>
              <Descriptions.Item label="连接名称">{connection.name}</Descriptions.Item>
              <Descriptions.Item label="基础地址"><Text code>{connection.baseUrl}</Text></Descriptions.Item>
              <Descriptions.Item label="接口密钥引用"><Text code>{connection.apiKeyRef}</Text></Descriptions.Item>
              <Descriptions.Item label="状态">
                {connection.status === 'connected' ? <Badge status="success" text="已连接" /> : <Badge status="error" text="断开" />}
              </Descriptions.Item>
              <Descriptions.Item label="最近测试">{connection.lastTestedAt}</Descriptions.Item>
              <Descriptions.Item label="最近同步">{connection.lastSyncedAt}</Descriptions.Item>
            </Descriptions>
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Row gutter={[12, 12]}>
            <Col span={12}>
              <Card size="small"><Statistic title="已登记知识源" value={registeredSources.length} prefix={<ApiOutlined />} /></Card>
            </Col>
            <Col span={12}>
              <Card size="small"><Statistic title="启用知识源" value={activeSources.length} prefix={<CheckCircleOutlined />} /></Card>
            </Col>
            <Col span={12}>
              <Card size="small"><Statistic title="可检索分块" value={totalChunks} /></Card>
            </Col>
            <Col span={12}>
              <Card size="small">
                <Statistic
                  title="失联风险"
                  value={sources.filter((source) => source.syncStatus === 'missing').length}
                  prefix={<WarningOutlined />}
                  styles={{ content: { color: missingBoundSources.length > 0 ? '#fa8c16' : undefined } }}
                />
              </Card>
            </Col>
          </Row>
        </Col>
      </Row>

      <Table
        dataSource={sources}
        columns={columns}
        rowKey="id"
        size="middle"
        pagination={{ pageSize: 8 }}
        style={{ marginBottom: 16 }}
      />

      <Card title={<Space><SearchOutlined />管理员检索预览</Space>} size="small">
        <Row gutter={16}>
          <Col xs={24} lg={10}>
            <Space orientation="vertical" style={{ width: '100%' }} size="middle">
              <div>
                <Text strong>知识源</Text>
                <Select
                  mode="multiple"
                  value={previewSourceIds}
                  onChange={setPreviewSourceIds}
                  style={{ width: '100%', marginTop: 8 }}
                  placeholder="选择一个或多个知识源"
                  options={sources
                    .filter((source) => source.syncStatus !== 'unregistered')
                    .map((source) => ({
                      label: `${source.name}（${syncStatusMap[source.syncStatus].label}）`,
                      value: source.id,
                    }))}
                />
              </div>
              <div>
                <Text strong>检索问题</Text>
                <Input.TextArea
                  rows={4}
                  value={previewQuery}
                  onChange={(event) => setPreviewQuery(event.target.value)}
                  style={{ marginTop: 8 }}
                  placeholder="输入用于验证 RAGFlow 检索效果的问题"
                />
              </div>
              <Button type="primary" icon={<SearchOutlined />} onClick={() => void runPreview()}>
                执行管理员预览
              </Button>
              <Alert
                type="info"
                showIcon
                title="管理员预览不代表员工运行时权限"
                description="预览可直接选择知识源，用于配置验证；员工运行时仍通过员工服务令牌和岗位模板动态鉴权。"
              />
            </Space>
          </Col>
          <Col xs={24} lg={14}>
            <Space orientation="vertical" style={{ width: '100%' }} size="middle">
              <Descriptions bordered size="small" column={2}>
                <Descriptions.Item label="审计编号">{previewAuditId ? <Text code>{previewAuditId}</Text> : <Text type="secondary">未执行</Text>}</Descriptions.Item>
                <Descriptions.Item label="命中数">{previewHits.length}</Descriptions.Item>
              </Descriptions>
              {previewWarnings.length > 0 && (
                <Alert
                  type="warning"
                  showIcon
                  title="部分知识源不可用"
                  description={previewWarnings.join(' ')}
                />
              )}
              {!previewRan ? (
                <Alert type="info" showIcon title="尚未执行预览" description="请选择已登记的知识源并输入检索问题后执行预览。" />
              ) : previewHits.length === 0 ? (
                <Alert type="error" showIcon title="知识源不可用" description="所选知识源全部不可用，本次预览返回可审计错误。" />
              ) : (
                previewHits.map((hit) => (
                  <div
                    key={hit.id}
                    style={{
                      border: '1px solid #f0f0f0',
                      borderRadius: 6,
                      padding: 12,
                      background: '#fff',
                    }}
                  >
                    <Space orientation="vertical" size={4} style={{ width: '100%' }}>
                      <Space>
                        <Tag color="blue">{hit.sourceName}</Tag>
                        <Text code>{hit.score.toFixed(2)}</Text>
                        <Text type="secondary">{hit.chunkId}</Text>
                      </Space>
                      <Paragraph style={{ marginBottom: 0 }}>{hit.content}</Paragraph>
                      <Text type="secondary">引用：{hit.citation}</Text>
                    </Space>
                  </div>
                ))
              )}
            </Space>
          </Col>
        </Row>
      </Card>

      <Modal
        title="编辑 RAGFlow 连接"
        open={connectionOpen}
        onCancel={() => setConnectionOpen(false)}
        onOk={saveConnection}
        width={680}
        forceRender
      >
        <Alert
          type="info"
          showIcon
          style={{ marginBottom: 16 }}
          title="最小可用版本只允许一个活跃的 RAGFlow 知识连接"
          description="数据模型保留连接编号扩展位，但当前后台不提供多连接切换。"
        />
        <Form form={connectionForm} layout="vertical">
          <Form.Item label="连接名称" name="name" rules={[{ required: true, message: '请输入连接名称' }]}>
            <Input placeholder="如：RAGFlow 企业知识库" />
          </Form.Item>
          <Form.Item label="基础地址" name="baseUrl" rules={[{ required: true, message: '请输入 RAGFlow 基础地址' }]}>
            <Input placeholder="https://ragflow.internal.example.com" />
          </Form.Item>
          <Form.Item label="接口密钥引用" name="apiKeyRef" rules={[{ required: true, message: '请输入接口密钥引用' }]}>
            <Input placeholder="secret/ragflow/main-api-key" />
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title={editingSource?.syncStatus === 'unregistered' ? '登记知识源' : '编辑知识源'}
        open={sourceOpen}
        onCancel={() => { setSourceOpen(false); setEditingSource(null); sourceForm.resetFields(); }}
        onOk={saveSource}
        width={720}
        forceRender
      >
        {editingSource && (
          <Descriptions bordered size="small" column={1} style={{ marginBottom: 16 }}>
            <Descriptions.Item label="RAGFlow 数据集"><Text code>{editingSource.externalDatasetName}</Text></Descriptions.Item>
            <Descriptions.Item label="数据集编号"><Text code>{editingSource.externalDatasetId}</Text></Descriptions.Item>
          </Descriptions>
        )}
        <Form form={sourceForm} layout="vertical">
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item label="平台显示名称" name="name" rules={[{ required: true, message: '请输入平台显示名称' }]}>
                <Input placeholder="如：产品手册" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="分类" name="category" rules={[{ required: true }]}>
                <Select options={categoryOptions.map((category) => ({ label: category, value: category }))} />
              </Form.Item>
            </Col>
          </Row>
          <Form.Item label="说明" name="description" rules={[{ required: true, message: '请输入说明' }]}>
            <Input.TextArea rows={3} placeholder="说明这个知识源适合哪些岗位使用" />
          </Form.Item>
          <Form.Item label="状态" name="status" rules={[{ required: true }]}>
            <Select options={[
              { label: '启用', value: 'active' },
              { label: '停用', value: 'disabled' },
            ]} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}

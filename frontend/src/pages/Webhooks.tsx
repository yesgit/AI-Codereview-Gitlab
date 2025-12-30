import { useState, useEffect } from 'react';
import { Table, Button, Modal, Form, Input, message, Popconfirm, Switch, Select, Tooltip, Tabs } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, SendOutlined } from '@ant-design/icons';
import { webhookApi } from '@/api/webhooks';
import type { Webhook, WebhookForm } from '@/types';

interface DefaultPrompts {
  custom_prompt_system: string;
  custom_prompt_user: string;
}

const Webhooks: React.FC = () => {
  const [data, setData] = useState<Webhook[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [editingRecord, setEditingRecord] = useState<Webhook | null>(null);
  const [defaultPrompts, setDefaultPrompts] = useState<DefaultPrompts | null>(null);
  const [defaultExtensions, setDefaultExtensions] = useState<string | null>(null);
  const [form] = Form.useForm();

  const fetchData = async () => {
    setLoading(true);
    try {
      const response = await webhookApi.getAll();
      setData(response);
    } catch (error) {
      console.error('Failed to fetch webhooks:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchDefaultPrompts = async () => {
    try {
      const response = await webhookApi.getDefaultPrompts();
      setDefaultPrompts(response);
    } catch (error) {
      console.error('Failed to fetch default prompts:', error);
    }
  };

  const fetchDefaultExtensions = async () => {
    try {
      const response = await webhookApi.getDefaultExtensions();
      setDefaultExtensions(response.supported_extensions);
    } catch (error) {
      console.error('Failed to fetch default extensions:', error);
    }
  };

  useEffect(() => {
    fetchData();
    fetchDefaultPrompts();
    fetchDefaultExtensions();
  }, []);

  const handleCreate = () => {
    setEditingRecord(null);
    form.resetFields();
    // 加载默认提示词
    if (defaultPrompts) {
      form.setFieldsValue({
        custom_prompt_system: defaultPrompts.custom_prompt_system,
        custom_prompt_user: defaultPrompts.custom_prompt_user,
      });
    }
    // 加载默认扩展名
    if (defaultExtensions) {
      form.setFieldsValue({
        supported_extensions: defaultExtensions,
      });
    }
    setModalVisible(true);
  };

  const handleEdit = (record: Webhook) => {
    setEditingRecord(record);
    form.setFieldsValue(record);
    setModalVisible(true);
  };

  const handleDelete = async (id: number) => {
    try {
      await webhookApi.delete(id);
      message.success('删除成功');
      fetchData();
    } catch (error) {
      console.error('Failed to delete webhook:', error);
    }
  };

  const handleSendReport = async (id: number) => {
    try {
      const result = await webhookApi.sendDailyReport(id);
      message.success(result.message || '日报发送成功');
    } catch (error: any) {
      const errorMsg = error?.response?.data?.detail || '日报发送失败';
      message.error(errorMsg);
    }
  };

  const handleSubmit = async (values: WebhookForm) => {
    try {
      if (editingRecord) {
        await webhookApi.update(editingRecord.id, values);
        message.success('更新成功');
      } else {
        await webhookApi.create(values);
        message.success('创建成功');
      }
      setModalVisible(false);
      fetchData();
    } catch (error) {
      console.error('Failed to save webhook:', error);
    }
  };

  const columns = [
    { 
      title: 'ID', 
      dataIndex: 'id', 
      key: 'id', 
      width: 50,
      hidden: false,
    },
    { 
      title: 'GitLab URL', 
      dataIndex: 'gitlab_base_url', 
      key: 'gitlab_base_url',
      width: 150,
      ellipsis: true,
      hidden: false,
      render: (url: string) => (
        <Tooltip title={url}>
          <span style={{ fontSize: '12px' }}>{url || '-'}</span>
        </Tooltip>
      ),
    },
    { 
      title: '项目 Slug', 
      dataIndex: 'project_slug', 
      key: 'project_slug',
      width: 130,
      ellipsis: true,
      hidden: false,
      render: (slug: string) => (
        <Tooltip title={slug}>
          <span style={{ fontSize: '12px' }}>{slug || '-'}</span>
        </Tooltip>
      ),
    },
    { 
      title: '项目名称', 
      dataIndex: 'project_name', 
      key: 'project_name',
      width: 120,
      hidden: false,
      ellipsis: true,
    },
    { 
      title: 'URL Slug', 
      dataIndex: 'url_slug', 
      key: 'url_slug',
      width: 100,
      ellipsis: true,
      hidden: true, // 默认隐藏，可在响应式逻辑中控制显示
      render: (slug: string) => (
        <Tooltip title={slug}>
          <span style={{ fontSize: '12px' }}>{slug || '-'}</span>
        </Tooltip>
      ),
    },
    { 
      title: '钉钉', 
      dataIndex: 'dingtalk_url', 
      key: 'dingtalk_url',
      width: 70,
      hidden: true, // 响应式隐藏
      ellipsis: true,
      render: (url: string, record: Webhook) => (
        <Tooltip title={url}>
          <span style={{ fontSize: '11px', display: 'flex', alignItems: 'center', gap: 4 }}>
            {record.dingtalk_enabled ? '✓' : '✗'}
          </span>
        </Tooltip>
      ),
    },
    { 
      title: '飞书', 
      dataIndex: 'feishu_url', 
      key: 'feishu_url',
      width: 70,
      hidden: true, // 响应式隐藏
      ellipsis: true,
      render: (url: string, record: Webhook) => (
        <Tooltip title={url}>
          <span style={{ fontSize: '11px', display: 'flex', alignItems: 'center', gap: 4 }}>
            {record.feishu_enabled ? '✓' : '✗'}
          </span>
        </Tooltip>
      ),
    },
    { 
      title: '企业微信', 
      dataIndex: 'wecom_url', 
      key: 'wecom_url',
      width: 70,
      hidden: true, // 响应式隐藏
      ellipsis: true,
      render: (url: string, record: Webhook) => (
        <Tooltip title={url}>
          <span style={{ fontSize: '11px', display: 'flex', alignItems: 'center', gap: 4 }}>
            {record.wecom_enabled ? '✓' : '✗'}
          </span>
        </Tooltip>
      ),
    },
    {
      title: '评审风格',
      dataIndex: 'review_style',
      key: 'review_style',
      width: 80,
      hidden: false,
      render: (style: string) => {
        const styleMap: Record<string, string> = {
          'professional': '专业',
          'sarcastic': '讽刺',
          'gentle': '温和',
          'humorous': '幽默',
          'random': '随机',
        };
        return <Tooltip title={style}>{styleMap[style] || '默认'}</Tooltip>;
      },
    },
    {
      title: '文件扩展名',
      dataIndex: 'supported_extensions',
      key: 'supported_extensions',
      width: 100,
      hidden: true,
      ellipsis: true,
      render: (exts: string) => (
        <Tooltip title={exts}>
          <span style={{ fontSize: '11px' }}>{exts || '-'}</span>
        </Tooltip>
      ),
    },
    {
      title: '操作',
      key: 'action',
      width: 140,
      fixed: 'right' as const,
      hidden: false,
      render: (_: any, record: Webhook) => (
        <span>
          <Button
            type="link"
            size="small"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
          >
            编辑
          </Button>
          <Button
            type="link"
            size="small"
            icon={<SendOutlined />}
            onClick={() => handleSendReport(record.id)}
          >
            发送日报
          </Button>
          <Popconfirm
            title="确认删除？"
            onConfirm={() => handleDelete(record.id)}
            okText="确认"
            cancelText="取消"
          >
            <Button
              type="link"
              size="small"
              danger
              icon={<DeleteOutlined />}
            >
              删除
            </Button>
          </Popconfirm>
        </span>
      ),
    },
  ];

  return (
    <div>
      <div style={{ marginBottom: 16 }}>
        <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
          新建配置
        </Button>
      </div>

      <Table
        columns={columns.filter(col => !col.hidden)}
        dataSource={data}
        rowKey="id"
        loading={loading}
        pagination={{ pageSize: 20 }}
        scroll={{ x: 'max-content' }}
        size="small"
      />

      <Modal
        title={editingRecord ? '编辑项目配置' : '新建项目配置'}
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        footer={null}
        width={800}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
          scrollToFirstError
          onFinishFailed={() => {
            message.warning('请检查表单，必填字段可能位于其他标签页中');
          }}
        >
          <Tabs
            defaultActiveKey="basic"
            items={[
              {
                key: 'basic',
                label: '📋 基础配置',
                children: (
                  <div style={{ padding: '8px 0' }}>
                    <Form.Item
                      label="GitLab 基础 URL"
                      name="gitlab_base_url"
                      tooltip="如 https://gitlab.com 或 http://a.b"
                      rules={[
                        {
                          validator: (_, value) => {
                            if (!value) {
                              return Promise.resolve();
                            }
                            // 自定义 URL 验证：更宽松的格式检查
                            const urlPattern = /^(https?:\/\/)?([^\/]+)(\/.*)?$/;
                            if (!urlPattern.test(value)) {
                              return Promise.reject(new Error('请输入有效的 URL，如 https://gitlab.com'));
                            }
                            return Promise.resolve();
                          },
                        },
                      ]}
                    >
                      <Input placeholder="https://gitlab.com" />
                    </Form.Item>

                    <Form.Item
                      label="项目 Slug"
                      name="project_slug"
                      tooltip="如 group/project"
                      dependencies={['gitlab_base_url']}
                      rules={[
                        { required: true, message: '请输入项目 Slug' },
                        ({ getFieldValue }) => ({
                          validator(_, value) {
                            const gitlabUrl = getFieldValue('gitlab_base_url');
                            if (gitlabUrl && !value) {
                              return Promise.reject(new Error('填写 GitLab URL 时必填'));
                            }
                            if (value && !gitlabUrl) {
                              return Promise.reject(new Error('请同时填写 GitLab URL'));
                            }
                            return Promise.resolve();
                          },
                        }),
                      ]}
                    >
                      <Input placeholder="group/project" />
                    </Form.Item>

                    <Form.Item
                      label="项目名称"
                      name="project_name"
                      tooltip="兼容旧方式，建议使用上面的 GitLab URL + Slug"
                      rules={[{ required: true, message: '请输入项目名称' }]}
                    >
                      <Input placeholder="项目名称" />
                    </Form.Item>

                    <Form.Item
                      label="URL Slug"
                      name="url_slug"
                      tooltip="兼容旧方式，建议使用上面的 GitLab URL + Slug"
                    >
                      <Input placeholder="url-slug" />
                    </Form.Item>
                  </div>
                ),
              },
              {
                key: 'notification',
                label: '🔔 通知配置',
                children: (
                  <div style={{ padding: '8px 0' }}>
                    <Form.Item label="钉钉 Webhook URL" name="dingtalk_url">
                      <Input.TextArea rows={2} placeholder="钉钉机器人 Webhook URL" />
                    </Form.Item>

                    <Form.Item 
                      label="启用钉钉通知" 
                      name="dingtalk_enabled" 
                      valuePropName="checked"
                      tooltip="开启后将发送钉钉通知"
                    >
                      <Switch />
                    </Form.Item>

                    <Form.Item label="飞书 Webhook URL" name="feishu_url">
                      <Input.TextArea rows={2} placeholder="飞书机器人 Webhook URL" />
                    </Form.Item>

                    <Form.Item 
                      label="启用飞书通知" 
                      name="feishu_enabled" 
                      valuePropName="checked"
                      tooltip="开启后将发送飞书通知"
                    >
                      <Switch />
                    </Form.Item>

                    <Form.Item label="企业微信 Webhook URL" name="wecom_url">
                      <Input.TextArea rows={2} placeholder="企业微信机器人 Webhook URL" />
                    </Form.Item>

                    <Form.Item 
                      label="启用企业微信通知" 
                      name="wecom_enabled" 
                      valuePropName="checked"
                      tooltip="开启后将发送企业微信通知"
                    >
                      <Switch />
                    </Form.Item>

                    <Form.Item 
                      label="启用日报" 
                      name="daily_report_enabled" 
                      valuePropName="checked"
                      tooltip="开启后将发送该项目的代码提交日报"
                    >
                      <Switch />
                    </Form.Item>
                  </div>
                ),
              },
              {
                key: 'advanced',
                label: '⚙️ 高级配置',
                children: (
                  <div style={{ padding: '8px 0' }}>
                    <Form.Item label="自定义系统 Prompt" name="custom_prompt_system">
                      <Input.TextArea rows={3} placeholder="自定义系统提示词" />
                    </Form.Item>

                    <Form.Item label="自定义用户 Prompt" name="custom_prompt_user">
                      <Input.TextArea rows={3} placeholder="自定义用户提示词" />
                    </Form.Item>

                    <Form.Item label="GitLab Token" name="gitlab_token">
                      <Input.Password placeholder="GitLab Personal Access Token" />
                    </Form.Item>

                    <Form.Item 
                      label="评审风格" 
                      name="review_style" 
                      tooltip="选择代码评审的风格，随机风格会从四种风格中随机选择"
                    >
                      <Select 
                        placeholder="选择评审风格" 
                        allowClear
                        options={[
                          { label: '专业风格', value: 'professional' },
                          { label: '讽刺风格', value: 'sarcastic' },
                          { label: '温和风格', value: 'gentle' },
                          { label: '幽默风格', value: 'humorous' },
                          { label: '🎲 随机风格', value: 'random' },
                        ]}
                      />
                    </Form.Item>

                    <Form.Item 
                      label="支持的文件扩展名" 
                      name="supported_extensions" 
                      tooltip="指定需要评审的文件扩展名，用逗号分隔。如：.java,.py,.js,.ts。留空则使用环境变量或系统默认值"
                    >
                      <Input.TextArea 
                        rows={2} 
                        placeholder=".java,.py,.php,.js,.ts,.tsx,.vue,.go,.rs,.java,.c,.cpp,.h" 
                      />
                    </Form.Item>
                  </div>
                ),
              },
            ]}
          />

          <Form.Item style={{ marginBottom: 0, textAlign: 'right', marginTop: 24 }}>
            <Button style={{ marginRight: 8 }} onClick={() => setModalVisible(false)}>
              取消
            </Button>
            <Button type="primary" htmlType="submit">
              {editingRecord ? '更新' : '创建'}
            </Button>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default Webhooks;

import { useState, useEffect } from 'react';
import { Table, Button, Modal, Form, Input, message, Popconfirm } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons';
import { branchWebhookApi } from '@/api/branch-webhooks';
import type { BranchWebhook, BranchWebhookForm } from '@/types';

const BranchWebhooks: React.FC = () => {
  const [data, setData] = useState<BranchWebhook[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [editingRecord, setEditingRecord] = useState<BranchWebhook | null>(null);
  const [form] = Form.useForm();

  const fetchData = async () => {
    setLoading(true);
    try {
      const response = await branchWebhookApi.getAll();
      setData(response);
    } catch (error) {
      console.error('Failed to fetch branch webhooks:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleCreate = () => {
    setEditingRecord(null);
    form.resetFields();
    setModalVisible(true);
  };

  const handleEdit = (record: BranchWebhook) => {
    setEditingRecord(record);
    form.setFieldsValue(record);
    setModalVisible(true);
  };

  const handleDelete = async (id: number) => {
    try {
      await branchWebhookApi.delete(id);
      message.success('删除成功');
      fetchData();
    } catch (error) {
      console.error('Failed to delete branch webhook:', error);
    }
  };

  const handleSubmit = async (values: BranchWebhookForm) => {
    try {
      if (editingRecord) {
        await branchWebhookApi.update(editingRecord.id, values);
        message.success('更新成功');
      } else {
        await branchWebhookApi.create(values);
        message.success('创建成功');
      }
      setModalVisible(false);
      fetchData();
    } catch (error) {
      console.error('Failed to save branch webhook:', error);
    }
  };

  const columns = [
    { 
      title: 'ID', 
      dataIndex: 'id', 
      key: 'id', 
      width: 60 
    },
    { 
      title: 'GitLab URL', 
      dataIndex: 'gitlab_base_url', 
      key: 'gitlab_base_url',
      width: 180,
      ellipsis: true,
    },
    { 
      title: '项目 Slug', 
      dataIndex: 'project_slug', 
      key: 'project_slug',
      width: 150,
      ellipsis: true,
    },
    { 
      title: '分支匹配模式', 
      dataIndex: 'branch_pattern', 
      key: 'branch_pattern',
      width: 150,
      ellipsis: true,
    },
    { 
      title: '钉钉 Webhook', 
      dataIndex: 'dingtalk_url', 
      key: 'dingtalk_url',
      width: 120,
      ellipsis: true,
    },
    { 
      title: '飞书 Webhook', 
      dataIndex: 'feishu_url', 
      key: 'feishu_url',
      width: 120,
      ellipsis: true,
    },
    { 
      title: '企业微信 Webhook', 
      dataIndex: 'wecom_url', 
      key: 'wecom_url',
      width: 120,
      ellipsis: true,
    },
    {
      title: '操作',
      key: 'action',
      width: 120,
      render: (_: any, record: BranchWebhook) => (
        <span>
          <Button
            type="link"
            size="small"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
          >
            编辑
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
        columns={columns}
        dataSource={data}
        rowKey="id"
        loading={loading}
        pagination={{ pageSize: 20 }}
        scroll={{ x: 1000 }}
      />

      <Modal
        title={editingRecord ? '编辑分支配置' : '新建分支配置'}
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        footer={null}
        width={600}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
        >
          <Form.Item
            label="GitLab 基础 URL"
            name="gitlab_base_url"
            rules={[{ required: true, message: '请输入 GitLab 基础 URL' }]}
          >
            <Input placeholder="https://gitlab.com" />
          </Form.Item>

          <Form.Item
            label="项目 Slug"
            name="project_slug"
            rules={[{ required: true, message: '请输入项目 Slug' }]}
          >
            <Input placeholder="group/project" />
          </Form.Item>

          <Form.Item
            label="分支匹配模式"
            name="branch_pattern"
            tooltip="支持通配符，如 feature/* 或 release/*"
            rules={[{ required: true, message: '请输入分支匹配模式' }]}
          >
            <Input placeholder="feature/* 或 release/*" />
          </Form.Item>

          <Form.Item label="钉钉 Webhook URL" name="dingtalk_url">
            <Input.TextArea rows={2} placeholder="钉钉机器人 Webhook URL" />
          </Form.Item>

          <Form.Item label="飞书 Webhook URL" name="feishu_url">
            <Input.TextArea rows={2} placeholder="飞书机器人 Webhook URL" />
          </Form.Item>

          <Form.Item label="企业微信 Webhook URL" name="wecom_url">
            <Input.TextArea rows={2} placeholder="企业微信机器人 Webhook URL" />
          </Form.Item>

          <Form.Item label="自定义系统 Prompt" name="custom_prompt_system">
            <Input.TextArea rows={3} placeholder="自定义系统提示词" />
          </Form.Item>

          <Form.Item label="自定义用户 Prompt" name="custom_prompt_user">
            <Input.TextArea rows={3} placeholder="自定义用户提示词" />
          </Form.Item>

          <Form.Item label="GitLab Token" name="gitlab_token">
            <Input.Password placeholder="GitLab Personal Access Token" />
          </Form.Item>

          <Form.Item style={{ marginBottom: 0, textAlign: 'right' }}>
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

export default BranchWebhooks;

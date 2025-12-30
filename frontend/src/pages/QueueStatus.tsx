import { useState, useEffect } from 'react';
import { Card, Statistic, Row, Col, Table, Tag, Alert, Button, Empty } from 'antd';
import { ReloadOutlined, HourglassOutlined, SyncOutlined, CheckCircleOutlined, CloseCircleOutlined, StopOutlined } from '@ant-design/icons';
import { reviewsApi } from '@/api/reviews';
import type { QueueStatsResponse } from '@/types';

const QueueStatus: React.FC = () => {
  const [queueData, setQueueData] = useState<QueueStatsResponse | null>(null);
  const [loading, setLoading] = useState(false);

  const fetchQueueStatus = async () => {
    setLoading(true);
    try {
      const data = await reviewsApi.getQueueStatus();
      setQueueData(data);
    } catch (error) {
      console.error('Failed to fetch queue status:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchQueueStatus();
  }, []);

  if (!queueData) return null;

  // 不支持队列状态统计
  if (!queueData.supported) {
    return (
      <div>
        <Alert
          message="队列状态统计功能"
          description={queueData.message || '队列状态统计功能仅支持 Redis Queue (RQ) 模式'}
          type="warning"
          showIcon
          style={{ marginBottom: 24 }}
        />
        <Card>
          <Empty
            description={
              <div>
                <p>当前队列驱动类型: <Tag color="blue">{queueData.queue_driver}</Tag></p>
                <p>请切换到 Redis Queue 模式以查看队列状态</p>
              </div>
            }
          />
        </Card>
      </div>
    );
  }

  const stats: { pending?: number; processing?: number; completed?: number; failed?: number } = queueData.stats || {};
  const byProject = queueData.by_project || {};

  // 项目表格列
  const projectColumns = [
    { 
      title: '项目名称', 
      dataIndex: 'project_name', 
      key: 'project_name',
      render: (text: string, record: any) => (
        <div>
          <div style={{ fontWeight: 'bold' }}>{text}</div>
          <div style={{ fontSize: '12px', color: '#999' }}>{record.tasks?.[0]?.project_name}</div>
        </div>
      )
    },
    { 
      title: '等待中', 
      dataIndex: 'pending', 
      key: 'pending',
      render: (count: number) => count > 0 ? <Tag color="orange">{count}</Tag> : <Tag>{count}</Tag>
    },
    { 
      title: '处理中', 
      dataIndex: 'processing', 
      key: 'processing',
      render: (count: number) => count > 0 ? <Tag color="blue">{count}</Tag> : <Tag>{count}</Tag>
    },
    {
      title: '任务列表',
      dataIndex: 'tasks',
      key: 'tasks',
      render: (tasks: any[]) => tasks.length,
    },
  ];

  const projectData = Object.entries(byProject).map(([projectName, info]) => ({
    project_name: projectName,
    pending: info.pending,
    processing: info.processing,
    tasks: info.tasks,
    key: projectName,
  }));

  // 任务详情表格列
  const taskColumns = [
    { title: '任务ID', dataIndex: 'job_id', key: 'job_id', render: (id: string) => <code>{id.slice(0, 8)}...</code> },
    { title: '事件类型', dataIndex: 'event_type', key: 'event_type', render: (type: string) => <Tag>{type}</Tag> },
    { title: '作者', dataIndex: 'author', key: 'author' },
    { 
      title: '分支', 
      key: 'branch',
      render: (record: any) => {
        if (record.event_type === 'merge_request') {
          return `${record.source_branch} → ${record.target_branch}`;
        } else if (record.event_type === 'push') {
          return record.branch;
        }
        return '-';
      }
    },
    { 
      title: '文件数/提交数', 
      key: 'files_commits',
      render: (record: any) => {
        if (record.changed_files !== undefined) {
          return <Tag color="green">{record.changed_files} 文件</Tag>;
        } else if (record.commit_count !== undefined) {
          return <Tag color="green">{record.commit_count} 提交</Tag>;
        }
        return '-';
      }
    },
    { 
      title: '状态', 
      dataIndex: 'status', 
      key: 'status',
      render: (status: string) => {
        const statusMap: Record<string, { color: string; icon: React.ReactNode; text: string }> = {
          pending: { color: 'orange', icon: <HourglassOutlined />, text: '等待中' },
          processing: { color: 'blue', icon: <SyncOutlined spin />, text: '处理中' },
          failed: { color: 'red', icon: <CloseCircleOutlined />, text: '失败' },
          completed: { color: 'green', icon: <CheckCircleOutlined />, text: '已完成' },
        };
        const config = statusMap[status] || { color: 'default', icon: <StopOutlined />, text: status };
        return <Tag color={config.color} icon={config.icon}>{config.text}</Tag>;
      }
    },
    { title: '创建时间', dataIndex: 'created_at', key: 'created_at' },
    {
      title: '操作',
      key: 'action',
      render: (record: any) => record.url ? (
        <a href={record.url} target="_blank" rel="noopener noreferrer">查看</a>
      ) : null,
    },
  ];

  // 展开行显示任务详情
  const expandedRowRender = (record: any) => {
    const tasks = record.tasks || [];
    return (
      <Table
        columns={taskColumns}
        dataSource={tasks}
        rowKey="job_id"
        pagination={false}
        size="small"
        showHeader={false}
      />
    );
  };

  return (
    <div>
      <div style={{ marginBottom: 16 }}>
        <Button
          type="primary"
          icon={<ReloadOutlined />}
          onClick={fetchQueueStatus}
          loading={loading}
        >
          刷新状态
        </Button>
      </div>

      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card>
            <Statistic
              title="等待中"
              value={('pending' in stats ? stats.pending : 0)}
              prefix={<HourglassOutlined />}
              valueStyle={{ color: '#faad14' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="处理中"
              value={('processing' in stats ? stats.processing : 0)}
              prefix={<SyncOutlined spin />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="已完成"
              value={('completed' in stats ? stats.completed : 0)}
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="失败"
              value={('failed' in stats ? stats.failed : 0)}
              prefix={<CloseCircleOutlined />}
              valueStyle={{ color: '#ff4d4f' }}
            />
          </Card>
        </Col>
      </Row>

      <Alert
        message="队列驱动类型"
        description={
          <span>
            当前使用: <Tag color="blue">{queueData.queue_driver}</Tag>
            {queueData.total !== undefined && ` | 总任务数: ${queueData.total}`}
          </span>
        }
        type="info"
        showIcon
        style={{ marginBottom: 16 }}
      />

      <Card title="按项目分组的队列状态">
        <Table
          columns={projectColumns}
          dataSource={projectData}
          rowKey="project_name"
          pagination={false}
          expandable={{
            expandedRowRender,
            expandRowByClick: true,
            rowExpandable: (record) => record.tasks && record.tasks.length > 0,
          }}
          loading={loading}
        />
      </Card>
    </div>
  );
};

export default QueueStatus;

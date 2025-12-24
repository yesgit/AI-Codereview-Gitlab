import { useState, useEffect } from 'react';
import { Table, Tabs, Select, DatePicker, Space, Tag, Button, message } from 'antd';
import { SendOutlined } from '@ant-design/icons';
import { reviewsApi } from '@/api/reviews';
import type { ReviewLog } from '@/types';
import type { Dayjs } from 'dayjs';

const { RangePicker } = DatePicker;
const { TabPane } = Tabs;

const Reviews: React.FC = () => {
  const [activeTab, setActiveTab] = useState('mr');
  const [data, setData] = useState<ReviewLog[]>([]);
  const [loading, setLoading] = useState(false);
  const [total, setTotal] = useState(0);
  const [averageScore, setAverageScore] = useState(0);
  const [authors, setAuthors] = useState<string[]>([]);
  const [projects, setProjects] = useState<string[]>([]);
  const [selectedAuthors, setSelectedAuthors] = useState<string[]>([]);
  const [selectedProjects, setSelectedProjects] = useState<string[]>([]);
  const [dateRange, setDateRange] = useState<[Dayjs, Dayjs] | null>(null);
  const [sendingReport, setSendingReport] = useState(false);

  const fetchData = async () => {
    setLoading(true);
    try {
      const params: any = {};
      if (selectedAuthors.length > 0) params.authors = selectedAuthors;
      if (selectedProjects.length > 0) params.project_names = selectedProjects;
      if (dateRange) {
        params.updated_at_gte = dateRange[0].unix();
        params.updated_at_lte = dateRange[1].unix();
      }

      const response = activeTab === 'mr' 
        ? await reviewsApi.getMrReviews(params)
        : await reviewsApi.getPushReviews(params);
      
      setData(response.data);
      setTotal(response.total);
      setAverageScore(response.average_score);
      
      // 提取唯一值用于筛选
      const uniqueAuthors = Array.from(new Set(response.data.map((item: ReviewLog) => item.author).filter((s): s is string => !!s)));
      const uniqueProjects = Array.from(new Set(response.data.map((item: ReviewLog) => item.project_name).filter((s): s is string => !!s)));
      setAuthors(uniqueAuthors);
      setProjects(uniqueProjects);
    } catch (error) {
      console.error('Failed to fetch reviews:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [activeTab, selectedAuthors, selectedProjects, dateRange]);

  const handleSendDailyReport = async () => {
    setSendingReport(true);
    try {
      await reviewsApi.sendDailyReport();
      message.success('日报发送成功！');
    } catch (error) {
      console.error('Failed to send daily report:', error);
      message.error('日报发送失败，请查看日志。');
    } finally {
      setSendingReport(false);
    }
  };

  const mrColumns = [
    { title: '项目', dataIndex: 'project_name', key: 'project_name', width: 150 },
    { title: '作者', dataIndex: 'author', key: 'author', width: 100 },
    { title: '源分支', dataIndex: 'source_branch', key: 'source_branch', width: 120 },
    { title: '目标分支', dataIndex: 'target_branch', key: 'target_branch', width: 120 },
    { title: '评分', dataIndex: 'score', key: 'score', width: 80, render: (score: number) => (
      <Tag color={score >= 80 ? 'green' : score >= 60 ? 'orange' : 'red'}>{score}</Tag>
    )},
    { title: '时间', dataIndex: 'updated_at', key: 'updated_at', width: 160 },
    { title: '提交信息', dataIndex: 'commit_messages', key: 'commit_messages', ellipsis: true },
    { title: '添加行数', dataIndex: 'additions', key: 'additions', width: 80 },
    { title: '删除行数', dataIndex: 'deletions', key: 'deletions', width: 80 },
  ];

  const pushColumns = [
    { title: '项目', dataIndex: 'project_name', key: 'project_name', width: 150 },
    { title: '作者', dataIndex: 'author', key: 'author', width: 100 },
    { title: '分支', dataIndex: 'branch', key: 'branch', width: 150 },
    { title: '评分', dataIndex: 'score', key: 'score', width: 80, render: (score: number) => (
      <Tag color={score >= 80 ? 'green' : score >= 60 ? 'orange' : 'red'}>{score}</Tag>
    )},
    { title: '时间', dataIndex: 'updated_at', key: 'updated_at', width: 160 },
    { title: '提交信息', dataIndex: 'commit_messages', key: 'commit_messages', ellipsis: true },
    { title: '添加行数', dataIndex: 'additions', key: 'additions', width: 80 },
    { title: '删除行数', dataIndex: 'deletions', key: 'deletions', width: 80 },
  ];

  return (
    <div>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Space>
          <Select
            mode="multiple"
            placeholder="选择作者"
            style={{ width: 200 }}
            value={selectedAuthors}
            onChange={setSelectedAuthors}
            options={authors.map(a => ({ label: a, value: a }))}
            allowClear
          />
          <Select
            mode="multiple"
            placeholder="选择项目"
            style={{ width: 200 }}
            value={selectedProjects}
            onChange={setSelectedProjects}
            options={projects.map(p => ({ label: p, value: p }))}
            allowClear
          />
          <RangePicker onChange={(dates) => setDateRange(dates as any)} />
        </Space>
        <Space>
          <Button 
            type="primary"
            icon={<SendOutlined />}
            onClick={handleSendDailyReport}
            loading={sendingReport}
          >
            手动发送日报
          </Button>
          <div>
            共 {total} 条记录，平均评分: <strong>{averageScore.toFixed(1)}</strong>
          </div>
        </Space>
      </div>
      
      <Tabs activeKey={activeTab} onChange={setActiveTab}>
        <TabPane tab={`MR 审查记录 (${data.length})`} key="mr">
          <Table
            columns={mrColumns}
            dataSource={data}
            rowKey="id"
            loading={loading}
            pagination={{ pageSize: 20 }}
            scroll={{ x: 1200 }}
          />
        </TabPane>
        <TabPane tab={`Push 审查记录 (${data.length})`} key="push">
          <Table
            columns={pushColumns}
            dataSource={data}
            rowKey="id"
            loading={loading}
            pagination={{ pageSize: 20 }}
            scroll={{ x: 1200 }}
          />
        </TabPane>
      </Tabs>
    </div>
  );
};

export default Reviews;

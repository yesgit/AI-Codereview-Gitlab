import { useState, useEffect } from 'react';
import { Card, Statistic, Row, Col, Table, Tabs } from 'antd';
import { ArrowUpOutlined, ArrowDownOutlined } from '@ant-design/icons';
import { reviewsApi } from '@/api/reviews';
import type { StatsResponse } from '@/types';

const { TabPane } = Tabs;

const Stats: React.FC = () => {
  const [stats, setStats] = useState<StatsResponse | null>(null);
  const [loading, setLoading] = useState(false);

  const fetchStats = async () => {
    setLoading(true);
    try {
      const data = await reviewsApi.getStats();
      setStats(data);
    } catch (error) {
      console.error('Failed to fetch stats:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStats();
  }, []);

  if (!stats) return null;

  const mrAuthorColumns = [
    { title: '作者', dataIndex: 'author', key: 'author' },
    { title: '审查次数', dataIndex: 'count', key: 'count', sorter: (a: any, b: any) => a.count - b.count },
    { title: '平均评分', dataIndex: 'score', key: 'score', render: (score: number) => score.toFixed(1) },
    { title: '添加行数', dataIndex: 'additions', key: 'additions', render: (val: number) => val.toLocaleString() },
    { title: '删除行数', dataIndex: 'deletions', key: 'deletions', render: (val: number) => val.toLocaleString() },
  ];

  const mrProjectColumns = [
    { title: '项目', dataIndex: 'project', key: 'project' },
    { title: '审查次数', dataIndex: 'count', key: 'count', sorter: (a: any, b: any) => a.count - b.count },
    { title: '平均评分', dataIndex: 'score', key: 'score', render: (score: number) => score.toFixed(1) },
  ];

  const mrAuthorData = Object.entries(stats.mr.author_counts).map(([author, count]) => ({
    author,
    count,
    score: stats.mr.author_scores[author] || 0,
    additions: stats.mr.author_additions[author] || 0,
    deletions: stats.mr.author_deletions[author] || 0,
  }));

  const mrProjectData = Object.entries(stats.mr.project_counts).map(([project, count]) => ({
    project,
    count,
    score: stats.mr.project_scores[project] || 0,
  }));

  const pushAuthorColumns = [
    { title: '作者', dataIndex: 'author', key: 'author' },
    { title: '审查次数', dataIndex: 'count', key: 'count', sorter: (a: any, b: any) => a.count - b.count },
  ];

  const pushAuthorData = Object.entries(stats.push.author_counts).map(([author, count]) => ({
    author,
    count,
  }));

  return (
    <div>
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={12}>
          <Card loading={loading}>
            <Statistic
              title="MR 总审查次数"
              value={stats.mr.total}
              prefix={<ArrowUpOutlined />}
            />
          </Card>
        </Col>
        <Col span={12}>
          <Card loading={loading}>
            <Statistic
              title="MR 平均评分"
              value={stats.mr.average_score}
              precision={1}
              suffix="分"
            />
          </Card>
        </Col>
      </Row>
      
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={12}>
          <Card loading={loading}>
            <Statistic
              title="Push 总审查次数"
              value={stats.push.total}
              prefix={<ArrowDownOutlined />}
            />
          </Card>
        </Col>
        <Col span={12}>
          <Card loading={loading}>
            <Statistic
              title="Push 平均评分"
              value={stats.push.average_score}
              precision={1}
              suffix="分"
            />
          </Card>
        </Col>
      </Row>

      <Tabs defaultActiveKey="mr">
        <TabPane tab="MR 统计" key="mr">
          <Card title="作者统计" style={{ marginBottom: 16 }}>
            <Table
              columns={mrAuthorColumns}
              dataSource={mrAuthorData}
              rowKey="author"
              pagination={false}
              size="small"
            />
          </Card>
          <Card title="项目统计">
            <Table
              columns={mrProjectColumns}
              dataSource={mrProjectData}
              rowKey="project"
              pagination={false}
              size="small"
            />
          </Card>
        </TabPane>
        <TabPane tab="Push 统计" key="push">
          <Card title="作者统计">
            <Table
              columns={pushAuthorColumns}
              dataSource={pushAuthorData}
              rowKey="author"
              pagination={false}
              size="small"
            />
          </Card>
        </TabPane>
      </Tabs>
    </div>
  );
};

export default Stats;

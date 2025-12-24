import { Layout, Menu, Button } from 'antd';
import { useNavigate, useLocation, Outlet } from 'react-router-dom';
import {
  FileSearchOutlined,
  BarChartOutlined,
  SettingOutlined,
  BranchesOutlined,
  LogoutOutlined,
} from '@ant-design/icons';

const { Header, Sider, Content } = Layout;

const MainLayout: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const username = localStorage.getItem('username');

  const menuItems = [
    { key: '/reviews', label: '查询审查', icon: <FileSearchOutlined /> },
    { key: '/stats', label: '统计分析', icon: <BarChartOutlined /> },
    { key: '/webhooks', label: '项目配置', icon: <SettingOutlined /> },
    { key: '/branch-webhooks', label: '分支配置', icon: <BranchesOutlined /> },
  ];

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('username');
    navigate('/login');
  };

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider width={200} theme="light">
        <div style={{ 
          height: 64, 
          display: 'flex', 
          alignItems: 'center', 
          justifyContent: 'center',
          fontSize: 18,
          fontWeight: 'bold',
          borderBottom: '1px solid #f0f0f0'
        }}>
          AI Code Review
        </div>
        <Menu
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
        />
      </Sider>
      <Layout>
        <Header style={{ 
          background: '#fff', 
          padding: '0 24px', 
          display: 'flex', 
          justifyContent: 'space-between',
          alignItems: 'center',
          borderBottom: '1px solid #f0f0f0'
        }}>
          <div />
          <Button 
            type="text" 
            icon={<LogoutOutlined />}
            onClick={handleLogout}
          >
            退出 ({username})
          </Button>
        </Header>
        <Content style={{ padding: '24px' }}>
          <div style={{ background: '#fff', padding: 24, minHeight: 400 }}>
            <Outlet />
          </div>
        </Content>
      </Layout>
    </Layout>
  );
};

export default MainLayout;

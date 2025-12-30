import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ConfigProvider, theme } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import Login from '@/pages/Login';
import MainLayout from '@/components/MainLayout';
import Reviews from '@/pages/Reviews';
import Stats from '@/pages/Stats';
import QueueStatus from '@/pages/QueueStatus';
import Webhooks from '@/pages/Webhooks';
import BranchWebhooks from '@/pages/BranchWebhooks';

const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const token = localStorage.getItem('token');
  if (!token) {
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
};

const App: React.FC = () => {
  return (
    <ConfigProvider
      locale={zhCN}
      theme={{
        algorithm: theme.defaultAlgorithm,
      }}
    >
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route
            path="/"
            element={
              <ProtectedRoute>
                <MainLayout />
              </ProtectedRoute>
            }
          >
            <Route index element={<Navigate to="/reviews" replace />} />
            <Route path="reviews" element={<Reviews />} />
            <Route path="stats" element={<Stats />} />
            <Route path="queue-status" element={<QueueStatus />} />
            <Route path="webhooks" element={<Webhooks />} />
            <Route path="branch-webhooks" element={<BranchWebhooks />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </ConfigProvider>
  );
};

export default App;

import React, { useState, useEffect } from 'react';
import { Layout, Menu, Typography, theme } from 'antd';
import { Routes, Route, Link, useLocation } from 'react-router-dom';
import { 
  AudioOutlined, 
  AppstoreOutlined, 
  BgColorsOutlined, 
  HistoryOutlined,
  CloudOutlined 
} from '@ant-design/icons';

import MeetingProcessor from './components/MeetingProcessor';
import PatternLibrary from './components/PatternLibrary';
import DyeLibrary from './components/DyeLibrary';
import MeetingHistory from './components/MeetingHistory';
import MeetingDetail from './components/MeetingDetail';

const { Header, Content, Sider } = Layout;
const { Title } = Typography;

const App = () => {
  const location = useLocation();
  const [collapsed, setCollapsed] = useState(false);
  const {
    token: { colorBgContainer, borderRadiusLG },
  } = theme.useToken();

  const menuItems = [
    {
      key: '/',
      icon: <AudioOutlined />,
      label: <Link to="/">会议处理</Link>,
    },
    {
      key: '/patterns',
      icon: <AppstoreOutlined />,
      label: <Link to="/patterns">图案设计库</Link>,
    },
    {
      key: '/dyes',
      icon: <BgColorsOutlined />,
      label: <Link to="/dyes">植物染料色谱</Link>,
    },
    {
      key: '/history',
      icon: <HistoryOutlined />,
      label: <Link to="/history">历史记录</Link>,
    },
  ];

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider 
        collapsible 
        collapsed={collapsed} 
        onCollapse={(value) => setCollapsed(value)}
        theme="dark"
        style={{
          background: 'linear-gradient(180deg, #1e3a5f 0%, #2d5a87 100%)',
        }}
      >
        <div style={{ 
          height: 64, 
          display: 'flex', 
          alignItems: 'center', 
          justifyContent: 'center',
          color: 'white',
          padding: '0 16px',
          borderBottom: '1px solid rgba(255,255,255,0.1)'
        }}>
          <CloudOutlined style={{ fontSize: 24, marginRight: collapsed ? 0 : 8 }} />
          {!collapsed && <Title level={4} style={{ color: 'white', margin: 0 }}>靛蓝纪要</Title>}
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          style={{ 
            borderRight: 'none',
            background: 'transparent',
            marginTop: 16
          }}
        />
      </Sider>
      <Layout>
        <Header 
          style={{ 
            padding: '0 24px', 
            background: colorBgContainer,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            borderBottom: '1px solid #e0e0e0'
          }}
        >
          <div>
            <Title level={3} style={{ margin: 0, color: '#1e3a5f' }}>
              手工扎染工坊产品开发会议系统
            </Title>
            <p style={{ margin: '4px 0 0 0', color: '#666', fontSize: 13 }}>
              记录工艺灵感，传承靛蓝智慧
            </p>
          </div>
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontSize: 12, color: '#999' }}>手工艺人讨论轻柔录制</div>
            <div style={{ fontSize: 12, color: '#999' }}>AI智能识别与摘要生成</div>
          </div>
        </Header>
        <Content
          style={{
            margin: '24px',
            padding: 24,
            minHeight: 280,
            background: colorBgContainer,
            borderRadius: borderRadiusLG,
          }}
        >
          <Routes>
            <Route path="/" element={<MeetingProcessor />} />
            <Route path="/patterns" element={<PatternLibrary />} />
            <Route path="/dyes" element={<DyeLibrary />} />
            <Route path="/history" element={<MeetingHistory />} />
            <Route path="/meeting/:id" element={<MeetingDetail />} />
          </Routes>
        </Content>
      </Layout>
    </Layout>
  );
};

export default App;

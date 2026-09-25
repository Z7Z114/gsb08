import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { 
  Card, 
  Typography, 
  Spin, 
  Button, 
  Space, 
  Tag, 
  Divider,
  Table,
  Row,
  Col,
  Timeline,
  message
} from 'antd';
import { 
  ArrowLeftOutlined, 
  MailOutlined, 
  DownloadOutlined,
  CalendarOutlined,
  UserOutlined
} from '@ant-design/icons';
import { getMeeting, sendEmail } from '../services/api';

const { Title, Text, Paragraph } = Typography;

const MeetingDetail = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [meeting, setMeeting] = useState(null);
  const [loading, setLoading] = useState(true);
  const [emailLoading, setEmailLoading] = useState(false);

  useEffect(() => {
    loadMeeting();
  }, [id]);

  const loadMeeting = async () => {
    try {
      const data = await getMeeting(id);
      setMeeting(data);
    } catch (error) {
      message.error('加载失败：' + error.message);
    } finally {
      setLoading(false);
    }
  };

  const handleSendEmail = async () => {
    setEmailLoading(true);
    try {
      await sendEmail(id, []);
      message.success('邮件已发送给买手店！');
    } catch (error) {
      message.error('发送失败：' + error.message);
    } finally {
      setEmailLoading(false);
    }
  };

  const handleDownload = () => {
    if (!meeting) return;
    
    const content = meeting.summary?.summary || '';
    const blob = new Blob([content], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${meeting.summary?.series_theme || '会议纪要'}.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const getRoleColor = (role) => {
    const colors = {
      '设计师': 'red',
      '染娘': 'green',
      '手工艺人': 'orange',
      '参与者': 'blue'
    };
    return colors[role] || 'default';
  };

  const getRoleClass = (role) => {
    const classes = {
      '设计师': 'speaker-designer',
      '染娘': 'speaker-dyer',
      '手工艺人': 'speaker-artisan',
      '参与者': 'speaker-other'
    };
    return classes[role] || 'speaker-other';
  };

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const costColumns = [
    {
      title: '项目',
      dataIndex: 'item',
      key: 'item',
      render: (text) => <Text strong>{text}</Text>,
    },
    {
      title: '成本（元）',
      dataIndex: 'cost',
      key: 'cost',
      render: (text) => <Text type="success">¥{text}</Text>,
    },
    {
      title: '占比',
      dataIndex: 'percentage',
      key: 'percentage',
      render: (text) => <Tag color="blue">{text}</Tag>,
    },
  ];

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '60px' }}>
        <Spin size="large" />
      </div>
    );
  }

  if (!meeting) {
    return (
      <div style={{ textAlign: 'center', padding: '60px' }}>
        <p>会议记录不存在</p>
        <Button onClick={() => navigate('/history')}>返回列表</Button>
      </div>
    );
  }

  const cost = meeting.summary?.cost_breakdown;
  const costData = cost ? [
    { item: '面料成本', cost: cost.fabric_cost, percentage: cost.fabric_percentage },
    { item: '染料成本', cost: cost.dye_cost, percentage: cost.dye_percentage },
    { item: '人工成本', cost: cost.labor_cost, percentage: cost.labor_percentage },
    { item: '水电能耗', cost: cost.utility_cost, percentage: cost.utility_percentage },
    { item: '其他费用', cost: cost.other_cost, percentage: cost.other_percentage },
  ] : [];

  const segments = meeting.transcript?.segments || [];
  const participants = [...new Set(segments.map(s => s.role))];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <div>
          <Button 
            icon={<ArrowLeftOutlined />} 
            onClick={() => navigate('/history')}
            style={{ marginBottom: 12 }}
          >
            返回列表
          </Button>
          <Title level={2} style={{ color: '#1e3a5f', marginTop: 0, marginBottom: 8 }}>
            {meeting.summary?.series_theme || '会议详情'}
          </Title>
          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            <span style={{ color: '#666' }}>
              <CalendarOutlined style={{ marginRight: 4 }} />
              {new Date(meeting.timestamp).toLocaleString('zh-CN')}
            </span>
            <span style={{ color: '#666' }}>
              <UserOutlined style={{ marginRight: 4 }} />
              {participants.length} 位参与者
            </span>
          </div>
        </div>
        <Space>
          <Button icon={<DownloadOutlined />} onClick={handleDownload}>
            下载纪要
          </Button>
          <Button 
            type="primary" 
            icon={<MailOutlined />} 
            loading={emailLoading}
            onClick={handleSendEmail}
          >
            发送给买手店
          </Button>
        </Space>
      </div>

      <Row gutter={[24, 24]}>
        <Col xs={24} lg={16}>
          <Card 
            title="会议摘要" 
            bordered={false} 
            style={{ marginBottom: 24, boxShadow: '0 2px 8px rgba(0,0,0,0.06)' }}
          >
            <div className="markdown-content">
              {meeting.summary?.summary || '暂无摘要'}
            </div>
          </Card>

          <Card 
            title="会议转录" 
            bordered={false} 
            style={{ boxShadow: '0 2px 8px rgba(0,0,0,0.06)' }}
          >
            <Timeline
              mode="left"
              items={segments.map((seg, i) => ({
                color: getRoleColor(seg.role),
                label: (
                  <div style={{ textAlign: 'right', paddingRight: 12 }}>
                    <div style={{ fontSize: 12, color: '#999' }}>{formatTime(seg.start)}</div>
                    <Tag color={getRoleColor(seg.role)} style={{ marginTop: 4 }}>
                      {seg.role}
                    </Tag>
                  </div>
                ),
                children: (
                  <div style={{ padding: '8px 12px', background: '#fafafa', borderRadius: 8 }}>
                    <Text className={getRoleClass(seg.role)} style={{ fontWeight: 500 }}>
                      {seg.role}
                    </Text>
                    <p style={{ marginTop: 4, marginBottom: 0, color: '#333' }}>{seg.text}</p>
                  </div>
                ),
              }))}
            />
          </Card>
        </Col>

        <Col xs={24} lg={8}>
          {meeting.patterns && (
            <Card 
              title="识别的工艺模式" 
              bordered={false} 
              style={{ marginBottom: 24, boxShadow: '0 2px 8px rgba(0,0,0,0.06)' }}
            >
              <div style={{ marginBottom: 16 }}>
                <Text type="secondary" style={{ display: 'block', marginBottom: 8 }}>扎结手法：</Text>
                <Space wrap>
                  {meeting.patterns.tie_methods?.map((m, i) => (
                    <Tag key={i} color="geekblue">{m}</Tag>
                  ))}
                </Space>
              </div>
              <div style={{ marginBottom: 16 }}>
                <Text type="secondary" style={{ display: 'block', marginBottom: 8 }}>色彩提及：</Text>
                <Space wrap>
                  {meeting.patterns.color_mentions?.map((c, i) => (
                    <Tag key={i} color="cyan">{c}</Tag>
                  ))}
                </Space>
              </div>
              <div>
                <Text type="secondary" style={{ display: 'block', marginBottom: 8 }}>染色次数讨论：</Text>
                <Text strong style={{ fontSize: 16, color: '#1e3a5f' }}>
                  {meeting.patterns.dye_count_mentions} 次
                </Text>
              </div>
            </Card>
          )}

          {cost && (
            <Card 
              title="成本核算" 
              bordered={false} 
              style={{ marginBottom: 24, boxShadow: '0 2px 8px rgba(0,0,0,0.06)' }}
            >
              <Table
                columns={costColumns}
                dataSource={costData}
                pagination={false}
                size="small"
              />
              <Divider style={{ margin: '12px 0' }} />
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Text strong>总成本：</Text>
                <Text strong style={{ fontSize: 18, color: '#1e3a5f' }}>¥{cost.total_cost}</Text>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 8 }}>
                <Text strong>建议零售价：</Text>
                <Text strong style={{ fontSize: 18, color: '#f39c12' }}>¥{cost.suggested_retail}</Text>
              </div>
            </Card>
          )}

          <Card 
            title="参与人员" 
            bordered={false} 
            style={{ boxShadow: '0 2px 8px rgba(0,0,0,0.06)' }}
          >
            {participants.map((role, i) => (
              <div key={i} style={{ display: 'flex', alignItems: 'center', marginBottom: 12 }}>
                <Tag color={getRoleColor(role)} style={{ marginRight: 12 }}>{role}</Tag>
                <Text>
                  {segments.filter(s => s.role === role).length} 条发言
                </Text>
              </div>
            ))}
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default MeetingDetail;

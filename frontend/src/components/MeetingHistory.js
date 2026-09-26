import React, { useState, useEffect } from 'react';
import { Card, List, Tag, Typography, Empty, Spin, Button, Space, message } from 'antd';
import { HistoryOutlined, EyeOutlined, MailOutlined, CalendarOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { getMeetings, sendEmail } from '../services/api';

const { Title, Text, Paragraph } = Typography;

const MeetingHistory = () => {
  const [meetings, setMeetings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [emailLoading, setEmailLoading] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    loadMeetings();
  }, []);

  const loadMeetings = async () => {
    try {
      const data = await getMeetings();
      setMeetings(data);
    } catch (error) {
      console.error('Failed to load meetings:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSendEmail = async (meetingId) => {
    setEmailLoading(meetingId);
    try {
      await sendEmail(meetingId, []);
      message.success('邮件已发送！');
    } catch (error) {
      message.error('发送失败：' + error.message);
    } finally {
      setEmailLoading(null);
    }
  };

  const formatDate = (dateStr) => {
    const date = new Date(dateStr);
    return date.toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    });
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

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '60px' }}>
        <Spin size="large" />
      </div>
    );
  }

  return (
    <div>
      <Title level={3} style={{ color: '#1e3a5f', marginTop: 0 }}>
        <HistoryOutlined /> 历史记录
      </Title>
      <Paragraph type="secondary">
        查看所有会议处理记录，包括转录内容、摘要和成本核算。
      </Paragraph>

      {meetings.length === 0 ? (
        <Empty description="暂无会议记录" />
      ) : (
        <List
          itemLayout="vertical"
          dataSource={meetings}
          renderItem={(meeting) => (
            <List.Item
              key={meeting.id}
              style={{ 
                background: 'white', 
                borderRadius: 12, 
                padding: 24, 
                marginBottom: 16,
                boxShadow: '0 2px 8px rgba(0,0,0,0.06)'
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div style={{ flex: 1 }}>
                  <div style={{ display: 'flex', alignItems: 'center', marginBottom: 12 }}>
                    <CalendarOutlined style={{ color: '#2d5a87', marginRight: 8 }} />
                    <Text type="secondary" style={{ fontSize: 13 }}>
                      {formatDate(meeting.timestamp)}
                    </Text>
                    <Tag color="blue" style={{ marginLeft: 12 }}>
                      {meeting.audio_file}
                    </Tag>
                  </div>
                  
                  <Title level={4} style={{ color: '#1e3a5f', marginTop: 0, marginBottom: 8 }}>
                    {meeting.summary?.series_theme || '未命名系列'}
                  </Title>

                  {meeting.patterns && (
                    <div style={{ marginBottom: 12 }}>
                      <Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 4 }}>
                        识别的工艺：
                      </Text>
                      <Space wrap>
                        {meeting.patterns.tie_methods?.map((m, i) => (
                          <Tag key={i} color="geekblue">{m}</Tag>
                        ))}
                        {meeting.patterns.color_mentions?.map((c, i) => (
                          <Tag key={i} color="cyan">{c}</Tag>
                        ))}
                      </Space>
                    </div>
                  )}

                  {meeting.transcript?.segments && (
                    <div style={{ marginBottom: 12 }}>
                      <Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 4 }}>
                        参与人员：
                      </Text>
                      <Space wrap>
                        {[...new Set(meeting.transcript.segments.map(s => s.role))].map((role, i) => (
                          <Tag key={i} color={getRoleColor(role)}>{role}</Tag>
                        ))}
                      </Space>
                    </div>
                  )}

                  {meeting.summary?.cost_breakdown && (
                    <div style={{ 
                      display: 'inline-flex', 
                      alignItems: 'center', 
                      padding: '8px 16px', 
                      background: 'linear-gradient(135deg, #1e3a5f 0%, #2d5a87 100%)',
                      borderRadius: 20,
                      color: 'white'
                    }}>
                      <span style={{ marginRight: 8 }}>总成本：</span>
                      <span style={{ fontSize: 18, fontWeight: 'bold' }}>
                        ¥{meeting.summary.cost_breakdown.total_cost}
                      </span>
                      <span style={{ margin: '0 8px', opacity: 0.5 }}>|</span>
                      <span style={{ marginRight: 8 }}>建议售价：</span>
                      <span style={{ fontSize: 18, fontWeight: 'bold', color: '#ffd700' }}>
                        ¥{meeting.summary.cost_breakdown.suggested_retail}
                      </span>
                    </div>
                  )}
                </div>

                <div style={{ marginLeft: 24 }}>
                  <Space direction="vertical">
                    <Button 
                      type="primary" 
                      icon={<EyeOutlined />}
                      onClick={() => navigate(`/meeting/${meeting.id}`)}
                    >
                      查看详情
                    </Button>
                    <Button 
                      icon={<MailOutlined />}
                      loading={emailLoading === meeting.id}
                      onClick={() => handleSendEmail(meeting.id)}
                    >
                      发送邮件
                    </Button>
                  </Space>
                </div>
              </div>
            </List.Item>
          )}
        />
      )}
    </div>
  );
};

export default MeetingHistory;
